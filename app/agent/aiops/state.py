"""Typed, serializable state for the durable AIOps workflow."""

import json
import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, NotRequired, TypedDict
from uuid import uuid4

from app.agent.identity import AgentIdentity, default_agent_identity

IncidentSeverity = Literal["critical", "high", "medium", "low", "unknown"]
IncidentStatus = Literal["pending", "running", "completed", "failed"]
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
    incident_id: str
    trace_id: str
    session_id: str
    identity: dict[str, object]
    severity: IncidentSeverity
    plan: list[str]
    past_steps: Annotated[list[ExecutedStep], operator.add]
    evidence: Annotated[list[EvidenceRecord], operator.add]
    tool_calls: Annotated[list[ToolCallAuditRecord], operator.add]
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
    identity: AgentIdentity | None = None,
) -> IncidentState:
    """Create a complete initial state using checkpoint-safe primitive values."""

    timestamp = utc_now_iso()
    resolved_identity = identity or default_agent_identity()
    return {
        "input": user_input,
        "incident_id": incident_id or str(uuid4()),
        "trace_id": trace_id or uuid4().hex,
        "session_id": session_id,
        "identity": resolved_identity.to_record(),
        "severity": severity,
        "plan": [],
        "past_steps": [],
        "evidence": [],
        "tool_calls": [],
        "response": "",
        "status": "pending",
        "error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


# Temporary compatibility alias for callers migrated in later lessons.
PlanExecuteState = IncidentState
