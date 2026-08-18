"""工具模块 - 供 Agent 调用的各种工具"""

from collections.abc import Iterable

from langchain_core.tools import BaseTool

from app.agent.tool_risk import ToolRiskLevel, risk_metadata_for
from app.tools.change_tools import DEFAULT_CHANGE_TOOLS
from app.tools.knowledge_tool import retrieve_knowledge
from app.tools.query_metrics_alerts import query_prometheus_alerts
from app.tools.remediation_tools import restart_service
from app.tools.time_tool import get_current_time

# 普通 Chat 只绑定只读工具，不暴露处置能力。
CHAT_READONLY_TOOLS = (
    retrieve_knowledge,
    get_current_time,
    query_prometheus_alerts,
    *DEFAULT_CHANGE_TOOLS,
)

# Incident Runtime 的本地工具目录。处置工具必须通过 Tool Gateway
# 执行身份、风险、策略、审批和审计检查。
DEFAULT_LOCAL_AGENT_TOOLS = (*CHAT_READONLY_TOOLS, restart_service)


def select_read_only_tools(tools: Iterable[BaseTool]) -> tuple[BaseTool, ...]:
    """按统一风险元数据为普通 Chat 筛选只读工具。"""

    return tuple(
        tool
        for tool in tools
        if risk_metadata_for(tool.name).level is ToolRiskLevel.READ_ONLY
    )


__all__ = [
    "CHAT_READONLY_TOOLS",
    "DEFAULT_LOCAL_AGENT_TOOLS",
    "retrieve_knowledge",
    "get_current_time",
    "query_prometheus_alerts",
    "restart_service",
    "select_read_only_tools",
]
