import json

from app.agent.identity import AgentIdentity, AgentRole
from app.agent.tool_risk import ToolRiskLevel


def test_identity_matches_tool_and_service_scopes() -> None:
    identity = AgentIdentity(
        identity_id="checkout-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("query_*", "restart_service"),
        service_scope=("checkout", "payment-*"),
        risk_ceiling=ToolRiskLevel.WRITE,
    )

    assert identity.allows_tool("query_cpu_metrics")
    assert identity.allows_tool("restart_service")
    assert not identity.allows_tool("delete_database")
    assert identity.allows_service("checkout")
    assert identity.allows_service("payment-api")
    assert not identity.allows_service("identity")


def test_identity_enforces_risk_ceiling_and_is_checkpoint_safe() -> None:
    identity = AgentIdentity(
        identity_id="readonly-agent",
        role=AgentRole.OBSERVER,
        tool_scope=("*",),
        service_scope=("*",),
        risk_ceiling=ToolRiskLevel.READ_ONLY,
    )

    assert identity.allows_risk(ToolRiskLevel.READ_ONLY)
    assert not identity.allows_risk(ToolRiskLevel.WRITE)
    assert not identity.allows_risk(ToolRiskLevel.HIGH_RISK)
    json.dumps(identity.to_record())


def test_identity_round_trips_from_checkpoint_record() -> None:
    original = AgentIdentity(
        identity_id="platform-operator",
        role=AgentRole.OPERATOR,
        tool_scope=("query_*",),
        service_scope=("platform",),
        risk_ceiling=ToolRiskLevel.WRITE,
    )

    restored = AgentIdentity.from_record(original.to_record())

    assert restored == original
