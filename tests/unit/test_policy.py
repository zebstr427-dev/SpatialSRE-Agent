import json

import pytest
from pydantic import ValidationError

from app.agent.identity import AgentIdentity, AgentRole
from app.agent.policy import (
    PolicyAction,
    PolicyContext,
    ToolPolicy,
    ToolPolicyEngine,
    load_tool_policy,
)
from app.agent.tool_risk import ToolRiskLevel


def _identity(role: AgentRole = AgentRole.OPERATOR) -> AgentIdentity:
    return AgentIdentity(
        identity_id="checkout-agent",
        role=role,
        tool_scope=("*",),
        service_scope=("checkout",),
        risk_ceiling=ToolRiskLevel.WRITE,
    )


def test_policy_loader_validates_versioned_json(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "version": "2026-08-05",
                "default_action": "deny",
                "rules": [
                    {
                        "name": "readonly-auto-allow",
                        "when": {"risk_levels": ["read_only"]},
                        "action": "allow",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    policy = load_tool_policy(path)

    assert policy.version == "2026-08-05"
    assert policy.rules[0].name == "readonly-auto-allow"

    with pytest.raises(ValidationError):
        ToolPolicy.model_validate(
            {"version": "v1", "default_action": "unknown", "rules": []}
        )


def test_policy_uses_first_matching_rule_and_default_deny() -> None:
    policy = ToolPolicy.model_validate(
        {
            "version": "v1",
            "default_action": "deny",
            "rules": [
                {
                    "name": "production-write-approval",
                    "when": {
                        "environments": ["production"],
                        "risk_levels": ["write"],
                    },
                    "action": "require_approval",
                },
                {
                    "name": "readonly-auto-allow",
                    "when": {"risk_levels": ["read_only"]},
                    "action": "allow",
                },
            ],
        }
    )
    engine = ToolPolicyEngine(policy)

    approval = engine.evaluate(
        PolicyContext(
            identity=_identity(),
            tool_name="restart_service",
            service="checkout",
            risk_level=ToolRiskLevel.WRITE,
            environment="production",
        )
    )
    allowed = engine.evaluate(
        PolicyContext(
            identity=_identity(),
            tool_name="query_cpu_metrics",
            service="checkout",
            risk_level=ToolRiskLevel.READ_ONLY,
            environment="production",
        )
    )
    denied = engine.evaluate(
        PolicyContext(
            identity=_identity(AgentRole.ADMIN),
            tool_name="custom_tool",
            service="checkout",
            risk_level=ToolRiskLevel.HIGH_RISK,
            environment="staging",
        )
    )

    assert approval.action is PolicyAction.REQUIRE_APPROVAL
    assert approval.rule_name == "production-write-approval"
    assert allowed.action is PolicyAction.ALLOW
    assert denied.action is PolicyAction.DENY
    assert denied.rule_name is None
    json.dumps(approval.to_record())


def test_policy_conditions_match_tool_role_and_service() -> None:
    policy = ToolPolicy.model_validate(
        {
            "version": "v1",
            "default_action": "deny",
            "rules": [
                {
                    "name": "operator-checkout-query",
                    "when": {
                        "tools": ["query_*"],
                        "roles": ["operator"],
                        "services": ["checkout"],
                    },
                    "action": "allow",
                }
            ],
        }
    )
    engine = ToolPolicyEngine(policy)

    allowed = engine.evaluate(
        PolicyContext(
            identity=_identity(),
            tool_name="query_logs",
            service="checkout",
            risk_level=ToolRiskLevel.READ_ONLY,
            environment="production",
        )
    )
    denied = engine.evaluate(
        PolicyContext(
            identity=_identity(),
            tool_name="query_logs",
            service="identity",
            risk_level=ToolRiskLevel.READ_ONLY,
            environment="production",
        )
    )

    assert allowed.action is PolicyAction.ALLOW
    assert denied.action is PolicyAction.DENY
