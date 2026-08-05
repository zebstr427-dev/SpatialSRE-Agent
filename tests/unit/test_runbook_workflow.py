import pytest
from types import SimpleNamespace

from app.agent.aiops.planner import planner
from app.agent.aiops.state import create_incident_state


@pytest.mark.asyncio
async def test_planner_prefers_matching_runbook_without_calling_llm() -> None:
    state = create_incident_state(
        "diagnose checkout CPU",
        alert={
            "alert_name": "HighCPUUsage",
            "severity": "warning",
            "service": "checkout",
        },
    )

    result = await planner(state)

    assert result["runbook_id"] == "cpu_high_usage"
    assert result["runbook_version"] == "1.0.0"
    assert [item["tool"] for item in result["runbook_steps"]] == [
        "query_prometheus_alerts",
        "query_cpu_metrics",
        "search_log",
    ]
    assert result["plan"][0].startswith("Runbook cpu_high_usage")


@pytest.mark.asyncio
async def test_planner_falls_back_when_no_runbook_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = create_incident_state(
        "diagnose unknown alert",
        alert={"alert_name": "UnknownAlert", "severity": "info"},
    )

    async def fail_retrieval(_arguments):
        raise RuntimeError("offline")

    async def fail_gateway():
        raise RuntimeError("gateway offline")

    monkeypatch.setattr(
        "app.agent.aiops.planner.retrieve_knowledge",
        SimpleNamespace(ainvoke=fail_retrieval),
    )
    monkeypatch.setattr(
        "app.agent.aiops.planner.create_tool_gateway",
        fail_gateway,
    )

    result = await planner(state)

    assert result["runbook_id"] is None
    assert result["runbook_steps"] == []
    assert result["plan"]
