import json

import pytest

from app.agent.approval import (
    ApprovalDecision,
    ApprovalStatus,
    create_approval_request,
    resolve_approval_request,
)
from app.agent.tool_risk import ToolRiskLevel


def test_approval_request_binds_identity_tool_and_arguments() -> None:
    request = create_approval_request(
        incident_id="incident-456",
        identity_id="checkout-operator",
        tool_call_id="call-restart",
        tool_name="restart_service",
        arguments={"service": "checkout", "dry_run": True},
        risk_level=ToolRiskLevel.WRITE,
        policy_decision_id="decision-123",
    )

    assert request.status is ApprovalStatus.PENDING
    assert request.tool_call_id == "call-restart"
    assert request.arguments["service"] == "checkout"
    json.dumps(request.to_record())


def test_approval_resolution_is_terminal_and_attributable() -> None:
    request = create_approval_request(
        incident_id="incident-456",
        identity_id="checkout-operator",
        tool_call_id="call-restart",
        tool_name="restart_service",
        arguments={"service": "checkout"},
        risk_level=ToolRiskLevel.WRITE,
        policy_decision_id="decision-123",
    )
    approved = resolve_approval_request(
        request,
        ApprovalDecision(
            approved=True,
            decided_by="sre.lead",
            reason="change window confirmed",
        ),
    )

    assert approved.status is ApprovalStatus.APPROVED
    assert approved.decided_by == "sre.lead"
    assert approved.decided_at

    with pytest.raises(ValueError, match="already resolved"):
        resolve_approval_request(
            approved,
            ApprovalDecision(approved=False, decided_by="sre.lead"),
        )
