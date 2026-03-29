from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .artifact_schema import validate_notification_artifact


class NotificationArtifactConsumer:
    def __init__(
        self,
        *,
        base_path: Path = Path(".dev_pipeline/notifications"),
        state_path: Path | None = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.state_path = Path(state_path) if state_path is not None else self.base_path / ".consumer_state.json"

    def read_all(self) -> list[dict[str, Any]]:
        if not self.base_path.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        for path in sorted(self.base_path.glob("*.json")):
            if path == self.state_path:
                continue
            payload = json.loads(path.read_text())
            try:
                validate_notification_artifact(payload)
            except ValueError:
                # The canonical runtime may colocate non-artifact JSON files
                # (for example bridge handoff metadata) in this directory.
                continue
            artifacts.append(payload)
        return artifacts

    def consume(self, handler: Callable[[dict[str, Any]], Any]) -> list[dict[str, Any]]:
        processed = self._load_processed_event_ids()
        consumed: list[dict[str, Any]] = []
        seen_in_run = set(processed)

        for artifact in self.read_all():
            event_id = artifact["event_id"]
            if event_id in seen_in_run:
                continue
            handler(artifact)
            processed.append(event_id)
            seen_in_run.add(event_id)
            consumed.append(artifact)

        self._store_processed_event_ids(processed)
        return consumed

    def _load_processed_event_ids(self) -> list[str]:
        if not self.state_path.exists():
            return []
        payload = json.loads(self.state_path.read_text())
        event_ids = payload.get("processed_event_ids", [])
        if not isinstance(event_ids, list):
            return []
        return [event_id for event_id in event_ids if isinstance(event_id, str)]

    def _store_processed_event_ids(self, event_ids: list[str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        deduped: list[str] = []
        seen = set()
        for event_id in event_ids:
            if event_id in seen:
                continue
            seen.add(event_id)
            deduped.append(event_id)
        self.state_path.write_text(json.dumps({"processed_event_ids": deduped}, indent=2, sort_keys=True))
