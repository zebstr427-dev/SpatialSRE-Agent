"""Typed, serializable state for the durable AIOps workflow."""

import json
import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, NotRequired, TypedDict
from uuid import uuid4

from app.agent.identity import AgentIdentity, default_agent_identity

IncidentSeverity = Literal["critical", "high", "medium", "low", "unknown"]
IncidentStatus = Literal[
    "pending",
    "running",
    "completed",
    "completed_with_partial_results",
    "failed",
]
DiagnosisStrategy = Literal["auto", "simple", "enterprise"]
StepStatus = Literal["succeeded", "failed"]
ToolCallStatus = Literal["succeeded", "failed"]
EvidenceSourceType = Literal["metric", "log", "knowledge", "change", "tool"]


class ExecutedStep(TypedDict):
    """One completed execution step stored in checkpoint history."""

    step: str
    result: str
    status: StepStatus
    started_at: str
    finished_at: str


class EvidenceRecord(TypedDict):
    """A traceable fact collected while diagnosing an incident."""

    evidence_id: str
    source_type: EvidenceSourceType
    source: str
    content: str
    collected_at: str
    tool_call_id: NotRequired[str]
    provenance: NotRequired[dict[str, object]]


class ToolCallAuditRecord(TypedDict):
    """One completed tool invocation stored for audit and replay."""

    tool_call_id: str
    tool_name: str
    step: str
    arguments: dict[str, object]
    result: str
    status: ToolCallStatus
    started_at: str
    finished_at: str
    identity_id: NotRequired[str]
    risk_level: NotRequired[str]
    dry_run: NotRequired[bool]


class IncidentState(TypedDict):
    """Shared state persisted after each LangGraph superstep."""

    input: str
    workflow_version: str
    incident_id: str
    trace_id: str
    session_id: str
    identity: dict[str, object]
    alert: dict[str, object]
    severity: IncidentSeverity
    requested_strategy: DiagnosisStrategy
    selected_strategy: Literal["simple", "enterprise"] | None
    routing_history: Annotated[list[dict[str, object]], operator.add]
    diagnosis_confidence: float
    escalation_count: int
    provider_failures: Annotated[list[dict[str, object]], operator.add]
    execute_remediation: bool
    runbook_id: str | None
    runbook_version: str | None
    runbook_steps: list[dict[str, object]]
    plan: list[str]
    past_steps: Annotated[list[ExecutedStep], operator.add]
    evidence: Annotated[list[EvidenceRecord], operator.add]
    tool_calls: Annotated[list[ToolCallAuditRecord], operator.add]
    policy_decisions: Annotated[list[dict[str, object]], operator.add]
    change_records: Annotated[list[dict[str, object]], operator.add]
    affected_services: list[str]
    graph_context: dict[str, object]
    root_cause: dict[str, object] | None
    remediation: dict[str, object] | None
    role_outputs: Annotated[list[dict[str, object]], operator.add]
    agent_spans: Annotated[list[dict[str, object]], operator.add]
    cost_metrics: dict[str, object]
    pending_tool_calls: list[dict[str, object]]
    approval_requests: list[dict[str, object]]
    approval_decision: dict[str, object] | None
    response: str
    status: IncidentStatus
    error: str | None
    created_at: str
    updated_at: str


def utc_now_iso() -> str:
    """Return an RFC 3339-compatible UTC timestamp."""

    return datetime.now(UTC).isoformat()


def create_tool_call_audit_record(
    tool_call_id: str,
    tool_name: str,
    step: str,
    arguments: dict[str, object],
    result: str,
    *,
    status: ToolCallStatus,
    started_at: str,
    finished_at: str | None = None,
    identity_id: str | None = None,
    risk_level: str | None = None,
    dry_run: bool | None = None,
) -> ToolCallAuditRecord:
    """Build a structured tool invocation record for checkpoint history."""

    try:
        json.dumps(arguments)
    except (TypeError, ValueError) as exc:
        raise ValueError("arguments must be JSON-serializable") from exc

    record: ToolCallAuditRecord = {
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "step": step,
        "arguments": arguments,
        "result": result,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at or utc_now_iso(),
    }
    if identity_id is not None:
        record["identity_id"] = identity_id
    if risk_level is not None:
        record["risk_level"] = risk_level
    if dry_run is not None:
        record["dry_run"] = dry_run
    return record


def create_executed_step(
    step: str,
    result: str,
    *,
    status: StepStatus,
    started_at: str,
    finished_at: str | None = None,
) -> ExecutedStep:
    """Build a structured execution record for checkpoint history."""

    return {
        "step": step,
        "result": result,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at or utc_now_iso(),
    }


def create_incident_state(
    user_input: str,
    *,
    session_id: str = "default",
    incident_id: str | None = None,
    trace_id: str | None = None,
    severity: IncidentSeverity = "unknown",
    strategy: DiagnosisStrategy = "auto",
    execute_remediation: bool = False,
    identity: AgentIdentity | None = None,
    alert: dict[str, object] | None = None,
) -> IncidentState:
    """Create a complete initial state using checkpoint-safe primitive values."""

    timestamp = utc_now_iso()
    resolved_identity = identity or default_agent_identity()
    return {
        "input": user_input,
        "workflow_version": "2",
        "incident_id": incident_id or str(uuid4()),
        "trace_id": trace_id or uuid4().hex,
        "session_id": session_id,
        "identity": resolved_identity.to_record(),
        "alert": dict(alert or {}),
        "severity": severity,
        "requested_strategy": strategy,
        "selected_strategy": None,
        "routing_history": [],
        "diagnosis_confidence": 0.0,
        "escalation_count": 0,
        "provider_failures": [],
        "execute_remediation": execute_remediation,
        "runbook_id": None,
        "runbook_version": None,
        "runbook_steps": [],
        "plan": [],
        "past_steps": [],
        "evidence": [],
        "tool_calls": [],
        "policy_decisions": [],
        "change_records": [],
        "affected_services": [],
        "graph_context": {},
        "root_cause": None,
        "remediation": None,
        "role_outputs": [],
        "agent_spans": [],
        "cost_metrics": {},
        "pending_tool_calls": [],
        "approval_requests": [],
        "approval_decision": None,
        "response": "",
        "status": "pending",
        "error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


# Temporary compatibility alias for callers migrated in later lessons.
PlanExecuteState = IncidentState
