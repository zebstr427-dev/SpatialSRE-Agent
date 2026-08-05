import json
from pathlib import Path

import pytest

from app.replay import (
    ReplayObservation,
    ReplaySimulator,
    evaluate_replay,
    load_replay_case,
    write_replay_report,
)


def test_project_replay_case_loads_isolated_fixed_tool_data() -> None:
    root = Path(__file__).resolve().parents[2]
    case = load_replay_case(root / "incident_cases" / "cpu_high_usage")

    assert case.case_id == "cpu_high_usage"
    assert case.alert["alert_name"] == "HighCPUUsage"
    assert case.tool_responses["query_cpu_metrics"]["cpu_percent"] == 99
    assert case.expected.root_cause == "batch worker exhausted thread pool"


@pytest.mark.asyncio
async def test_simulator_uses_fixed_tools_and_records_sequence() -> None:
    root = Path(__file__).resolve().parents[2]
    case = load_replay_case(root / "incident_cases" / "cpu_high_usage")

    async def workflow(replay_case, toolbox):
        metrics = await toolbox.invoke("query_cpu_metrics", {"service": "payment"})
        logs = await toolbox.invoke("search_log", {"service": "payment"})
        return ReplayObservation(
            root_cause="batch worker exhausted thread pool",
            tool_calls=tuple(toolbox.calls),
            evidence_ids=("metric-cpu", "log-thread-pool"),
            report=(
                f"CPU {metrics['cpu_percent']} and {logs['error_code']} "
                "[evidence:metric-cpu] [evidence:log-thread-pool]"
            ),
            latency_ms=120,
            token_cost=0.002,
        )

    observation = await ReplaySimulator().run(case, workflow)

    assert [item.tool_name for item in observation.tool_calls] == [
        "query_cpu_metrics",
        "search_log",
    ]
    assert observation.tool_calls[0].arguments == {"service": "payment"}


def test_replay_metrics_detect_tool_accuracy_evidence_and_hallucinations(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    case = load_replay_case(root / "incident_cases" / "cpu_high_usage")
    observation = ReplayObservation.model_validate(
        {
            "root_cause": "batch worker exhausted thread pool",
            "tool_calls": [
                {"tool_name": "query_cpu_metrics", "arguments": {}},
                {"tool_name": "search_log", "arguments": {}},
            ],
            "evidence_ids": ["metric-cpu", "log-thread-pool"],
            "report": (
                "Root cause [evidence:metric-cpu] "
                "[evidence:invented]"
            ),
            "latency_ms": 120,
            "token_cost": 0.002,
        }
    )

    result = evaluate_replay(case, observation)
    report_path = write_replay_report([result], tmp_path / "report.json")

    assert result.root_cause_hit is True
    assert result.tool_call_f1 == 1.0
    assert result.evidence_coverage == 1.0
    assert result.hallucination_found is True
    assert json.loads(report_path.read_text(encoding="utf-8"))[0]["case_id"] == (
        "cpu_high_usage"
    )
