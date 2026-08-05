import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

import pytest
from langchain_core.tools import StructuredTool

from app.agent.tool_gateway import ToolGateway, create_tool_gateway
from app.agent.tool_risk import (
    HIGH_RISK_METADATA,
    READ_ONLY_METADATA,
    ToolRiskLevel,
    ToolRiskMetadata,
)


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
    gateway.register(
        _tool("echo", echo),
        source="local",
        risk_metadata=READ_ONLY_METADATA,
    )

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
        risk_metadata=READ_ONLY_METADATA,
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
        risk_metadata=READ_ONLY_METADATA,
    )
    gateway.register(
        _tool("slow", slow),
        source="mcp",
        timeout_seconds=0.01,
        max_attempts=2,
        risk_metadata=READ_ONLY_METADATA,
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
    gateway.register(
        _tool("cancelled", cancelled),
        source="local",
        risk_metadata=READ_ONLY_METADATA,
    )

    with pytest.raises(asyncio.CancelledError):
        await gateway.invoke(
            tool_call_id="call-cancelled",
            tool_name="cancelled",
            arguments={},
        )


@pytest.mark.asyncio
async def test_read_only_tool_executes_without_dry_run() -> None:
    async def query(service: str) -> str:
        return f"healthy:{service}"

    gateway = ToolGateway()
    gateway.register(
        _tool("query_health", query),
        source="local",
        risk_metadata=READ_ONLY_METADATA,
    )

    result = await gateway.invoke(
        tool_call_id="call-read",
        tool_name="query_health",
        arguments={"service": "checkout"},
    )

    assert result.status == "succeeded"
    assert result.risk_level is ToolRiskLevel.READ_ONLY
    assert result.dry_run is False


@pytest.mark.asyncio
async def test_write_tool_requires_and_forces_registered_dry_run_argument() -> None:
    received: list[bool] = []

    async def restart(service: str, simulate: bool) -> str:
        received.append(simulate)
        return f"restart:{service}:simulate={simulate}"

    gateway = ToolGateway()
    gateway.register(
        _tool("restart_service", restart),
        source="local",
        risk_metadata=ToolRiskMetadata(
            level=ToolRiskLevel.WRITE,
            dry_run_argument="simulate",
        ),
    )

    blocked = await gateway.invoke(
        tool_call_id="call-write-blocked",
        tool_name="restart_service",
        arguments={"service": "checkout", "simulate": False},
    )
    simulated = await gateway.invoke(
        tool_call_id="call-write-dry-run",
        tool_name="restart_service",
        arguments={"service": "checkout", "simulate": False},
        dry_run=True,
    )

    assert blocked.error_code == "tool_dry_run_required"
    assert blocked.attempts == 0
    assert simulated.status == "succeeded"
    assert simulated.arguments["simulate"] is True
    assert simulated.dry_run is True
    assert received == [True]


@pytest.mark.asyncio
async def test_high_risk_and_unclassified_registered_tools_fail_closed() -> None:
    called: list[str] = []

    async def mutate() -> str:
        called.append("called")
        return "mutated"

    gateway = ToolGateway()
    gateway.register(
        _tool("delete_database", mutate),
        source="local",
        risk_metadata=HIGH_RISK_METADATA,
    )
    gateway.register(_tool("mystery_operation", mutate), source="mcp")

    explicit = await gateway.invoke(
        tool_call_id="call-high-risk",
        tool_name="delete_database",
        arguments={},
        dry_run=True,
    )
    unclassified = await gateway.invoke(
        tool_call_id="call-unknown-risk",
        tool_name="mystery_operation",
        arguments={},
        dry_run=True,
    )

    assert explicit.error_code == "tool_risk_blocked"
    assert unclassified.error_code == "tool_risk_blocked"
    assert explicit.risk_level is ToolRiskLevel.HIGH_RISK
    assert unclassified.risk_level is ToolRiskLevel.HIGH_RISK
    assert called == []
