from __future__ import annotations

import json
from pathlib import Path

from shared_notifications.artifact_writer import NotificationArtifactWriter
from shared_notifications.openclaw_bridge import OpenClawNotificationBridge


class RecordingSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, *, session_key: str, message: str, artifact: dict) -> dict[str, str]:
        self.calls.append(
            {
                "session_key": session_key,
                "message": message,
                "event_id": artifact["event_id"],
            }
        )
        return {"status": "sent", "event_id": artifact["event_id"]}


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_bridge_replays_high_value_artifacts_once(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    sender = RecordingSender()
    bridge = OpenClawNotificationBridge(
        artifact_path=artifact_dir,
        session_key="agent:main:test",
        sender=sender,
    )

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-bridge-1",
    )

    first = bridge.replay_pending()
    second = bridge.replay_pending()

    assert [record["event_id"] for record in first] == ["evt-bridge-1"]
    assert second == []
    assert [call["event_id"] for call in sender.calls] == ["evt-bridge-1"]

    state = json.loads(bridge.state_path.read_text())
    assert state["delivered_event_ids"]["evt-bridge-1"]


def test_bridge_skips_non_high_value_events_by_default(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    sender = RecordingSender()
    bridge = OpenClawNotificationBridge(
        artifact_path=artifact_dir,
        session_key="agent:main:test",
        sender=sender,
    )

    writer.write_event(
        event_type="round_started",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="started",
        summary="Refresh started",
        event_id="evt-bridge-2",
    )

    records = bridge.replay_pending()
    assert records == []
    assert sender.calls == []
    assert not bridge.state_path.exists()


def test_bridge_queues_failures_into_inbox_without_marking_delivered(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)

    class FailingSender:
        def send(self, *, session_key: str, message: str, artifact: dict) -> dict[str, str]:
            raise RuntimeError("boom")

    bridge = OpenClawNotificationBridge(
        artifact_path=artifact_dir,
        session_key="agent:main:test",
        sender=FailingSender(),
    )

    writer.write_event(
        event_type="blocked",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="blocked",
        summary="Blocked",
        event_id="evt-bridge-3",
    )

    records = bridge.replay_pending()
    assert records[0]["status"] == "queued"
    assert records[0]["error"] == "boom"
    state = json.loads(bridge.state_path.read_text())
    assert state["queued_event_ids"]["evt-bridge-3"]
    assert "evt-bridge-3" not in state["delivered_event_ids"]
    lines = _read_jsonl(bridge.delivery_log_path)
    assert lines[0]["status"] == "queued"
    inbox = _read_jsonl(bridge.inbox_path)
    assert inbox[0]["status"] == "queued"


def test_bridge_dry_run_records_without_sender(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    bridge = OpenClawNotificationBridge(
        artifact_path=artifact_dir,
        sender=RecordingSender(),
    )

    writer.write_event(
        event_type="ready_for_evaluation",
        project="PropertyAdvisor",
        phase="phase2",
        round="round4",
        slice_id="phase2-round4-notification-artifact-foundation",
        status="ready",
        summary="Needs review",
        event_id="evt-bridge-4",
    )

    records = bridge.replay_pending(dry_run=True)
    assert records[0]["status"] == "dry-run"
    lines = _read_jsonl(bridge.delivery_log_path)
    assert lines[0]["status"] == "dry-run"
    state = json.loads(bridge.state_path.read_text())
    assert "evt-bridge-4" in state["delivered_event_ids"]


def test_bridge_can_collect_and_ack_without_sender(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    bridge = OpenClawNotificationBridge(artifact_path=artifact_dir, session_key="agent:main:test")

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-bridge-5",
    )

    pending = bridge.build_pending_records()
    assert pending[0]["event_id"] == "evt-bridge-5"
    assert "PropertyAdvisor notification: Refresh done" in pending[0]["message"]

    record = bridge.mark_delivered(
        artifact=pending[0]["artifact"],
        session_key="agent:main:test",
        delivery_result={"status": "sent"},
    )
    assert record["status"] == "sent"
    assert bridge.build_pending_records() == []


def test_bridge_does_not_duplicate_inbox_entries_for_already_queued_event(tmp_path) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)

    class FailingSender:
        def send(self, *, session_key: str, message: str, artifact: dict) -> dict[str, str]:
            raise RuntimeError("still-broken")

    bridge = OpenClawNotificationBridge(
        artifact_path=artifact_dir,
        session_key="agent:main:test",
        sender=FailingSender(),
    )

    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-bridge-6",
    )

    first = bridge.replay_pending()
    second = bridge.replay_pending()

    assert first[0]["status"] == "queued"
    assert second[0]["status"] == "queued"
    inbox = _read_jsonl(bridge.inbox_path)
    assert [entry["event_id"] for entry in inbox] == ["evt-bridge-6"]
