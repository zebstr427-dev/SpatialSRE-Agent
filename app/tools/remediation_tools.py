"""Controlled remediation tools exposed through the Tool Gateway."""

import json

from langchain_core.tools import tool


@tool
def restart_service(service: str, dry_run: bool = False) -> str:
    """Validate a service restart request without changing the running service.

    This project intentionally implements only the dry-run control plane.  The
    Tool Gateway also forces ``dry_run=true`` for write tools, while this second
    check protects callers that accidentally invoke the tool directly.
    """

    normalized_service = service.strip()
    if not normalized_service:
        raise ValueError("service must not be empty")
    if not dry_run:
        raise PermissionError("restart_service only supports dry_run=true")

    return json.dumps(
        {
            "action": "restart_service",
            "service": normalized_service,
            "dry_run": True,
            "executed": False,
            "message": "restart validated; no service was restarted",
        },
        ensure_ascii=False,
    )


__all__ = ["restart_service"]
