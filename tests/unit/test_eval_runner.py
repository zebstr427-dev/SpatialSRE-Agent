import json
from collections.abc import Sequence

import pytest

from app.agent.aiops.state import ToolCallAuditRecord, ToolCallStatus
from app.evals.models import IncidentEvalCase
from app.evals.runner import run_evaluation, write_eval_report


def _case(
    incident_id: str,
    gold_actions: Sequence[str],
) -> IncidentEvalCase:
    return IncidentEvalCase(
        incident_id=incident_id,
        alert="service alert",
        metrics="metric evidence",
        logs="log evidence",
        change_records="no change",
        gold_root_cause="resource saturation",
        gold_actions=tuple(gold_actions),
        expected_report_points=("resource saturation",),
    )


def _audit(
    tool_name: str,
    *,
    status: ToolCallStatus = "succeeded",
) -> ToolCallAuditRecord:
    return {
        "tool_call_id": f"call-{tool_name}-{status}",
        "tool_name": tool_name,
        "step": "collect evidence",
        "arguments": {},
        "result": "evidence" if status == "succeeded" else "timeout",
        "status": status,
        "started_at": "2026-08-03T01:00:00+00:00",
        "finished_at": "2026-08-03T01:00:01+00:00",
    }


def test_run_evaluation_computes_selection_and_status_metrics() -> None:
    cases = [
        _case("case_exact", ["query_prometheus_alerts", "retrieve_knowledge"]),
        _case("case_partial", ["query_prometheus_alerts", "retrieve_knowledge"]),
    ]
    observed = {
        "case_exact": [
            _audit("retrieve_knowledge"),
            _audit("query_prometheus_alerts"),
        ],
        "case_partial": [
            _audit("query_prometheus_alerts"),
            _audit("query_prometheus_alerts", status="failed"),
        ],
    }
    visited: list[str] = []

    def execute_case(case: IncidentEvalCase) -> list[ToolCallAuditRecord]:
        visited.append(case.incident_id)
        return observed[case.incident_id]

    report = run_evaluation(cases, execute_case)

    assert visited == ["case_exact", "case_partial"]
    assert report.total_cases == 2
    assert report.exact_match_cases == 1
    assert report.exact_match_rate == pytest.approx(0.5)
    assert report.expected_calls == 4
    assert report.observed_calls == 4
    assert report.matched_calls == 3
    assert report.precision == pytest.approx(0.75)
    assert report.recall == pytest.approx(0.75)
    assert report.f1 == pytest.approx(0.75)
    assert report.tool_success_rate == pytest.approx(0.75)
    assert report.failed_case_ids == ("case_partial",)
    assert json.loads(report.model_dump_json())["matched_calls"] == 3


def test_run_evaluation_rejects_empty_case_list() -> None:
    with pytest.raises(ValueError, match="at least one incident case"):
        run_evaluation([], lambda _case: [])


def test_run_evaluation_identifies_executor_failure() -> None:
    def failing_executor(
        _case: IncidentEvalCase,
    ) -> list[ToolCallAuditRecord]:
        raise TimeoutError("simulated timeout")

    with pytest.raises(
        RuntimeError,
        match="evaluation failed for incident case_error",
    ) as exc_info:
        run_evaluation([_case("case_error", ["retrieve_knowledge"])], failing_executor)

    assert isinstance(exc_info.value.__cause__, TimeoutError)


def test_write_eval_report_creates_utf8_json(tmp_path) -> None:
    report = run_evaluation(
        [_case("case_report", ["retrieve_knowledge"])],
        lambda _case: [_audit("retrieve_knowledge")],
    )
    destination = tmp_path / "nested" / "report.json"

    written_path = write_eval_report(report, destination)

    assert written_path == destination
    assert destination.read_text(encoding="utf-8").endswith("\n")
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["total_cases"] == 1
    assert payload["exact_match_rate"] == 1.0
