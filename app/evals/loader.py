import json
from pathlib import Path

from pydantic import ValidationError

from app.evals.models import IncidentEvalCase


def load_incident_cases(path: str | Path) -> list[IncidentEvalCase]:
    """Load and validate UTF-8 JSONL incident cases."""

    source = Path(path)
    cases: list[IncidentEvalCase] = []
    seen_ids: set[str] = set()

    with source.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue

            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{source}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc

            try:
                case = IncidentEvalCase.model_validate(payload)
            except ValidationError as exc:
                raise ValueError(
                    f"{source}:{line_number}: invalid incident case: {exc}"
                ) from exc

            if case.incident_id in seen_ids:
                raise ValueError(
                    f"{source}:{line_number}: duplicate incident_id: "
                    f"{case.incident_id}"
                )

            seen_ids.add(case.incident_id)
            cases.append(case)

    return cases
