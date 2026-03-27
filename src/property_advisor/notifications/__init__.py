"""PropertyAdvisor adapter for shared notification utilities."""

from shared_notifications import (
    NOTIFICATION_EVENT_TYPES,
    NOTIFICATION_SCHEMA_VERSION,
    NotificationArtifactConsumer,
    NotificationArtifactWriter,
    NotificationRelay,
    PipelineNotificationHooks,
    build_notification_artifact,
    render_notification_payload,
    render_notification_text,
    render_openclaw_message,
    utc_now_iso,
    validate_notification_artifact,
)

from .openclaw_bridge import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DELIVERY_LOG_FILENAME,
    DEFAULT_EVENT_TYPES,
    DEFAULT_STATE_FILENAME,
    OpenClawNotificationBridge,
    OpenClawSessionSender,
)

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
    "render_notification_payload",
    "render_notification_text",
    "render_openclaw_message",
    "utc_now_iso",
    "validate_notification_artifact",
]
