from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from .artifact_consumer import NotificationArtifactConsumer
from .artifact_schema import utc_now_iso, validate_notification_artifact
from .openclaw_delivery import deliver_to_openclaw_session, resolve_session_key
from .render import render_openclaw_message

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
DEFAULT_INBOX_FILENAME = "bridge_inbox.jsonl"


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
        inbox_path: Path | None = None,
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
        self.inbox_path = Path(inbox_path) if inbox_path is not None else self.artifact_path / DEFAULT_INBOX_FILENAME
        self.session_key = resolve_session_key(session_key)
        self.sender = sender or OpenClawSessionSender()
        self.event_types = frozenset(event_types or DEFAULT_EVENT_TYPES)
        self.consumer = NotificationArtifactConsumer(
            base_path=self.artifact_path,
            state_path=self.state_path,
        )

    def collect_pending(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        delivered_state, _queued_state = self._load_state()
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

    def build_pending_records(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        _delivered_state, queued_state = self._load_state()
        records: list[dict[str, Any]] = []
        for artifact in self.collect_pending(limit=limit):
            records.append(
                {
                    "event_id": artifact["event_id"],
                    "event_type": artifact["event_type"],
                    "session_key": self.session_key,
                    "message": render_openclaw_message(artifact),
                    "created_at": artifact["created_at"],
                    "queued_at": queued_state.get(artifact["event_id"]),
                    "artifact": artifact,
                }
            )
        return records

    def mark_delivered(
        self,
        *,
        artifact: Mapping[str, Any],
        session_key: str | None,
        delivery_result: Mapping[str, Any] | None = None,
        status: str = "sent",
    ) -> dict[str, Any]:
        attempted_at = utc_now_iso()
        record = {
            "event_id": artifact["event_id"],
            "event_type": artifact["event_type"],
            "session_key": session_key,
            "message": render_openclaw_message(artifact),
            "created_at": artifact["created_at"],
            "attempted_at": attempted_at,
            "status": status,
        }
        if delivery_result is not None:
            record["delivery_result"] = dict(delivery_result)
        delivered_state, queued_state = self._load_state()
        delivered_state[artifact["event_id"]] = attempted_at
        queued_state.pop(artifact["event_id"], None)
        self._store_state(delivered_state=delivered_state, queued_state=queued_state)
        self._append_delivery_log(record)
        return record

    def mark_failed(
        self,
        *,
        artifact: Mapping[str, Any],
        session_key: str | None,
        error: str,
    ) -> dict[str, Any]:
        record = {
            "event_id": artifact["event_id"],
            "event_type": artifact["event_type"],
            "session_key": session_key,
            "message": render_openclaw_message(artifact),
            "created_at": artifact["created_at"],
            "attempted_at": utc_now_iso(),
            "status": "failed",
            "error": error,
        }
        self._append_delivery_log(record)
        return record

    def mark_queued(
        self,
        *,
        artifact: Mapping[str, Any],
        session_key: str | None,
        error: str,
        queue_reason: str = "sender-unavailable",
    ) -> dict[str, Any]:
        queued_at = utc_now_iso()
        delivered_state, queued_state = self._load_state()
        first_queue_for_event = artifact["event_id"] not in queued_state
        queued_state[artifact["event_id"]] = queued_at
        self._store_state(delivered_state=delivered_state, queued_state=queued_state)
        record = {
            "event_id": artifact["event_id"],
            "event_type": artifact["event_type"],
            "session_key": session_key,
            "message": render_openclaw_message(artifact),
            "created_at": artifact["created_at"],
            "attempted_at": queued_at,
            "queued_at": queued_at,
            "status": "queued",
            "queue_reason": queue_reason,
            "error": error,
        }
        self._append_delivery_log(record)
        if first_queue_for_event:
            self._append_inbox(record)
        return record

    def replay_pending(
        self,
        *,
        limit: int | None = None,
        dry_run: bool = False,
        queue_on_failure: bool = True,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for pending in self.build_pending_records(limit=limit):
            artifact = pending["artifact"]
            try:
                if dry_run:
                    record = self.mark_delivered(
                        artifact=artifact,
                        session_key=self.session_key,
                        delivery_result={"status": "dry-run"},
                        status="dry-run",
                    )
                else:
                    if not self.session_key:
                        raise RuntimeError(
                            "Bridge delivery requires --session-key or OPENCLAW_NOTIFICATION_SESSION_KEY."
                        )
                    delivery_result = self.sender.send(
                        session_key=self.session_key,
                        message=pending["message"],
                        artifact=artifact,
                    )
                    record = self.mark_delivered(
                        artifact=artifact,
                        session_key=self.session_key,
                        delivery_result=delivery_result,
                        status="sent",
                    )
            except Exception as exc:  # noqa: BLE001
                if queue_on_failure:
                    record = self.mark_queued(
                        artifact=artifact,
                        session_key=self.session_key,
                        error=str(exc),
                    )
                else:
                    record = self.mark_failed(
                        artifact=artifact,
                        session_key=self.session_key,
                        error=str(exc),
                    )
            records.append(record)
        return records

    def _load_state(self) -> tuple[dict[str, str], dict[str, str]]:
        if not self.state_path.exists():
            return {}, {}
        payload = json.loads(self.state_path.read_text())
        delivered = payload.get("delivered_event_ids", {})
        queued = payload.get("queued_event_ids", {})
        if not isinstance(delivered, dict):
            delivered = {}
        if not isinstance(queued, dict):
            queued = {}
        delivered_state = {
            event_id: delivered_at
            for event_id, delivered_at in delivered.items()
            if isinstance(event_id, str) and isinstance(delivered_at, str)
        }
        queued_state = {
            event_id: queued_at
            for event_id, queued_at in queued.items()
            if isinstance(event_id, str) and isinstance(queued_at, str)
        }
        return delivered_state, queued_state

    def _store_state(self, *, delivered_state: Mapping[str, str], queued_state: Mapping[str, str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "delivered_event_ids": dict(sorted(delivered_state.items())),
            "queued_event_ids": dict(sorted(queued_state.items())),
        }
        self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _append_delivery_log(self, record: Mapping[str, Any]) -> None:
        self.delivery_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.delivery_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def _append_inbox(self, record: Mapping[str, Any]) -> None:
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)
        with self.inbox_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
