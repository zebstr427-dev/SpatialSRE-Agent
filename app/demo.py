"""Deterministic enterprise incident-response demo."""

import asyncio
import json

from app.agent.aiops.state import IncidentState
from app.agent.enterprise_workflow import EnterpriseIncidentWorkflow


async def run_enterprise_demo() -> IncidentState:
    workflow = EnterpriseIncidentWorkflow()
    return await workflow.run(
        "Diagnose data-sync-service CPU saturation after deployment",
        incident_id="demo-data-sync-cpu-001",
        trace_id="demo-trace-data-sync-cpu-001",
        alert={
            "alert_name": "HighCPUUsage",
            "severity": "warning",
            "service": "data-sync-service",
            "started_at": "2026-08-05T01:50:00+00:00",
        },
    )


def main() -> None:
    result = asyncio.run(run_enterprise_demo())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
