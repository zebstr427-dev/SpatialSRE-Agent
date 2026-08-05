from pathlib import Path

import pytest
from pydantic import ValidationError

from app.runbooks import Runbook, RunbookRegistry, load_runbook


def test_load_runbook_validates_schema_and_version(tmp_path: Path) -> None:
    path = tmp_path / "cpu.yaml"
    path.write_text(
        """
id: cpu_high_usage
version: 1.0.0
name: CPU high usage diagnosis
trigger:
  alert_name: HighCPUUsage
  severity: warning
steps:
  - id: query_cpu
    tool: query_cpu_metrics
    arguments:
      window_minutes: 15
    risk_level: read_only
stop_conditions:
  - max_steps_reached
expected_evidence:
  - cpu_usage_series
""".strip(),
        encoding="utf-8",
    )

    runbook = load_runbook(path)

    assert runbook.id == "cpu_high_usage"
    assert runbook.version == "1.0.0"
    assert runbook.steps[0].tool == "query_cpu_metrics"
    assert runbook.source_path == str(path.resolve())


def test_runbook_rejects_duplicate_step_ids_and_empty_steps() -> None:
    payload = {
        "id": "invalid",
        "version": "1.0.0",
        "name": "Invalid",
        "trigger": {"alert_name": "Alert"},
        "steps": [
            {"id": "same", "tool": "one", "risk_level": "read_only"},
            {"id": "same", "tool": "two", "risk_level": "read_only"},
        ],
    }

    with pytest.raises(ValidationError, match="step ids must be unique"):
        Runbook.model_validate(payload)

    payload["steps"] = []
    with pytest.raises(ValidationError):
        Runbook.model_validate(payload)


def test_registry_loads_directory_matches_alert_and_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    content = """
id: service_unavailable
version: 1.0.0
name: Service unavailable
trigger:
  alert_name: Service*Unavailable
  severity: critical
steps:
  - id: query_logs
    tool: search_log
    risk_level: read_only
""".strip()
    (tmp_path / "first.yaml").write_text(content, encoding="utf-8")
    registry = RunbookRegistry.load_directory(tmp_path)

    matched = registry.match(
        alert_name="ServiceCheckoutUnavailable",
        severity="critical",
    )

    assert matched is not None
    assert matched.id == "service_unavailable"
    assert registry.match(alert_name="HighCPUUsage", severity="warning") is None

    (tmp_path / "duplicate.yaml").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate runbook id"):
        RunbookRegistry.load_directory(tmp_path)


def test_project_runbook_catalog_contains_core_incidents() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = RunbookRegistry.load_directory(root / "runbooks")

    assert {item.id for item in registry.list_runbooks()} == {
        "cpu_high_usage",
        "disk_high_usage",
        "memory_leak",
        "service_unavailable",
        "slow_response",
    }
