import json
from datetime import datetime
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.agent.aiops.state import (
    EvidenceRecord,
    ExecutedStep,
    IncidentState,
    create_executed_step,
    create_incident_state,
)


def test_create_incident_state_generates_durable_defaults() -> None:
    state = create_incident_state("diagnose checkout latency", session_id="session-123")

    UUID(state["incident_id"])
    UUID(state["trace_id"])
    datetime.fromisoformat(state["created_at"])
    assert state["session_id"] == "session-123"
    assert state["severity"] == "unknown"
    assert state["status"] == "pending"
    assert state["plan"] == []
    assert state["past_steps"] == []
    assert state["evidence"] == []
    assert state["response"] == ""
    assert state["error"] is None
    assert state["created_at"] == state["updated_at"]
    json.dumps(state)


def test_create_incident_state_preserves_caller_owned_identifiers() -> None:
    state = create_incident_state(
        "diagnose checkout latency",
        session_id="session-123",
        incident_id="incident-456",
        trace_id="trace-789",
        severity="critical",
    )

    assert state["incident_id"] == "incident-456"
    assert state["trace_id"] == "trace-789"
    assert state["severity"] == "critical"


def test_create_executed_step_uses_structured_checkpoint_safe_values() -> None:
    step = create_executed_step(
        "query metrics",
        "cpu=95%",
        status="succeeded",
        started_at="2026-07-22T00:00:00+00:00",
        finished_at="2026-07-22T00:00:01+00:00",
    )

    assert step == {
        "step": "query metrics",
        "result": "cpu=95%",
        "status": "succeeded",
        "started_at": "2026-07-22T00:00:00+00:00",
        "finished_at": "2026-07-22T00:00:01+00:00",
    }
    json.dumps(step)


def test_langgraph_reducers_append_steps_and_evidence() -> None:
    timestamp = "2026-07-22T00:00:00+00:00"
    first_step: ExecutedStep = {
        "step": "query metrics",
        "result": "cpu=95%",
        "status": "succeeded",
        "started_at": timestamp,
        "finished_at": timestamp,
    }
    second_step: ExecutedStep = {
        "step": "query logs",
        "result": "timeout",
        "status": "succeeded",
        "started_at": timestamp,
        "finished_at": timestamp,
    }
    first_evidence: EvidenceRecord = {
        "evidence_id": "evidence-1",
        "source_type": "metric",
        "source": "prometheus",
        "content": "cpu=95%",
        "collected_at": timestamp,
    }
    second_evidence: EvidenceRecord = {
        "evidence_id": "evidence-2",
        "source_type": "log",
        "source": "cls",
        "content": "timeout",
        "collected_at": timestamp,
    }

    graph_builder = StateGraph(IncidentState)
    graph_builder.add_node(
        "metrics",
        lambda _state: {"past_steps": [first_step], "evidence": [first_evidence]},
    )
    graph_builder.add_node(
        "logs",
        lambda _state: {"past_steps": [second_step], "evidence": [second_evidence]},
    )
    graph_builder.add_edge(START, "metrics")
    graph_builder.add_edge("metrics", "logs")
    graph_builder.add_edge("logs", END)

    result = graph_builder.compile().invoke(create_incident_state("diagnose"))

    assert [step["step"] for step in result["past_steps"]] == ["query metrics", "query logs"]
    assert [item["evidence_id"] for item in result["evidence"]] == [
        "evidence-1",
        "evidence-2",
    ]
