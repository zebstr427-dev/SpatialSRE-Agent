"""Typed Failure Replay cases, observations, and results."""

from pydantic import BaseModel, ConfigDict, Field


class ReplayExpected(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root_cause: str
    tool_sequence: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    report_points: tuple[str, ...] = ()


class ReplayCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    alert: dict[str, object]
    tool_responses: dict[str, dict[str, object]]
    expected: ReplayExpected
    source_directory: str


class ReplayToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class ReplayObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    root_cause: str
    tool_calls: tuple[ReplayToolCall, ...]
    evidence_ids: tuple[str, ...]
    report: str
    latency_ms: int = Field(ge=0)
    token_cost: float = Field(ge=0)


class ReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    root_cause_hit: bool
    tool_call_accuracy: float
    tool_call_f1: float
    evidence_coverage: float
    hallucination_found: bool
    latency_ms: int
    token_cost: float

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")
