from __future__ import annotations

import json
from typing import Any, Mapping


def render_notification_text(artifact: Mapping[str, Any]) -> str:
    """Render a compact local notification message."""
    return (
        f"[{artifact['event_type']}] {artifact['summary']} "
        f"(project={artifact['project']}, phase={artifact['phase']}, round={artifact['round']}, "
        f"slice={artifact['slice_id']})"
    )


def render_openclaw_message(artifact: Mapping[str, Any]) -> str:
    """Render a chat-friendly message for delivery into an OpenClaw session."""
    lines = [
        f"PropertyAdvisor notification: {artifact['summary']}",
        f"- event: {artifact['event_type']}",
        f"- status: {artifact['status']}",
        f"- phase: {artifact['phase']}",
        f"- round: {artifact['round']}",
        f"- slice: {artifact['slice_id']}",
    ]
    details = artifact.get("details") or {}
    if details:
        lines.append(f"- details: {json.dumps(details, ensure_ascii=False, sort_keys=True)}")
    artifacts = artifact.get("artifacts") or []
    if artifacts:
        lines.append(f"- artifacts: {json.dumps(artifacts, ensure_ascii=False, sort_keys=True)}")
    lines.append(f"- created_at: {artifact['created_at']}")
    return "\n".join(lines)


def render_notification_payload(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Render a minimal payload suitable for local replay logs."""
    return {
        "text": render_notification_text(artifact),
        "openclaw_message": render_openclaw_message(artifact),
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
