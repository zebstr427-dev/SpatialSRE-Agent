import pytest
from pydantic import ValidationError

from app.models.aiops import AIOpsRequest


def test_aiops_request_uses_default_session_id() -> None:
    request = AIOpsRequest()

    assert request.session_id == "default"
    assert request.incident_id is None


def test_aiops_request_preserves_explicit_session_id() -> None:
    request = AIOpsRequest(session_id="session-123", incident_id="incident-456")

    assert request.session_id == "session-123"
    assert request.incident_id == "incident-456"


def test_aiops_request_rejects_empty_incident_id() -> None:
    with pytest.raises(ValidationError):
        AIOpsRequest(incident_id="")
