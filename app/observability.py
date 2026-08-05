"""OpenTelemetry-backed, checkpoint-safe AgentOps span records."""

from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace

_TRACER = trace.get_tracer("super-biz-agent")


def start_agent_span(name: str, attributes: dict[str, Any]):
    span = _TRACER.start_as_current_span(name)
    context = span.__enter__()
    for key, value in attributes.items():
        if value is not None:
            context.set_attribute(f"agent.{key}", value)
    return span, context


def finish_agent_span(
    span_context,
    span,
    *,
    name: str,
    incident_id: str,
    trace_id: str,
    started_at: str,
    latency_ms: int,
    success: bool,
    error: str | None,
    model: str | None = None,
    tokens: int = 0,
    token_cost: float = 0.0,
) -> dict[str, object]:
    span_context.set_attribute("agent.success", success)
    span_context.set_attribute("agent.latency_ms", latency_ms)
    if error:
        span_context.set_attribute("agent.error", error)
    span.__exit__(None, None, None)
    return {
        "name": name,
        "incident_id": incident_id,
        "trace_id": trace_id,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
        "model": model,
        "tokens": tokens,
        "token_cost": token_cost,
    }
