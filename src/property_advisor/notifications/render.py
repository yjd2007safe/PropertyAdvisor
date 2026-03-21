from __future__ import annotations

from typing import Any, Mapping


def render_notification_text(artifact: Mapping[str, Any]) -> str:
    """Render a compact local notification message."""
    return (
        f"[{artifact['event_type']}] {artifact['summary']} "
        f"(project={artifact['project']}, phase={artifact['phase']}, round={artifact['round']}, "
        f"slice={artifact['slice_id']})"
    )


def render_notification_payload(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Render a minimal payload suitable for local replay logs."""
    return {
        "text": render_notification_text(artifact),
        "event_type": artifact["event_type"],
        "status": artifact["status"],
        "project": artifact["project"],
        "phase": artifact["phase"],
        "round": artifact["round"],
        "slice_id": artifact["slice_id"],
        "summary": artifact["summary"],
        "details": artifact.get("details", {}),
        "artifacts": artifact.get("artifacts", []),
        "delivery_targets": artifact.get("delivery_targets", []),
        "origin": artifact.get("origin", {}),
        "created_at": artifact["created_at"],
    }
