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
from .openclaw_bridge import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DELIVERY_LOG_FILENAME,
    DEFAULT_EVENT_TYPES,
    DEFAULT_STATE_FILENAME,
    OpenClawNotificationBridge,
    OpenClawSessionSender,
)
from .openclaw_delivery import build_sessions_send_params, deliver_to_openclaw_session, resolve_session_key
from .relay import NotificationRelay
from .render import render_notification_payload, render_notification_text, render_openclaw_message

__all__ = [
    "NOTIFICATION_EVENT_TYPES",
    "NOTIFICATION_SCHEMA_VERSION",
    "NotificationArtifactConsumer",
    "NotificationArtifactWriter",
    "DEFAULT_ARTIFACT_PATH",
    "DEFAULT_DELIVERY_LOG_FILENAME",
    "DEFAULT_EVENT_TYPES",
    "DEFAULT_STATE_FILENAME",
    "NotificationRelay",
    "OpenClawNotificationBridge",
    "OpenClawSessionSender",
    "PipelineNotificationHooks",
    "build_notification_artifact",
    "build_sessions_send_params",
    "deliver_to_openclaw_session",
    "render_notification_payload",
    "render_notification_text",
    "render_openclaw_message",
    "resolve_session_key",
    "utc_now_iso",
    "validate_notification_artifact",
]
