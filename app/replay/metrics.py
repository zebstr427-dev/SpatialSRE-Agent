"""Failure Replay quality metrics and machine-readable reports."""

import json
import re
from collections import Counter
from pathlib import Path

from app.replay.models import ReplayCase, ReplayObservation, ReplayResult


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_replay(
    case: ReplayCase,
    observation: ReplayObservation,
) -> ReplayResult:
    expected_tools = Counter(case.expected.tool_sequence)
    observed_tools = Counter(item.tool_name for item in observation.tool_calls)
    true_positive = sum((expected_tools & observed_tools).values())
    precision = _ratio(true_positive, sum(observed_tools.values()))
    recall = _ratio(true_positive, sum(expected_tools.values()))
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    expected_evidence = set(case.expected.evidence_ids)
    observed_evidence = set(observation.evidence_ids)
    cited_evidence = set(
        re.findall(r"\[evidence:([^\]]+)\]", observation.report)
    )
    expected_root = case.expected.root_cause.casefold()
    observed_root = observation.root_cause.casefold()
    return ReplayResult(
        case_id=case.case_id,
        root_cause_hit=(
            expected_root in observed_root or observed_root in expected_root
        ),
        tool_call_accuracy=precision,
        tool_call_f1=f1,
        evidence_coverage=_ratio(
            len(expected_evidence & observed_evidence),
            len(expected_evidence),
        ),
        hallucination_found=bool(cited_evidence - observed_evidence),
        latency_ms=observation.latency_ms,
        token_cost=observation.token_cost,
    )


def write_replay_report(
    results: list[ReplayResult],
    path: str | Path,
) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            [item.to_record() for item in results],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path
