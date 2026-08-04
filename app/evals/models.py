from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class IncidentEvalCase(BaseModel):
    """One version-controlled incident evaluation case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    incident_id: NonEmptyText
    alert: NonEmptyText
    metrics: str
    logs: str
    change_records: str
    gold_root_cause: NonEmptyText
    gold_actions: tuple[NonEmptyText, ...] = Field(min_length=1)
    expected_report_points: tuple[NonEmptyText, ...] = Field(min_length=1)


class CaseEvalResult(BaseModel):
    """Metrics and observed trace for one incident case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    incident_id: str
    expected_tools: tuple[str, ...]
    observed_tools: tuple[str, ...]
    matched_calls: int
    precision: float
    recall: float
    f1: float
    exact_match: bool
    succeeded_calls: int
    failed_calls: int
    tool_success_rate: float


class EvalReport(BaseModel):
    """JSON-serializable aggregate evaluation report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_cases: int
    exact_match_cases: int
    exact_match_rate: float
    expected_calls: int
    observed_calls: int
    matched_calls: int
    precision: float
    recall: float
    f1: float
    succeeded_calls: int
    failed_calls: int
    tool_success_rate: float
    failed_case_ids: tuple[str, ...]
    cases: tuple[CaseEvalResult, ...]
