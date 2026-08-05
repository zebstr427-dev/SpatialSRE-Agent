"""Change records, repositories, and explainable incident correlation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ChangeType(StrEnum):
    DEPLOYMENT = "deployment"
    CONFIG = "config"
    GIT = "git"
    K8S_ROLLOUT = "k8s_rollout"
    IMAGE = "image"
    DATABASE = "database"


class ChangeRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    change_type: ChangeType
    timestamp: datetime
    environment: str = "production"
    summary: str = Field(min_length=1)
    version: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class CorrelatedChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    change: ChangeRecord
    score: float = Field(ge=0, le=1)
    reasons: tuple[str, ...]
    time_delta_seconds: float

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class ChangeRepository:
    def __init__(self, records: list[ChangeRecord]) -> None:
        self._records = sorted(records, key=lambda item: item.timestamp, reverse=True)

    @classmethod
    def from_jsonl(cls, path: str | Path) -> ChangeRepository:
        records = []
        for line_number, line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(),
            1,
        ):
            if not line.strip():
                continue
            try:
                records.append(ChangeRecord.model_validate_json(line))
            except Exception as exc:
                raise ValueError(
                    f"invalid change record at line {line_number}"
                ) from exc
        return cls(records)

    def query(
        self,
        *,
        service: str,
        start: str | datetime,
        end: str | datetime,
        change_types: set[str] | None = None,
    ) -> list[ChangeRecord]:
        start_time = datetime.fromisoformat(start) if isinstance(start, str) else start
        end_time = datetime.fromisoformat(end) if isinstance(end, str) else end
        return [
            item
            for item in self._records
            if item.service == service
            and start_time <= item.timestamp <= end_time
            and (
                not change_types
                or item.change_type.value in change_types
            )
        ]


def correlate_changes(
    records: list[ChangeRecord],
    *,
    incident_time: str | datetime,
    service: str,
    dependency_services: set[str] | None = None,
    window_minutes: int = 30,
    environment: str = "production",
) -> list[CorrelatedChange]:
    incident_at = (
        datetime.fromisoformat(incident_time)
        if isinstance(incident_time, str)
        else incident_time
    )
    window = timedelta(minutes=window_minutes)
    dependencies = dependency_services or set()
    correlated = []
    for item in records:
        delta = abs(incident_at - item.timestamp)
        if delta > window:
            continue
        reasons = []
        score = 0.0
        if item.service == service:
            score += 0.5
            reasons.append("same_service")
        elif item.service in dependencies:
            score += 0.25
            reasons.append("dependency_service")
        else:
            continue
        proximity = 1 - (delta.total_seconds() / window.total_seconds())
        score += 0.4 * proximity
        reasons.append("within_time_window")
        if item.environment == environment:
            score += 0.1
            reasons.append("same_environment")
        correlated.append(
            CorrelatedChange(
                change=item,
                score=round(min(score, 1.0), 4),
                reasons=tuple(reasons),
                time_delta_seconds=delta.total_seconds(),
            )
        )
    return sorted(
        correlated,
        key=lambda item: (-item.score, item.time_delta_seconds),
    )


def default_change_repository() -> ChangeRepository:
    root = Path(__file__).resolve().parents[1]
    return ChangeRepository.from_jsonl(root / "data" / "change_records.jsonl")
