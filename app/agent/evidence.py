"""Evidence provenance and deterministic input/output guardrails."""

from __future__ import annotations

import re
from typing import Any


class InputGuardrailError(ValueError):
    """Raised when an incident request violates a deterministic boundary."""


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"忽略(所有)?之前的指令"),
    re.compile(r"绕过(安全|权限|审批)"),
)
_CITATION_PATTERN = re.compile(r"\[evidence:([^\]]+)\]")


def validate_incident_input(value: str, *, max_chars: int = 50_000) -> str:
    normalized = value.strip()
    if not normalized:
        raise InputGuardrailError("incident input cannot be empty")
    if len(normalized) > max_chars:
        raise InputGuardrailError("incident input exceeds maximum length")
    if any(pattern.search(normalized) for pattern in _INJECTION_PATTERNS):
        raise InputGuardrailError("incident input contains prompt injection")
    return normalized


def _source_type(tool_name: str) -> str:
    lowered = tool_name.lower()
    if "metric" in lowered or "prometheus" in lowered:
        return "metric"
    if "log" in lowered:
        return "log"
    if "knowledge" in lowered or "document" in lowered:
        return "knowledge"
    if "change" in lowered or "deployment" in lowered:
        return "change"
    return "tool"


def create_tool_evidence(
    *,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    output: str,
    identity_id: str | None,
    risk_level: str,
    dry_run: bool,
    started_at: str,
    finished_at: str,
    policy_decision_id: str | None,
) -> dict[str, Any]:
    return {
        "evidence_id": f"evidence-{tool_call_id}",
        "source_type": _source_type(tool_name),
        "source": tool_name,
        "content": output,
        "collected_at": finished_at,
        "tool_call_id": tool_call_id,
        "provenance": {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments": dict(arguments),
            "identity_id": identity_id,
            "risk_level": risk_level,
            "dry_run": dry_run,
            "started_at": started_at,
            "finished_at": finished_at,
            "policy_decision_id": policy_decision_id,
        },
    }


def bind_report_to_evidence(
    report: str,
    evidence: list[dict[str, Any]],
    *,
    max_chars: int = 20_000,
) -> str:
    if not evidence:
        return (
            "# 诊断报告\n\n"
            "证据不足，当前无法形成可靠根因结论。"
            "请补充指标、日志、变更记录或知识库证据后重试。"
        )

    valid_ids = {str(item["evidence_id"]) for item in evidence}

    def replace_unknown(match: re.Match[str]) -> str:
        evidence_id = match.group(1)
        return match.group(0) if evidence_id in valid_ids else "[invalid-citation]"

    constrained = _CITATION_PATTERN.sub(replace_unknown, report.strip())[:max_chars]
    citation_lines = []
    for item in evidence:
        content = str(item.get("content", "")).replace("\n", " ")[:300]
        citation_lines.append(
            f"- [evidence:{item['evidence_id']}] "
            f"{item.get('source', 'unknown')}: {content}"
        )
    return f"{constrained}\n\n## 证据引用\n\n" + "\n".join(citation_lines)


def evidence_citations(evidence: list[dict[str, Any]]) -> list[str]:
    return [f"[evidence:{item['evidence_id']}]" for item in evidence]
