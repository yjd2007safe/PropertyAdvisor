from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .artifact_consumer import NotificationArtifactConsumer
from .artifact_schema import utc_now_iso, validate_notification_artifact
from .render import render_notification_payload, render_notification_text


class NotificationRelay:
    """Scan notification artifacts and render a durable local delivery log."""

    def __init__(
        self,
        *,
        artifact_path: Path = Path(".dev_pipeline/notifications"),
        delivery_log_path: Path | None = None,
        state_path: Path | None = None,
        renderer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.artifact_path = Path(artifact_path)
        self.delivery_log_path = (
            Path(delivery_log_path)
            if delivery_log_path is not None
            else self.artifact_path / "delivery_log.jsonl"
        )
        self.consumer = NotificationArtifactConsumer(
            base_path=self.artifact_path,
            state_path=state_path,
        )
        self.renderer = renderer or render_notification_payload

    def replay_pending(self) -> list[dict[str, Any]]:
        delivered: list[dict[str, Any]] = []

        def handle(artifact: dict[str, Any]) -> None:
            validate_notification_artifact(artifact)
            payload = dict(self.renderer(artifact))
            record = {
                "event_id": artifact["event_id"],
                "event_type": artifact["event_type"],
                "created_at": artifact["created_at"],
                "delivered_at": utc_now_iso(),
                "payload": payload,
                "rendered_text": render_notification_text(artifact),
            }
            self._append_delivery(record)
            delivered.append(record)

        self.consumer.consume(handle)
        return delivered

    def _append_delivery(self, record: Mapping[str, Any]) -> None:
        self.delivery_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.delivery_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), sort_keys=True))
            handle.write("\n")
