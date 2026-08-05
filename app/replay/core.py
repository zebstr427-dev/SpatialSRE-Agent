"""Isolated case loading and fixed-response replay execution."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.replay.models import (
    ReplayCase,
    ReplayExpected,
    ReplayObservation,
    ReplayToolCall,
)


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load replay fixture: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"replay fixture must be an object: {path}")
    return payload


def load_replay_case(path: str | Path) -> ReplayCase:
    directory = Path(path).resolve()
    alert = _read_json(directory / "alert.json")
    expected = ReplayExpected.model_validate(_read_json(directory / "expected.json"))
    tool_responses = {
        "query_cpu_metrics": _read_json(directory / "metrics.json"),
        "search_log": _read_json(directory / "logs.json"),
        "query_recent_deployments": _read_json(directory / "changes.json"),
    }
    return ReplayCase(
        case_id=directory.name,
        alert=alert,
        tool_responses=tool_responses,
        expected=expected,
        source_directory=str(directory),
    )


class ReplayToolbox:
    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[ReplayToolCall] = []

    async def invoke(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        if tool_name not in self._responses:
            raise KeyError(f"tool is not isolated in replay case: {tool_name}")
        self.calls.append(
            ReplayToolCall(tool_name=tool_name, arguments=dict(arguments))
        )
        return dict(self._responses[tool_name])


ReplayWorkflow = Callable[
    [ReplayCase, ReplayToolbox],
    Awaitable[ReplayObservation],
]


class ReplaySimulator:
    async def run(
        self,
        case: ReplayCase,
        workflow: ReplayWorkflow,
    ) -> ReplayObservation:
        toolbox = ReplayToolbox(case.tool_responses)
        observation = await workflow(case, toolbox)
        if tuple(observation.tool_calls) != tuple(toolbox.calls):
            raise ValueError("workflow observation must use simulator tool-call log")
        return observation
