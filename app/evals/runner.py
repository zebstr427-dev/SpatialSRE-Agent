from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from app.agent.aiops.state import ToolCallAuditRecord
from app.evals.models import CaseEvalResult, EvalReport, IncidentEvalCase

CaseExecutor = Callable[
    [IncidentEvalCase],
    Sequence[ToolCallAuditRecord],
]


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate_case(
    case: IncidentEvalCase,
    tool_calls: Sequence[ToolCallAuditRecord],
) -> CaseEvalResult:
    """Compare one expected tool trace with its observed audit records."""

    expected_tools = tuple(case.gold_actions)
    observed_tools = tuple(record["tool_name"] for record in tool_calls)
    expected_counts = Counter(expected_tools)
    observed_counts = Counter(observed_tools)
    matched_calls = sum((expected_counts & observed_counts).values())

    precision = _ratio(matched_calls, len(observed_tools))
    recall = _ratio(matched_calls, len(expected_tools))
    succeeded_calls = sum(
        record["status"] == "succeeded" for record in tool_calls
    )
    failed_calls = sum(record["status"] == "failed" for record in tool_calls)

    return CaseEvalResult(
        incident_id=case.incident_id,
        expected_tools=expected_tools,
        observed_tools=observed_tools,
        matched_calls=matched_calls,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        exact_match=expected_counts == observed_counts,
        succeeded_calls=succeeded_calls,
        failed_calls=failed_calls,
        tool_success_rate=_ratio(succeeded_calls, len(tool_calls)),
    )


def run_evaluation(
    cases: Sequence[IncidentEvalCase],
    execute_case: CaseExecutor,
) -> EvalReport:
    """Execute cases sequentially and aggregate micro-averaged metrics."""

    if not cases:
        raise ValueError("evaluation requires at least one incident case")

    case_results: list[CaseEvalResult] = []
    for case in cases:
        try:
            tool_calls = execute_case(case)
        except Exception as exc:
            raise RuntimeError(
                f"evaluation failed for incident {case.incident_id}"
            ) from exc

        case_results.append(evaluate_case(case, tool_calls))

    results = tuple(case_results)
    expected_calls = sum(len(result.expected_tools) for result in results)
    observed_calls = sum(len(result.observed_tools) for result in results)
    matched_calls = sum(result.matched_calls for result in results)
    succeeded_calls = sum(result.succeeded_calls for result in results)
    failed_calls = sum(result.failed_calls for result in results)
    exact_match_cases = sum(result.exact_match for result in results)
    precision = _ratio(matched_calls, observed_calls)
    recall = _ratio(matched_calls, expected_calls)

    return EvalReport(
        total_cases=len(results),
        exact_match_cases=exact_match_cases,
        exact_match_rate=_ratio(exact_match_cases, len(results)),
        expected_calls=expected_calls,
        observed_calls=observed_calls,
        matched_calls=matched_calls,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        succeeded_calls=succeeded_calls,
        failed_calls=failed_calls,
        tool_success_rate=_ratio(succeeded_calls, observed_calls),
        failed_case_ids=tuple(
            result.incident_id
            for result in results
            if not result.exact_match
        ),
        cases=results,
    )


def write_eval_report(
    report: EvalReport,
    path: str | Path,
) -> Path:
    """Write one UTF-8 JSON report and return its path."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
