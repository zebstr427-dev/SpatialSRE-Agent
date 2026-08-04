"""Unified registration and execution boundary for AIOps tools."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from langchain_core.tools import BaseTool
from loguru import logger

ToolSource = Literal["local", "mcp"]
ToolExecutionStatus = Literal["succeeded", "failed"]
ToolErrorCode = Literal[
    "tool_not_found",
    "tool_timeout",
    "tool_execution_failed",
]


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    tool: BaseTool
    source: ToolSource
    timeout_seconds: float
    max_attempts: int
    retry_delay_seconds: float


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    tool_call_id: str
    tool_name: str
    source: ToolSource | None
    arguments: dict[str, Any]
    status: ToolExecutionStatus
    output: str
    error_code: ToolErrorCode | None
    error_message: str | None
    attempts: int
    started_at: str
    finished_at: str


ToolAuditHook = Callable[
    [ToolExecutionResult],
    Awaitable[None] | None,
]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ToolGateway:
    def __init__(
        self,
        *,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        self._registrations: dict[str, ToolRegistration] = {}
        self._audit_hook = audit_hook

    def register(
        self,
        tool: BaseTool,
        *,
        source: ToolSource,
        timeout_seconds: float = 10.0,
        max_attempts: int = 1,
        retry_delay_seconds: float = 0.0,
    ) -> None:
        if tool.name in self._registrations:
            raise ValueError(f"tool name already registered: {tool.name}")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")

        self._registrations[tool.name] = ToolRegistration(
            tool=tool,
            source=source,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )

    def list_tools(self) -> list[BaseTool]:
        return [
            registration.tool
            for registration in self._registrations.values()
        ]

    def registration_for(
        self,
        tool_name: str,
    ) -> ToolRegistration | None:
        return self._registrations.get(tool_name)

    async def invoke(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        started_at = _utc_now_iso()
        safe_arguments = dict(arguments)
        registration = self.registration_for(tool_name)

        if registration is None:
            result = ToolExecutionResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                source=None,
                arguments=safe_arguments,
                status="failed",
                output=f"Tool '{tool_name}' is not registered",
                error_code="tool_not_found",
                error_message=f"Tool '{tool_name}' is not registered",
                attempts=0,
                started_at=started_at,
                finished_at=_utc_now_iso(),
            )
            await self._emit_audit(result)
            return result

        try:
            json.dumps(safe_arguments)
        except (TypeError, ValueError) as exc:
            message = (
                f"Tool '{tool_name}' received non-serializable arguments: "
                f"{exc}"
            )
            result = ToolExecutionResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                source=registration.source,
                arguments={},
                status="failed",
                output=message,
                error_code="tool_execution_failed",
                error_message=message,
                attempts=0,
                started_at=started_at,
                finished_at=_utc_now_iso(),
            )
            await self._emit_audit(result)
            return result

        error_code: ToolErrorCode = "tool_execution_failed"
        error_message = ""
        attempts = 0

        for attempts in range(1, registration.max_attempts + 1):
            try:
                raw_output = await asyncio.wait_for(
                    registration.tool.ainvoke(safe_arguments),
                    timeout=registration.timeout_seconds,
                )
                result = ToolExecutionResult(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    source=registration.source,
                    arguments=safe_arguments,
                    status="succeeded",
                    output=str(raw_output),
                    error_code=None,
                    error_message=None,
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=_utc_now_iso(),
                )
                await self._emit_audit(result)
                return result
            except TimeoutError:
                error_code = "tool_timeout"
                error_message = (
                    f"Tool '{tool_name}' timed out after "
                    f"{registration.timeout_seconds:g} seconds"
                )
            except Exception as exc:
                error_code = "tool_execution_failed"
                error_message = f"Tool '{tool_name}' failed: {exc}"

            if (
                attempts < registration.max_attempts
                and registration.retry_delay_seconds > 0
            ):
                await asyncio.sleep(registration.retry_delay_seconds)

        result = ToolExecutionResult(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            source=registration.source,
            arguments=safe_arguments,
            status="failed",
            output=error_message,
            error_code=error_code,
            error_message=error_message,
            attempts=attempts,
            started_at=started_at,
            finished_at=_utc_now_iso(),
        )
        await self._emit_audit(result)
        return result

    async def _emit_audit(
        self,
        result: ToolExecutionResult,
    ) -> None:
        if self._audit_hook is None:
            return

        try:
            hook_result = self._audit_hook(result)
            if inspect.isawaitable(hook_result):
                await hook_result
        except Exception:
            logger.exception(
                "Tool audit hook failed: tool_call_id={}",
                result.tool_call_id,
            )


async def create_tool_gateway(
    *,
    local_tools: Iterable[BaseTool] | None = None,
    mcp_tools: Iterable[BaseTool] | None = None,
    audit_hook: ToolAuditHook | None = None,
    timeout_seconds: float = 10.0,
    max_attempts: int = 1,
    retry_delay_seconds: float = 0.0,
) -> ToolGateway:
    if local_tools is None:
        from app.tools import DEFAULT_LOCAL_AGENT_TOOLS

        local_tools = DEFAULT_LOCAL_AGENT_TOOLS

    if mcp_tools is None:
        from app.agent.mcp_client import get_mcp_client

        mcp_client = await get_mcp_client(force_new=True)
        mcp_tools = await mcp_client.get_tools()

    resolved_local_tools = tuple(local_tools)
    resolved_mcp_tools = tuple(mcp_tools)
    gateway = ToolGateway(audit_hook=audit_hook)

    for tool in resolved_local_tools:
        gateway.register(
            tool,
            source="local",
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )

    for tool in resolved_mcp_tools:
        gateway.register(
            tool,
            source="mcp",
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )

    logger.info(
        "Tool Gateway ready: local={}, MCP={}",
        len(resolved_local_tools),
        len(resolved_mcp_tools),
    )
    return gateway
