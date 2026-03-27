from __future__ import annotations

import json
from pathlib import Path

from property_advisor.notifications.openclaw_bridge import OpenClawNotificationBridge
from shared_notifications.artifact_writer import NotificationArtifactWriter


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


def test_bridge_logs_failures_without_marking_state(tmp_path) -> None:
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
    assert records[0]["status"] == "failed"
    assert records[0]["error"] == "boom"
    assert not bridge.state_path.exists()
    lines = _read_jsonl(bridge.delivery_log_path)
    assert lines[0]["status"] == "failed"


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
