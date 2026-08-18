import json

import pytest

from app.agent.identity import AgentIdentity, AgentRole, default_agent_identity
from app.agent.tool_gateway import create_tool_gateway
from app.agent.tool_risk import ToolRiskLevel
from app.tools import (
    CHAT_READONLY_TOOLS,
    DEFAULT_LOCAL_AGENT_TOOLS,
    select_read_only_tools,
)
from app.tools.remediation_tools import restart_service


@pytest.mark.asyncio
async def test_restart_service_requires_operator_approval_and_stays_dry_run() -> None:
    chat_tool_names = {tool.name for tool in CHAT_READONLY_TOOLS}
    incident_tool_names = {tool.name for tool in DEFAULT_LOCAL_AGENT_TOOLS}
    assert "restart_service" not in chat_tool_names
    assert "restart_service" in incident_tool_names
    assert chat_tool_names < incident_tool_names
    assert {tool.name for tool in select_read_only_tools(DEFAULT_LOCAL_AGENT_TOOLS)} == (
        chat_tool_names
    )

    gateway = await create_tool_gateway(local_tools=[restart_service], mcp_tools=[])

    observer_result = await gateway.invoke(
        tool_call_id="observer-restart",
        tool_name="restart_service",
        arguments={"service": "checkout"},
        dry_run=True,
        identity=default_agent_identity(),
    )
    assert observer_result.error_code == "tool_identity_denied"

    operator = AgentIdentity(
        identity_id="checkout-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("restart_service",),
        service_scope=("checkout",),
        risk_ceiling=ToolRiskLevel.WRITE,
    )
    approval_result = await gateway.invoke(
        tool_call_id="operator-restart",
        tool_name="restart_service",
        arguments={"service": "checkout", "dry_run": False},
        dry_run=True,
        identity=operator,
    )
    assert approval_result.error_code == "tool_approval_required"

    approved = await gateway.invoke(
        tool_call_id="operator-restart-approved",
        tool_name="restart_service",
        arguments={"service": "checkout", "dry_run": False},
        dry_run=True,
        identity=operator,
        approval_granted=True,
    )
    assert approved.status == "succeeded"
    assert approved.arguments["dry_run"] is True
    assert json.loads(approved.output)["executed"] is False
