import pytest

from app.agent.aiops.router import (
    assess_evidence_confidence,
    evidence_assessor,
    incident_router,
    select_initial_strategy,
)
from app.agent.aiops.state import create_incident_state


@pytest.mark.parametrize("strategy", ["simple", "enterprise"])
def test_explicit_strategy_overrides_router(strategy: str) -> None:
    state = create_incident_state(
        "diagnose",
        strategy=strategy,
        alert={"severity": "critical", "affected_services": ["a", "b"]},
    )

    selected, reasons = select_initial_strategy(state)

    assert selected == strategy
    assert reasons == [f"forced_{strategy}"]


@pytest.mark.parametrize(
    ("alert", "reason"),
    [
        ({"severity": "critical", "service": "checkout"}, "critical_severity"),
        (
            {"severity": "medium", "affected_services": ["checkout", "payment"]},
            "multiple_affected_services",
        ),
        (
            {"severity": "high", "service": "checkout", "recent_change": True},
            "high_severity_recent_change",
        ),
        (
            {"severity": "medium", "requires_graph_analysis": True},
            "graph_analysis_requested",
        ),
    ],
)
def test_auto_routes_structurally_complex_incidents_to_enterprise(
    alert: dict[str, object],
    reason: str,
) -> None:
    selected, reasons = select_initial_strategy(
        create_incident_state("diagnose", strategy="auto", alert=alert)
    )

    assert selected == "enterprise"
    assert reason in reasons


@pytest.mark.asyncio
async def test_auto_prefers_simple_for_incomplete_low_severity_incident() -> None:
    update = await incident_router(
        create_incident_state(
            "intermittent timeout",
            strategy="auto",
            alert={"severity": "medium", "service": "checkout"},
        )
    )

    assert update["selected_strategy"] == "simple"
    assert update["routing_history"][0]["reason_codes"] == ["simple_first"]


def test_evidence_score_matches_documented_boundaries() -> None:
    state = create_incident_state("diagnose", strategy="auto")
    state.update(
        runbook_id="cpu-high",
        evidence=[
            {
                "evidence_id": "metric-1",
                "source_type": "metric",
                "source": "prometheus",
                "content": "cpu=95",
                "collected_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "evidence_id": "log-1",
                "source_type": "log",
                "source": "cls",
                "content": "worker exhausted",
                "collected_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "evidence_id": "change-1",
                "source_type": "change",
                "source": "deployment",
                "content": "deploy v2",
                "collected_at": "2026-01-01T00:00:00+00:00",
            },
        ],
        tool_calls=[
            {"status": "succeeded"},
            {"status": "succeeded"},
        ],
        response="Root cause [evidence:metric-1]",
    )

    assert assess_evidence_confidence(state) == 1.0


@pytest.mark.asyncio
async def test_auto_escalates_once_and_preserves_completed_evidence() -> None:
    state = create_incident_state("diagnose", strategy="auto")
    state.update(
        selected_strategy="simple",
        plan=["unfinished"],
        response="weak conclusion",
        evidence=[
            {
                "evidence_id": "metric-1",
                "source_type": "metric",
                "source": "prometheus",
                "content": "cpu=95",
                "collected_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )

    update = await evidence_assessor(state)

    assert update["selected_strategy"] == "enterprise"
    assert update["escalation_count"] == 1
    assert update["plan"] == []
    assert update["response"] == ""
    assert state["evidence"][0]["evidence_id"] == "metric-1"

    state.update(update)
    second = await evidence_assessor(state)
    assert "escalation_count" not in second
    assert second["status"] == "completed"


@pytest.mark.asyncio
async def test_forced_simple_never_escalates() -> None:
    state = create_incident_state("diagnose", strategy="simple")
    state["selected_strategy"] = "simple"

    update = await evidence_assessor(state)

    assert update["status"] == "completed"
    assert "selected_strategy" not in update
