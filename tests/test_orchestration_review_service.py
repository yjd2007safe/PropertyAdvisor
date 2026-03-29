import json
from pathlib import Path

from property_advisor.api.services import get_orchestration_review_status


def _write_artifact(base_path: Path, *, event_type: str, event_id: str, created_at: str) -> None:
    payload = {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": event_type,
        "project": "PropertyAdvisor",
        "phase": "phase3",
        "round": "round3",
        "slice_id": "orchestration-review",
        "status": "ok",
        "summary": f"{event_type} update",
        "details": {"note": "test"},
        "artifacts": [],
        "origin": {"channel": "test", "session_key": "session-1"},
        "delivery_targets": [],
        "delivery": {"status": "pending", "attempted_at": None, "failure": None},
        "created_at": created_at,
    }
    (base_path / f"{event_id}.json").write_text(json.dumps(payload))


def test_orchestration_review_status_flags_manual_review(tmp_path: Path) -> None:
    _write_artifact(
        tmp_path,
        event_type="completed",
        event_id="evt-progress",
        created_at="2026-03-28T10:00:00+00:00",
    )
    _write_artifact(
        tmp_path,
        event_type="ready_for_evaluation",
        event_id="evt-review",
        created_at="2026-03-29T09:30:00+00:00",
    )

    status = get_orchestration_review_status(artifact_path=tmp_path)

    assert status.summary.current_state == "awaiting_review"
    assert status.summary.review_needed is True
    assert status.summary.review_required_count == 1
    assert status.summary.pending_count == 2
    assert status.summary.latest_event_at == "2026-03-29T09:30:00+00:00"
    assert status.plans[0].event_id == "evt-review"
    assert status.plans[0].requires_human_review is True


def test_orchestration_review_status_empty_queue(tmp_path: Path) -> None:
    status = get_orchestration_review_status(artifact_path=tmp_path)

    assert status.summary.current_state == "idle"
    assert status.summary.review_needed is False
    assert status.summary.pending_count == 0
    assert status.summary.freshness == "empty"
    assert status.summary.latest_event_at is None
    assert status.plans == []
