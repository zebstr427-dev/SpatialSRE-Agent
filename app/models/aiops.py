"""
AIOps 请求和响应模型
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agent.identity import AgentIdentity, default_agent_identity


class AIOpsRequest(BaseModel):
    """AIOps 诊断请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-123",
                "incident_id": "incident-456",
            }
        }
    )

    session_id: str | None = Field(
        default="default",
        description="会话ID，用于追踪诊断历史"
    )
    incident_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="故障ID，用作持久化工作流的唯一线程标识",
    )
    identity: AgentIdentity = Field(
        default_factory=default_agent_identity,
        description="执行诊断的 Agent 身份与权限范围",
    )
    alert: dict[str, Any] | None = Field(
        default=None,
        description="可选的结构化告警，用于匹配 Runbook",
    )


class ApprovalDecisionRequest(BaseModel):
    """Human decision used to resume a paused incident."""

    approved: bool
    decided_by: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=1000)


class EnterpriseAlert(BaseModel):
    """Validated alert envelope used by the enterprise workflow."""

    model_config = ConfigDict(extra="forbid")

    alert_name: str = Field(min_length=1, max_length=128)
    service: str = Field(min_length=1, max_length=128)
    severity: str = Field(default="unknown", min_length=1, max_length=32)
    started_at: datetime | None = None
    environment: str = Field(default="production", min_length=1, max_length=64)


class EnterpriseIncidentRequest(BaseModel):
    """Request for the structured enterprise incident workflow."""

    input: str = Field(min_length=1, max_length=10_000)
    alert: EnterpriseAlert
    incident_id: str | None = Field(default=None, min_length=1, max_length=128)
    trace_id: str | None = Field(default=None, min_length=1, max_length=128)


class AlertInfo(BaseModel):
    """告警信息"""
    alertname: str
    severity: str
    instance: str
    duration: str
    description: str | None = None


class DiagnosisResponse(BaseModel):
    """诊断响应（非流式）"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 200,
                "message": "success",
                "data": {
                    "status": "completed",
                    "target_alert": {
                        "alertname": "HighCPUUsage",
                        "severity": "critical",
                    },
                    "diagnosis": {
                        "root_cause": "数据库连接池耗尽",
                        "recommendations": ["扩容数据库连接池", "优化SQL查询"],
                    },
                },
            }
        }
    )

    code: int = 200
    message: str = "success"
    data: dict[str, Any]
