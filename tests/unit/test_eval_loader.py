import json
from pathlib import Path

import pytest

from app.evals.loader import load_incident_cases


def _case_payload(incident_id: str = "case_cpu_001") -> dict[str, object]:
    return {
        "incident_id": incident_id,
        "alert": "checkout cpu is above 90 percent",
        "metrics": "cpu=96%",
        "logs": "worker queue depth is increasing",
        "change_records": "no recent deployment",
        "gold_root_cause": "checkout workers are saturated",
        "gold_actions": ["query_prometheus_alerts"],
        "expected_report_points": ["cpu saturation", "checkout impact"],
    }


def test_load_incident_cases_validates_jsonl_records(tmp_path: Path) -> None:
    source = tmp_path / "cases.jsonl"
    source.write_text(json.dumps(_case_payload()) + "\n", encoding="utf-8")

    cases = load_incident_cases(source)

    assert len(cases) == 1
    assert cases[0].incident_id == "case_cpu_001"
    assert cases[0].gold_actions == ("query_prometheus_alerts",)


def test_load_incident_cases_reports_invalid_line_number(tmp_path: Path) -> None:
    source = tmp_path / "cases.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps(_case_payload()),
                json.dumps({"incident_id": "case_broken"}),
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"cases\.jsonl:2: invalid incident case",
    ):
        load_incident_cases(source)


def test_load_incident_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    source = tmp_path / "cases.jsonl"
    payload = json.dumps(_case_payload())
    source.write_text(f"{payload}\n{payload}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate incident_id: case_cpu_001"):
        load_incident_cases(source)


def test_repository_baseline_cases_load_successfully() -> None:
    project_root = Path(__file__).resolve().parents[2]

    cases = load_incident_cases(project_root / "evals" / "incident_cases.jsonl")

    assert [case.incident_id for case in cases] == [
        "case_cpu_001",
        "case_runbook_001",
        "case_cpu_runbook_001",
    ]
    assert all(case.gold_actions for case in cases)
