import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, StructuredTool

import app.agent.aiops.executor as executor_module
from app.agent.aiops.state import create_incident_state
from app.agent.tool_gateway import ToolGateway


def _tool(name: str, coroutine) -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=coroutine,
        name=name,
        description=f"{name} test tool",
    )


def _patch_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    first_response: AIMessage,
    tools: list[BaseTool],
) -> SimpleNamespace:
    llm = SimpleNamespace()
    llm.bind_tools = lambda _tools: llm
    llm.ainvoke = AsyncMock(
        side_effect=[
            first_response,
            AIMessage(content="final summary"),
        ]
    )

    async def create_gateway(*, audit_hook=None):
        gateway = ToolGateway(audit_hook=audit_hook)
        for tool in tools:
            gateway.register(tool, source="local")
        return gateway

    monkeypatch.setattr(executor_module, "ChatQwen", lambda **_kwargs: llm)
    monkeypatch.setattr(
        executor_module,
        "create_tool_gateway",
        create_gateway,
    )
    return llm


def _state_with_plan(step: str):
    state = create_incident_state("diagnose checkout")
    state["plan"] = [step]
    return state


@pytest.mark.asyncio
async def test_executor_routes_tools_and_audits_by_call_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def metrics(service: str) -> str:
        return "cpu=95%"

    async def logs(service: str) -> str:
        return "error-rate=1%"

    first_response = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call-metrics",
                "name": "query_metrics",
                "args": {"service": "checkout"},
            },
            {
                "id": "call-logs",
                "name": "query_logs",
                "args": {"service": "checkout"},
            },
        ],
    )
    _patch_runtime(
        monkeypatch,
        first_response=first_response,
        tools=[
            _tool("query_metrics", metrics),
            _tool("query_logs", logs),
        ],
    )

    result = await executor_module.executor(
        _state_with_plan("query telemetry")
    )

    audits = result["tool_calls"]
    assert result["past_steps"][0]["status"] == "succeeded"
    assert [
        (item["tool_call_id"], item["result"], item["status"])
        for item in audits
    ] == [
        ("call-metrics", "cpu=95%", "succeeded"),
        ("call-logs", "error-rate=1%", "succeeded"),
    ]
    assert all(datetime.fromisoformat(item["started_at"]) for item in audits)
    assert all(datetime.fromisoformat(item["finished_at"]) for item in audits)
    json.dumps(audits)


@pytest.mark.asyncio
async def test_executor_preserves_gateway_failure_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def monitor(service: str) -> str:
        raise RuntimeError("monitor unavailable")

    first_response = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call-monitor",
                "name": "query_monitor",
                "args": {"service": "checkout"},
            }
        ],
    )
    llm = _patch_runtime(
        monkeypatch,
        first_response=first_response,
        tools=[_tool("query_monitor", monitor)],
    )

    result = await executor_module.executor(
        _state_with_plan("query monitor")
    )

    assert result["past_steps"][0]["status"] == "failed"
    assert result["tool_calls"][0]["status"] == "failed"
    assert result["tool_calls"][0]["result"] == (
        "Tool 'query_monitor' failed: monitor unavailable"
    )
    assert llm.ainvoke.await_count == 1
    json.dumps(result["tool_calls"])
