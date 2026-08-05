"""Typed graph nodes and edges."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NodeType(StrEnum):
    SERVICE = "service"
    API = "api"
    INSTANCE = "instance"
    POD = "pod"
    DATABASE = "database"
    QUEUE = "queue"
    CACHE = "cache"
    ALERT = "alert"
    ERROR = "error"
    CHANGE = "change"
    OWNER = "owner"
    RUNBOOK = "runbook"
    INCIDENT = "incident"
    DOCUMENT = "document"


class EdgeType(StrEnum):
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    HOSTED_ON = "hosted_on"
    TRIGGERED = "triggered"
    CHANGED_BY = "changed_by"
    OWNED_BY = "owned_by"
    DOCUMENTED_BY = "documented_by"
    SIMILAR_TO = "similar_to"
    AFFECTS = "affects"


class GraphNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    type: NodeType
    name: str = Field(min_length=1)
    properties: dict[str, object] = Field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str
    type: EdgeType
    timestamp: datetime | None = None
    properties: dict[str, object] = Field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")
