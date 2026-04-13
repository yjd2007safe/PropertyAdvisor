import json
from pathlib import Path

from property_advisor.api.schemas import OrchestrationReviewActionRequest
from property_advisor.api.services import apply_orchestration_review_action, get_orchestration_review_status


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
    assert "apply reviewer action state" in status.summary.next_action
    assert "active follow-up states" in status.summary.next_action.lower()
    assert "awaiting operator outcome ×1" in status.summary.next_action.lower()
    assert "carry-forward summary" in status.summary.next_action.lower()
    assert "outcome triage" in status.summary.next_action.lower()
    assert "default scan" in status.summary.next_action.lower()
    assert "no recorded outcome" in status.summary.decision_outcome_cue.lower()
    assert "default scan" in status.summary.action_scan_default_cue.lower()
    assert status.summary.latest_outcome_distribution
    assert status.summary.latest_outcome_distribution[0].outcome in {"escalate_for_closer_review", "revisit_later", "unrecorded"}
    assert any(item.outcome == "unrecorded" and item.is_actionable for item in status.summary.latest_outcome_distribution)
    assert "awaiting operator outcome: waiting on explicit review outcome before continuing this session" in status.summary.next_action.lower()
    assert status.plans[0].event_id == "evt-review"
    assert status.plans[0].requires_human_review is True
    assert status.plans[0].follow_up_state == "awaiting_outcome"
    assert status.plans[0].is_carry_forward_follow_up is True
    assert status.plans[0].reviewer_action_state == "pending"
    assert status.plans[0].reviewer_available_actions == ["acknowledge", "close_follow_up"]
    assert status.plans[0].decision_support_state == "active_attention"
    assert "action still open" in status.plans[0].next_review_cue.lower()
    assert "needs active attention" in status.plans[0].revisit_guidance.lower()
    assert "decision" in status.plans[0].next_step_outcome.lower()
    assert "capture a reviewer outcome" in status.plans[0].next_step_action_cue.lower()
    assert "review outcome" in status.plans[0].revisit_reason.lower()
    assert status.plans[1].follow_up_state == "revisit_downstream_surfaces"
    assert status.plans[1].decision_support_state == "mostly_stable"
    assert "stable for now" in status.plans[1].next_review_cue.lower()
    assert "capture a reviewer outcome" in status.plans[1].next_step_action_cue.lower()
    assert "revisit guidance" in status.summary.next_action.lower()


def test_orchestration_review_action_closes_follow_up_and_updates_state(tmp_path: Path) -> None:
    _write_artifact(
        tmp_path,
        event_type="ready_for_evaluation",
        event_id="evt-review",
        created_at="2026-03-29T09:30:00+00:00",
    )
    _write_artifact(
        tmp_path,
        event_type="completed",
        event_id="evt-progress",
        created_at="2026-03-29T10:00:00+00:00",
    )

    acknowledged = apply_orchestration_review_action(
        OrchestrationReviewActionRequest(event_id="evt-review", action="acknowledge"),
        artifact_path=tmp_path,
    )
    assert acknowledged.updated_plan.reviewer_action_state == "acknowledged"
    assert acknowledged.updated_plan.reviewer_available_actions == ["close_follow_up"]
    assert acknowledged.updated_plan.reviewer_last_action_at is not None
    assert acknowledged.updated_plan.reviewer_last_action == "acknowledge"
    assert acknowledged.updated_plan.reviewer_last_action_rationale
    assert "acknowledged to keep this carry-forward item visible" in acknowledged.updated_plan.reviewer_last_action_rationale.lower()
    assert acknowledged.updated_plan.reviewer_decision_outcome == "escalate_for_closer_review"
    assert acknowledged.updated_plan.reviewer_decision_record is not None
    assert "kept it active" in acknowledged.updated_plan.reviewer_decision_summary.lower()
    assert acknowledged.updated_plan.decision_support_state == "reopen_for_closer_review"
    assert "recheck soon" in acknowledged.updated_plan.next_review_cue.lower()

    closed = apply_orchestration_review_action(
        OrchestrationReviewActionRequest(event_id="evt-review", action="close_follow_up"),
        artifact_path=tmp_path,
    )
    assert closed.updated_plan.reviewer_action_state == "closed"
    assert closed.updated_plan.reviewer_available_actions == []
    assert closed.updated_plan.reviewer_last_action == "close_follow_up"
    assert closed.updated_plan.reviewer_last_action_rationale
    assert closed.updated_plan.reviewer_decision_outcome == "continue_monitoring"
    assert closed.updated_plan.reviewer_decision_record is not None
    assert "moved the item back to monitoring posture" in closed.updated_plan.reviewer_decision_summary.lower()
    assert "closed follow-up after reviewer decision" in closed.updated_plan.reviewer_last_action_rationale.lower()

    refreshed = get_orchestration_review_status(artifact_path=tmp_path)
    closed_plan = next(plan for plan in refreshed.plans if plan.event_id == "evt-review")
    assert closed_plan.reviewer_action_state == "closed"
    assert closed_plan.reviewer_last_action == "close_follow_up"
    assert closed_plan.reviewer_last_action_rationale
    assert closed_plan.decision_support_state == "mostly_stable"
    assert "stable for now" in closed_plan.next_review_cue.lower()
    assert "awaiting operator outcome ×1" not in refreshed.summary.next_action.lower()
    assert refreshed.summary.decision_outcome_breakdown["continue_monitoring"] >= 1


