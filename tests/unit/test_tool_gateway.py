import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

import pytest
from langchain_core.tools import StructuredTool

from app.agent.tool_gateway import ToolGateway, create_tool_gateway


def _tool(
    name: str,
    coroutine: Callable[..., Awaitable[Any]],
) -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=coroutine,
        name=name,
        description=f"{name} test tool",
    )


@pytest.mark.asyncio
async def test_registry_unifies_sources_and_rejects_duplicate_names() -> None:
    async def local_echo(value: str) -> str:
        return value

    async def mcp_echo(value: str) -> str:
        return value

    gateway = await create_tool_gateway(
        local_tools=[_tool("local_echo", local_echo)],
        mcp_tools=[_tool("mcp_echo", mcp_echo)],
    )

    assert [tool.name for tool in gateway.list_tools()] == [
        "local_echo",
        "mcp_echo",
    ]
    assert gateway.registration_for("local_echo").source == "local"
    assert gateway.registration_for("mcp_echo").source == "mcp"

    with pytest.raises(ValueError, match="already registered"):
        gateway.register(_tool("local_echo", mcp_echo), source="mcp")


@pytest.mark.asyncio
async def test_invoke_returns_standard_success_and_not_found_results() -> None:
    audits = []

    async def audit(result) -> None:
        audits.append(result)

    async def echo(value: str) -> str:
        return f"echo:{value}"

    gateway = ToolGateway(audit_hook=audit)
    gateway.register(_tool("echo", echo), source="local")

    succeeded = await gateway.invoke(
        tool_call_id="call-ok",
        tool_name="echo",
        arguments={"value": "checkout"},
    )
    missing = await gateway.invoke(
        tool_call_id="call-missing",
        tool_name="missing",
        arguments={},
    )

    assert succeeded.status == "succeeded"
    assert succeeded.output == "echo:checkout"
    assert succeeded.error_code is None
    assert succeeded.attempts == 1

    assert missing.status == "failed"
    assert missing.error_code == "tool_not_found"
    assert missing.attempts == 0
    assert audits == [succeeded, missing]
    json.dumps(asdict(succeeded))


@pytest.mark.asyncio
async def test_invoke_retries_within_the_registered_attempt_limit() -> None:
    attempts = 0

    async def flaky(value: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary failure")
        return value

    gateway = ToolGateway()
    gateway.register(
        _tool("flaky", flaky),
        source="local",
        max_attempts=2,
    )

    result = await gateway.invoke(
        tool_call_id="call-retry",
        tool_name="flaky",
        arguments={"value": "recovered"},
    )

    assert result.status == "succeeded"
    assert result.output == "recovered"
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_invoke_returns_standard_execution_and_timeout_failures() -> None:
    async def broken() -> str:
        raise RuntimeError("monitor unavailable")

    async def slow() -> str:
        await asyncio.sleep(0.1)
        return "late"

    gateway = ToolGateway()
    gateway.register(
        _tool("broken", broken),
        source="mcp",
        max_attempts=2,
    )
    gateway.register(
        _tool("slow", slow),
        source="mcp",
        timeout_seconds=0.01,
        max_attempts=2,
    )

    broken_result = await gateway.invoke(
        tool_call_id="call-broken",
        tool_name="broken",
        arguments={},
    )
    timeout_result = await gateway.invoke(
        tool_call_id="call-slow",
        tool_name="slow",
        arguments={},
    )

    assert broken_result.error_code == "tool_execution_failed"
    assert broken_result.attempts == 2
    assert "monitor unavailable" in broken_result.error_message

    assert timeout_result.error_code == "tool_timeout"
    assert timeout_result.attempts == 2


@pytest.mark.asyncio
async def test_invoke_does_not_swallow_task_cancellation() -> None:
    async def cancelled() -> str:
        raise asyncio.CancelledError

    gateway = ToolGateway()
    gateway.register(_tool("cancelled", cancelled), source="local")

    with pytest.raises(asyncio.CancelledError):
        await gateway.invoke(
            tool_call_id="call-cancelled",
            tool_name="cancelled",
            arguments={},
        )
