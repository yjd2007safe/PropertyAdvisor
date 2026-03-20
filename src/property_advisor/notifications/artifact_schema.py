from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

NOTIFICATION_SCHEMA_VERSION = "1.0"
NOTIFICATION_EVENT_TYPES = {
    "round_started",
    "ready_for_evaluation",
    "evaluated",
    "evaluation_failed",
    "delivered",
    "completed",
    "blocked",
    "interrupted",
}
_REQUIRED_FIELDS = {
    "schema_version",
    "event_id",
    "event_type",
    "project",
    "phase",
    "round",
    "slice_id",
    "status",
    "summary",
    "details",
    "artifacts",
    "origin",
    "delivery_targets",
    "delivery",
    "created_at",
}
_ORIGIN_FIELDS = (
    "channel",
    "chat_id",
    "thread_id",
    "session_key",
    "user_id",
    "reply_mode",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_iso8601_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _normalize_origin(origin: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if origin:
        normalized.update(deepcopy(dict(origin)))
    for field in _ORIGIN_FIELDS:
        normalized.setdefault(field, None)
    return normalized


def _normalize_delivery(delivery: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "status": "pending",
        "attempted_at": None,
        "failure": None,
    }
    if delivery:
        normalized.update(deepcopy(dict(delivery)))
    return normalized


def build_notification_artifact(
    *,
    event_type: str,
    project: str,
    phase: str,
    round: str,
    slice_id: str,
    status: str,
    summary: str,
    details: Optional[Mapping[str, Any]] = None,
    artifacts: Optional[list[Mapping[str, Any]]] = None,
    origin: Optional[Mapping[str, Any]] = None,
    delivery_targets: Optional[list[Mapping[str, Any]]] = None,
    delivery: Optional[Mapping[str, Any]] = None,
    event_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> dict[str, Any]:
    artifact = {
        "schema_version": NOTIFICATION_SCHEMA_VERSION,
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "project": project,
        "phase": phase,
        "round": str(round),
        "slice_id": slice_id,
        "status": status,
        "summary": summary,
        "details": deepcopy(dict(details or {})),
        "artifacts": deepcopy(list(artifacts or [])),
        "origin": _normalize_origin(origin),
        "delivery_targets": deepcopy(list(delivery_targets or [])),
        "delivery": _normalize_delivery(delivery),
        "created_at": created_at or utc_now_iso(),
    }
    validate_notification_artifact(artifact)
    return artifact


def validate_notification_artifact(artifact: Mapping[str, Any]) -> None:
    missing = sorted(_REQUIRED_FIELDS.difference(artifact.keys()))
    if missing:
        raise ValueError(f"notification artifact missing required fields: {', '.join(missing)}")

    if artifact["schema_version"] != NOTIFICATION_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported notification schema version: {artifact['schema_version']!r}"
        )

    if artifact["event_type"] not in NOTIFICATION_EVENT_TYPES:
        raise ValueError(f"unsupported notification event_type: {artifact['event_type']!r}")

    for field in ("event_id", "project", "phase", "round", "slice_id", "status", "summary"):
        value = artifact.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"notification artifact field {field!r} must be a non-empty string")

    if not isinstance(artifact["details"], MutableMapping):
        raise ValueError("notification artifact field 'details' must be an object")
    if not isinstance(artifact["artifacts"], list):
        raise ValueError("notification artifact field 'artifacts' must be a list")
    if not isinstance(artifact["delivery_targets"], list):
        raise ValueError("notification artifact field 'delivery_targets' must be a list")
    if not isinstance(artifact["origin"], MutableMapping):
        raise ValueError("notification artifact field 'origin' must be an object")
    if not isinstance(artifact["delivery"], MutableMapping):
        raise ValueError("notification artifact field 'delivery' must be an object")
    if not isinstance(artifact["created_at"], str) or not _is_iso8601_timestamp(artifact["created_at"]):
        raise ValueError("notification artifact field 'created_at' must be an ISO-8601 timestamp")

    for field in _ORIGIN_FIELDS:
        artifact["origin"].get(field)
