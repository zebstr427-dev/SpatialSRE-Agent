"""Deterministic retrieval and citation metrics."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    context_precision: float
    context_recall: float
    citation_coverage: float
    faithfulness: float


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_retrieval(
    *,
    retrieved_ids: list[str],
    relevant_ids: set[str],
    report: str,
    supported_claims: int,
    total_claims: int,
) -> RetrievalMetrics:
    retrieved_relevant = set(retrieved_ids) & relevant_ids
    cited_ids = set(re.findall(r"\[doc:([^\]]+)\]", report))
    return RetrievalMetrics(
        context_precision=_ratio(len(retrieved_relevant), len(retrieved_ids)),
        context_recall=_ratio(len(retrieved_relevant), len(relevant_ids)),
        citation_coverage=_ratio(
            len(cited_ids & retrieved_relevant),
            len(retrieved_relevant),
        ),
        faithfulness=_ratio(supported_claims, total_claims),
    )
