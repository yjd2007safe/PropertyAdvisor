"""PropertyAdvisor adapter for the shared notification artifact schema."""

from shared_notifications.artifact_schema import (
    NOTIFICATION_EVENT_TYPES,
    NOTIFICATION_SCHEMA_VERSION,
    build_notification_artifact,
    utc_now_iso,
    validate_notification_artifact,
)

__all__ = [
    "NOTIFICATION_EVENT_TYPES",
    "NOTIFICATION_SCHEMA_VERSION",
    "build_notification_artifact",
    "utc_now_iso",
    "validate_notification_artifact",
]
