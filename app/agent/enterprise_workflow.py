"""Structured in-project multi-agent incident workflow."""

from __future__ import annotations

import asyncio
import operator
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from app.agent.evidence import bind_report_to_evidence, validate_incident_input
from app.change_intelligence import correlate_changes, default_change_repository
from app.incident_graph import GraphEdge, GraphNode, NetworkXIncidentGraph
from app.incident_graph.graphrag import GraphRAGRetriever
from app.observability import finish_agent_span, start_agent_span
from app.retrieval.hybrid import DocumentChunk, HybridRetriever
from app.runbooks import RunbookRegistry

RoleStatus = Literal["succeeded", "failed"]


class RoleOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    status: RoleStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: tuple[dict[str, Any], ...] = ()
    started_at: str
    finished_at: str
    latency_ms: int = Field(ge=0)
    error: str | None = None

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


RoleHandler = Callable[[dict[str, Any]], Awaitable[RoleOutput]]


class AgentRoleRunner:
    def __init__(
        self,
        role: str,
        handler: RoleHandler,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.role = role
        self.handler = handler
        self.timeout_seconds = timeout_seconds

    async def invoke(
        self,
        state: Mapping[str, Any],
    ) -> tuple[RoleOutput, dict[str, object]]:
        started_at = datetime.now(UTC).isoformat()
        started = perf_counter()
        span_manager, span = start_agent_span(
            f"agent.{self.role}",
            {
                "incident_id": state.get("incident_id"),
                "trace_id": state.get("trace_id"),
                "role": self.role,
            },
        )
        error = None
        try:
            output = await asyncio.wait_for(
                self.handler(dict(state)),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            error = "agent timeout"
            output = self._failed_output(started_at, error, started)
        except Exception as exc:
            error = str(exc)
            output = self._failed_output(started_at, error, started)
        latency_ms = max(int((perf_counter() - started) * 1000), 0)
        tokens = int(output.data.get("tokens", 0))
        token_cost = float(output.data.get("token_cost", 0.0))
        span_record = finish_agent_span(
            span,
            span_manager,
            name=f"agent.{self.role}",
            incident_id=str(state.get("incident_id", "")),
            trace_id=str(state.get("trace_id", "")),
            started_at=started_at,
            latency_ms=latency_ms,
            success=output.status == "succeeded",
            error=error,
            model=(str(output.data["model"]) if output.data.get("model") else None),
            tokens=tokens,
            token_cost=token_cost,
        )
        return output, span_record

    def _failed_output(
        self,
        started_at: str,
        error: str,
        started: float,
    ) -> RoleOutput:
        return RoleOutput(
            role=self.role,
            status="failed",
            summary=f"{self.role} failed",
            error=error,
            started_at=started_at,
            finished_at=datetime.now(UTC).isoformat(),
            latency_ms=max(int((perf_counter() - started) * 1000), 0),
        )


class EnterpriseState(TypedDict):
    input: str
    incident_id: str
    trace_id: str
    alert: dict[str, object]
    severity: str
    affected_services: list[str]
    runbook_id: str | None
    runbook_steps: list[dict[str, object]]
    role_outputs: Annotated[list[dict[str, object]], operator.add]
    evidence: Annotated[list[dict[str, object]], operator.add]
    change_records: Annotated[list[dict[str, object]], operator.add]
    graph_context: dict[str, object]
    root_cause: dict[str, object] | None
    remediation: dict[str, object] | None
    report: str
    status: str
    agent_spans: Annotated[list[dict[str, object]], operator.add]
    cost_metrics: dict[str, object]


class EnterpriseIncidentWorkflow:
    def __init__(
        self,
        *,
        agents: Mapping[str, AgentRoleRunner] | None = None,
    ) -> None:
        self.agents = dict(agents or build_default_agents())
        required = {"triage", "rag", "sre", "change", "report"}
        missing = required - self.agents.keys()
        if missing:
            raise ValueError(f"missing enterprise agents: {sorted(missing)}")
        self.graph = self._build_graph()

    async def _run_role(
        self,
        role: str,
        state: EnterpriseState,
    ) -> tuple[RoleOutput, dict[str, object]]:
        return await self.agents[role].invoke(state)

    def _build_graph(self):
        workflow = StateGraph(EnterpriseState)

        async def triage(state: EnterpriseState) -> dict[str, Any]:
            output, span = await self._run_role("triage", state)
            service = output.data.get("service")
            return {
                "role_outputs": [output.to_record()],
                "agent_spans": [span],
                "severity": str(output.data.get("severity", "unknown")),
                "affected_services": [str(service)] if service else [],
            }

        async def rag(state: EnterpriseState) -> dict[str, Any]:
            output, span = await self._run_role("rag", state)
            return {
                "role_outputs": [output.to_record()],
                "agent_spans": [span],
                "runbook_id": output.data.get("runbook_id"),
                "runbook_steps": list(output.data.get("runbook_steps", [])),
                "graph_context": dict(output.data.get("graph_context", {})),
                "evidence": list(output.evidence),
            }

        async def sre(state: EnterpriseState) -> dict[str, Any]:
            output, span = await self._run_role("sre", state)
            return {
                "role_outputs": [output.to_record()],
                "agent_spans": [span],
                "evidence": list(output.evidence),
            }

        async def change(state: EnterpriseState) -> dict[str, Any]:
            output, span = await self._run_role("change", state)
            return {
                "role_outputs": [output.to_record()],
                "agent_spans": [span],
                "change_records": list(
                    output.data.get("correlated_changes", [])
                ),
                "evidence": list(output.evidence),
            }

        async def root_cause(state: EnterpriseState) -> dict[str, Any]:
            outputs = {item["role"]: item for item in state["role_outputs"]}
            sre_data = dict(outputs.get("sre", {}).get("data", {}))
            hint = str(sre_data.get("root_cause_hint", "insufficient evidence"))
            changes = state.get("change_records", [])
            summary = hint
            if changes and hint != "insufficient evidence":
                versioned_change = next(
                    (
                        item
                        for item in changes
                        if item.get("service") and item.get("version")
                    ),
                    None,
                )
                if versioned_change:
                    summary = (
                        f"{hint} after {versioned_change['service']} "
                        f"{versioned_change['version']} rollout"
                    )
            return {
                "root_cause": {
                    "summary": summary,
                    "confidence": 0.9 if state.get("evidence") else 0.3,
                    "evidence_ids": [
                        item["evidence_id"] for item in state.get("evidence", [])
                    ],
                }
            }

        async def remediation(state: EnterpriseState) -> dict[str, Any]:
            root = state.get("root_cause") or {}
            conclusive = root.get("summary") != "insufficient evidence"
            return {
                "remediation": {
                    "actions": [
                        "pause batch worker",
                        "rollback deployment after approval",
                    ] if conclusive else ["collect additional evidence"],
                    "risk_level": "high_risk" if conclusive else "read_only",
                    "approval_required": conclusive,
                }
            }

        async def report(state: EnterpriseState) -> dict[str, Any]:
            output, span = await self._run_role("report", state)
            raw_report = str(output.data.get("report", output.summary))
            report_text = bind_report_to_evidence(
                raw_report,
                list(state.get("evidence", [])),
            )
            all_outputs = [*state["role_outputs"], output.to_record()]
            failed = any(item["status"] == "failed" for item in all_outputs)
            all_spans = [*state["agent_spans"], span]
            return {
                "role_outputs": [output.to_record()],
                "agent_spans": [span],
                "report": report_text,
                "status": (
                    "completed_with_partial_results" if failed else "completed"
                ),
                "cost_metrics": {
                    "tokens": sum(int(item.get("tokens", 0)) for item in all_spans),
                    "token_cost": sum(
                        float(item.get("token_cost", 0.0)) for item in all_spans
                    ),
                    "agent_latency_ms": sum(
                        int(item.get("latency_ms", 0)) for item in all_spans
                    ),
                },
            }

        workflow.add_node("triage", triage)
        workflow.add_node("rag", rag)
        workflow.add_node("sre", sre)
        workflow.add_node("change", change)
        workflow.add_node("root_cause", root_cause)
        workflow.add_node("remediation", remediation)
        workflow.add_node("report", report)
        workflow.add_edge(START, "triage")
        workflow.add_edge("triage", "rag")
        workflow.add_edge("rag", "sre")
        workflow.add_edge("rag", "change")
        workflow.add_edge("sre", "root_cause")
        workflow.add_edge("change", "root_cause")
        workflow.add_edge("root_cause", "remediation")
        workflow.add_edge("remediation", "report")
        workflow.add_edge("report", END)
        return workflow.compile()

    async def run(
        self,
        user_input: str,
        *,
        alert: dict[str, object],
        incident_id: str | None = None,
        trace_id: str | None = None,
    ) -> EnterpriseState:
        safe_input = validate_incident_input(user_input, max_chars=10_000)
        initial: EnterpriseState = {
            "input": safe_input,
            "incident_id": incident_id or str(uuid4()),
            "trace_id": trace_id or uuid4().hex,
            "alert": dict(alert),
            "severity": "unknown",
            "affected_services": [],
            "runbook_id": None,
            "runbook_steps": [],
            "role_outputs": [],
            "evidence": [],
            "change_records": [],
            "graph_context": {},
            "root_cause": None,
            "remediation": None,
            "report": "",
            "status": "running",
            "agent_spans": [],
            "cost_metrics": {},
        }
        return await self.graph.ainvoke(initial)


def _role_output(
    role: str,
    summary: str,
    *,
    data: dict[str, Any] | None = None,
    evidence: tuple[dict[str, Any], ...] = (),
) -> RoleOutput:
    now = datetime.now(UTC).isoformat()
    return RoleOutput(
        role=role,
        status="succeeded",
        summary=summary,
        data=data or {},
        evidence=evidence,
        started_at=now,
        finished_at=now,
        latency_ms=0,
    )


def build_default_agents() -> dict[str, AgentRoleRunner]:
    async def triage(state: dict[str, Any]) -> RoleOutput:
        alert = state["alert"]
        return _role_output(
            "triage",
            "alert classified",
            data={
                "service": alert.get("service"),
                "severity": alert.get("severity", "unknown"),
                "incident_type": alert.get("alert_name", "unknown"),
                "time_window_minutes": 30,
            },
        )

    async def rag(state: dict[str, Any]) -> RoleOutput:
        alert = state["alert"]
        runbook = RunbookRegistry.default().match(
            alert_name=str(alert.get("alert_name", "")),
            severity=(str(alert["severity"]) if alert.get("severity") else None),
        )
        graph_context = _build_demo_graph_retriever().retrieve(
            str(state["input"]),
            max_hops=2,
            top_k_documents=3,
        )
        dependency_ids = [
            node.id
            for node in graph_context.nodes
            if node.type.value == "service" and node.id != alert.get("service")
        ]
        historical_incident_ids = [
            node.id
            for node in graph_context.nodes
            if node.type.value == "incident"
        ]
        evidence = (
            {
                "evidence_id": "graph-payment-context",
                "source_type": "knowledge",
                "source": "incident_graph",
                "content": (
                    f"dependencies={dependency_ids}; "
                    f"historical_incidents={historical_incident_ids}"
                ),
                "collected_at": datetime.now(UTC).isoformat(),
                "provenance": {
                    "citations": list(graph_context.citations),
                    "seed_node_ids": list(graph_context.seed_node_ids),
                },
            },
        )
        return _role_output(
            "rag",
            "runbook and history retrieved",
            data={
                "runbook_id": runbook.id if runbook else None,
                "runbook_steps": (
                    [item.to_record() for item in runbook.steps] if runbook else []
                ),
                "confidence": 0.95 if runbook else 0.2,
                "graph_context": graph_context.to_record(),
                "cited_docs": list(graph_context.citations),
            },
            evidence=evidence,
        )

    async def sre(state: dict[str, Any]) -> RoleOutput:
        service = str(state["alert"].get("service", "unknown"))
        evidence = (
            {
                "evidence_id": "metric-cpu",
                "source_type": "metric",
                "source": "query_cpu_metrics",
                "content": "cpu=99%, top_process=batch-worker",
                "collected_at": datetime.now(UTC).isoformat(),
            },
            {
                "evidence_id": "log-thread-pool",
                "source_type": "log",
                "source": "search_log",
                "content": "THREAD_POOL_EXHAUSTED batch worker rejected task",
                "collected_at": datetime.now(UTC).isoformat(),
            },
        )
        return _role_output(
            "sre",
            "metrics and logs collected",
            data={
                "service": service,
                "root_cause_hint": "batch worker exhausted thread pool",
            },
            evidence=evidence,
        )

    async def change(state: dict[str, Any]) -> RoleOutput:
        service = str(state["alert"].get("service", "unknown"))
        incident_at = datetime.fromisoformat(
            str(
                state["alert"].get("started_at")
                or datetime.now(UTC).isoformat()
            )
        )
        window = timedelta(minutes=30)
        records = default_change_repository().query(
            service=service,
            start=incident_at - window,
            end=incident_at + window,
        )
        correlated = correlate_changes(
            records,
            incident_time=incident_at,
            service=service,
            window_minutes=30,
        )
        correlated_records = []
        for item in correlated:
            record = item.change.to_record()
            record.update(
                {
                    "correlation_score": item.score,
                    "correlation_reasons": list(item.reasons),
                    "time_delta_seconds": item.time_delta_seconds,
                }
            )
            correlated_records.append(record)
        evidence = (
            {
                "evidence_id": "change-payment-correlation",
                "source_type": "change",
                "source": "query_recent_deployments",
                "content": (
                    f"correlated changes for {service}: "
                    f"{[item['change_id'] for item in correlated_records]}"
                ),
                "collected_at": datetime.now(UTC).isoformat(),
            },
        )
        return _role_output(
            "change",
            "recent changes correlated",
            data={"correlated_changes": correlated_records},
            evidence=evidence,
        )

    async def report(state: dict[str, Any]) -> RoleOutput:
        root = state.get("root_cause") or {}
        remediation = state.get("remediation") or {}
        return _role_output(
            "report",
            "report generated",
            data={
                "report": (
                    f"# Incident diagnosis\n\nRoot cause: {root.get('summary')}.\n\n"
                    f"Remediation: {remediation.get('actions')}."
                )
            },
        )

    return {
        "triage": AgentRoleRunner("triage", triage),
        "rag": AgentRoleRunner("rag", rag),
        "sre": AgentRoleRunner("sre", sre),
        "change": AgentRoleRunner("change", change),
        "report": AgentRoleRunner("report", report),
    }


def _build_demo_graph_retriever() -> GraphRAGRetriever:
    graph = NetworkXIncidentGraph()
    for node in (
        GraphNode(id="payment", type="service", name="Payment Service"),
        GraphNode(id="inventory", type="service", name="Inventory Service"),
        GraphNode(id="change-payment-v2", type="change", name="Payment v2 rollout"),
        GraphNode(
            id="incident-payment-batch",
            type="incident",
            name="Historical payment batch worker incident",
            properties={"root_cause": "thread pool exhaustion"},
        ),
    ):
        graph.upsert_node(node)
    for edge in (
        GraphEdge(source="payment", target="inventory", type="depends_on"),
        GraphEdge(source="payment", target="change-payment-v2", type="changed_by"),
        GraphEdge(
            source="incident-payment-batch",
            target="payment",
            type="affects",
        ),
    ):
        graph.add_edge(edge)
    documents = [
        DocumentChunk(
            chunk_id="cpu-high-usage-runbook",
            content=(
                "Payment CPU diagnosis: inspect batch worker thread pool, "
                "logs, metrics, and rollout evidence."
            ),
            source="runbooks/cpu_high_usage.yaml",
            service="payment",
            fault_type="cpu_high_usage",
            version="1.0.0",
        )
    ]
    return GraphRAGRetriever(
        graph,
        documents=documents,
        hybrid_retriever=HybridRetriever(documents),
    )
