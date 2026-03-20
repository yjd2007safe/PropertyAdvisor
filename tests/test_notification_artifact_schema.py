from __future__ import annotations

import pytest

from property_advisor.notifications.artifact_schema import (
    NOTIFICATION_SCHEMA_VERSION,
    build_notification_artifact,
    validate_notification_artifact,
)


def test_build_notification_artifact_populates_required_fields_and_origin_defaults() -> None:
    artifact = build_notification_artifact(
        event_type="round_started",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="started",
        summary="Round 5 started",
        origin={"channel": "telegram", "chat_id": "123"},
        delivery_targets=[{"channel": "telegram", "chat_id": "123"}],
    )

    assert artifact["schema_version"] == NOTIFICATION_SCHEMA_VERSION
    assert artifact["origin"]["channel"] == "telegram"
    assert artifact["origin"]["chat_id"] == "123"
    assert artifact["origin"]["thread_id"] is None
    assert artifact["delivery"]["status"] == "pending"


def test_validate_notification_artifact_rejects_unknown_event_type() -> None:
    artifact = build_notification_artifact(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="completed",
        summary="done",
    )
    artifact["event_type"] = "unknown"

    with pytest.raises(ValueError):
        validate_notification_artifact(artifact)
