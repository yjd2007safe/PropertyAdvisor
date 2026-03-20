from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from property_advisor.notifications.artifact_writer import NotificationArtifactWriter


class PipelineNotificationHooks:
    def __init__(
        self,
        *,
        project: str,
        phase: str,
        round: str,
        slice_id: str,
        origin: Optional[Mapping[str, Any]] = None,
        delivery_targets: Optional[list[Mapping[str, Any]]] = None,
        writer: NotificationArtifactWriter | None = None,
        artifact_path: Path = Path(".dev_pipeline/notifications"),
        delivery_handler: Optional[Callable[[dict[str, Any]], Mapping[str, Any]]] = None,
    ) -> None:
        self.project = project
        self.phase = phase
        self.round = str(round)
        self.slice_id = slice_id
        self.origin = dict(origin or {})
        self.delivery_targets = list(delivery_targets or [])
        self.writer = writer or NotificationArtifactWriter(artifact_path)
        self.delivery_handler = delivery_handler

    def emit(
        self,
        *,
        event_type: str,
        status: str,
        summary: str,
        details: Optional[Mapping[str, Any]] = None,
        artifacts: Optional[list[Mapping[str, Any]]] = None,
        origin: Optional[Mapping[str, Any]] = None,
        delivery_targets: Optional[list[Mapping[str, Any]]] = None,
        event_id: Optional[str] = None,
        delivery_handler: Optional[Callable[[dict[str, Any]], Mapping[str, Any]]] = None,
    ) -> tuple[dict[str, Any], Path]:
        merged_origin = deepcopy(self.origin)
        if origin:
            merged_origin.update(origin)
        merged_delivery_targets = deepcopy(self.delivery_targets)
        if delivery_targets:
            merged_delivery_targets.extend(delivery_targets)
        return self.writer.write_event(
            event_type=event_type,
            project=self.project,
            phase=self.phase,
            round=self.round,
            slice_id=self.slice_id,
            status=status,
            summary=summary,
            details=details,
            artifacts=artifacts,
            origin=merged_origin,
            delivery_targets=merged_delivery_targets,
            event_id=event_id,
            delivery_handler=delivery_handler or self.delivery_handler,
        )

    def round_started(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="round_started", status="started", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def ready_for_evaluation(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="ready_for_evaluation", status="ready_for_evaluation", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def evaluated(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="evaluated", status="evaluated", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def evaluation_failed(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="evaluation_failed", status="evaluation_failed", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def delivered(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None, delivery_handler: Optional[Callable[[dict[str, Any]], Mapping[str, Any]]] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="delivered", status="delivered", summary=summary, details=details, artifacts=artifacts, event_id=event_id, delivery_handler=delivery_handler)

    def completed(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="completed", status="completed", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def blocked(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="blocked", status="blocked", summary=summary, details=details, artifacts=artifacts, event_id=event_id)

    def interrupted(self, *, summary: str, details: Optional[Mapping[str, Any]] = None, artifacts: Optional[list[Mapping[str, Any]]] = None, event_id: Optional[str] = None) -> tuple[dict[str, Any], Path]:
        return self.emit(event_type="interrupted", status="interrupted", summary=summary, details=details, artifacts=artifacts, event_id=event_id)
