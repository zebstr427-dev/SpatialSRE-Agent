import asyncio
import json
from time import perf_counter

import pytest

from app.agent.enterprise_workflow import (
    AgentRoleRunner,
    EnterpriseIncidentWorkflow,
    RoleOutput,
)


def _output(role: str, *, data: dict | None = None) -> RoleOutput:
    return RoleOutput(
        role=role,
        status="succeeded",
        summary=f"{role} complete",
        data=data or {},
        evidence=(),
        started_at="2026-08-05T01:00:00+00:00",
        finished_at="2026-08-05T01:00:01+00:00",
        latency_ms=1000,
    )


@pytest.mark.asyncio
async def test_sre_and_change_agents_run_in_parallel_and_join() -> None:
    started: list[str] = []
    both_started = asyncio.Event()

    async def triage(_state):
        return _output(
            "triage",
            data={"service": "payment", "severity": "warning"},
        )

    async def rag(_state):
        return _output("rag", data={"runbook_id": "cpu_high_usage"})

    async def parallel(role: str):
        started.append(role)
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=0.5)
        data = (
            {"root_cause_hint": "thread pool exhaustion"}
            if role == "sre"
            else {"correlated_changes": [{"change_id": "deploy-v2"}]}
        )
        return _output(role, data=data)

    async def report(_state):
        return _output("report", data={"report": "diagnosis"})

    agents = {
        "triage": AgentRoleRunner("triage", triage),
        "rag": AgentRoleRunner("rag", rag),
        "sre": AgentRoleRunner("sre", lambda state: parallel("sre")),
        "change": AgentRoleRunner("change", lambda state: parallel("change")),
        "report": AgentRoleRunner("report", report),
    }
    workflow = EnterpriseIncidentWorkflow(agents=agents)

    state = await asyncio.wait_for(
        workflow.run(
            "diagnose payment CPU",
            alert={
                "alert_name": "HighCPUUsage",
                "severity": "warning",
                "service": "payment",
            },
        ),
        timeout=1,
    )

    assert set(started) == {"sre", "change"}
    assert state["root_cause"]["summary"] == "thread pool exhaustion"
    assert state["status"] == "completed"
    assert {item["role"] for item in state["role_outputs"]} == {
        "triage",
        "rag",
        "sre",
        "change",
        "report",
    }
    assert len(state["agent_spans"]) == 5
    json.dumps(state)


@pytest.mark.asyncio
async def test_agent_failure_is_isolated_and_partial_evidence_reaches_report() -> None:
    async def ok(role: str, data: dict | None = None):
        return _output(role, data=data)

    async def broken(_state):
        raise RuntimeError("change provider unavailable")

    agents = {
        "triage": AgentRoleRunner(
            "triage",
            lambda state: ok("triage", {"service": "payment"}),
        ),
        "rag": AgentRoleRunner("rag", lambda state: ok("rag")),
        "sre": AgentRoleRunner(
            "sre",
            lambda state: ok(
                "sre",
                {"root_cause_hint": "CPU saturation"},
            ),
        ),
        "change": AgentRoleRunner("change", broken),
        "report": AgentRoleRunner(
            "report",
            lambda state: ok("report", {"report": "partial diagnosis"}),
        ),
    }

    state = await EnterpriseIncidentWorkflow(agents=agents).run(
        "diagnose payment CPU",
        alert={"alert_name": "HighCPUUsage", "service": "payment"},
    )

    change = next(
        item for item in state["role_outputs"] if item["role"] == "change"
    )
    assert change["status"] == "failed"
    assert "change provider unavailable" in change["error"]
    assert state["root_cause"]["summary"] == "CPU saturation"
    assert state["status"] == "completed_with_partial_results"


@pytest.mark.asyncio
async def test_role_runner_enforces_timeout_and_records_agentops_span() -> None:
    async def slow(_state):
        await asyncio.sleep(0.1)
        return _output("sre")

    started = perf_counter()
    output, span = await AgentRoleRunner("sre", slow, timeout_seconds=0.01).invoke(
        {"incident_id": "incident-1", "trace_id": "trace-1"}
    )

    assert perf_counter() - started < 0.08
    assert output.status == "failed"
    assert output.error == "agent timeout"
    assert span["name"] == "agent.sre"
    assert span["success"] is False
    assert span["incident_id"] == "incident-1"
