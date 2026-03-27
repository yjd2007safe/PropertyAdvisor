from __future__ import annotations

import json

from property_advisor.notifications.openclaw_bridge_cli import main
from shared_notifications.artifact_writer import NotificationArtifactWriter


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

    exit_code = main(["--artifact-path", str(artifact_dir), "--dry-run"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["record_count"] == 1
    assert payload["dry_run_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["event_ids"] == ["evt-cli-1"]
