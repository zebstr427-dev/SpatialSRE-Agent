import os
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from app.agent.aiops.state import (
    IncidentState,
    create_executed_step,
    create_incident_state,
    create_tool_call_audit_record,
    utc_now_iso,
)
from app.config import Settings
from app.core.checkpoint import open_checkpoint_runtime
from app.services.aiops_service import AIOpsService

DEFAULT_TEST_DSN = "postgresql://oncall_agent:oncall_dev@127.0.0.1:5433/oncall_agent"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        checkpoint_database_url=os.getenv(
            "TEST_CHECKPOINT_DATABASE_URL",
            DEFAULT_TEST_DSN,
        ),
        checkpoint_pool_min_size=1,
        checkpoint_pool_max_size=2,
        checkpoint_pool_timeout=5,
        checkpoint_auto_setup=True,
    )


async def _planner(_state: IncidentState) -> dict[str, Any]:
    return {
        "plan": ["collect deterministic evidence"],
        "status": "running",
        "updated_at": utc_now_iso(),
    }


async def _executor(state: IncidentState) -> dict[str, Any]:
    step = state["plan"][0]
    started_at = utc_now_iso()
    result = f"evidence for {state['input']}"

    return {
        "plan": [],
        "past_steps": [
            create_executed_step(
                step,
                result,
                status="succeeded",
                started_at=started_at,
            )
        ],
        "tool_calls": [
            create_tool_call_audit_record(
                tool_call_id=f"call-{state['incident_id']}",
                tool_name="collect_deterministic_evidence",
                step=step,
                arguments={"incident_id": state["incident_id"]},
                result=result,
                status="succeeded",
                started_at=started_at,
            )
        ],
        "updated_at": utc_now_iso(),
    }


async def _replanner(state: IncidentState) -> dict[str, Any]:
    return {
        "response": f"diagnosed: {state['input']}",
        "status": "completed",
        "updated_at": utc_now_iso(),
    }


def _service(checkpointer: BaseCheckpointSaver) -> AIOpsService:
    return AIOpsService(
        checkpointer,
        planner_node=_planner,
        executor_node=_executor,
        replanner_node=_replanner,
    )


async def _consume(
    events: AsyncGenerator[dict[str, Any], None],
) -> list[dict[str, Any]]:
    return [event async for event in events]


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_incidents_survive_pool_recreation_and_remain_isolated() -> None:
    incident_a = f"integration-{uuid4()}"
    incident_b = f"integration-{uuid4()}"
    settings = _settings()

    async with open_checkpoint_runtime(settings) as first_runtime:
        first_service = _service(first_runtime.saver)
        events_a = await _consume(
            first_service.execute(
                "checkout latency",
                session_id="shared-session",
                incident_id=incident_a,
                trace_id="trace-a",
            )
        )
        events_b = await _consume(
            first_service.execute(
                "payment errors",
                session_id="shared-session",
                incident_id=incident_b,
                trace_id="trace-b",
            )
        )

        assert events_a[-1]["type"] == "complete"
        assert events_b[-1]["type"] == "complete"

    assert first_runtime.pool.closed

    async with open_checkpoint_runtime(settings) as second_runtime:
        try:
            second_service = _service(second_runtime.saver)
            state_a = await second_service.get_incident(incident_a)
            state_b = await second_service.get_incident(incident_b)

            assert state_a is not None
            assert state_b is not None
            assert state_a["input"] == "checkout latency"
            assert state_b["input"] == "payment errors"
            assert state_a["session_id"] == state_b["session_id"] == "shared-session"
            assert state_a["incident_id"] != state_b["incident_id"]
            assert state_a["past_steps"][0]["result"] != state_b["past_steps"][0]["result"]

            audit_a = state_a["tool_calls"][0]
            audit_b = state_b["tool_calls"][0]

            assert audit_a["tool_call_id"] == f"call-{incident_a}"
            assert audit_b["tool_call_id"] == f"call-{incident_b}"
            assert audit_a["tool_name"] == "collect_deterministic_evidence"
            assert audit_b["tool_name"] == "collect_deterministic_evidence"
            assert audit_a["step"] == "collect deterministic evidence"
            assert audit_b["step"] == "collect deterministic evidence"
            assert audit_a["arguments"] == {"incident_id": incident_a}
            assert audit_b["arguments"] == {"incident_id": incident_b}
            assert audit_a["result"] == "evidence for checkout latency"
            assert audit_b["result"] == "evidence for payment errors"
            assert audit_a["status"] == audit_b["status"] == "succeeded"
            assert isinstance(audit_a["started_at"], str)
            assert isinstance(audit_a["finished_at"], str)
            assert isinstance(audit_b["started_at"], str)
            assert isinstance(audit_b["finished_at"], str)
        finally:
            await second_runtime.saver.adelete_thread(incident_a)
            await second_runtime.saver.adelete_thread(incident_b)


def _resumable_graph(
    checkpointer: BaseCheckpointSaver,
    run_counts: dict[str, int],
    *,
    pause_after_collection: bool,
):
    async def collect_evidence(state: IncidentState) -> dict[str, Any]:
        run_counts["collect"] += 1
        return {
            "evidence": [
                {
                    "evidence_id": "metric-1",
                    "source_type": "metric",
                    "source": "prometheus",
                    "content": f"cpu=95 for {state['incident_id']}",
                    "collected_at": utc_now_iso(),
                }
            ],
            "status": "running",
            "updated_at": utc_now_iso(),
        }

    async def finish_diagnosis(state: IncidentState) -> dict[str, Any]:
        run_counts["finish"] += 1
        return {
            "response": f"recovered with {len(state['evidence'])} evidence item",
            "status": "completed",
            "updated_at": utc_now_iso(),
        }

    workflow = StateGraph(IncidentState)
    workflow.add_node("collect_evidence", collect_evidence)
    workflow.add_node("finish_diagnosis", finish_diagnosis)
    workflow.set_entry_point("collect_evidence")
    workflow.add_edge("collect_evidence", "finish_diagnosis")
    workflow.add_edge("finish_diagnosis", END)
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["collect_evidence"] if pause_after_collection else None,
    )


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_interrupted_graph_resumes_without_repeating_completed_node() -> None:
    incident_id = f"integration-{uuid4()}"
    settings = _settings()
    config = {"configurable": {"thread_id": incident_id}}
    run_counts = {"collect": 0, "finish": 0}

    async with open_checkpoint_runtime(settings) as first_runtime:
        first_graph = _resumable_graph(
            first_runtime.saver,
            run_counts,
            pause_after_collection=True,
        )
        await first_graph.ainvoke(
            create_incident_state(
                "resume checkout incident",
                session_id="session-resume",
                incident_id=incident_id,
                trace_id="trace-resume",
            ),
            config,
        )
        paused = await first_graph.aget_state(config)

        assert paused.next == ("finish_diagnosis",)
        assert paused.values["evidence"][0]["source"] == "prometheus"
        assert run_counts == {"collect": 1, "finish": 0}

    assert first_runtime.pool.closed

    async with open_checkpoint_runtime(settings) as second_runtime:
        try:
            second_graph = _resumable_graph(
                second_runtime.saver,
                run_counts,
                pause_after_collection=False,
            )
            await second_graph.ainvoke(None, config)
            completed = await second_graph.aget_state(config)

            assert completed.next == ()
            assert completed.values["status"] == "completed"
            assert completed.values["response"] == "recovered with 1 evidence item"
            assert completed.values["evidence"][0]["content"].startswith("cpu=95")
            assert run_counts == {"collect": 1, "finish": 1}
        finally:
            await second_runtime.saver.adelete_thread(incident_id)