def test_orchestration_review_status_empty_queue(tmp_path: Path) -> None:
    status = get_orchestration_review_status(artifact_path=tmp_path)

    assert status.summary.current_state == "idle"
    assert status.summary.review_needed is False
    assert status.summary.pending_count == 0
    assert status.summary.freshness == "empty"
    assert status.summary.latest_event_at is None
    assert "restart review" in status.summary.next_action.lower()
    assert status.plans == []


def test_orchestration_review_status_auto_progressing_includes_follow_up_state_cue(tmp_path: Path) -> None:
    _write_artifact(
        tmp_path,
        event_type="completed",
        event_id="evt-completed",
        created_at="2026-03-29T11:00:00+00:00",
    )
    _write_artifact(
        tmp_path,
        event_type="interrupted",
        event_id="evt-interrupted",
        created_at="2026-03-29T11:05:00+00:00",
    )

    status = get_orchestration_review_status(artifact_path=tmp_path)

    assert status.summary.current_state == "auto_progressing"
    assert "active follow-up states" in status.summary.next_action.lower()
    assert "revisit after resume ×1" in status.summary.next_action.lower()
    assert "carry-forward summary" in status.summary.next_action.lower()
    assert "outcome triage" in status.summary.next_action.lower()
    assert "no recorded outcome" in status.summary.decision_outcome_cue.lower()
    assert "revisit after resume: interrupted runs should be rechecked after auto-resume" in status.summary.next_action.lower()


def test_orchestration_review_supports_outcome_focus_filter(tmp_path: Path) -> None:
    _write_artifact(
        tmp_path,
        event_type="ready_for_evaluation",
        event_id="evt-review",
        created_at="2026-03-29T09:30:00+00:00",
    )
    _write_artifact(
        tmp_path,
        event_type="completed",
        event_id="evt-progress",
        created_at="2026-03-29T10:00:00+00:00",
    )
    apply_orchestration_review_action(
        OrchestrationReviewActionRequest(event_id="evt-review", action="acknowledge"),
        artifact_path=tmp_path,
    )

    focused = get_orchestration_review_status(artifact_path=tmp_path, outcome_focus="escalate_for_closer_review")
    assert focused.summary.active_decision_outcome_filter == "escalate_for_closer_review"
    assert focused.summary.pending_count == 1
    assert focused.summary.total_pending_count == 2
    assert all(plan.reviewer_decision_outcome == "escalate_for_closer_review" for plan in focused.plans)


def test_orchestration_review_orders_actionable_outcomes_first(tmp_path: Path) -> None:
    _write_artifact(
        tmp_path,
        event_type="ready_for_evaluation",
        event_id="evt-review",
        created_at="2026-03-29T09:30:00+00:00",
    )
    _write_artifact(
        tmp_path,
        event_type="completed",
        event_id="evt-progress",
        created_at="2026-03-29T10:00:00+00:00",
    )

    apply_orchestration_review_action(
        OrchestrationReviewActionRequest(event_id="evt-progress", action="close_follow_up"),
        artifact_path=tmp_path,
    )
    status = get_orchestration_review_status(artifact_path=tmp_path, limit=10)

    assert status.plans
    assert status.plans[0].event_id == "evt-review"
    assert status.plans[0].reviewer_decision_outcome is None
