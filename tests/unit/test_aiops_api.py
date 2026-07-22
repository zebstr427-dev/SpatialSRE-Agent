from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.aiops import router


class FakeAIOpsService:
    def __init__(self) -> None:
        self.diagnose_calls: list[dict[str, str | None]] = []
        self.incidents: dict[str, dict[str, Any]] = {
            "incident-456": {
                "incident_id": "incident-456",
                "session_id": "session-123",
                "status": "completed",
            }
        }

    async def diagnose(
        self,
        session_id: str = "default",
        *,
        incident_id: str | None = None,
        trace_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        self.diagnose_calls.append(
            {
                "session_id": session_id,
                "incident_id": incident_id,
                "trace_id": trace_id,
            }
        )
        yield {
            "type": "complete",
            "incident_id": incident_id,
            "trace_id": trace_id,
            "sequence": 1,
            "timestamp": "2026-07-22T00:00:00+00:00",
        }

    async def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        return self.incidents.get(incident_id)


def _client(service: FakeAIOpsService) -> TestClient:
    app = FastAPI()
    app.state.aiops_service = service
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_diagnose_forwards_incident_id_to_service() -> None:
    service = FakeAIOpsService()

    response = _client(service).post(
        "/api/aiops",
        json={"session_id": "session-123", "incident_id": "incident-456"},
    )

    assert response.status_code == 200
    assert service.diagnose_calls[0]["session_id"] == "session-123"
    assert service.diagnose_calls[0]["incident_id"] == "incident-456"
    assert service.diagnose_calls[0]["trace_id"]
    assert '"incident_id": "incident-456"' in response.text


def test_get_incident_returns_persisted_state() -> None:
    response = _client(FakeAIOpsService()).get("/api/incidents/incident-456")

    assert response.status_code == 200
    assert response.json()["incident_id"] == "incident-456"


def test_get_incident_returns_404_for_unknown_id() -> None:
    response = _client(FakeAIOpsService()).get("/api/incidents/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}
