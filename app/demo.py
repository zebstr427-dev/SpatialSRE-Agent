"""Deterministic enterprise incident-response demo."""

import asyncio
import json

from app.agent.enterprise_workflow import EnterpriseIncidentWorkflow


async def run_enterprise_demo() -> dict:
    workflow = EnterpriseIncidentWorkflow()
    return await workflow.run(
        "Diagnose payment CPU 100% after deployment",
        incident_id="demo-payment-cpu-001",
        trace_id="demo-trace-payment-cpu-001",
        alert={
            "alert_name": "HighCPUUsage",
            "severity": "warning",
            "service": "payment",
            "started_at": "2026-08-05T01:50:00+00:00",
        },
    )


def main() -> None:
    result = asyncio.run(run_enterprise_demo())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
