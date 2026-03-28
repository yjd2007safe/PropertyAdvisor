from __future__ import annotations

import json

from shared_notifications.artifact_writer import NotificationArtifactWriter
from shared_notifications.openclaw_bridge_cli import main


def test_bridge_cli_dry_run(tmp_path, capsys) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-cli-1",
    )

    exit_code = main(["replay", "--artifact-path", str(artifact_dir), "--dry-run"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["record_count"] == 1
    assert payload["dry_run_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["queued_count"] == 0
    assert payload["event_ids"] == ["evt-cli-1"]


def test_bridge_cli_collect_and_ack(tmp_path, capsys) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-cli-2",
    )

    exit_code = main(["collect", "--artifact-path", str(artifact_dir), "--session-key", "agent:main:test"])
    assert exit_code == 0
    collected = json.loads(capsys.readouterr().out.strip())
    assert collected["record_count"] == 1
    assert collected["records"][0]["event_id"] == "evt-cli-2"
    assert collected["records"][0]["queued_at"] is None
    assert collected["records"][0]["ack"]["command"] == "ack"

    exit_code = main(
        [
            "ack",
            "--artifact-path",
            str(artifact_dir),
            "--session-key",
            "agent:main:test",
            "--event-id",
            "evt-cli-2",
            "--delivery-result-json",
            '{"status":"sent"}',
        ]
    )
    assert exit_code == 0
    acked = json.loads(capsys.readouterr().out.strip())
    assert acked["record"]["status"] == "sent"

    exit_code = main(["collect", "--artifact-path", str(artifact_dir)])
    assert exit_code == 0
    collected_again = json.loads(capsys.readouterr().out.strip())
    assert collected_again["record_count"] == 0


def test_bridge_cli_replay_queues_failures_into_inbox(tmp_path, capsys, monkeypatch) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="southport-qld-4215",
        status="completed",
        summary="Refresh done",
        event_id="evt-cli-3",
    )

    def fake_deliver(*args, **kwargs):
        raise RuntimeError("bridge-delivery-down")

    monkeypatch.setattr("shared_notifications.openclaw_bridge.deliver_to_openclaw_session", fake_deliver)

    exit_code = main([
        "replay",
        "--artifact-path",
        str(artifact_dir),
        "--session-key",
        "agent:main:test",
    ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["queued_count"] == 1
    inbox_path = artifact_dir / "bridge_inbox.jsonl"
    inbox = [json.loads(line) for line in inbox_path.read_text().splitlines() if line.strip()]
    assert inbox[0]["event_id"] == "evt-cli-3"
    assert inbox[0]["status"] == "queued"

    exit_code = main([
        "consume",
        "--artifact-path",
        str(artifact_dir),
        "--session-key",
        "agent:main:test",
    ])
    assert exit_code == 0
    consume_payload = json.loads(capsys.readouterr().out.strip())
    assert consume_payload["record_count"] == 1
    assert consume_payload["queued_count"] == 1
    assert consume_payload["records"][0]["event_id"] == "evt-cli-3"
    assert consume_payload["records"][0]["queued_at"] is not None
    assert consume_payload["records"][0]["ack"]["event_id"] == "evt-cli-3"

    exit_code = main(
        [
            "ack",
            "--artifact-path",
            str(artifact_dir),
            "--session-key",
            "agent:main:test",
            "--event-id",
            "evt-cli-3",
            "--status",
            "consumed",
            "--delivery-result-json",
            '{"status":"consumed-by-session"}',
        ]
    )
    assert exit_code == 0
    ack_payload = json.loads(capsys.readouterr().out.strip())
    assert ack_payload["record"]["status"] == "consumed"

    exit_code = main([
        "consume",
        "--artifact-path",
        str(artifact_dir),
        "--session-key",
        "agent:main:test",
    ])
    assert exit_code == 0
    consume_again = json.loads(capsys.readouterr().out.strip())
    assert consume_again["record_count"] == 0


def test_bridge_cli_orchestrate_prioritizes_review_and_auto_continue(tmp_path, capsys, monkeypatch) -> None:
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="slice-completed",
        status="completed",
        summary="Completed slice",
        event_id="evt-cli-4",
    )
    writer.write_event(
        event_type="ready_for_evaluation",
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id="slice-review",
        status="ready_for_evaluation",
        summary="Needs review",
        event_id="evt-cli-5",
    )

    def fake_deliver(*args, **kwargs):
        raise RuntimeError("bridge-delivery-down")

    monkeypatch.setattr("shared_notifications.openclaw_bridge.deliver_to_openclaw_session", fake_deliver)

    exit_code = main([
        "replay",
        "--artifact-path",
        str(artifact_dir),
        "--session-key",
        "agent:main:test",
    ])
    assert exit_code == 0
    _ = capsys.readouterr().out

    exit_code = main([
        "orchestrate",
        "--artifact-path",
        str(artifact_dir),
        "--session-key",
        "agent:main:test",
    ])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["record_count"] == 2
    assert payload["plans"][0]["event_id"] == "evt-cli-5"
    assert payload["plans"][0]["requires_human_review"] is True
    assert payload["plans"][1]["event_id"] == "evt-cli-4"
    assert payload["plans"][1]["auto_continue"] is True
