"""Shared notification runtime for local pipeline artifacts."""

from .artifact_consumer import NotificationArtifactConsumer
from .artifact_schema import (
    NOTIFICATION_EVENT_TYPES,
    NOTIFICATION_SCHEMA_VERSION,
    build_notification_artifact,
    utc_now_iso,
    validate_notification_artifact,
)
from .artifact_writer import NotificationArtifactWriter
from .hooks import PipelineNotificationHooks
from .relay import NotificationRelay
from .render import render_notification_payload, render_notification_text

__all__ = [
    "NOTIFICATION_EVENT_TYPES",
    "NOTIFICATION_SCHEMA_VERSION",
    "NotificationArtifactConsumer",
    "NotificationArtifactWriter",
    "NotificationRelay",
    "PipelineNotificationHooks",
    "build_notification_artifact",
    "render_notification_payload",
    "render_notification_text",
    "utc_now_iso",
    "validate_notification_artifact",
]
