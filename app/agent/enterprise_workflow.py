"""Structured enterprise roles embedded in the durable incident runtime."""

from __future__ import annotations

import ast
import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph
from pydantic import BaseModel, ConfigDict, Field

from app.agent.aiops.state import (
    IncidentState,
    ToolCallAuditRecord,
    create_incident_state,
    create_tool_call_audit_record,
    utc_now_iso,
)
from app.agent.evidence import (
    bind_report_to_evidence,
    create_tool_evidence,
    validate_incident_input,
)
from app.agent.identity import AgentIdentity
from app.agent.tool_gateway import ToolExecutionResult, ToolGateway, create_tool_gateway
from app.change_intelligence import ChangeRecord, correlate_changes
from app.incident_graph import NetworkXIncidentGraph
from app.incident_graph.graphrag import GraphRAGRetriever
from app.observability import finish_agent_span, start_agent_span
from app.retrieval.hybrid import DocumentChunk, HybridRetriever
from app.runbooks import RunbookRegistry

RoleStatus = Literal["succeeded", "failed"]
GatewayFactory = Callable[..., Awaitable[ToolGateway]]

NODE_ENTERPRISE_TRIAGE = "enterprise_triage"
NODE_ENTERPRISE_RAG = "enterprise_rag"
NODE_ENTERPRISE_SRE = "enterprise_sre"
NODE_ENTERPRISE_CHANGE = "enterprise_change"
NODE_ENTERPRISE_ROOT_CAUSE = "enterprise_root_cause"
NODE_ENTERPRISE_REMEDIATION = "enterprise_remediation"
NODE_ENTERPRISE_REPORT = "enterprise_report"


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
    def __init__(self, role: str, handler: RoleHandler, *, timeout_seconds: float = 15.0) -> None:
        self.role = role
        self.handler = handler
        self.timeout_seconds = timeout_seconds

    async def invoke(self, state: Mapping[str, Any]) -> tuple[RoleOutput, dict[str, object]]:
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
            output = await asyncio.wait_for(self.handler(dict(state)), timeout=self.timeout_seconds)
        except TimeoutError:
            error = "agent timeout"
            output = self._failed_output(started_at, error, started)
        except Exception as exc:
            error = str(exc)
            output = self._failed_output(started_at, error, started)
        latency_ms = max(int((perf_counter() - started) * 1000), 0)
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
            model=str(output.data["model"]) if output.data.get("model") else None,
            tokens=int(output.data.get("tokens", 0)),
            token_cost=float(output.data.get("token_cost", 0.0)),
        )
        return output, span_record

    def _failed_output(self, started_at: str, error: str, started: float) -> RoleOutput:
        return RoleOutput(
            role=self.role,
            status="failed",
            summary=f"{self.role} failed",
            error=error,
            data={"provider_failures": [{"provider": self.role, "error": error}]},
            started_at=started_at,
            finished_at=datetime.now(UTC).isoformat(),
            latency_ms=max(int((perf_counter() - started) * 1000), 0),
        )


# Compatibility name for callers from the enterprise-only implementation.
EnterpriseState = IncidentState


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


