import json

import pytest

from app.demo import run_enterprise_demo


@pytest.mark.asyncio
async def test_enterprise_demo_covers_runbook_change_graph_evidence_and_agentops() -> None:
    result = await run_enterprise_demo()

    assert result["status"] in {"completed", "completed_with_partial_results"}
    assert result["runbook_id"] == "cpu_high_usage"
    assert result["root_cause"]["summary"]
    assert result["remediation"]["approval_required"] is False
    assert len(result["evidence"]) >= 1
    assert {node["id"] for node in result["graph_context"]["nodes"]} >= {
        "service:data-sync-service",
        "database:primary-postgres",
        "incident:data-sync-cpu-2025",
    }
    assert "[graph:service:data-sync-service]" in result["graph_context"]["citations"]
    graph_evidence = next(
        item for item in result["evidence"] if item["source"] == "incident_graph_snapshot"
    )
    assert "data-sync-service" in graph_evidence["content"]
    assert "[evidence:" in result["response"]
    if result["status"] == "completed_with_partial_results":
        assert result["provider_failures"]
    assert {span["name"] for span in result["agent_spans"]} == {
        "agent.triage",
        "agent.rag",
        "agent.sre",
        "agent.change",
        "agent.report",
    }
    json.dumps(result)
