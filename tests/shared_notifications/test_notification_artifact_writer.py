from __future__ import annotations

import json

from shared_notifications.artifact_writer import NotificationArtifactWriter


def test_writer_persists_notification_artifact(tmp_path) -> None:
    writer = NotificationArtifactWriter(tmp_path / ".dev_pipeline" / "notifications")

    artifact, path = writer.write_event(
        event_type="round_started",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="started",
        summary="Round 5 started",
    )

    persisted = json.loads(path.read_text())
    assert path.parent.name == "notifications"
    assert persisted["event_id"] == artifact["event_id"]
    assert persisted["event_type"] == "round_started"


def test_writer_persists_artifact_even_when_delivery_fails(tmp_path) -> None:
    writer = NotificationArtifactWriter(tmp_path / ".dev_pipeline" / "notifications")

    artifact, path = writer.write_event(
        event_type="delivered",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="delivered",
        summary="Relay attempted",
        delivery_targets=[{"channel": "telegram", "chat_id": "123"}],
        delivery_handler=lambda _: (_ for _ in ()).throw(RuntimeError("gateway unavailable")),
    )

    persisted = json.loads(path.read_text())
    assert artifact["delivery"]["status"] == "failed"
    assert persisted["delivery"]["status"] == "failed"
    assert persisted["delivery"]["failure"]["message"] == "gateway unavailable"
