import json

import pytest

from app.demo import run_enterprise_demo


@pytest.mark.asyncio
async def test_enterprise_demo_covers_runbook_change_graph_evidence_and_agentops() -> None:
    result = await run_enterprise_demo()

    assert result["status"] == "completed"
    assert result["runbook_id"] == "cpu_high_usage"
    assert result["root_cause"]["summary"] == (
        "batch worker exhausted thread pool after payment v2 rollout"
    )
    assert result["remediation"]["approval_required"] is True
    assert len(result["evidence"]) >= 3
    assert "[evidence:" in result["report"]
    assert {span["name"] for span in result["agent_spans"]} == {
        "agent.triage",
        "agent.rag",
        "agent.sre",
        "agent.change",
        "agent.report",
    }
    json.dumps(result)
