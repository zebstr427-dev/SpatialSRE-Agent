"""Versioned Runbook-as-Code schema, loader, and registry."""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.tool_risk import ToolRiskLevel


class RunbookTrigger(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    alert_name: str = Field(min_length=1)
    severity: str | None = None


class RunbookStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel
    continue_on_failure: bool = False

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class Runbook(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str = Field(min_length=1)
    trigger: RunbookTrigger
    steps: tuple[RunbookStep, ...] = Field(min_length=1)
    stop_conditions: tuple[str, ...] = ()
    approval_required: tuple[str, ...] = ()
    expected_evidence: tuple[str, ...] = ()
    source_path: str | None = None

    @model_validator(mode="after")
    def validate_unique_steps(self) -> Runbook:
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("runbook step ids must be unique")
        return self

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def load_runbook(path: str | Path) -> Runbook:
    runbook_path = Path(path).resolve()
    try:
        payload = yaml.safe_load(runbook_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load runbook: {runbook_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"runbook must contain a mapping: {runbook_path}")
    return Runbook.model_validate({**payload, "source_path": str(runbook_path)})


class RunbookRegistry:
    def __init__(self, runbooks: list[Runbook]) -> None:
        self._runbooks: dict[str, Runbook] = {}
        for runbook in runbooks:
            if runbook.id in self._runbooks:
                raise ValueError(f"duplicate runbook id: {runbook.id}")
            self._runbooks[runbook.id] = runbook

    @classmethod
    def load_directory(cls, path: str | Path) -> RunbookRegistry:
        directory = Path(path)
        paths = sorted((*directory.glob("*.yaml"), *directory.glob("*.yml")))
        return cls([load_runbook(item) for item in paths])

    @classmethod
    def default(cls) -> RunbookRegistry:
        root = Path(__file__).resolve().parents[1]
        return cls.load_directory(root / "runbooks")

    def list_runbooks(self) -> list[Runbook]:
        return list(self._runbooks.values())

    def get(self, runbook_id: str) -> Runbook | None:
        return self._runbooks.get(runbook_id)

    def match(self, *, alert_name: str, severity: str | None) -> Runbook | None:
        for runbook in self._runbooks.values():
            trigger = runbook.trigger
            if not fnmatchcase(alert_name, trigger.alert_name):
                continue
            if trigger.severity and trigger.severity != severity:
                continue
            return runbook
        return None
