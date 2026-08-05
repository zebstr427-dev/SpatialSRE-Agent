"""Durable human-approval contracts and LangGraph interrupt node."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field

from app.agent.tool_risk import ToolRiskLevel


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    approved: bool
    decided_by: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=1000)

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    incident_id: str
    identity_id: str
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    risk_level: ToolRiskLevel
    policy_decision_id: str
    status: ApprovalStatus
    requested_at: str
    decided_at: str | None = None
    decided_by: str | None = None
    reason: str | None = None

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def create_approval_request(
    *,
    incident_id: str,
    identity_id: str,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    risk_level: ToolRiskLevel,
    policy_decision_id: str,
) -> ApprovalRequest:
    try:
        json.dumps(arguments)
    except (TypeError, ValueError) as exc:
        raise ValueError("approval arguments must be JSON-serializable") from exc
    return ApprovalRequest(
        request_id=uuid4().hex,
        incident_id=incident_id,
        identity_id=identity_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=dict(arguments),
        risk_level=risk_level,
        policy_decision_id=policy_decision_id,
        status=ApprovalStatus.PENDING,
        requested_at=datetime.now(UTC).isoformat(),
    )


def resolve_approval_request(
    request: ApprovalRequest,
    decision: ApprovalDecision,
) -> ApprovalRequest:
    if request.status is not ApprovalStatus.PENDING:
        raise ValueError("approval request is already resolved")
    return request.model_copy(
        update={
            "status": (
                ApprovalStatus.APPROVED
                if decision.approved
                else ApprovalStatus.REJECTED
            ),
            "decided_at": datetime.now(UTC).isoformat(),
            "decided_by": decision.decided_by,
            "reason": decision.reason,
        }
    )


async def approval_node(state: dict[str, Any]) -> dict[str, Any]:
    requests = list(state.get("approval_requests", []))
    pending = next(
        (
            ApprovalRequest.model_validate(item)
            for item in reversed(requests)
            if item.get("status") == ApprovalStatus.PENDING
        ),
        None,
    )
    if pending is None:
        raise ValueError("approval node requires a pending approval request")

    resumed = interrupt(
        {
            "type": "tool_approval",
            "approval": pending.to_record(),
        }
    )
    decision = ApprovalDecision.model_validate(resumed)
    resolved = resolve_approval_request(pending, decision)
    updated_requests = [
        resolved.to_record() if item["request_id"] == pending.request_id else item
        for item in requests
    ]
    return {
        "approval_requests": updated_requests,
        "approval_decision": decision.to_record(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
