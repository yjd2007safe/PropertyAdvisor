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
