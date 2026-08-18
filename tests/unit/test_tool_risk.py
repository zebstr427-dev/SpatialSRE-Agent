import pytest

from app.agent.tool_risk import (
    DEFAULT_READ_ONLY_TOOL_NAMES,
    RESTART_SERVICE_METADATA,
    ToolRiskLevel,
    ToolRiskMetadata,
    risk_metadata_for,
)


def test_known_query_tools_are_read_only_and_unknown_tools_fail_closed() -> None:
    expected_names = {
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
        "query_recent_deployments",
        "query_config_changes",
        "query_git_commits",
        "query_k8s_rollout_history",
    }

    assert DEFAULT_READ_ONLY_TOOL_NAMES == frozenset(expected_names)
    assert all(risk_metadata_for(name).level is ToolRiskLevel.READ_ONLY for name in expected_names)
    assert risk_metadata_for("restart_service") is RESTART_SERVICE_METADATA
    assert RESTART_SERVICE_METADATA.level is ToolRiskLevel.WRITE
    assert RESTART_SERVICE_METADATA.dry_run_argument == "dry_run"


def test_write_metadata_requires_a_dry_run_argument() -> None:
    metadata = ToolRiskMetadata(
        level=ToolRiskLevel.WRITE,
        dry_run_argument="dry_run",
    )

    assert metadata.dry_run_argument == "dry_run"

    with pytest.raises(ValueError, match="must declare dry_run_argument"):
        ToolRiskMetadata(level=ToolRiskLevel.WRITE)

    with pytest.raises(ValueError, match="only valid for write tools"):
        ToolRiskMetadata(
            level=ToolRiskLevel.READ_ONLY,
            dry_run_argument="dry_run",
        )


def test_explicit_metadata_overrides_the_default_catalog() -> None:
    write_metadata = ToolRiskMetadata(
        level=ToolRiskLevel.WRITE,
        dry_run_argument="simulate",
    )

    result = risk_metadata_for(
        "restart_service",
        overrides={"restart_service": write_metadata},
    )

    assert result is write_metadata