def _parse_output(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value


def _tool_records(
    result: ToolExecutionResult,
    *,
    step: str,
) -> tuple[ToolCallAuditRecord, dict[str, Any] | None, dict[str, object] | None]:
    audit = create_tool_call_audit_record(
        tool_call_id=result.tool_call_id,
        tool_name=result.tool_name,
        step=step,
        arguments=dict(result.arguments),
        result=result.output,
        status=result.status,
        started_at=result.started_at,
        finished_at=result.finished_at,
        identity_id=result.identity_id,
        risk_level=result.risk_level.value,
        dry_run=result.dry_run,
    )
    evidence = None
    if result.status == "succeeded":
        decision = result.policy_decision or {}
        evidence = create_tool_evidence(
            tool_call_id=result.tool_call_id,
            tool_name=result.tool_name,
            arguments=dict(result.arguments),
            output=result.output,
            identity_id=result.identity_id,
            risk_level=result.risk_level.value,
            dry_run=result.dry_run,
            started_at=result.started_at,
            finished_at=result.finished_at,
            policy_decision_id=(
                str(decision["decision_id"]) if decision.get("decision_id") else None
            ),
        )
    return audit, evidence, result.policy_decision


def load_default_graph_retriever() -> GraphRAGRetriever | None:
    """Load a versioned graph snapshot; never construct request-time demo facts."""

    path = Path(__file__).resolve().parents[2] / "data" / "incident_graph.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    graph = NetworkXIncidentGraph.from_record(dict(payload.get("graph", {})))
    documents = [DocumentChunk.model_validate(item) for item in payload.get("documents", [])]
    return GraphRAGRetriever(
        graph, documents=documents, hybrid_retriever=HybridRetriever(documents)
    )


def build_default_agents(
    *,
    gateway_factory: GatewayFactory = create_tool_gateway,
    graph_retriever: GraphRAGRetriever | None = None,
) -> dict[str, AgentRoleRunner]:
    async def triage(state: dict[str, Any]) -> RoleOutput:
        alert = state.get("alert", {})
        services = list(state.get("affected_services", []))
        service = alert.get("service")
        if service and service not in services:
            services.append(str(service))
        return _role_output(
            "triage",
            "alert classified",
            data={
                "service": service,
                "affected_services": services,
                "severity": alert.get("severity", state.get("severity", "unknown")),
                "incident_type": alert.get("alert_name", "unknown"),
                "time_window_minutes": 30,
            },
        )

    async def rag(state: dict[str, Any]) -> RoleOutput:
        alert = state.get("alert", {})
        runbook = RunbookRegistry.default().match(
            alert_name=str(alert.get("alert_name", "")),
            severity=str(alert["severity"]) if alert.get("severity") else None,
        )
        evidence: list[dict[str, Any]] = []
        audits: list[dict[str, object]] = []
        decisions: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        graph_context: dict[str, object] = {}
        if graph_retriever is not None:
            context = graph_retriever.retrieve(str(state["input"]), max_hops=2)
            graph_context = context.to_record()
            if context.citations:
                evidence.append(
                    {
                        "evidence_id": f"graph-{state['incident_id']}",
                        "source_type": "knowledge",
                        "source": "incident_graph_snapshot",
                        "content": "; ".join(context.citations),
                        "collected_at": utc_now_iso(),
                        "provenance": {
                            "source": "sample",
                            "snapshot": "data/incident_graph.json",
                            "citations": list(context.citations),
                        },
                    }
                )
        else:
            failures.append({"provider": "incident_graph", "error": "snapshot unavailable"})
        try:
            gateway = await gateway_factory()
            identity = AgentIdentity.from_record(state["identity"])
            result = await gateway.invoke(
                tool_call_id=f"rag-{uuid4().hex}",
                tool_name="retrieve_knowledge",
                arguments={"query": str(state["input"])},
                identity=identity,
            )
            audit, tool_evidence, decision = _tool_records(result, step="enterprise rag")
            audits.append(audit)
            if tool_evidence:
                evidence.append(tool_evidence)
            if decision:
                decisions.append(dict(decision))
            if result.status == "failed":
                failures.append(
                    {"provider": "milvus", "error": result.error_message or result.output}
                )
        except Exception as exc:
            failures.append({"provider": "tool_gateway", "error": str(exc)})
        return _role_output(
            "rag",
            "runbook and graph context retrieved",
            data={
                "runbook_id": runbook.id if runbook else None,
                "runbook_version": runbook.version if runbook else None,
                "runbook_steps": [item.to_record() for item in runbook.steps] if runbook else [],
                "graph_context": graph_context,
                "tool_calls": audits,
                "policy_decisions": decisions,
                "provider_failures": failures,
            },
            evidence=tuple(evidence),
        )

    async def sre(state: dict[str, Any]) -> RoleOutput:
        service = str(state.get("alert", {}).get("service") or "unknown")
        identity = AgentIdentity.from_record(state["identity"])
        gateway = await gateway_factory()
        audits: list[dict[str, object]] = []
        evidence: list[dict[str, Any]] = []
        decisions: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        alert_name = str(state.get("alert", {}).get("alert_name", "")).lower()
        metric_tools = (
            ["query_cpu_metrics"]
            if "cpu" in alert_name
            else (
                ["query_memory_metrics"]
                if "memory" in alert_name
                else ["query_cpu_metrics", "query_memory_metrics"]
            )
        )
        for tool_name in metric_tools:
            result = await gateway.invoke(
                tool_call_id=f"sre-{uuid4().hex}",
                tool_name=tool_name,
                arguments={"service_name": service},
                identity=identity,
            )
            audit, item_evidence, decision = _tool_records(result, step="enterprise sre")
            audits.append(audit)
            if item_evidence:
                evidence.append(item_evidence)
            if decision:
                decisions.append(dict(decision))
            if result.status == "failed":
                failures.append(
                    {"provider": tool_name, "error": result.error_message or result.output}
                )
        topic_result = await gateway.invoke(
            tool_call_id=f"sre-topic-{uuid4().hex}",
            tool_name="search_topic_by_service_name",
            arguments={"service_name": service},
            identity=identity,
        )
        audit, item_evidence, decision = _tool_records(topic_result, step="enterprise sre")
        audits.append(audit)
        if item_evidence:
            evidence.append(item_evidence)
        if decision:
            decisions.append(dict(decision))
        if topic_result.status == "failed":
            failures.append(
                {"provider": "cls", "error": topic_result.error_message or topic_result.output}
            )
        else:
            topic_payload = _parse_output(topic_result.output)
            topics = topic_payload.get("topics", []) if isinstance(topic_payload, dict) else []
            if topics:
                end_time = int(datetime.now(UTC).timestamp() * 1000)
                log_result = await gateway.invoke(
                    tool_call_id=f"sre-log-{uuid4().hex}",
                    tool_name="search_log",
                    arguments={
                        "topic_id": str(topics[0]["topic_id"]),
                        "start_time": end_time - 30 * 60 * 1000,
                        "end_time": end_time,
                        "query": "level:ERROR",
                        "limit": 100,
                    },
                    identity=identity,
                )
                audit, item_evidence, decision = _tool_records(
                    log_result,
                    step="enterprise sre",
                )
                audits.append(audit)
                if item_evidence:
                    evidence.append(item_evidence)
                if decision:
                    decisions.append(dict(decision))
                if log_result.status == "failed":
                    failures.append(
                        {
                            "provider": "cls.search_log",
                            "error": log_result.error_message or log_result.output,
                        }
                    )
        return _role_output(
            "sre",
            "metrics and log sources queried",
            data={
                "service": service,
                "root_cause_hint": (
                    "monitoring and log evidence indicates service resource saturation"
                    if evidence
                    else "insufficient evidence"
                ),
                "tool_calls": audits,
                "policy_decisions": decisions,
                "provider_failures": failures,
            },
            evidence=tuple(evidence),
        )

    async def change(state: dict[str, Any]) -> RoleOutput:
        alert = state.get("alert", {})
        service = str(alert.get("service") or "unknown")
        incident_at = datetime.fromisoformat(str(alert.get("started_at") or utc_now_iso()))
        window = timedelta(minutes=30)
        identity = AgentIdentity.from_record(state["identity"])
        gateway = await gateway_factory()
        records: list[ChangeRecord] = []
        audits: list[dict[str, object]] = []
        evidence: list[dict[str, Any]] = []
        decisions: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        for tool_name in (
            "query_recent_deployments",
            "query_config_changes",
            "query_git_commits",
            "query_k8s_rollout_history",
        ):
            result = await gateway.invoke(
                tool_call_id=f"change-{uuid4().hex}",
                tool_name=tool_name,
                arguments={
                    "service": service,
                    "start": (incident_at - window).isoformat(),
                    "end": (incident_at + window).isoformat(),
                },
                identity=identity,
            )
            audit, item_evidence, decision = _tool_records(result, step="enterprise change")
            audits.append(audit)
            if item_evidence:
                evidence.append(item_evidence)
            if decision:
                decisions.append(dict(decision))
            if result.status == "failed":
                failures.append(
                    {"provider": tool_name, "error": result.error_message or result.output}
                )
                continue
            payload = _parse_output(result.output)
            if isinstance(payload, list):
                known = {item.change_id for item in records}
                for item in payload:
                    try:
                        record = ChangeRecord.model_validate(item)
                    except Exception:
                        continue
                    if record.change_id not in known:
                        records.append(record)
                        known.add(record.change_id)
        correlated = correlate_changes(
            records, incident_time=incident_at, service=service, window_minutes=30
        )
        correlated_records = []
        for item in correlated:
            record = item.change.to_record()
            record.update(
                correlation_score=item.score,
                correlation_reasons=list(item.reasons),
                time_delta_seconds=item.time_delta_seconds,
                provenance={"source": "registered_change_provider"},
            )
            correlated_records.append(record)
        return _role_output(
            "change",
            "recent changes queried and correlated",
            data={
                "correlated_changes": correlated_records,
                "tool_calls": audits,
                "policy_decisions": decisions,
                "provider_failures": failures,
            },
            evidence=tuple(evidence),
        )

    async def report(state: dict[str, Any]) -> RoleOutput:
        root = state.get("root_cause") or {}
        remediation = state.get("remediation") or {}
        response = (
            "# Incident diagnosis\n\n"
            f"Root cause: {root.get('summary', 'insufficient evidence')}.\n\n"
            f"Confidence: {float(root.get('confidence', 0)):.2f}.\n\n"
            f"Remediation: {remediation.get('actions', ['collect additional evidence'])}."
        )
        return _role_output("report", "report generated", data={"report": response})

    return {
        "triage": AgentRoleRunner("triage", triage),
        "rag": AgentRoleRunner("rag", rag),
        "sre": AgentRoleRunner("sre", sre),
        "change": AgentRoleRunner("change", change),
        "report": AgentRoleRunner("report", report),
    }


class EnterpriseIncidentWorkflow:
    """Enterprise role collection used by the single durable parent graph."""

    def __init__(
        self,
        *,
        agents: Mapping[str, AgentRoleRunner] | None = None,
        gateway_factory: GatewayFactory = create_tool_gateway,
        graph_retriever: GraphRAGRetriever | None = None,
    ) -> None:
        resolved_graph = (
            graph_retriever if graph_retriever is not None else load_default_graph_retriever()
        )
        self.agents = dict(
            agents
            or build_default_agents(gateway_factory=gateway_factory, graph_retriever=resolved_graph)
        )
        missing = {"triage", "rag", "sre", "change", "report"} - self.agents.keys()
        if missing:
            raise ValueError(f"missing enterprise agents: {sorted(missing)}")

    async def _run_role(
        self, role: str, state: IncidentState
    ) -> tuple[RoleOutput, dict[str, object]]:
        return await self.agents[role].invoke(state)

    @staticmethod
    def _role_update(output: RoleOutput, span: dict[str, object]) -> dict[str, Any]:
        return {
            "role_outputs": [output.to_record()],
            "agent_spans": [span],
            "evidence": list(output.evidence),
            "tool_calls": list(output.data.get("tool_calls", [])),
            "policy_decisions": list(output.data.get("policy_decisions", [])),
            "provider_failures": list(output.data.get("provider_failures", [])),
        }

    async def triage_node(self, state: IncidentState) -> dict[str, Any]:
        output, span = await self._run_role("triage", state)
        update = self._role_update(output, span)
        update.update(
            severity=str(output.data.get("severity", "unknown")),
            affected_services=[str(item) for item in output.data.get("affected_services", [])],
        )
        return update

    async def rag_node(self, state: IncidentState) -> dict[str, Any]:
        output, span = await self._run_role("rag", state)
        update = self._role_update(output, span)
        update.update(
            runbook_id=output.data.get("runbook_id"),
            runbook_version=output.data.get("runbook_version"),
            runbook_steps=list(output.data.get("runbook_steps", [])),
            graph_context=dict(output.data.get("graph_context", {})),
        )
        return update

    async def sre_node(self, state: IncidentState) -> dict[str, Any]:
        output, span = await self._run_role("sre", state)
        return self._role_update(output, span)

    async def change_node(self, state: IncidentState) -> dict[str, Any]:
        output, span = await self._run_role("change", state)
        update = self._role_update(output, span)
        update["change_records"] = list(output.data.get("correlated_changes", []))
        return update

    async def root_cause_node(self, state: IncidentState) -> dict[str, Any]:
        outputs = {str(item["role"]): item for item in state.get("role_outputs", [])}
        sre_data = outputs.get("sre", {}).get("data", {})
        hint = (
            str(sre_data.get("root_cause_hint", "insufficient evidence"))
            if isinstance(sre_data, Mapping)
            else "insufficient evidence"
        )
        changes = state.get("change_records", [])
        evidence_ids = [str(item["evidence_id"]) for item in state.get("evidence", [])]
        confidence = min(0.35 + len(evidence_ids) * 0.1, 0.9) if evidence_ids else 0.2
        return {
            "root_cause": {
                "summary": hint,
                "confidence": confidence,
                "evidence_ids": evidence_ids,
                "correlated_change_id": (changes[0].get("change_id") if changes else None),
            },
            "updated_at": utc_now_iso(),
        }

    async def remediation_node(self, state: IncidentState) -> dict[str, Any]:
        root = state.get("root_cause") or {}
        conclusive = root.get("summary") != "insufficient evidence"
        service = next(iter(state.get("affected_services", [])), None)
        actions = (
            ["collect additional evidence"]
            if not conclusive
            else ["pause risky workload", "restart service after approval"]
        )
        update: dict[str, Any] = {}
        if state.get("execute_remediation") and conclusive and service:
            update.update(
                plan=[f"Controlled restart dry-run for {service}"],
                runbook_steps=[
                    {
                        "id": "controlled-restart",
                        "tool": "restart_service",
                        "arguments": {"service": service},
                        "risk_level": "write",
                    }
                ],
            )
        update.update(
            remediation={
                "actions": actions,
                "risk_level": "write" if conclusive else "read_only",
                "approval_required": bool(
                    state.get("execute_remediation") and conclusive and service
                ),
            },
            updated_at=utc_now_iso(),
        )
        return update

    async def report_node(self, state: IncidentState) -> dict[str, Any]:
        output, span = await self._run_role("report", state)
        report_text = bind_report_to_evidence(
            str(output.data.get("report", output.summary)), list(state.get("evidence", []))
        )
        all_outputs = [*state.get("role_outputs", []), output.to_record()]
        all_spans = [*state.get("agent_spans", []), span]
        degraded = bool(state.get("provider_failures")) or any(
            item.get("status") == "failed" for item in all_outputs
        )
        return {
            "role_outputs": [output.to_record()],
            "agent_spans": [span],
            "response": report_text,
            "diagnosis_confidence": float((state.get("root_cause") or {}).get("confidence", 0.0)),
            "status": "completed_with_partial_results" if degraded else "completed",
            "cost_metrics": {
                "tokens": sum(int(item.get("tokens", 0)) for item in all_spans),
                "token_cost": sum(float(item.get("token_cost", 0.0)) for item in all_spans),
                "agent_latency_ms": sum(int(item.get("latency_ms", 0)) for item in all_spans),
            },
            "updated_at": utc_now_iso(),
        }

    def register_nodes(self, workflow: StateGraph) -> None:
        workflow.add_node(NODE_ENTERPRISE_TRIAGE, self.triage_node)
        workflow.add_node(NODE_ENTERPRISE_RAG, self.rag_node)
        workflow.add_node(NODE_ENTERPRISE_SRE, self.sre_node)
        workflow.add_node(NODE_ENTERPRISE_CHANGE, self.change_node)
        workflow.add_node(NODE_ENTERPRISE_ROOT_CAUSE, self.root_cause_node)
        workflow.add_node(NODE_ENTERPRISE_REMEDIATION, self.remediation_node)
        workflow.add_node(NODE_ENTERPRISE_REPORT, self.report_node)

    async def run(
        self,
        user_input: str,
        *,
        alert: dict[str, object],
        incident_id: str | None = None,
        trace_id: str | None = None,
    ) -> IncidentState:
        initial = create_incident_state(
            validate_incident_input(user_input, max_chars=10_000),
            incident_id=incident_id,
            trace_id=trace_id,
            alert=alert,
            strategy="enterprise",
        )
        initial["selected_strategy"] = "enterprise"
        initial["status"] = "running"

        # Compatibility wrapper only. Production APIs register these nodes on
        # AIOpsService's checkpointed parent graph and never execute this path.
        state: dict[str, Any] = dict(initial)
        additive_fields = {
            "routing_history",
            "provider_failures",
            "past_steps",
            "evidence",
            "tool_calls",
            "policy_decisions",
            "change_records",
            "role_outputs",
            "agent_spans",
        }

        def apply_update(update: Mapping[str, Any]) -> None:
            for key, value in update.items():
                if key in additive_fields:
                    state[key] = [*state.get(key, []), *value]
                else:
                    state[key] = value

        apply_update(await self.triage_node(state))
        apply_update(await self.rag_node(state))
        sre_update, change_update = await asyncio.gather(
            self.sre_node(state),
            self.change_node(state),
        )
        apply_update(sre_update)
        apply_update(change_update)
        apply_update(await self.root_cause_node(state))
        apply_update(await self.remediation_node(state))
        apply_update(await self.report_node(state))
        return state  # type: ignore[return-value]
