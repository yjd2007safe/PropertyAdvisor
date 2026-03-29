from __future__ import annotations

from shared_notifications.artifact_consumer import NotificationArtifactConsumer
from shared_notifications.artifact_writer import NotificationArtifactWriter


def test_consumer_reads_and_processes_each_event_id_once(tmp_path) -> None:
    base_path = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(base_path)
    consumer = NotificationArtifactConsumer(base_path=base_path)

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

    handled: list[str] = []

    first_pass = consumer.consume(lambda artifact: handled.append(artifact["event_id"]))
    second_pass = consumer.consume(lambda artifact: handled.append(f"again:{artifact['event_id']}"))

    assert [artifact["event_id"] for artifact in first_pass] == ["evt-1", "evt-2"]
    assert second_pass == []
    assert handled == ["evt-1", "evt-2"]


def test_consumer_ignores_non_artifact_json_files(tmp_path) -> None:
    base_path = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(base_path)
    consumer = NotificationArtifactConsumer(base_path=base_path)

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase3",
        round="round1",
        slice_id="phase3-round1-runtime-realignment",
        status="completed",
        summary="done",
        event_id="evt-real-1",
    )
    (base_path / "bridge_handoff.json").write_text('{"runtime":"auto-dev-orchestrator"}')

    events = consumer.read_all()
    assert [artifact["event_id"] for artifact in events] == ["evt-real-1"]
