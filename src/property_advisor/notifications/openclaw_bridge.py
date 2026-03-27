from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from shared_notifications.artifact_consumer import NotificationArtifactConsumer
from shared_notifications.artifact_schema import utc_now_iso, validate_notification_artifact
from shared_notifications.openclaw_delivery import (
    deliver_to_openclaw_session,
    resolve_session_key,
)
from shared_notifications.render import render_openclaw_message

DEFAULT_EVENT_TYPES = frozenset(
    {
        "completed",
        "blocked",
        "interrupted",
        "ready_for_evaluation",
        "evaluation_failed",
        "delivered",
        "evaluated",
    }
)
DEFAULT_ARTIFACT_PATH = Path(".dev_pipeline/notifications")
DEFAULT_STATE_FILENAME = "bridge_state.json"
DEFAULT_DELIVERY_LOG_FILENAME = "bridge_delivery_log.jsonl"


class NotificationSender(Protocol):
    def send(
        self,
        *,
        session_key: str,
        message: str,
        artifact: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class OpenClawSessionSender:
    def __init__(self, *, timeout_seconds: int = 0) -> None:
        self.timeout_seconds = timeout_seconds

    def send(
        self,
        *,
        session_key: str,
        message: str,
        artifact: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return deliver_to_openclaw_session(
            artifact,
            session_key=session_key,
            timeout_seconds=self.timeout_seconds,
        )


class OpenClawNotificationBridge:
    def __init__(
        self,
        *,
        artifact_path: Path = DEFAULT_ARTIFACT_PATH,
        state_path: Path | None = None,
        delivery_log_path: Path | None = None,
        session_key: str | None = None,
        sender: NotificationSender | None = None,
        event_types: Iterable[str] | None = None,
    ) -> None:
        self.artifact_path = Path(artifact_path)
        self.state_path = Path(state_path) if state_path is not None else self.artifact_path / DEFAULT_STATE_FILENAME
        self.delivery_log_path = (
            Path(delivery_log_path)
            if delivery_log_path is not None
            else self.artifact_path / DEFAULT_DELIVERY_LOG_FILENAME
        )
        self.session_key = resolve_session_key(session_key)
        self.sender = sender or OpenClawSessionSender()
        self.event_types = frozenset(event_types or DEFAULT_EVENT_TYPES)
        self.consumer = NotificationArtifactConsumer(
            base_path=self.artifact_path,
            state_path=self.state_path,
        )

    def collect_pending(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        delivered_state = self._load_state()
        pending: list[dict[str, Any]] = []
        for artifact in self.consumer.read_all():
            validate_notification_artifact(artifact)
            if artifact["event_type"] not in self.event_types:
                continue
            if artifact["event_id"] in delivered_state:
                continue
            pending.append(artifact)
            if limit is not None and len(pending) >= limit:
                break
        return pending

    def replay_pending(self, *, limit: int | None = None, dry_run: bool = False) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        state = self._load_state()
        pending = self.collect_pending(limit=limit)
        for artifact in pending:
            message = render_openclaw_message(artifact)
            record = {
                "event_id": artifact["event_id"],
                "event_type": artifact["event_type"],
                "session_key": self.session_key,
                "message": message,
                "created_at": artifact["created_at"],
                "attempted_at": utc_now_iso(),
            }
            try:
                if dry_run:
                    delivery_result: Mapping[str, Any] = {"status": "dry-run"}
                else:
                    if not self.session_key:
                        raise RuntimeError(
                            "Bridge delivery requires --session-key or OPENCLAW_NOTIFICATION_SESSION_KEY."
                        )
                    delivery_result = self.sender.send(
                        session_key=self.session_key,
                        message=message,
                        artifact=artifact,
                    )
                record["status"] = "sent" if not dry_run else "dry-run"
                record["delivery_result"] = dict(delivery_result)
                state[artifact["event_id"]] = record["attempted_at"]
                self._store_state(state)
            except Exception as exc:  # noqa: BLE001
                record["status"] = "failed"
                record["error"] = str(exc)
            self._append_delivery_log(record)
            records.append(record)
        return records

    def _load_state(self) -> dict[str, str]:
        if not self.state_path.exists():
            return {}
        payload = json.loads(self.state_path.read_text())
        delivered = payload.get("delivered_event_ids", {})
        if not isinstance(delivered, dict):
            return {}
        return {
            event_id: delivered_at
            for event_id, delivered_at in delivered.items()
            if isinstance(event_id, str) and isinstance(delivered_at, str)
        }

    def _store_state(self, state: Mapping[str, str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"delivered_event_ids": dict(sorted(state.items()))}
        self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _append_delivery_log(self, record: Mapping[str, Any]) -> None:
        self.delivery_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.delivery_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
