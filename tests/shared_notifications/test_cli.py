import json
from pathlib import Path

from shared_notifications import cli
from shared_notifications.artifact_writer import NotificationArtifactWriter


def test_cli_emit_writes_artifact(tmp_path, capsys):
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    args = [
        "emit",
        "--project",
        "PropertyAdvisor",
        "--phase",
        "phase1",
        "--round",
        "round1",
        "--slice-id",
        "slice1",
        "--event-type",
        "round_started",
        "--status",
        "started",
        "--summary",
        "Round started",
        "--artifact-path",
        str(artifact_dir),
        "--details-json",
        '{"note": "hello"}',
        "--artifacts-json",
        '[{"name": "artifact-1"}]',
        "--origin-json",
        '{"channel": "local"}',
        "--delivery-targets-json",
        '[{"channel": "local"}]',
        "--event-id",
        "event-123",
        "--created-at",
        "2024-01-01T00:00:00+00:00",
    ]

    exit_code = cli.main(args)

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["status"] == "ok"

    artifact = payload["artifact"]
    assert artifact["event_id"] == "event-123"
    assert artifact["event_type"] == "round_started"
    assert artifact["summary"] == "Round started"

    artifact_path = Path(payload["artifact_path"])
    assert artifact_path.exists()
    saved = json.loads(artifact_path.read_text())
    assert saved["event_id"] == "event-123"


def test_cli_replay_idempotent(tmp_path, capsys):
    artifact_dir = tmp_path / ".dev_pipeline" / "notifications"
    writer = NotificationArtifactWriter(artifact_dir)
    writer.write_event(
        event_type="round_started",
        project="PropertyAdvisor",
        phase="phase1",
        round="round1",
        slice_id="slice1",
        status="started",
        summary="Round started",
        event_id="event-1",
    )
    writer.write_event(
        event_type="completed",
        project="PropertyAdvisor",
        phase="phase1",
        round="round1",
        slice_id="slice1",
        status="completed",
        summary="Done",
        event_id="event-2",
    )

    exit_code = cli.main(["replay", "--artifact-path", str(artifact_dir)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["replayed_count"] == 2
    assert set(payload["delivered_event_ids"]) == {"event-1", "event-2"}

    exit_code = cli.main(["replay", "--artifact-path", str(artifact_dir)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["replayed_count"] == 0
    assert payload["delivered_event_ids"] == []

    delivery_log_path = Path(payload["delivery_log_path"])
    assert delivery_log_path.exists()
    lines = delivery_log_path.read_text().strip().splitlines()
    assert len(lines) == 2

    missing_dir = tmp_path / "missing" / "notifications"
    exit_code = cli.main(["replay", "--artifact-path", str(missing_dir)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["replayed_count"] == 0
