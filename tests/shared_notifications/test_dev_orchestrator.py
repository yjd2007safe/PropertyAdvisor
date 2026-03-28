from __future__ import annotations

from shared_notifications.dev_orchestrator import build_dev_orchestration_plan, build_dev_orchestration_queue


def _record(event_type: str, *, event_id: str, queued_at: str | None = None) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "session_key": "agent:main:test",
        "message": f"msg-{event_id}",
        "created_at": f"2026-03-29T00:0{event_id[-1]}:00+00:00",
        "queued_at": queued_at,
        "ack": {"command": "ack", "event_id": event_id},
    }


def test_dev_orchestration_plan_flags_review_events() -> None:
    plan = build_dev_orchestration_plan(_record("ready_for_evaluation", event_id="evt-1", queued_at="2026-03-29T00:10:00+00:00"))
    assert plan["action"] == "notify_and_pause_for_review"
    assert plan["requires_human_review"] is True
    assert plan["auto_continue"] is False


def test_dev_orchestration_queue_prioritizes_review_then_recovery_then_progress() -> None:
    plans = build_dev_orchestration_queue(
        [
            _record("completed", event_id="evt-3", queued_at="2026-03-29T00:12:00+00:00"),
            _record("blocked", event_id="evt-2", queued_at="2026-03-29T00:11:00+00:00"),
            _record("ready_for_evaluation", event_id="evt-1", queued_at="2026-03-29T00:10:00+00:00"),
        ]
    )
    assert [plan["event_id"] for plan in plans] == ["evt-1", "evt-2", "evt-3"]


def test_dev_orchestration_plan_marks_completed_as_continue() -> None:
    plan = build_dev_orchestration_plan(_record("completed", event_id="evt-4"))
    assert plan["action"] == "notify_progress_and_continue"
    assert plan["auto_continue"] is True
    assert plan["requires_human_review"] is False
