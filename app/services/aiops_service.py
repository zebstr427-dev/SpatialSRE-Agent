"""Single durable incident runtime with Simple and Enterprise strategies."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from textwrap import dedent
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from loguru import logger

from app.agent.aiops.router import (
    ENTERPRISE,
    SIMPLE,
    evidence_assessor,
    incident_router,
    route_after_evidence_assessor,
    route_after_incident_router,
)
from app.agent.aiops.state import (
    DiagnosisStrategy,
    IncidentState,
    create_incident_state,
    utc_now_iso,
)
from app.agent.enterprise_workflow import (
    NODE_ENTERPRISE_CHANGE,
    NODE_ENTERPRISE_RAG,
    NODE_ENTERPRISE_REMEDIATION,
    NODE_ENTERPRISE_REPORT,
    NODE_ENTERPRISE_ROOT_CAUSE,
    NODE_ENTERPRISE_SRE,
    NODE_ENTERPRISE_TRIAGE,
    EnterpriseIncidentWorkflow,
)
from app.agent.evidence import evidence_citations, validate_incident_input
from app.agent.identity import AgentIdentity

NODE_INCIDENT_ROUTER = "incident_router"
NODE_PLANNER = "planner"
NODE_EXECUTOR = "executor"
NODE_REPLANNER = "replanner"
NODE_APPROVAL = "approval"
NODE_EVIDENCE_ASSESSOR = "evidence_assessor"
NodeCallable = Callable[[IncidentState], Awaitable[dict[str, Any]]]


class AIOpsService:
    """Own the only checkpointed incident graph used by production APIs."""

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        *,
        planner_node: NodeCallable | None = None,
        executor_node: NodeCallable | None = None,
        replanner_node: NodeCallable | None = None,
        approval_node_callable: NodeCallable | None = None,
        enterprise_workflow: EnterpriseIncidentWorkflow | None = None,
    ) -> None:
        if planner_node is None:
            from app.agent.aiops.planner import planner as planner_node
        if executor_node is None:
            from app.agent.aiops.executor import executor as executor_node
        if replanner_node is None:
            from app.agent.aiops.replanner import replanner as replanner_node
        if approval_node_callable is None:
            from app.agent.approval import approval_node as approval_node_callable

        self.checkpointer = checkpointer
        self.planner_node = planner_node
        self.executor_node = executor_node
        self.replanner_node = replanner_node
        self.approval_node = approval_node_callable
        self.enterprise_workflow = enterprise_workflow or EnterpriseIncidentWorkflow()
        self.graph = self._build_graph()
        logger.info("Durable Incident Runtime initialized")

    def _build_graph(self):
        workflow = StateGraph(IncidentState)
        workflow.add_node(NODE_INCIDENT_ROUTER, incident_router)
        workflow.add_node(NODE_PLANNER, self.planner_node)
        workflow.add_node(NODE_EXECUTOR, self.executor_node)
        workflow.add_node(NODE_REPLANNER, self.replanner_node)
        workflow.add_node(NODE_APPROVAL, self.approval_node)
        workflow.add_node(NODE_EVIDENCE_ASSESSOR, evidence_assessor)
        self.enterprise_workflow.register_nodes(workflow)

        workflow.add_edge(START, NODE_INCIDENT_ROUTER)
        workflow.add_conditional_edges(
            NODE_INCIDENT_ROUTER,
            route_after_incident_router,
            {SIMPLE: NODE_PLANNER, ENTERPRISE: NODE_ENTERPRISE_TRIAGE},
        )
        workflow.add_edge(NODE_PLANNER, NODE_EXECUTOR)

        def after_executor(state: IncidentState) -> str:
            if state.get("pending_tool_calls") and state.get("approval_decision") is None:
                return NODE_APPROVAL
            if state.get("selected_strategy") == ENTERPRISE:
                return NODE_EXECUTOR if state.get("plan") else NODE_ENTERPRISE_REPORT
            return NODE_REPLANNER

        workflow.add_conditional_edges(
            NODE_EXECUTOR,
            after_executor,
            {
                NODE_APPROVAL: NODE_APPROVAL,
                NODE_EXECUTOR: NODE_EXECUTOR,
                NODE_REPLANNER: NODE_REPLANNER,
                NODE_ENTERPRISE_REPORT: NODE_ENTERPRISE_REPORT,
            },
        )
        # Keeping this edge and the node name preserves old approval checkpoints.
        workflow.add_edge(NODE_APPROVAL, NODE_EXECUTOR)

        def after_replanner(state: IncidentState) -> str:
            if state.get("plan") and not state.get("response"):
                return NODE_EXECUTOR
            return NODE_EVIDENCE_ASSESSOR

        workflow.add_conditional_edges(
            NODE_REPLANNER,
            after_replanner,
            {
                NODE_EXECUTOR: NODE_EXECUTOR,
                NODE_EVIDENCE_ASSESSOR: NODE_EVIDENCE_ASSESSOR,
            },
        )
        workflow.add_conditional_edges(
            NODE_EVIDENCE_ASSESSOR,
            route_after_evidence_assessor,
            {ENTERPRISE: NODE_ENTERPRISE_TRIAGE, "complete": END},
        )

        workflow.add_edge(NODE_ENTERPRISE_TRIAGE, NODE_ENTERPRISE_RAG)
        # SRE and Change run in one superstep and converge before root cause.
        workflow.add_edge(NODE_ENTERPRISE_RAG, NODE_ENTERPRISE_SRE)
        workflow.add_edge(NODE_ENTERPRISE_RAG, NODE_ENTERPRISE_CHANGE)
        workflow.add_edge(NODE_ENTERPRISE_SRE, NODE_ENTERPRISE_ROOT_CAUSE)
        workflow.add_edge(NODE_ENTERPRISE_CHANGE, NODE_ENTERPRISE_ROOT_CAUSE)
        workflow.add_edge(NODE_ENTERPRISE_ROOT_CAUSE, NODE_ENTERPRISE_REMEDIATION)

        def after_remediation(state: IncidentState) -> str:
            return NODE_EXECUTOR if state.get("plan") else NODE_ENTERPRISE_REPORT

        workflow.add_conditional_edges(
            NODE_ENTERPRISE_REMEDIATION,
            after_remediation,
            {
                NODE_EXECUTOR: NODE_EXECUTOR,
                NODE_ENTERPRISE_REPORT: NODE_ENTERPRISE_REPORT,
            },
        )
        workflow.add_edge(NODE_ENTERPRISE_REPORT, END)
        return workflow.compile(checkpointer=self.checkpointer)

    @staticmethod
    def _config(incident_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": incident_id}}

    async def execute(
        self,
        user_input: str,
        session_id: str = "default",
        *,
        incident_id: str | None = None,
        trace_id: str | None = None,
        identity: AgentIdentity | None = None,
        alert: dict[str, object] | None = None,
        strategy: DiagnosisStrategy = "simple",
        execute_remediation: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute one incident and emit a stable event stream.

        The programmatic compatibility default remains ``simple``; both HTTP
        request models explicitly default to ``auto``.
        """

        safe_input = validate_incident_input(user_input)
        initial_state = create_incident_state(
            safe_input,
            session_id=session_id,
            incident_id=incident_id,
            trace_id=trace_id,
            identity=identity,
            alert=alert,
            strategy=strategy,
            execute_remediation=execute_remediation,
        )
        resolved_incident_id = initial_state["incident_id"]
        resolved_trace_id = initial_state["trace_id"]
        sequence = 0

        def enrich(event: dict[str, Any]) -> dict[str, Any]:
            nonlocal sequence
            sequence += 1
            return {
                **event,
                "incident_id": resolved_incident_id,
                "trace_id": resolved_trace_id,
                "sequence": sequence,
                "timestamp": utc_now_iso(),
            }

        config_dict = self._config(resolved_incident_id)
        logger.info(
            "[incident={}] starting strategy={} input={}",
            resolved_incident_id,
            strategy,
            safe_input,
        )
        try:
            async for event in self.graph.astream(
                input=initial_state,
                config=config_dict,
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    formatted = self._format_node_event(node_name, node_output)
                    if formatted is not None:
                        yield enrich(formatted)

            snapshot = await self.graph.aget_state(config_dict)
            values = dict(snapshot.values or {})
            pending = next(
                (
                    item
                    for item in reversed(values.get("approval_requests", []))
                    if item.get("status") == "pending"
                ),
                None,
            )
            if pending is not None:
                yield enrich(
                    {
                        "type": "approval_required",
                        "stage": "approval",
                        "message": "工具调用等待人工审批",
                        "approval": pending,
                        "selected_strategy": values.get("selected_strategy"),
                    }
                )
                return

            evidence = list(values.get("evidence", []))
            yield enrich(
                {
                    "type": "complete",
                    "stage": "complete",
                    "message": "任务执行完成",
                    "response": values.get("response", ""),
                    "status": values.get("status", "completed"),
                    "selected_strategy": values.get("selected_strategy"),
                    "diagnosis_confidence": values.get("diagnosis_confidence", 0.0),
                    "provider_failures": values.get("provider_failures", []),
                    "routing_history": values.get("routing_history", []),
                    "evidence": evidence,
                    "citations": evidence_citations(evidence),
                }
            )
        except Exception as exc:
            logger.exception("[incident={}] execution failed", resolved_incident_id)
            yield enrich({"type": "error", "stage": "error", "message": f"任务执行出错: {exc}"})

    async def execute_to_state(
        self,
        user_input: str,
        session_id: str = "default",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run through the shared graph and return its persisted state."""

        resolved_incident_id = kwargs.get("incident_id")
        terminal_event: dict[str, Any] | None = None
        async for terminal_event in self.execute(user_input, session_id, **kwargs):
            if resolved_incident_id is None:
                resolved_incident_id = terminal_event.get("incident_id")
        if resolved_incident_id is None:
            raise RuntimeError("incident runtime did not create an incident id")
        if terminal_event and terminal_event.get("type") == "error":
            raise RuntimeError(str(terminal_event.get("message", "incident runtime failed")))
        state = await self.get_incident(str(resolved_incident_id))
        if state is None:
            raise RuntimeError("incident state was not persisted")
        return state

    async def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        snapshot = await self.graph.aget_state(self._config(incident_id))
        if not snapshot.values:
            return None
        values = dict(snapshot.values)
        # v1 checkpoints are interpreted as Simple without a database migration.
        values.setdefault("workflow_version", "1")
        values.setdefault("requested_strategy", "simple")
        values.setdefault("selected_strategy", "simple")
        values.setdefault("routing_history", [])
        values.setdefault("diagnosis_confidence", 0.0)
        values.setdefault("escalation_count", 0)
        values.setdefault("provider_failures", [])
        values.setdefault("execute_remediation", False)
        return values

    async def resolve_approval(
        self,
        incident_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        config_dict = self._config(incident_id)
        snapshot = await self.graph.aget_state(config_dict)
        if not snapshot.values:
            raise KeyError("incident not found")
        pending = [
            item
            for item in snapshot.values.get("approval_requests", [])
            if item.get("status") == "pending"
        ]
        if not pending:
            raise ValueError("incident has no pending approval")
        await self.graph.ainvoke(
            Command(resume={"approved": approved, "decided_by": decided_by, "reason": reason}),
            config=config_dict,
        )
        resolved = await self.graph.aget_state(config_dict)
        return dict(resolved.values)

    async def diagnose(
        self,
        session_id: str = "default",
        *,
        user_input: str | None = None,
        incident_id: str | None = None,
        trace_id: str | None = None,
        identity: AgentIdentity | None = None,
        alert: dict[str, object] | None = None,
        strategy: DiagnosisStrategy = "auto",
        execute_remediation: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        aiops_task = user_input or dedent("""\
            诊断当前系统是否存在告警；基于工具返回的真实证据分析根因，
            明确标注失败的查询，并输出 Markdown 告警分析报告和处理建议。
            严禁编造没有证据支持的指标、日志或变更。
            """).strip()
        async for event in self.execute(
            aiops_task,
            session_id,
            incident_id=incident_id,
            trace_id=trace_id,
            identity=identity,
            alert=alert,
            strategy=strategy,
            execute_remediation=execute_remediation,
        ):
            if event.get("type") == "complete":
                yield {
                    **event,
                    "stage": "diagnosis_complete",
                    "message": "诊断流程完成",
                    "diagnosis": {
                        "status": event.get("status", "completed"),
                        "report": event.get("response", ""),
                    },
                }
            else:
                yield event

    def _format_node_event(
        self,
        node_name: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if node_name == NODE_INCIDENT_ROUTER:
            history = list((state or {}).get("routing_history", []))
            decision = history[-1] if history else {}
            return {
                "type": "routing",
                "stage": "incident_router",
                "message": "诊断策略已选择",
                "selected_strategy": (state or {}).get("selected_strategy"),
                "routing": decision,
            }
        if node_name == NODE_PLANNER:
            return self._format_planner_event(state)
        if node_name == NODE_EXECUTOR:
            return self._format_executor_event(state)
        if node_name == NODE_REPLANNER:
            return self._format_replanner_event(state)
        if node_name == NODE_EVIDENCE_ASSESSOR:
            escalated = (state or {}).get("selected_strategy") == ENTERPRISE
            return {
                "type": "escalation" if escalated else "status",
                "stage": "evidence_assessor",
                "message": "证据不足，升级到企业多 Agent" if escalated else "证据评估完成",
                "diagnosis_confidence": (state or {}).get("diagnosis_confidence", 0.0),
                "selected_strategy": (state or {}).get("selected_strategy"),
                "routing": ((state or {}).get("routing_history") or [None])[-1],
            }
        if node_name.startswith("enterprise_"):
            role_outputs = list((state or {}).get("role_outputs", []))
            role = role_outputs[-1] if role_outputs else None
            event_type = "report" if node_name == NODE_ENTERPRISE_REPORT else "agent_update"
            return {
                "type": event_type,
                "stage": node_name,
                "message": f"{node_name} 完成",
                "agent": role,
                "provider_failures": (state or {}).get("provider_failures", []),
                "report": (state or {}).get("response", ""),
            }
        return None

    @staticmethod
    def _format_planner_event(state: dict[str, Any] | None) -> dict[str, Any]:
        plan = list((state or {}).get("plan", []))
        return {
            "type": "plan",
            "stage": "plan_created",
            "message": f"执行计划已制定，共 {len(plan)} 个步骤",
            "plan": plan,
        }

    @staticmethod
    def _format_executor_event(state: dict[str, Any] | None) -> dict[str, Any]:
        plan = list((state or {}).get("plan", []))
        past_steps = list((state or {}).get("past_steps", []))
        if not past_steps:
            return {"type": "status", "stage": "executor", "message": "开始执行步骤"}
        return {
            "type": "step_complete",
            "stage": "step_executed",
            "message": f"步骤执行完成 ({len(past_steps)}/{len(past_steps) + len(plan)})",
            "current_step": past_steps[-1].get("step"),
            "remaining_steps": len(plan),
        }

    @staticmethod
    def _format_replanner_event(state: dict[str, Any] | None) -> dict[str, Any]:
        response = (state or {}).get("response", "")
        plan = list((state or {}).get("plan", []))
        if response:
            return {
                "type": "report",
                "stage": "final_report",
                "message": "最终报告已生成",
                "report": response,
            }
        return {
            "type": "status",
            "stage": "replanner",
            "message": "评估完成",
            "remaining_steps": len(plan),
        }
