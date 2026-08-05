import json
from pathlib import Path

import pytest

from app.change_intelligence import (
    ChangeRecord,
    ChangeRepository,
    correlate_changes,
)
from app.tools.change_tools import create_change_tools


def _records() -> list[ChangeRecord]:
    return [
        ChangeRecord(
            change_id="deploy-1",
            service="checkout",
            change_type="deployment",
            timestamp="2026-08-05T01:55:00+00:00",
            environment="production",
            summary="checkout image v2 deployed",
            version="v2",
        ),
        ChangeRecord(
            change_id="config-1",
            service="payment",
            change_type="config",
            timestamp="2026-08-05T01:45:00+00:00",
            environment="production",
            summary="payment timeout changed",
        ),
        ChangeRecord(
            change_id="deploy-old",
            service="checkout",
            change_type="deployment",
            timestamp="2026-08-04T20:00:00+00:00",
            environment="production",
            summary="old deployment",
        ),
    ]


def test_repository_loads_jsonl_and_queries_time_window(tmp_path: Path) -> None:
    path = tmp_path / "changes.jsonl"
    path.write_text(
        "\n".join(json.dumps(item.to_record()) for item in _records()),
        encoding="utf-8",
    )
    repository = ChangeRepository.from_jsonl(path)

    result = repository.query(
        service="checkout",
        start="2026-08-05T01:30:00+00:00",
        end="2026-08-05T02:00:00+00:00",
        change_types={"deployment"},
    )

    assert [item.change_id for item in result] == ["deploy-1"]


def test_change_correlation_scores_same_service_and_dependencies() -> None:
    correlated = correlate_changes(
        _records(),
        incident_time="2026-08-05T02:00:00+00:00",
        service="checkout",
        dependency_services={"payment"},
        window_minutes=30,
        environment="production",
    )

    assert [item.change.change_id for item in correlated] == [
        "deploy-1",
        "config-1",
    ]
    assert correlated[0].score > correlated[1].score
    assert "same_service" in correlated[0].reasons
    assert "dependency_service" in correlated[1].reasons
    json.dumps([item.to_record() for item in correlated])


@pytest.mark.asyncio
async def test_change_tools_return_checkpoint_safe_records() -> None:
    tools = create_change_tools(ChangeRepository(_records()))
    by_name = {tool.name: tool for tool in tools}

    output = await by_name["query_recent_deployments"].ainvoke(
        {
            "service": "checkout",
            "start": "2026-08-05T01:30:00+00:00",
            "end": "2026-08-05T02:00:00+00:00",
        }
    )

    payload = json.loads(output)
    assert payload[0]["change_id"] == "deploy-1"
    assert set(by_name) == {
        "query_config_changes",
        "query_git_commits",
        "query_k8s_rollout_history",
        "query_recent_deployments",
    }
