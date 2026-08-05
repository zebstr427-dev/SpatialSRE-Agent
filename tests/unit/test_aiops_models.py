import pytest
from pydantic import ValidationError

from app.models.aiops import AIOpsRequest


def test_aiops_request_uses_default_session_id() -> None:
    request = AIOpsRequest()

    assert request.session_id == "default"
    assert request.incident_id is None
    assert request.identity.identity_id == "oncall-observer"


def test_aiops_request_preserves_explicit_session_id() -> None:
    request = AIOpsRequest(session_id="session-123", incident_id="incident-456")

    assert request.session_id == "session-123"
    assert request.incident_id == "incident-456"


def test_aiops_request_accepts_agent_identity() -> None:
    request = AIOpsRequest(
        identity={
            "identity_id": "checkout-operator",
            "role": "operator",
            "tool_scope": ["query_*"],
            "service_scope": ["checkout"],
            "risk_ceiling": "write",
        }
    )

    assert request.identity.identity_id == "checkout-operator"
    assert request.identity.to_record()["risk_ceiling"] == "write"


def test_aiops_request_rejects_empty_incident_id() -> None:
    with pytest.raises(ValidationError):
        AIOpsRequest(incident_id="")
