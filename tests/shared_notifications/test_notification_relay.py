from __future__ import annotations

import json

from shared_notifications.artifact_writer import NotificationArtifactWriter
from shared_notifications.relay import NotificationRelay


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_relay_replays_pending_artifacts_once(tmp_path) -> None:
    base_path = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(base_path)
    relay = NotificationRelay(artifact_path=base_path)

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="completed",
        summary="done",
        event_id="evt-1",
    )
    writer.write_event(
        event_type="delivered",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="delivered",
        summary="relay done",
        event_id="evt-1",
    )
    writer.write_event(
        event_type="blocked",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="blocked",
        summary="blocked",
        event_id="evt-2",
    )

    delivered = relay.replay_pending()
    assert [record["event_id"] for record in delivered] == ["evt-1", "evt-2"]
    assert relay.delivery_log_path.exists()

    delivered_again = relay.replay_pending()
    assert delivered_again == []

    lines = _read_jsonl(relay.delivery_log_path)
    assert [record["event_id"] for record in lines] == ["evt-1", "evt-2"]
    assert all("rendered_text" in record for record in lines)
    assert all("payload" in record for record in lines)


def test_relay_can_forward_to_delivery_handler(tmp_path) -> None:
    base_path = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(base_path)
    delivered = []
    relay = NotificationRelay(
        artifact_path=base_path,
        delivery_handler=lambda artifact: delivered.append(artifact["event_id"]) or {"status": "sent"},
    )

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        status="completed",
        summary="done",
        event_id="evt-forward-1",
    )

    replayed = relay.replay_pending()
    assert delivered == ["evt-forward-1"]
    assert replayed[0]["delivery_result"]["status"] == "sent"
