import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.aiops.state import IncidentState, create_executed_step, utc_now_iso
from app.agent.identity import AgentIdentity, AgentRole
from app.agent.tool_risk import ToolRiskLevel
from app.services.aiops_service import AIOpsService


async def _planner(_state: IncidentState) -> dict:
    return {"plan": ["query metrics"], "status": "running", "updated_at": utc_now_iso()}


async def _executor(state: IncidentState) -> dict:
    started_at = utc_now_iso()
    return {
        "plan": state["plan"][1:],
        "past_steps": [
            create_executed_step(
                state["plan"][0],
                "cpu=95%",
                status="succeeded",
                started_at=started_at,
            )
        ],
        "updated_at": utc_now_iso(),
    }


async def _replanner(_state: IncidentState) -> dict:
    return {
        "response": "diagnosis complete",
        "status": "completed",
        "updated_at": utc_now_iso(),
    }


def _service() -> AIOpsService:
    return AIOpsService(
        InMemorySaver(),
        planner_node=_planner,
        executor_node=_executor,
        replanner_node=_replanner,
    )


@pytest.mark.asyncio
async def test_execute_uses_incident_as_thread_and_enriches_every_event() -> None:
    service = _service()
    identity = AgentIdentity(
        identity_id="checkout-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("query_*",),
        service_scope=("checkout",),
        risk_ceiling=ToolRiskLevel.WRITE,
    )

    events = [
        event
        async for event in service.execute(
            "diagnose checkout",
            session_id="session-123",
            incident_id="incident-456",
            trace_id="trace-789",
            identity=identity,
        )
    ]

    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert all(event["incident_id"] == "incident-456" for event in events)
    assert all(event["trace_id"] == "trace-789" for event in events)
    assert all(event["timestamp"] for event in events)
    assert events[-1]["type"] == "complete"
    assert events[-1]["response"] == "diagnosis complete"

    snapshot = await service.get_incident("incident-456")
    assert snapshot is not None
    assert snapshot["incident_id"] == "incident-456"
    assert snapshot["session_id"] == "session-123"
    assert snapshot["status"] == "completed"
    assert snapshot["identity"] == identity.to_record()
    assert snapshot["past_steps"][0]["step"] == "query metrics"


@pytest.mark.asyncio
async def test_get_incident_returns_none_for_unknown_thread() -> None:
    assert await _service().get_incident("missing") is None
