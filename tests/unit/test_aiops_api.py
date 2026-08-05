from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.identity import AgentIdentity
from app.api.aiops import router


class FakeAIOpsService:
    def __init__(self) -> None:
        self.diagnose_calls: list[dict[str, Any]] = []
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
        identity: AgentIdentity | None = None,
        alert: dict[str, object] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        self.diagnose_calls.append(
            {
                "session_id": session_id,
                "incident_id": incident_id,
                "trace_id": trace_id,
                "identity": identity,
                "alert": alert,
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

    async def resolve_approval(
        self,
        incident_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "incident_id": incident_id,
            "approval_requests": [
                {
                    "status": "approved" if approved else "rejected",
                    "decided_by": decided_by,
                    "reason": reason,
                }
            ],
        }


class FakeEnterpriseWorkflow:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(
        self,
        user_input: str,
        *,
        alert: dict[str, object],
        incident_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "user_input": user_input,
                "alert": alert,
                "incident_id": incident_id,
                "trace_id": trace_id,
            }
        )
        return {
            "incident_id": incident_id,
            "trace_id": trace_id,
            "status": "completed",
            "root_cause": {"summary": "thread pool exhaustion"},
        }


def _client(service: FakeAIOpsService) -> TestClient:
    app = FastAPI()
    app.state.aiops_service = service
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _enterprise_client(workflow: FakeEnterpriseWorkflow | None) -> TestClient:
    app = FastAPI()
    if workflow is not None:
        app.state.enterprise_workflow = workflow
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_diagnose_forwards_incident_id_to_service() -> None:
    service = FakeAIOpsService()

    response = _client(service).post(
        "/api/aiops",
        json={
            "session_id": "session-123",
            "incident_id": "incident-456",
            "identity": {
                "identity_id": "checkout-operator",
                "role": "operator",
                "tool_scope": ["query_*"],
                "service_scope": ["checkout"],
                "risk_ceiling": "write",
            },
        },
    )

    assert response.status_code == 200
    assert service.diagnose_calls[0]["session_id"] == "session-123"
    assert service.diagnose_calls[0]["incident_id"] == "incident-456"
    assert service.diagnose_calls[0]["trace_id"]
    assert service.diagnose_calls[0]["identity"].identity_id == "checkout-operator"
    assert '"incident_id": "incident-456"' in response.text


def test_get_incident_returns_persisted_state() -> None:
    response = _client(FakeAIOpsService()).get("/api/incidents/incident-456")

    assert response.status_code == 200
    assert response.json()["incident_id"] == "incident-456"


def test_get_incident_returns_404_for_unknown_id() -> None:
    response = _client(FakeAIOpsService()).get("/api/incidents/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}


def test_resolve_incident_approval() -> None:
    response = _client(FakeAIOpsService()).post(
        "/api/incidents/incident-456/approval",
        json={
            "approved": True,
            "decided_by": "sre.lead",
            "reason": "change window confirmed",
        },
    )

    assert response.status_code == 200
    assert response.json()["approval_requests"][0]["status"] == "approved"


def test_run_enterprise_incident_workflow() -> None:
    workflow = FakeEnterpriseWorkflow()

    response = _enterprise_client(workflow).post(
        "/api/enterprise/incidents",
        json={
            "input": "diagnose payment CPU",
            "incident_id": "incident-enterprise-1",
            "trace_id": "trace-enterprise-1",
            "alert": {
                "alert_name": "HighCPUUsage",
                "severity": "warning",
                "service": "payment",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert workflow.calls == [
        {
            "user_input": "diagnose payment CPU",
            "incident_id": "incident-enterprise-1",
            "trace_id": "trace-enterprise-1",
            "alert": {
                "alert_name": "HighCPUUsage",
                "severity": "warning",
                "service": "payment",
            },
        }
    ]


def test_enterprise_incident_returns_503_when_runtime_is_missing() -> None:
    response = _enterprise_client(None).post(
        "/api/enterprise/incidents",
        json={
            "input": "diagnose payment CPU",
            "alert": {"alert_name": "HighCPUUsage", "service": "payment"},
        },
    )

    assert response.status_code == 503
