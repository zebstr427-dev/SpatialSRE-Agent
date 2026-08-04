"""Typed, serializable state for the durable AIOps workflow."""

import json
import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, NotRequired, TypedDict
from uuid import uuid4

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


class IncidentState(TypedDict):
    """Shared state persisted after each LangGraph superstep."""

    input: str
    incident_id: str
    trace_id: str
    session_id: str
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
) -> ToolCallAuditRecord:
    """Build a structured tool invocation record for checkpoint history."""

    try:
        json.dumps(arguments)
    except (TypeError, ValueError) as exc:
        raise ValueError("arguments must be JSON-serializable") from exc

    return {
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "step": step,
        "arguments": arguments,
        "result": result,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at or utc_now_iso(),
    }


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
) -> IncidentState:
    """Create a complete initial state using checkpoint-safe primitive values."""

    timestamp = utc_now_iso()
    return {
        "input": user_input,
        "incident_id": incident_id or str(uuid4()),
        "trace_id": trace_id or uuid4().hex,
        "session_id": session_id,
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
