from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .artifact_schema import build_notification_artifact, utc_now_iso, validate_notification_artifact


class NotificationArtifactWriter:
    def __init__(self, base_path: Path = Path(".dev_pipeline/notifications")) -> None:
        self.base_path = Path(base_path)

    def persist_artifact(self, artifact: Mapping[str, Any]) -> Path:
        validate_notification_artifact(artifact)
        self.base_path.mkdir(parents=True, exist_ok=True)
        filename = f"{artifact['created_at'].replace(':', '').replace('+', '_')}-{artifact['event_id']}.json"
        path = self.base_path / filename
        path.write_text(json.dumps(dict(artifact), indent=2, sort_keys=True))
        return path

    def write_event(
        self,
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
        delivery_handler: Optional[Callable[[dict[str, Any]], Mapping[str, Any]]] = None,
    ) -> tuple[dict[str, Any], Path]:
        artifact = build_notification_artifact(
            event_type=event_type,
            project=project,
            phase=phase,
            round=round,
            slice_id=slice_id,
            status=status,
            summary=summary,
            details=details,
            artifacts=artifacts,
            origin=origin,
            delivery_targets=delivery_targets,
            delivery=delivery,
            event_id=event_id,
            created_at=created_at,
        )
        path = self.persist_artifact(artifact)

        if delivery_handler is None:
            return artifact, path

        try:
            delivery_result = dict(delivery_handler(deepcopy(artifact)))
        except Exception as exc:
            artifact["delivery"] = {
                "status": "failed",
                "attempted_at": utc_now_iso(),
                "failure": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }
            self.persist_artifact(artifact)
            return artifact, path

        merged_delivery = dict(artifact["delivery"])
        merged_delivery.update(delivery_result)
        merged_delivery.setdefault("attempted_at", utc_now_iso())
        artifact["delivery"] = merged_delivery
        self.persist_artifact(artifact)
        return artifact, path
