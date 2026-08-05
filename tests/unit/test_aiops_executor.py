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
from app.agent.identity import AgentIdentity, AgentRole
from app.agent.policy import ToolPolicy, ToolPolicyEngine
from app.agent.tool_risk import READ_ONLY_METADATA
from app.agent.tool_risk import ToolRiskLevel, ToolRiskMetadata


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
    risk_metadata: ToolRiskMetadata = READ_ONLY_METADATA,
    policy_engine: ToolPolicyEngine | None = None,
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
        gateway = ToolGateway(
            audit_hook=audit_hook,
            policy_engine=policy_engine,
        )
        for tool in tools:
            gateway.register(
                tool,
                source="local",
                risk_metadata=risk_metadata,
            )
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
    assert all(item["identity_id"] == "oncall-observer" for item in audits)
    assert result["policy_decisions"] == []
    assert [item["evidence_id"] for item in result["evidence"]] == [
        "evidence-call-metrics",
        "evidence-call-logs",
    ]
    assert result["evidence"][0]["provenance"]["tool_call_id"] == "call-metrics"
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


@pytest.mark.asyncio
async def test_executor_requests_write_tools_in_dry_run_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[bool] = []

    async def restart(service: str, simulate: bool) -> str:
        received.append(simulate)
        return "restart simulation complete"

    _patch_runtime(
        monkeypatch,
        first_response=AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call-restart",
                    "name": "restart_service",
                    "args": {"service": "checkout", "simulate": False},
                }
            ],
        ),
        tools=[_tool("restart_service", restart)],
        risk_metadata=ToolRiskMetadata(
            level=ToolRiskLevel.WRITE,
            dry_run_argument="simulate",
        ),
    )

    state = _state_with_plan("simulate checkout restart")
    state["identity"] = AgentIdentity(
        identity_id="checkout-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("restart_service",),
        service_scope=("checkout",),
        risk_ceiling=ToolRiskLevel.WRITE,
    ).to_record()
    result = await executor_module.executor(state)

    assert result["past_steps"][0]["status"] == "succeeded"
    assert received == [True]
    assert result["tool_calls"][0]["identity_id"] == "checkout-operator"


@pytest.mark.asyncio
async def test_executor_persists_policy_decision_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def metrics(service: str) -> str:
        return "cpu=95%"

    policy = ToolPolicy.model_validate(
        {
            "version": "executor-v1",
            "default_action": "deny",
            "rules": [
                {
                    "name": "readonly-allow",
                    "when": {"risk_levels": ["read_only"]},
                    "action": "allow",
                }
            ],
        }
    )
    _patch_runtime(
        monkeypatch,
        first_response=AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call-metrics",
                    "name": "query_metrics",
                    "args": {"service": "checkout"},
                }
            ],
        ),
        tools=[_tool("query_metrics", metrics)],
        policy_engine=ToolPolicyEngine(policy),
    )

    result = await executor_module.executor(
        _state_with_plan("query checkout metrics")
    )

    assert result["policy_decisions"][0]["policy_version"] == "executor-v1"
    assert result["policy_decisions"][0]["rule_name"] == "readonly-allow"


@pytest.mark.asyncio
async def test_executor_pauses_then_executes_an_approved_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[bool] = []

    async def restart(service: str, dry_run: bool) -> str:
        received.append(dry_run)
        return "restart simulation complete"

    policy = ToolPolicy.model_validate(
        {
            "version": "approval-v1",
            "default_action": "deny",
            "rules": [
                {
                    "name": "write-approval",
                    "when": {"risk_levels": ["write"]},
                    "action": "require_approval",
                }
            ],
        }
    )
    _patch_runtime(
        monkeypatch,
        first_response=AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call-restart",
                    "name": "restart_service",
                    "args": {"service": "checkout", "dry_run": False},
                }
            ],
        ),
        tools=[_tool("restart_service", restart)],
        risk_metadata=ToolRiskMetadata(
            level=ToolRiskLevel.WRITE,
            dry_run_argument="dry_run",
        ),
        policy_engine=ToolPolicyEngine(policy),
    )
    state = _state_with_plan("restart checkout")
    state["identity"] = AgentIdentity(
        identity_id="checkout-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("restart_service",),
        service_scope=("checkout",),
        risk_ceiling=ToolRiskLevel.WRITE,
    ).to_record()

    paused = await executor_module.executor(state)

    assert paused["pending_tool_calls"][0]["tool_call_id"] == "call-restart"
    assert paused["approval_requests"][0]["status"] == "pending"
    assert "past_steps" not in paused
    assert received == []

    resumed_state = {**state, **paused}
    resumed_state["approval_decision"] = {
        "approved": True,
        "decided_by": "sre.lead",
        "reason": "approved",
    }
    resumed = await executor_module.executor(resumed_state)

    assert resumed["past_steps"][0]["status"] == "succeeded"
    assert resumed["pending_tool_calls"] == []
    assert resumed["approval_decision"] is None
    assert received == [True]


@pytest.mark.asyncio
async def test_executor_rejection_never_invokes_pending_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    async def restart(service: str, dry_run: bool) -> str:
        called.append(service)
        return "unexpected"

    _patch_runtime(
        monkeypatch,
        first_response=AIMessage(content="unused"),
        tools=[_tool("restart_service", restart)],
        risk_metadata=ToolRiskMetadata(
            level=ToolRiskLevel.WRITE,
            dry_run_argument="dry_run",
        ),
    )
    state = _state_with_plan("restart checkout")
    state["pending_tool_calls"] = [
        {
            "tool_call_id": "call-restart",
            "tool_name": "restart_service",
            "arguments": {"service": "checkout"},
        }
    ]
    state["approval_decision"] = {
        "approved": False,
        "decided_by": "sre.lead",
        "reason": "outside change window",
    }

    result = await executor_module.executor(state)

    assert result["past_steps"][0]["status"] == "failed"
    assert "rejected" in result["past_steps"][0]["result"]
    assert result["pending_tool_calls"] == []
    assert called == []
