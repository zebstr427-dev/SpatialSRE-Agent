"""Versioned Policy-as-Code evaluation for controlled tool execution."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from fnmatch import fnmatchcase
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.agent.identity import AgentIdentity, AgentRole
from app.agent.tool_risk import ToolRiskLevel


class PolicyAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyConditions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tools: tuple[str, ...] = ()
    roles: tuple[AgentRole, ...] = ()
    services: tuple[str, ...] = ()
    risk_levels: tuple[ToolRiskLevel, ...] = ()
    environments: tuple[str, ...] = ()


class PolicyRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    when: PolicyConditions = Field(default_factory=PolicyConditions)
    action: PolicyAction


class ToolPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1, max_length=64)
    default_action: PolicyAction = PolicyAction.DENY
    rules: tuple[PolicyRule, ...]


class PolicyContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    identity: AgentIdentity
    tool_name: str
    service: str | None = None
    risk_level: ToolRiskLevel
    environment: str = "production"


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    policy_version: str
    rule_name: str | None
    action: PolicyAction
    reason: str
    identity_id: str
    tool_name: str
    service: str | None
    risk_level: ToolRiskLevel
    environment: str
    decided_at: str

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return not patterns or any(fnmatchcase(value, pattern) for pattern in patterns)


def _rule_matches(rule: PolicyRule, context: PolicyContext) -> bool:
    conditions = rule.when
    service = context.service or ""
    return (
        _matches_any(context.tool_name, conditions.tools)
        and (not conditions.roles or context.identity.role in conditions.roles)
        and _matches_any(service, conditions.services)
        and (
            not conditions.risk_levels
            or context.risk_level in conditions.risk_levels
        )
        and _matches_any(context.environment, conditions.environments)
    )


class ToolPolicyEngine:
    def __init__(self, policy: ToolPolicy) -> None:
        self.policy = policy

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        matched_rule = next(
            (rule for rule in self.policy.rules if _rule_matches(rule, context)),
            None,
        )
        action = (
            matched_rule.action if matched_rule else self.policy.default_action
        )
        rule_name = matched_rule.name if matched_rule else None
        reason = (
            f"matched policy rule '{rule_name}'"
            if rule_name
            else "no policy rule matched; default action applied"
        )
        return PolicyDecision(
            decision_id=uuid4().hex,
            policy_version=self.policy.version,
            rule_name=rule_name,
            action=action,
            reason=reason,
            identity_id=context.identity.identity_id,
            tool_name=context.tool_name,
            service=context.service,
            risk_level=context.risk_level,
            environment=context.environment,
            decided_at=datetime.now(UTC).isoformat(),
        )


def load_tool_policy(path: str | Path) -> ToolPolicy:
    policy_path = Path(path)
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load tool policy: {policy_path}") from exc
    return ToolPolicy.model_validate(payload)


def load_default_tool_policy() -> ToolPolicy:
    root = Path(__file__).resolve().parents[2]
    return load_tool_policy(root / "policies" / "tool-execution.json")
