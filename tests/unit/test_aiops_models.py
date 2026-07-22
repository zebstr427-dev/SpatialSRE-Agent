from app.models.aiops import AIOpsRequest


def test_aiops_request_uses_default_session_id() -> None:
    request = AIOpsRequest()

    assert request.session_id == "default"


def test_aiops_request_preserves_explicit_session_id() -> None:
    request = AIOpsRequest(session_id="session-123")

    assert request.session_id == "session-123"
