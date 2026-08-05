"""Agent identity and mandatory execution scope boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from fnmatch import fnmatchcase
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agent.tool_risk import ToolRiskLevel


class AgentRole(StrEnum):
    OBSERVER = "observer"
    OPERATOR = "operator"
    ADMIN = "admin"


_RISK_ORDER = {
    ToolRiskLevel.READ_ONLY: 0,
    ToolRiskLevel.WRITE: 1,
    ToolRiskLevel.HIGH_RISK: 2,
}


class AgentIdentity(BaseModel):
    """Checkpoint-safe identity used for every controlled tool call."""

    model_config = ConfigDict(frozen=True)

    identity_id: str = Field(min_length=1, max_length=128)
    role: AgentRole
    tool_scope: tuple[str, ...] = Field(min_length=1)
    service_scope: tuple[str, ...] = Field(min_length=1)
    risk_ceiling: ToolRiskLevel

    def allows_tool(self, tool_name: str) -> bool:
        return any(fnmatchcase(tool_name, pattern) for pattern in self.tool_scope)

    def allows_service(self, service: str | None) -> bool:
        if service is None:
            return "*" in self.service_scope
        return any(fnmatchcase(service, pattern) for pattern in self.service_scope)

    def allows_risk(self, risk_level: ToolRiskLevel) -> bool:
        return _RISK_ORDER[risk_level] <= _RISK_ORDER[self.risk_ceiling]

    def to_record(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> AgentIdentity:
        return cls.model_validate(record)


def default_agent_identity() -> AgentIdentity:
    return AgentIdentity(
        identity_id="oncall-observer",
        role=AgentRole.OBSERVER,
        tool_scope=("*",),
        service_scope=("*",),
        risk_ceiling=ToolRiskLevel.READ_ONLY,
    )
