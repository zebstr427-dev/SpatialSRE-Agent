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
    changes = {item["change_id"]: item for item in result["change_records"]}
    assert {"deploy-payment-v2", "config-payment-timeout"} <= changes.keys()
    assert changes["deploy-payment-v2"]["correlation_score"] > 0.8
    assert "same_service" in changes["deploy-payment-v2"]["correlation_reasons"]
    assert result["remediation"]["approval_required"] is True
    assert len(result["evidence"]) >= 3
    assert {node["id"] for node in result["graph_context"]["nodes"]} >= {
        "payment",
        "inventory",
        "incident-payment-batch",
    }
    assert "[graph:payment]" in result["graph_context"]["citations"]
    graph_evidence = next(
        item for item in result["evidence"] if item["source"] == "incident_graph"
    )
    assert "inventory" in graph_evidence["content"]
    assert "incident-payment-batch" in graph_evidence["content"]
    assert "[evidence:" in result["report"]
    assert {span["name"] for span in result["agent_spans"]} == {
        "agent.triage",
        "agent.rag",
        "agent.sre",
        "agent.change",
        "agent.report",
    }
    json.dumps(result)
