"""Risk metadata used by the Tool Gateway."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class ToolRiskLevel(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"
    HIGH_RISK = "high_risk"


@dataclass(frozen=True, slots=True)
class ToolRiskMetadata:
    level: ToolRiskLevel
    dry_run_argument: str | None = None

    def __post_init__(self) -> None:
        if self.level is ToolRiskLevel.WRITE:
            if (
                self.dry_run_argument is None
                or not self.dry_run_argument.strip()
            ):
                raise ValueError(
                    "write tools must declare dry_run_argument"
                )
        elif self.dry_run_argument is not None:
            raise ValueError(
                "dry_run_argument is only valid for write tools"
            )


READ_ONLY_METADATA = ToolRiskMetadata(
    level=ToolRiskLevel.READ_ONLY
)
HIGH_RISK_METADATA = ToolRiskMetadata(
    level=ToolRiskLevel.HIGH_RISK
)

DEFAULT_READ_ONLY_TOOL_NAMES = frozenset(
    {
        "retrieve_knowledge",
        "get_current_time",
        "query_prometheus_alerts",
        "get_current_timestamp",
        "get_region_code_by_name",
        "get_topic_info_by_name",
        "search_topic_by_service_name",
        "search_log",
        "query_cpu_metrics",
        "query_memory_metrics",
    }
)


def risk_metadata_for(
    tool_name: str,
    *,
    overrides: Mapping[str, ToolRiskMetadata] | None = None,
) -> ToolRiskMetadata:
    if overrides is not None and tool_name in overrides:
        return overrides[tool_name]
    if tool_name in DEFAULT_READ_ONLY_TOOL_NAMES:
        return READ_ONLY_METADATA
    return HIGH_RISK_METADATA