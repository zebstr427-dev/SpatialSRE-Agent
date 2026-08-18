"""Deterministic routing and escalation for the durable incident graph."""

from __future__ import annotations

from typing import Any, Literal

from app.config import config

from .state import DiagnosisStrategy, IncidentState, utc_now_iso

SIMPLE = "simple"
ENTERPRISE = "enterprise"


def _affected_services(state: IncidentState) -> list[str]:
    alert = state.get("alert", {})
    raw = alert.get("affected_services")
    services = [str(item) for item in raw] if isinstance(raw, list) else []
    service = alert.get("service")
    if isinstance(service, str) and service and service not in services:
        services.append(service)
    for item in state.get("affected_services", []):
        if item and item not in services:
            services.append(item)
    return services


def select_initial_strategy(
    state: IncidentState,
) -> tuple[Literal["simple", "enterprise"], list[str]]:
    """Choose a strategy using auditable structured incident facts."""

    requested: DiagnosisStrategy = state.get("requested_strategy", "simple")
    if requested == SIMPLE:
        return SIMPLE, ["forced_simple"]
    if requested == ENTERPRISE:
        return ENTERPRISE, ["forced_enterprise"]

    alert = state.get("alert", {})
    severity = str(alert.get("severity") or state.get("severity", "unknown")).lower()
    services = _affected_services(state)
    reasons: list[str] = []
    if severity == "critical":
        reasons.append("critical_severity")
    if len(services) > 1:
        reasons.append("multiple_affected_services")
    if alert.get("requires_graph_analysis") is True:
        reasons.append("graph_analysis_requested")
    if alert.get("requires_change_correlation") is True:
        reasons.append("change_correlation_requested")
    recent_change = alert.get("recent_change") is True or alert.get("has_recent_change") is True
    if severity == "high" and recent_change:
        reasons.append("high_severity_recent_change")
    if reasons:
        return ENTERPRISE, reasons
    return SIMPLE, ["simple_first"]


async def incident_router(state: IncidentState) -> dict[str, Any]:
    selected, reasons = select_initial_strategy(state)
    alert = state.get("alert", {})
    severity = str(alert.get("severity") or state.get("severity", "unknown")).lower()
    if severity not in {"critical", "high", "medium", "low", "unknown"}:
        severity = "unknown"
    return {
        "severity": severity,
        "affected_services": _affected_services(state),
        "selected_strategy": selected,
        "routing_history": [
            {
                "phase": "initial",
                "from_strategy": None,
                "to_strategy": selected,
                "reason_codes": reasons,
                "requested_strategy": state.get("requested_strategy", "simple"),
                "timestamp": utc_now_iso(),
            }
        ],
        "status": "running",
        "updated_at": utc_now_iso(),
    }


def route_after_incident_router(state: IncidentState) -> str:
    return ENTERPRISE if state.get("selected_strategy") == ENTERPRISE else SIMPLE


def assess_evidence_confidence(state: IncidentState) -> float:
    """Score evidence using checkpointed facts rather than an LLM opinion."""

    score = 0.20 if state.get("runbook_id") else 0.0
    source_types = {
        str(item.get("source_type"))
        for item in state.get("evidence", [])
        if item.get("source_type")
    }
    score += min(len(source_types), 3) * 0.15

    succeeded_tools = sum(
        1 for item in state.get("tool_calls", []) if item.get("status") == "succeeded"
    )
    if succeeded_tools >= 2:
        score += 0.20
    elif succeeded_tools == 1:
        score += 0.10

    response = state.get("response", "")
    evidence_ids = {
        str(item.get("evidence_id"))
        for item in state.get("evidence", [])
        if item.get("evidence_id")
    }
    if any(f"[evidence:{evidence_id}]" in response for evidence_id in evidence_ids):
        score += 0.15

    if any(item.get("status") == "failed" for item in state.get("tool_calls", [])):
        score -= 0.15
    failed_steps = sum(1 for item in state.get("past_steps", []) if item.get("status") == "failed")
    if failed_steps >= 2:
        score -= 0.15
    return round(max(0.0, min(score, 1.0)), 4)


async def evidence_assessor(state: IncidentState) -> dict[str, Any]:
    confidence = assess_evidence_confidence(state)
    failed_steps = sum(1 for item in state.get("past_steps", []) if item.get("status") == "failed")
    reasons: list[str] = []
    if not state.get("response"):
        reasons.append("missing_response")
    if confidence < config.incident_confidence_threshold:
        reasons.append("low_evidence_confidence")
    if failed_steps >= 2:
        reasons.append("repeated_step_failures")

    can_escalate = (
        state.get("requested_strategy") == "auto"
        and state.get("escalation_count", 0) < config.incident_max_escalations
        and bool(reasons)
    )
    if can_escalate:
        return {
            "diagnosis_confidence": confidence,
            "selected_strategy": ENTERPRISE,
            "escalation_count": state.get("escalation_count", 0) + 1,
            "routing_history": [
                {
                    "phase": "escalation",
                    "from_strategy": SIMPLE,
                    "to_strategy": ENTERPRISE,
                    "reason_codes": reasons,
                    "diagnosis_confidence": confidence,
                    "timestamp": utc_now_iso(),
                }
            ],
            "plan": [],
            "runbook_steps": [],
            "pending_tool_calls": [],
            "approval_decision": None,
            "response": "",
            "status": "running",
            "updated_at": utc_now_iso(),
        }

    return {
        "diagnosis_confidence": confidence,
        "status": "completed",
        "updated_at": utc_now_iso(),
    }


def route_after_evidence_assessor(state: IncidentState) -> str:
    return ENTERPRISE if state.get("selected_strategy") == ENTERPRISE else "complete"
