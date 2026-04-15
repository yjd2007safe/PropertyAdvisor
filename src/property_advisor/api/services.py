from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

import json
from datetime import datetime, timedelta, timezone
from statistics import mean
from pathlib import Path
from typing import Dict, List, Literal, Optional

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.repositories import ComparableQuery, WatchlistQuery, WatchlistUpsertRequest
from property_advisor.api.schemas import (
    DecisionOutcomeDistributionItem,
    DecisionOutcomeSummary,
    OrchestrationPlanItem,
    OrchestrationReviewActionRequest,
    OrchestrationReviewActionResponse,
    OrchestrationReviewResponse,
    OrchestrationReviewSummary,
    AdvisoryInputs,
    AdvisoryInvestorSignal,
    AdvisoryMarketContext,
    AdvisoryRationaleItem,
    ComparableNarrative,
    ComparableSnapshot,
    ComparableSummary,
    ComparablesResponse,
    DataSourceStatus,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    SummaryCard,
    WatchlistAlertsResponse,
    WatchlistActionRequest,
    WatchlistActionResponse,
    WatchlistContextSummary,
    WatchlistDetailResponse,
    WatchlistEntry,
    WatchlistEventItem,
    WatchlistEventsResponse,
    WatchlistGroup,
    WatchlistResponse,
    WatchlistSummary,
    WorkflowLink,
    WorkflowSnapshot,
)



_DAL = DataAccessLayer.create(create_session_factory())

_ORCHESTRATION_EVENT_TYPES = {
    "completed",
    "blocked",
    "interrupted",
    "ready_for_evaluation",
    "evaluation_failed",
    "delivered",
    "evaluated",
}

_ORCHESTRATION_POLICY: dict[str, dict[str, object]] = {
    "ready_for_evaluation": {"priority": 100, "action": "notify_and_pause_for_review", "auto_continue": False, "requires_human_review": True, "bucket": "review"},
    "evaluation_failed": {"priority": 90, "action": "notify_and_resume_fix", "auto_continue": True, "requires_human_review": False, "bucket": "recovery"},
    "blocked": {"priority": 80, "action": "notify_and_wait_on_blocker", "auto_continue": False, "requires_human_review": False, "bucket": "blocked"},
    "interrupted": {"priority": 70, "action": "notify_and_resume", "auto_continue": True, "requires_human_review": False, "bucket": "recovery"},
    "completed": {"priority": 60, "action": "notify_progress_and_continue", "auto_continue": True, "requires_human_review": False, "bucket": "progress"},
    "evaluated": {"priority": 50, "action": "notify_progress_and_continue", "auto_continue": True, "requires_human_review": False, "bucket": "progress"},
    "delivered": {"priority": 40, "action": "notify_closure", "auto_continue": False, "requires_human_review": False, "bucket": "closure"},
}

_DEFAULT_ORCHESTRATION_POLICY = {"priority": 10, "action": "notify_only", "auto_continue": False, "requires_human_review": False, "bucket": "other"}

_ORCHESTRATION_STRATEGY_SUMMARY = {
    "notify_and_pause_for_review": "通知关键进展，并暂停等待人工复核。",
    "notify_and_resume_fix": "通知失败原因，并自动继续修复链路。",
    "notify_and_wait_on_blocker": "通知阻塞点，等待外部条件解除。",
    "notify_and_resume": "通知中断原因，并尝试自动恢复执行。",
    "notify_progress_and_continue": "反馈阶段性进展，并在已授权前提下继续推进下一步。",
    "notify_closure": "通知该轮结果已正式交付闭环。",
    "notify_only": "仅通知，不自动推进。",
}

_ORCHESTRATION_OUTCOME_FRAMING = {
    "ready_for_evaluation": {
        "next_step_outcome": "Capture operator evaluation decision so execution can safely continue.",
        "revisit_reason": "Waiting on explicit review outcome before continuing this session.",
        "follow_up_state": "awaiting_outcome",
    },
    "evaluation_failed": {
        "next_step_outcome": "Confirm recovery run resolves the failed evaluation path.",
        "revisit_reason": "Revisit after recovery evidence lands to verify outcome quality.",
        "follow_up_state": "revisit_after_recovery",
    },
    "blocked": {
        "next_step_outcome": "Unblock dependency and resume orchestration flow.",
        "revisit_reason": "External blocker must clear before outcome can progress.",
        "follow_up_state": "waiting_on_dependency",
    },
    "interrupted": {
        "next_step_outcome": "Validate resumed run completed without introducing new regressions.",
        "revisit_reason": "Interrupted runs should be rechecked after auto-resume.",
        "follow_up_state": "revisit_after_resume",
    },
    "completed": {
        "next_step_outcome": "Confirm completion output is reflected in downstream review surfaces.",
        "revisit_reason": "Carry completed results into advisor/watchlist follow-up checks.",
        "follow_up_state": "revisit_downstream_surfaces",
    },
    "evaluated": {
        "next_step_outcome": "Propagate evaluated result through decision-facing surfaces.",
        "revisit_reason": "Review downstream decision context after evaluation updates.",
        "follow_up_state": "revisit_downstream_surfaces",
    },
    "delivered": {
        "next_step_outcome": "Verify delivered payload has been acknowledged by the operator.",
        "revisit_reason": "Revisit only if delivery acknowledgement is missing or stale.",
        "follow_up_state": "monitor_delivery_ack",
    },
}

_DEFAULT_OUTCOME_FRAMING = {
    "next_step_outcome": "Capture the next operator-visible outcome and then reassess queue priority.",
    "revisit_reason": "Revisit when fresh orchestration evidence is available.",
    "follow_up_state": "monitor",
}

_FOLLOW_UP_STATE_LABELS = {
    "awaiting_outcome": "awaiting operator outcome",
    "revisit_after_recovery": "revisit after recovery",
    "waiting_on_dependency": "waiting on dependency",
    "revisit_after_resume": "revisit after resume",
    "revisit_downstream_surfaces": "carry-forward downstream",
    "monitor_delivery_ack": "monitor delivery acknowledgement",
    "monitor": "monitor",
}

_CARRY_FORWARD_FOLLOW_UP_STATES = {
    "awaiting_outcome",
    "revisit_after_recovery",
    "waiting_on_dependency",
    "revisit_after_resume",
    "revisit_downstream_surfaces",
    "monitor_delivery_ack",
}

_DECISION_SUPPORT_LABELS = {
    "active_attention": "Needs active attention",
    "mostly_stable": "Mostly stable",
    "reopen_for_closer_review": "Re-open for closer review",
}


_DECISION_OUTCOME_LABELS = {
    "escalate_for_closer_review": "Escalate",
    "revisit_later": "Revisit later",
    "continue_monitoring": "Continue monitoring",
    "close_for_now": "Closed for now",
}

_DECISION_OUTCOME_PRIORITY = {
    "escalate_for_closer_review": 4,
    "revisit_later": 3,
    "unrecorded": 3,
    "continue_monitoring": 2,
    "close_for_now": 1,
}


_DECISION_OUTCOME_FILTER_VALUES = {
    "continue_monitoring",
    "revisit_later",
    "close_for_now",
    "escalate_for_closer_review",
    "unrecorded",
}

_REVIEWER_ACTION_STATE_FILTER_VALUES = {"pending", "acknowledged", "closed"}

_FOLLOW_UP_STATE_FILTER_VALUES = set(_FOLLOW_UP_STATE_LABELS.keys())

_ACTIONABLE_DECISION_OUTCOMES = {
    "escalate_for_closer_review",
    "revisit_later",
    "unrecorded",
}

_DECISION_OUTCOME_SUMMARY_ORDER = [
    "escalate_for_closer_review",
    "revisit_later",
    "unrecorded",
    "continue_monitoring",
    "close_for_now",
]

_WATCHLIST_STATUS_PRIORITY = {
    "review": 4,
    "paused": 3,
    "active": 2,
    "archived": 1,
}


def _review_state_path(artifact_path: Path) -> Path:
    return artifact_path / "review_state.json"


def _load_review_state(artifact_path: Path) -> dict[str, dict[str, str]]:
    path = _review_state_path(artifact_path)
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text())
    if not isinstance(loaded, dict):
        return {}
    actions = loaded.get("event_actions", {})
    if not isinstance(actions, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for event_id, payload in actions.items():
        if not isinstance(event_id, str) or not isinstance(payload, dict):
            continue
        action = str(payload.get("action") or "").strip()
        acted_at = str(payload.get("acted_at") or "").strip()
        if action in {"acknowledge", "close_follow_up"} and acted_at:
            rationale = str(payload.get("rationale") or "").strip()
            normalized_payload = {"action": action, "acted_at": acted_at}
            if rationale:
                normalized_payload["rationale"] = rationale
            decision_outcome = str(payload.get("decision_outcome") or "").strip()
            decision_summary = str(payload.get("decision_summary") or "").strip()
            if decision_outcome:
                normalized_payload["decision_outcome"] = decision_outcome
            if decision_summary:
                normalized_payload["decision_summary"] = decision_summary
            normalized[event_id] = normalized_payload
    return normalized


def _save_review_state(artifact_path: Path, event_actions: dict[str, dict[str, str]]) -> None:
    artifact_path.mkdir(parents=True, exist_ok=True)
    payload = {"event_actions": event_actions}
    _review_state_path(artifact_path).write_text(json.dumps(payload, indent=2, sort_keys=True))


def _build_orchestration_plan(record: dict[str, object]) -> dict[str, object]:
    event_type = _normalize_event_type(record.get("event_type"))
    policy = dict(_DEFAULT_ORCHESTRATION_POLICY)
    policy.update(_ORCHESTRATION_POLICY.get(event_type, {}))
    outcome_framing = dict(_DEFAULT_OUTCOME_FRAMING)
    outcome_framing.update(_ORCHESTRATION_OUTCOME_FRAMING.get(event_type, {}))
    action = str(policy["action"])
    return {
        "event_id": record.get("event_id"),
        "event_type": event_type,
        "queued_at": record.get("queued_at"),
        "created_at": record.get("created_at"),
        "session_key": record.get("session_key"),
        "message": record.get("message"),
        "priority": int(policy["priority"]),
        "bucket": str(policy["bucket"]),
        "action": action,
        "auto_continue": bool(policy["auto_continue"]),
        "requires_human_review": bool(policy["requires_human_review"]),
        "strategy_summary": _ORCHESTRATION_STRATEGY_SUMMARY[action],
        "follow_up_state": str(outcome_framing["follow_up_state"]),
        "next_step_outcome": str(outcome_framing["next_step_outcome"]),
        "revisit_reason": str(outcome_framing["revisit_reason"]),
    }


def _build_reviewer_action_rationale(plan: dict[str, object], action: str) -> str:
    follow_up_state = str(plan.get("follow_up_state") or "monitor")
    follow_up_label = _FOLLOW_UP_STATE_LABELS.get(follow_up_state, follow_up_state.replace("_", " "))
    revisit_reason = str(plan.get("revisit_reason") or "").strip().rstrip(".")
    if action == "acknowledge":
        if revisit_reason:
            return f"Acknowledged to keep this carry-forward item visible: {follow_up_label}; {revisit_reason}."
        return f"Acknowledged to keep this carry-forward item visible: {follow_up_label}."
    if action == "close_follow_up":
        if revisit_reason:
            return f"Closed follow-up after reviewer decision: {follow_up_label}; {revisit_reason}."
        return f"Closed follow-up after reviewer decision: {follow_up_label}."
    return ""


def _build_reviewer_decision_outcome(plan: dict[str, object], action: str, rationale: str) -> dict[str, str]:
    follow_up_state = str(plan.get("follow_up_state") or "monitor")
    event_id = str(plan.get("event_id") or "")
    if action == "acknowledge":
        outcome = "escalate_for_closer_review" if follow_up_state in {
            "awaiting_outcome",
            "revisit_after_recovery",
            "waiting_on_dependency",
            "revisit_after_resume",
        } else "revisit_later"
        summary = "Reviewer acknowledged the item and kept it active for a later decision pass."
    else:
        outcome = "close_for_now" if follow_up_state in {"monitor_delivery_ack", "monitor"} else "continue_monitoring"
        summary = "Reviewer closed the current follow-up and moved the item back to monitoring posture."
    return {
        "outcome": outcome,
        "summary": summary,
        "rationale": rationale,
        "source_event_id": event_id,
        "source_surface": "orchestration",
    }


def _build_orchestration_queue(records: list[dict[str, object]]) -> list[dict[str, object]]:
    plans = [_build_orchestration_plan(record) for record in records]
    plans.sort(key=lambda plan: (-int(plan["priority"]), str(plan.get("queued_at") or ""), str(plan.get("created_at") or ""), str(plan.get("event_id") or "")))
    return plans


def _decision_outcome_priority(outcome: Optional[str]) -> int:
    normalized = (outcome or "").strip()
    if not normalized:
        normalized = "unrecorded"
    return _DECISION_OUTCOME_PRIORITY.get(normalized, 0)


def _sort_orchestration_plans_for_scan(plans: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        plans,
        key=lambda plan: (
            0 if bool(plan.get("requires_human_review")) else 1,
            -_decision_outcome_priority(str(plan.get("reviewer_decision_outcome") or "")),
            -(
                int(
                    (_parse_timestamp(plan.get("queued_at")) or _parse_timestamp(plan.get("created_at")) or datetime.fromtimestamp(0, tz=timezone.utc)).timestamp()
                )
            ),
            str(plan.get("event_id") or ""),
        ),
    )


def _build_revisit_decision_support(plan: dict[str, object]) -> dict[str, str]:
    follow_up_state = str(plan.get("follow_up_state") or "monitor")
    reviewer_state = str(plan.get("reviewer_action_state") or "pending")
    requires_human_review = bool(plan.get("requires_human_review"))
    is_carry_forward = bool(plan.get("is_carry_forward_follow_up"))
    revisit_reason = str(plan.get("revisit_reason") or "").strip()

    decision_support_state = "mostly_stable"
    if requires_human_review and reviewer_state == "pending":
        decision_support_state = "active_attention"
    elif is_carry_forward and reviewer_state == "acknowledged" and follow_up_state in {
        "awaiting_outcome",
        "revisit_after_recovery",
        "waiting_on_dependency",
        "revisit_after_resume",
    }:
        decision_support_state = "reopen_for_closer_review"

    cue = ""
    if decision_support_state == "active_attention":
        cue = "Action still open — reviewer outcome needed."
    elif decision_support_state == "reopen_for_closer_review":
        cue = "Recheck soon — prior acknowledgement may no longer be enough."
    else:
        cue = "Stable for now — monitor in weekly low-noise pass."

    guidance = _DECISION_SUPPORT_LABELS[decision_support_state]
    if revisit_reason:
        guidance = f"{guidance}: {revisit_reason.rstrip('.')}"
    return {
        "decision_support_state": decision_support_state,
        "next_review_cue": cue,
        "revisit_guidance": guidance,
    }


def _apply_reviewer_action_state(
    plans: list[dict[str, object]],
    review_actions: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for plan in plans:
        event_id = str(plan.get("event_id") or "")
        follow_up_state = str(plan.get("follow_up_state") or "monitor")
        action_payload = review_actions.get(event_id, {})
        action = str(action_payload.get("action") or "")
        is_carry_forward = follow_up_state in _CARRY_FORWARD_FOLLOW_UP_STATES
        reviewer_state = "pending"
        if action == "acknowledge":
            reviewer_state = "acknowledged"
        elif action == "close_follow_up":
            reviewer_state = "closed"
        available_actions: list[str] = []
        if is_carry_forward:
            if reviewer_state == "pending":
                available_actions = ["acknowledge", "close_follow_up"]
            elif reviewer_state == "acknowledged":
                available_actions = ["close_follow_up"]

        enriched_plan = dict(plan)
        enriched_plan["is_carry_forward_follow_up"] = is_carry_forward
        enriched_plan["reviewer_action_state"] = reviewer_state
        enriched_plan["reviewer_available_actions"] = available_actions
        enriched_plan["reviewer_last_action_at"] = action_payload.get("acted_at")
        enriched_plan["reviewer_last_action"] = action if action in {"acknowledge", "close_follow_up"} else None
        enriched_plan["reviewer_last_action_rationale"] = action_payload.get("rationale")
        decision_outcome = str(action_payload.get("decision_outcome") or "").strip()
        decision_summary = str(action_payload.get("decision_summary") or "").strip()
        enriched_plan["reviewer_decision_outcome"] = decision_outcome or None
        enriched_plan["reviewer_decision_summary"] = decision_summary or None
        enriched_plan["reviewer_decision_record"] = (
            {
                "outcome": decision_outcome,
                "summary": decision_summary,
                "rationale": action_payload.get("rationale"),
                "acted_at": action_payload.get("acted_at"),
                "source_event_id": event_id,
                "source_surface": "orchestration",
            }
            if decision_outcome and decision_summary
            else None
        )
        enriched_plan.update(_build_revisit_decision_support(enriched_plan))
        enriched.append(enriched_plan)
    return enriched


def _build_follow_up_state_cue(plans: list[dict[str, object]], *, max_items: int = 2) -> str:
    if not plans:
        return ""

    state_counts: dict[str, int] = {}
    for plan in plans:
        state = str(plan.get("follow_up_state") or "monitor")
        state_counts[state] = state_counts.get(state, 0) + 1

    ranked_states = sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))
    compact_states = [
        f"{_FOLLOW_UP_STATE_LABELS.get(state, state.replace('_', ' '))} ×{count}"
        for state, count in ranked_states[:max_items]
    ]
    remaining = len(ranked_states) - len(compact_states)
    if remaining > 0:
        compact_states.append(f"+{remaining} more")
    return "; ".join(compact_states)


def _build_carry_forward_summary(plans: list[dict[str, object]], *, max_items: int = 2) -> str:
    if not plans:
        return ""

    grouped_rationale: dict[str, int] = {}
    for plan in plans:
        state = str(plan.get("follow_up_state") or "monitor")
        state_label = _FOLLOW_UP_STATE_LABELS.get(state, state.replace("_", " "))
        revisit_reason = str(plan.get("revisit_reason") or "").strip()
        compact_reason = revisit_reason.rstrip(".") if revisit_reason else "No additional rationale provided"
        key = f"{state_label}: {compact_reason}"
        grouped_rationale[key] = grouped_rationale.get(key, 0) + 1

    ranked = sorted(grouped_rationale.items(), key=lambda item: (-item[1], item[0]))
    compact = [f"{reason}{f' ×{count}' if count > 1 else ''}" for reason, count in ranked[:max_items]]
    remaining = len(ranked) - len(compact)
    if remaining > 0:
        compact.append(f"+{remaining} more")
    return " · ".join(compact)


def _build_revisit_guidance_cue(plans: list[dict[str, object]]) -> str:
    if not plans:
        return ""
    state_counts: dict[str, int] = {}
    for plan in plans:
        state = str(plan.get("decision_support_state") or "active_attention")
        state_counts[state] = state_counts.get(state, 0) + 1
    ranked = sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(
        f"{_DECISION_SUPPORT_LABELS.get(state, state.replace('_', ' '))} ×{count}"
        for state, count in ranked
    )


def _build_notification_boundary_cue(plans: list[dict[str, object]]) -> str:
    if not plans:
        return ""
    progress_count = sum(
        1
        for plan in plans
        if _normalize_event_type(plan.get("event_type")) in {"completed", "evaluated"}
    )
    closure_count = sum(1 for plan in plans if _normalize_event_type(plan.get("event_type")) == "delivered")
    if progress_count <= 0 and closure_count <= 0:
        return ""
    return (
        "Bridge validation boundary: completed/evaluated events should remain in progress notifications, "
        f"while delivered events close the loop (progress ×{progress_count}, closure ×{closure_count})."
    )




def _format_decision_triage_cue(record: DecisionOutcomeSummary) -> str:
    label = _DECISION_OUTCOME_LABELS.get(record.outcome, record.outcome.replace("_", " "))
    summary = record.summary.strip()
    compact = summary.rstrip(".") if summary else "No summary"
    return f"{label}: {compact}"


def _decision_next_step_cue(outcome: Optional[str]) -> str:
    normalized = (outcome or "").strip() or "unrecorded"
    if normalized == "escalate_for_closer_review":
        return "Escalate now: run advisor + comparables, then capture a reviewer closure decision."
    if normalized == "revisit_later":
        return "Revisit next pass: keep this in review/paused scan and refresh signals before changing status."
    if normalized == "continue_monitoring":
        return "Monitor in weekly scan: keep alerts visible and only reopen if risk signals worsen."
    if normalized == "close_for_now":
        return "Closed for now: deprioritize unless a fresh high-severity signal appears."
    return "No recorded outcome yet: capture a reviewer outcome before de-prioritizing this item."


def _decision_batch_cue(outcome: Optional[str]) -> str:
    normalized = (outcome or "").strip() or "unrecorded"
    if normalized in {"escalate_for_closer_review", "revisit_later"}:
        return "Batch with active-intervention rows (Escalate/Revisit) for the same next-step treatment."
    if normalized in {"continue_monitoring", "close_for_now"}:
        return "Batch with monitor-later rows (Continue/Closed) for low-noise weekly treatment."
    return "Batch with outcome-capture rows first so follow-up treatment stays explicit."


def _build_next_step_batching_cue(breakdown: dict[str, int]) -> str:
    active_intervention = int(breakdown.get("escalate_for_closer_review", 0)) + int(breakdown.get("revisit_later", 0))
    monitor_later = int(breakdown.get("continue_monitoring", 0)) + int(breakdown.get("close_for_now", 0))
    unrecorded = int(breakdown.get("unrecorded", 0))
    compact: list[str] = []
    if active_intervention > 0:
        compact.append(f"Active-intervention batch (Escalate/Revisit) ×{active_intervention}")
    if unrecorded > 0:
        compact.append(f"Outcome-capture batch ×{unrecorded}")
    if monitor_later > 0:
        compact.append(f"Monitor-later batch (Continue/Closed) ×{monitor_later}")
    return " · ".join(compact) if compact else "No next-step batching signals yet."


def _build_compact_follow_up_grouping_cue(breakdown: dict[str, int]) -> str:
    active_intervention = int(breakdown.get("escalate_for_closer_review", 0)) + int(breakdown.get("revisit_later", 0))
    outcome_capture = int(breakdown.get("unrecorded", 0))
    monitor_later = int(breakdown.get("continue_monitoring", 0)) + int(breakdown.get("close_for_now", 0))
    compact: list[str] = []
    if active_intervention > 0:
        compact.append(f"Active-intervention ×{active_intervention}")
    if outcome_capture > 0:
        compact.append(f"Outcome-capture ×{outcome_capture}")
    if monitor_later > 0:
        compact.append(f"Monitor-later ×{monitor_later}")
    return " · ".join(compact) if compact else "No compact follow-up groups yet."


def _build_compact_rationale_language_cue(breakdown: dict[str, int]) -> str:
    active_intervention = int(breakdown.get("escalate_for_closer_review", 0)) + int(breakdown.get("revisit_later", 0))
    outcome_capture = int(breakdown.get("unrecorded", 0))
    monitor_later = int(breakdown.get("continue_monitoring", 0)) + int(breakdown.get("close_for_now", 0))
    compact: list[str] = []
    if active_intervention > 0:
        compact.append("Highlighted first: Escalate/Revisit items still need active follow-up.")
    if outcome_capture > 0:
        compact.append("Highlighted next: unrecorded outcomes still need a reviewer outcome.")
    if monitor_later > 0:
        compact.append("Grouped later: Continue/Closed rows move to low-noise weekly follow-up.")
    return " ".join(compact) if compact else "No rationale cues yet; follow default outcome ordering."


_REASON_LABELS = {
    "active_follow_up": "Reason: Active follow-up",
    "near_term_recheck": "Reason: Near-term recheck",
    "weekly_monitor": "Reason: Weekly monitor",
}


def _reason_label_phrase(label_key: Literal["active_follow_up", "near_term_recheck", "weekly_monitor"]) -> str:
    return _REASON_LABELS[label_key]


def _build_compact_evidence_hint(
    *,
    outcome: Optional[str],
    emphasis_reason: str,
    grouping_reason: Optional[str] = None,
) -> str:
    normalized_outcome = (outcome or "").strip() or "unrecorded"
    outcome_label = "No recorded outcome" if normalized_outcome == "unrecorded" else _DECISION_OUTCOME_LABELS.get(
        normalized_outcome,
        normalized_outcome.replace("_", " "),
    )
    compact_parts = [f"Rationale cue: {outcome_label}"]
    if emphasis_reason.strip():
        compact_parts.append(emphasis_reason.strip().rstrip("."))
    if grouping_reason and grouping_reason.strip():
        compact_parts.append(grouping_reason.strip().rstrip("."))
    return " · ".join(compact_parts) + "."


def _build_plan_compact_rationale_cue(plan: dict[str, object]) -> str:
    outcome = str(plan.get("reviewer_decision_outcome") or "").strip() or "unrecorded"
    action_state = str(plan.get("reviewer_action_state") or "pending")
    follow_up_state = str(plan.get("follow_up_state") or "monitor")
    follow_up_label = _FOLLOW_UP_STATE_LABELS.get(follow_up_state, follow_up_state.replace("_", " "))
    next_review_cue = str(plan.get("next_review_cue") or "").strip()
    decision_support_state = str(plan.get("decision_support_state") or "active_attention")
    if decision_support_state == "active_attention":
        emphasis = f"{_reason_label_phrase('active_follow_up')}; prioritize now for active follow-up"
    elif decision_support_state == "reopen_for_closer_review":
        emphasis = f"{_reason_label_phrase('near_term_recheck')}; recheck soon"
    else:
        emphasis = f"{_reason_label_phrase('weekly_monitor')}; queue later in weekly monitor"
    follow_up_intent = f"Follow-up intent: {follow_up_label}"
    if next_review_cue:
        follow_up_intent += f"; watch next={next_review_cue.rstrip('.')}"
    return _build_compact_evidence_hint(
        outcome=outcome,
        emphasis_reason=f"{emphasis}; reviewer state={action_state.replace('_', ' ')}; {follow_up_intent}",
    )


def _build_decision_outcome_grouping(plans: list[dict[str, object]]) -> tuple[str, dict[str, int]]:
    counts = {
        "escalate_for_closer_review": 0,
        "revisit_later": 0,
        "continue_monitoring": 0,
        "close_for_now": 0,
        "unrecorded": 0,
    }
    for plan in plans:
        outcome = str(plan.get("reviewer_decision_outcome") or "").strip()
        if outcome in counts and outcome != "unrecorded":
            counts[outcome] += 1
        else:
            counts["unrecorded"] += 1

    ranked_known = sorted(
        ((key, value) for key, value in counts.items() if key != "unrecorded" and value > 0),
        key=lambda item: (-_DECISION_OUTCOME_PRIORITY[item[0]], -item[1], item[0]),
    )
    compact = [f"{_DECISION_OUTCOME_LABELS[key]} ×{value}" for key, value in ranked_known[:3]]
    if counts["unrecorded"] > 0:
        compact.append(f"No recorded outcome ×{counts['unrecorded']}")
    return (" · ".join(compact) if compact else "No decision outcomes recorded yet.", counts)


def _build_action_scan_default_cue(breakdown: dict[str, int]) -> str:
    escalate = int(breakdown.get("escalate_for_closer_review", 0))
    revisit = int(breakdown.get("revisit_later", 0))
    unrecorded = int(breakdown.get("unrecorded", 0))
    if escalate > 0:
        return "Default scan: start with Escalate outcomes, then Revisit later, then unrecorded decisions."
    if revisit > 0:
        return "Default scan: start with Revisit later outcomes, then unrecorded decisions."
    if unrecorded > 0:
        return "Default scan: capture unrecorded outcomes first so repeat-review priority stays explicit."
    return "Default scan: monitor Continue/Closed outcomes in a low-noise weekly pass."


def _build_outcome_distribution(breakdown: dict[str, int]) -> list[DecisionOutcomeDistributionItem]:
    distribution: list[DecisionOutcomeDistributionItem] = []
    for outcome in _DECISION_OUTCOME_SUMMARY_ORDER:
        count = int(breakdown.get(outcome, 0))
        if count <= 0:
            continue
        label = "No recorded outcome" if outcome == "unrecorded" else _DECISION_OUTCOME_LABELS.get(outcome, outcome.replace("_", " "))
        distribution.append(
            DecisionOutcomeDistributionItem(
                outcome=outcome,
                label=label,
                count=count,
                is_actionable=outcome in _ACTIONABLE_DECISION_OUTCOMES,
            )
        )
    return distribution


def _filter_plans_by_decision_outcome(plans: list[dict[str, object]], outcome_focus: Optional[str]) -> list[dict[str, object]]:
    if not outcome_focus or outcome_focus not in _DECISION_OUTCOME_FILTER_VALUES:
        return plans
    if outcome_focus == "unrecorded":
        return [plan for plan in plans if not str(plan.get("reviewer_decision_outcome") or "").strip()]
    return [plan for plan in plans if str(plan.get("reviewer_decision_outcome") or "").strip() == outcome_focus]


def _filter_plans_by_execution_state(
    plans: list[dict[str, object]],
    reviewer_action_state_focus: Optional[str],
    follow_up_state_focus: Optional[str],
) -> list[dict[str, object]]:
    filtered = plans
    if reviewer_action_state_focus and reviewer_action_state_focus in _REVIEWER_ACTION_STATE_FILTER_VALUES:
        filtered = [plan for plan in filtered if str(plan.get("reviewer_action_state") or "pending") == reviewer_action_state_focus]
    if follow_up_state_focus and follow_up_state_focus in _FOLLOW_UP_STATE_FILTER_VALUES:
        filtered = [plan for plan in filtered if str(plan.get("follow_up_state") or "monitor") == follow_up_state_focus]
    return filtered

def _read_source(repository: object) -> Literal["mock", "postgres", "fallback_mock"]:
    source = getattr(repository, "last_source", "mock")
    if source not in {"mock", "postgres", "fallback_mock"}:
        return "mock"
    return source


def _resolve_data_source(
    dal: DataAccessLayer,
    repository: object,
    domain: str,
    upstream_repositories: Optional[Dict[str, object]] = None,
) -> DataSourceStatus:
    source = _read_source(repository)
    fallback_reason = getattr(repository, "last_fallback_reason", None)
    upstream_sources = {name: _read_source(repo) for name, repo in (upstream_repositories or {}).items()}
    source_breakdown = {"mock": 0, "postgres": 0, "fallback_mock": 0}
    source_breakdown[source] += 1
    for upstream_source in upstream_sources.values():
        source_breakdown[upstream_source] += 1
    all_sources = {key for key, count in source_breakdown.items() if count > 0}
    consistency = "uniform" if len(all_sources) <= 1 else "mixed"

    if source == "postgres":
        primary_message = f"{domain} is DB-backed from PostgreSQL."
        status_label = "live_db"
        investor_note = "Live DB feed available for this view."
    elif source == "fallback_mock":
        primary_message = f"{domain} is using fallback mock payloads because PostgreSQL data was unavailable."
        status_label = "fallback"
        investor_note = "Fallback sample payloads are shown while DB reads recover."
    else:
        primary_message = f"{domain} is using mock fixtures."
        status_label = "sample_data"
        investor_note = "Sample fixtures are active; use as directional guidance only."

    if upstream_sources:
        details = ", ".join(f"{name}:{value}" for name, value in sorted(upstream_sources.items()))
        primary_message = f"{primary_message} Upstream sources -> {details}."

    if fallback_reason:
        primary_message = f"{primary_message} Fallback reason: {fallback_reason}"

    if consistency == "mixed":
        primary_message = f"{primary_message} Response uses a mixed-source chain."

    return DataSourceStatus(
        mode=dal.mode,
        source=source,
        is_fallback=(source == "fallback_mock"),
        message=primary_message,
        status_label=status_label,
        investor_note=(
            f"{investor_note} Mixed-source response detected across dependencies."
            if consistency == "mixed"
            else investor_note
        ),
        consistency=consistency,
        upstream_sources=upstream_sources,
        source_breakdown=source_breakdown,
        fallback_reason=fallback_reason,
    )


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def _product_workflow_links(suburb_slug: Optional[str] = None, source_surface: Optional[str] = None) -> List[WorkflowLink]:
    suffix = f"?detail_slug={suburb_slug}&suburb_slug={suburb_slug}" if suburb_slug else ""
    save_href = "/watchlist"
    advisor_href = "/advisor"
    comparables_href = "/comparables"
    if suburb_slug:
        inferred_query_type = "slug" if "-" in suburb_slug and "," not in suburb_slug else "auto"
        advisor_href = f"/advisor?query={suburb_slug}&query_type={inferred_query_type}"
        comparables_href = f"/comparables?query={suburb_slug}"
    if suburb_slug and source_surface:
        save_href = f"/watchlist/actions?suburb_slug={suburb_slug}&source_surface={source_surface}"
    orchestration_href = "/orchestration"
    if source_surface == "watchlist":
        orchestration_href = "/orchestration?view=actionable&reviewer_action_state_focus=pending&follow_up_state_focus=awaiting_outcome"
    return [
        WorkflowLink(label="Suburb dashboard", href="/suburbs", context="Re-check suburb-level momentum and liquidity."),
        WorkflowLink(label="Property advisor", href=advisor_href, context="Convert evidence into a decision recommendation."),
        WorkflowLink(label="Comparables", href=comparables_href, context="Validate pricing fit and comp confidence."),
        WorkflowLink(label="Watchlist", href=f"/watchlist{suffix}", context="Track strategy alerts and action queue."),
        WorkflowLink(label="Save to watchlist", href=save_href, context="Capture this suburb into watchlist action review."),
        WorkflowLink(label="Orchestration review", href=orchestration_href, context="Check runtime review blockers, freshness, and operator actions."),
    ]


def _workflow_snapshot(
    stage: str,
    next_step: str,
    next_href: str,
    investor_message: str,
    primary_suburb_slug: Optional[str] = None,
) -> WorkflowSnapshot:
    return WorkflowSnapshot(
        stage=stage,
        primary_suburb_slug=primary_suburb_slug,
        next_step=next_step,
        next_href=next_href,
        investor_message=investor_message,
    )


def get_suburbs_overview(dal: DataAccessLayer = _DAL) -> SuburbsOverviewResponse:
    items = dal.suburbs.list_overview()
    watchlist_slugs = {item.suburb_slug for item in dal.watchlist.list_entries(WatchlistQuery())}
    summary = SuburbOverviewSummary(
        tracked_suburbs=len(items),
        watchlist_suburbs=sum(1 for item in items if item.slug in watchlist_slugs),
        data_freshness=f"{dal.mode}-weekly" if items else "empty",
    )

    improving_count = sum(1 for item in items if item.trend == "improving")
    watching_count = sum(1 for item in items if item.trend == "watching")
    median_dom = round(mean([item.avg_days_on_market for item in items])) if items else 0

    return SuburbsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        data_source=_resolve_data_source(
            dal,
            dal.suburbs,
            "Suburb overview",
            upstream_repositories={"watchlist": dal.watchlist},
        ),
        summary=summary,
        investor_signals=[
            SummaryCard(
                title="Trend balance",
                value=f"{improving_count} improving / {watching_count} watching",
                detail="Use this to calibrate how aggressive to be with pipeline expansion.",
            ),
            SummaryCard(
                title="Average liquidity",
                value=f"{median_dom} DOM",
                detail="Lower days-on-market can reduce negotiation windows.",
            ),
        ],
        workflow_links=_product_workflow_links(source_surface="suburbs"),
        workflow_snapshot=_workflow_snapshot(
            stage="suburb_dashboard",
            primary_suburb_slug=(items[0].slug if items else None),
            next_step="Open advisor for the highest-priority suburb and run a strategy-aligned recommendation.",
            next_href=(f"/advisor?query={items[0].slug}&query_type=slug" if items else "/advisor"),
            investor_message="Convert suburb-level momentum into a property-level go/no-go recommendation.",
        ),
        items=items,
    )


def _get_price_position(subject_price: int, low: int, high: int) -> str:
    if high == 0:
        return "insufficient_data"
    if subject_price < low:
        return "below_range"
    if subject_price > high:
        return "above_range"
    return "in_range"


def _build_advisory_input_contract(
    query: str,
    effective_type: str,
    suburb_slug: Optional[str],
    comparable_count: int,
) -> AdvisoryInputs:
    required_inputs = {
        "subject_property_identity": bool(query),
        "persisted_property_record": bool(suburb_slug or effective_type in {"address", "slug"}),
    }
    optional_inputs = {
        "persisted_comparable_sales": comparable_count > 0,
        "persisted_suburb_metrics": suburb_slug is not None,
        "persisted_watchlist_context": True,
    }
    missing_behavior = {
        "required": "If required persisted identity is missing, return baseline watch guidance rather than synthesizing unsupported advice.",
        "persisted_comparable_sales": (
            "If no comparable candidates pass selection rules, advice remains available but confidence and comparable snapshot move to explicit insufficient-data semantics."
        ),
        "persisted_suburb_metrics": "If suburb metrics are missing, retain property advice output and use baseline demand/supply wording.",
        "persisted_watchlist_context": "If watchlist context is missing, omit strategy-specific reinforcement and keep a balanced default lens.",
    }
    return AdvisoryInputs(
        query=query,
        query_type=effective_type,
        suburb_slug=suburb_slug,
        contract_version="phase2.round3",
        required_persisted_inputs=required_inputs,
        optional_persisted_inputs=optional_inputs,
        missing_data_behavior=missing_behavior,
    )


def get_property_advice(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    query_type: str = "auto",
    focus_strategy: Optional[str] = None,
    dal: DataAccessLayer = _DAL,
) -> PropertyAdvisorResponse:
    if query_type == "auto":
        effective_type = "slug" if "-" in query and "," not in query else "address"
    else:
        effective_type = query_type

    advice = dal.property_advice.get_by_address_or_slug(query) or PROPERTY_ADVISOR_FIXTURE.model_copy(
        update={
            "advice": PROPERTY_ADVISOR_FIXTURE.advice.model_copy(
                update={
                    "recommendation": "watch",
                    "confidence": "low",
                    "headline": "No direct property match found yet; showing baseline guidance.",
                }
            )
        }
    )
    suburb = dal.suburbs.get_by_slug(query) if effective_type == "slug" else None
    if not isinstance(focus_strategy, str):
        focus_strategy = None
    strategy_focus = focus_strategy or "balanced"

    comparable_items = dal.comparables.list_by_subject(ComparableQuery(query=query, max_items=5))
    prices = [item.price for item in comparable_items]
    comparable_min = min(prices) if prices else 0
    comparable_max = max(prices) if prices else 0
    subject_price = 895000
    position = _get_price_position(subject_price, comparable_min, comparable_max)

    strategy_note = f"Align recommendation with {strategy_focus} watchlist strategy assumptions."
    next_steps = list(advice.advice.next_steps)
    if strategy_note not in next_steps:
        next_steps.append(strategy_note)

    market_context = AdvisoryMarketContext(
        suburb=(suburb.name if suburb else "Southport"),
        strategy_focus=strategy_focus,
        demand_signal="Rental demand remains resilient with low vacancy in sample feed.",
        supply_signal="Listing momentum is elevated, which can soften short-term negotiation leverage.",
    )

    comparable_snapshot = ComparableSnapshot(
        sample_size=len(comparable_items),
        price_position=position,
        summary=(
            "Subject pricing sits inside the current comparable range."
            if position == "in_range"
            else (
                "No matched comparables available yet; confidence is constrained by sample depth."
                if position == "insufficient_data"
                else "Subject pricing appears stretched relative to recent sample comparables."
            )
        ),
    )

    rationale = [
        AdvisoryRationaleItem(
            signal="Comparable pricing fit",
            stance="supporting" if position == "in_range" else "caution",
            evidence=comparable_snapshot.summary,
        ),
        AdvisoryRationaleItem(
            signal="Demand vs supply",
            stance="neutral",
            evidence=f"Demand: {market_context.demand_signal} Supply: {market_context.supply_signal}",
        ),
        AdvisoryRationaleItem(
            signal="Strategy alignment",
            stance="supporting" if strategy_focus != "owner-occupier" else "neutral",
            evidence=f"Recommendation evaluated with {strategy_focus} strategy framing.",
        ),
    ]

    investor_signals = [
        AdvisoryInvestorSignal(
            title="Comp confidence",
            status="positive" if comparable_snapshot.sample_size >= 3 else "risk",
            detail=f"{comparable_snapshot.sample_size} nearby comparables currently available.",
        ),
        AdvisoryInvestorSignal(
            title="Supply pressure",
            status="risk",
            detail="Inventory momentum is elevated; model discount assumptions should stay conservative.",
        ),
    ]

    advisory_inputs = _build_advisory_input_contract(
        query=query,
        effective_type=effective_type,
        suburb_slug=(suburb.slug if suburb else advice.inputs.suburb_slug),
        comparable_count=len(comparable_items),
    )
    use_persisted_snapshot = _read_source(dal.property_advice) == "postgres" and advice.advice.evidence_summary is not None

    return advice.model_copy(
        update={
            "generated_at": datetime.now(timezone.utc),
            "data_source": _resolve_data_source(
                dal,
                dal.property_advice,
                "Property advice",
                upstream_repositories={"suburbs": dal.suburbs, "comparables": dal.comparables, "watchlist": dal.watchlist},
            ),
            "advice": advice.advice.model_copy(update={"next_steps": next_steps}),
            "market_context": (advice.market_context if use_persisted_snapshot else market_context),
            "comparable_snapshot": (advice.comparable_snapshot if use_persisted_snapshot else comparable_snapshot),
            "decision_summary": (
                advice.decision_summary
                if use_persisted_snapshot
                else (
                    f"{advice.advice.recommendation.title()} with {advice.advice.confidence} confidence. "
                    f"Subject price anchor ${subject_price:,}; comp range ${comparable_min:,}-${comparable_max:,}. "
                    "Use comparables and watchlist alerts together before placing an offer."
                )
            ),
            "rationale": (advice.rationale if use_persisted_snapshot and advice.rationale else rationale),
            "investor_signals": (advice.investor_signals if use_persisted_snapshot and advice.investor_signals else investor_signals),
            "summary_cards": [
                SummaryCard(
                    title="Recommendation",
                    value=advice.advice.recommendation.title(),
                    detail=f"Confidence: {advice.advice.confidence}",
                ),
                SummaryCard(
                    title="Comparable position",
                    value=comparable_snapshot.price_position.replace("_", " "),
                    detail=comparable_snapshot.summary,
                ),
                SummaryCard(
                    title="Strategy lens",
                    value=strategy_focus,
                    detail="Decision framing aligned to selected strategy.",
                ),
            ],
            "workflow_links": _product_workflow_links(suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug, source_surface="advisor"),
            "workflow_snapshot": _workflow_snapshot(
                stage="property_advisor",
                primary_suburb_slug=(suburb.slug if suburb else advice.inputs.suburb_slug),
                next_step="Validate price confidence in comparables before progressing offer assumptions.",
                next_href=f"/comparables?query={(suburb.slug if suburb else query)}",
                investor_message="Use this recommendation with comp evidence and watchlist alerts as one decision chain.",
            ),
            "inputs": advisory_inputs,
        }
    )


def _build_comparable_narrative(summary: ComparableSummary, query: str) -> ComparableNarrative:
    if summary.count == 0:
        return ComparableNarrative(
            price_position="insufficient_data",
            spread_commentary="No usable comps matched the current filters.",
            investor_takeaway="Broaden radius or price bounds before making a decision.",
            action_prompt="Relax one filter and rerun the comp set.",
        )
    if summary.sample_state == "low":
        return ComparableNarrative(
            price_position="aligned",
            spread_commentary=f"Only {summary.count} persisted sale candidate(s) matched for {query}; treat the range as directional only.",
            investor_takeaway="Low sample depth means negotiation anchors are usable, but conviction should stay conservative.",
            action_prompt="Validate the closest sale manually and rerun when fresher evidence lands.",
        )

    spread = summary.max_price - summary.min_price
    if summary.average_price < 870000:
        position = "discount"
    elif summary.average_price > 900000:
        position = "premium"
    else:
        position = "aligned"

    return ComparableNarrative(
        price_position=position,
        spread_commentary=f"Spread is {spread:,} across {summary.count} comparable sales for {query}.",
        investor_takeaway="Treat this as a negotiation anchor, not a valuation substitute.",
        action_prompt="Prioritise the two closest matches and verify renovation/land deltas.",
    )


def _build_comparable_summary_cards(summary: ComparableSummary, narrative: ComparableNarrative) -> List[SummaryCard]:
    if summary.count == 0:
        return [SummaryCard(title="Comp set", value="No matches", detail="Widen filters to restore signal quality.")]
    if summary.sample_state == "low":
        return [
            SummaryCard(title="Comp set", value="Low sample", detail="Persisted candidate rules found fewer than 3 matches."),
            SummaryCard(title="Average price", value=f"${summary.average_price:,}", detail="Directional only until more evidence is available."),
            SummaryCard(title="Action", value="Validate manually", detail=narrative.action_prompt),
        ]
    return [
        SummaryCard(title="Average price", value=f"${summary.average_price:,}", detail="Directional anchor for negotiation planning."),
        SummaryCard(title="Price spread", value=f"${summary.max_price - summary.min_price:,}", detail="Tighter spreads usually improve confidence."),
        SummaryCard(title="Position signal", value=narrative.price_position, detail=narrative.investor_takeaway),
    ]



def _resolve_comparable_set_quality(
    source: Literal["mock", "postgres", "fallback_mock"],
    min_price: Optional[int],
    max_price: Optional[int],
    max_distance_km: Optional[float],
) -> str:
    filtered = any(value is not None for value in [min_price, max_price, max_distance_km])
    if source == "postgres":
        return "db-backed-filtered" if filtered else "db-backed"
    return "mvp-sample-filtered" if filtered else "mvp-sample"

def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_distance_km: Optional[float] = None,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    criteria = ComparableQuery(
        query=query,
        max_items=max_items,
        min_price=min_price,
        max_price=max_price,
        max_distance_km=max_distance_km,
    )
    latest_set = dal.comparables.get_latest_set(criteria)
    generated_set = latest_set or (
        dal.comparables.generate_comparable_set(criteria) if _read_source(dal.comparables) != "mock" else None
    )
    items = generated_set.items if generated_set is not None else dal.comparables.list_by_subject(criteria)

    if not items:
        empty_summary = ComparableSummary(
            count=0,
            min_price=0,
            max_price=0,
            average_price=0,
            sample_state="empty",
            quality_score=(generated_set.quality_score if generated_set is not None else None),
            quality_label=(generated_set.quality_label if generated_set is not None else None),
            algorithm_version=(generated_set.algorithm_version if generated_set is not None else None),
        )
        narrative = _build_comparable_narrative(empty_summary, query)
        return ComparablesResponse(
            generated_at=datetime.now(timezone.utc),
            data_source=_resolve_data_source(dal, dal.comparables, "Comparables", upstream_repositories={"suburbs": dal.suburbs}),
            subject=query,
            set_quality="empty",
            query=query,
            items=[],
            summary=empty_summary,
            narrative=narrative,
            summary_cards=_build_comparable_summary_cards(empty_summary, narrative),
            workflow_links=_product_workflow_links(suburb_slug=query, source_surface="comparables"),
            workflow_snapshot=_workflow_snapshot(
                stage="comparables",
                next_step="Return to advisor and apply this pricing evidence to recommendation confidence.",
                next_href=f"/advisor?query={query}&query_type=auto",
                investor_message="Comparables are a negotiation anchor that should feed recommendation confidence.",
            ),
        )

    prices = [item.price for item in items]
    summary = ComparableSummary(
        count=len(items),
        min_price=min(prices),
        max_price=max(prices),
        average_price=round(mean(prices)),
        sample_state=("low" if len(items) < 3 else "adequate"),
        quality_score=(generated_set.quality_score if generated_set is not None else None),
        quality_label=(generated_set.quality_label if generated_set is not None else None),
        algorithm_version=(generated_set.algorithm_version if generated_set is not None else None),
    )
    narrative = _build_comparable_narrative(summary, query)
    return ComparablesResponse(
        generated_at=datetime.now(timezone.utc),
        data_source=_resolve_data_source(dal, dal.comparables, "Comparables", upstream_repositories={"suburbs": dal.suburbs}),
        subject=query,
        set_quality=(
            f"persisted-{generated_set.quality_label}"
            if latest_set is not None
            else (
                f"generated-{generated_set.quality_label}"
                if generated_set is not None and _read_source(dal.comparables) == "postgres"
                else (
                    "db-backed-low-sample"
                    if _read_source(dal.comparables) == "postgres" and summary.sample_state == "low"
                    else _resolve_comparable_set_quality(
                        _read_source(dal.comparables),
                        min_price=min_price,
                        max_price=max_price,
                        max_distance_km=max_distance_km,
                    )
                )
            )
        ),
        query=query,
        items=items,
        summary=summary,
        narrative=narrative,
        summary_cards=_build_comparable_summary_cards(summary, narrative),
        workflow_links=_product_workflow_links(suburb_slug=query, source_surface="comparables"),
        workflow_snapshot=_workflow_snapshot(
            stage="comparables",
            next_step="Push this comp evidence into advisor and then confirm watchlist action status.",
            next_href=f"/advisor?query={query}&query_type=auto",
            investor_message="Treat comp pricing as evidence, then decide via advisor and action through watchlist.",
        ),
    )


def _build_watchlist_groups(group_by: Literal["none", "state", "strategy"], items: List[WatchlistEntry]) -> List[WatchlistGroup]:
    if group_by == "none":
        return []

    grouped: Dict[str, List[WatchlistEntry]] = {}
    for item in items:
        key = item.state if group_by == "state" else item.strategy
        grouped.setdefault(key, []).append(item)

    ranked_groups: list[tuple[int, WatchlistGroup]] = []
    for key, entries in grouped.items():
        prioritized_entries = _sort_watchlist_entries_for_scan(entries)
        actionable_outcomes = sum(
            1
            for entry in prioritized_entries
            if (entry.latest_context.latest_decision.outcome if entry.latest_context and entry.latest_context.latest_decision else "unrecorded")
            in _ACTIONABLE_DECISION_OUTCOMES
        )
        top_entry = prioritized_entries[0] if prioritized_entries else None
        top_outcome = (
            top_entry.latest_context.latest_decision.outcome
            if top_entry and top_entry.latest_context and top_entry.latest_context.latest_decision
            else "unrecorded"
        )
        ranked_groups.append(
            (
                actionable_outcomes,
                WatchlistGroup(
                    key=key.lower(),
                    label=key,
                    entries=prioritized_entries,
                    action_required=sum(1 for entry in prioritized_entries if entry.watch_status in {"review", "paused"}),
                    high_alerts=sum(1 for entry in prioritized_entries for alert in entry.alerts if alert.severity == "high"),
                    compact_rationale_cue=_build_compact_evidence_hint(
                        outcome=top_outcome,
                        emphasis_reason=(
                            f"{_reason_label_phrase('active_follow_up')}; "
                            "prioritize first: actionable/review follow-up rows"
                        ),
                        grouping_reason=f"grouped by {group_by}",
                    ),
                ),
            )
        )
    return [
        group
        for _, group in sorted(
            ranked_groups,
        key=lambda group: (
                -group[0],
                -group[1].action_required,
                -group[1].high_alerts,
                group[1].label.lower(),
        ),
    )
    ]


def _sort_watchlist_entries_for_scan(items: List[WatchlistEntry]) -> List[WatchlistEntry]:
    def _entry_timestamp(entry: WatchlistEntry) -> int:
        latest_decision_at = (
            entry.latest_context.latest_decision.acted_at
            if entry.latest_context and entry.latest_context.latest_decision
            else None
        )
        context_updated_at = entry.latest_context.updated_at.isoformat() if entry.latest_context else None
        parsed = _parse_timestamp(latest_decision_at) or _parse_timestamp(context_updated_at)
        return int(parsed.timestamp()) if parsed else 0

    def _entry_outcome(entry: WatchlistEntry) -> str:
        if entry.latest_context and entry.latest_context.latest_decision:
            return entry.latest_context.latest_decision.outcome
        return "unrecorded"

    return sorted(
        items,
        key=lambda entry: (
            -_decision_outcome_priority(_entry_outcome(entry)),
            -_WATCHLIST_STATUS_PRIORITY.get(entry.watch_status, 0),
            -_entry_timestamp(entry),
            entry.suburb_slug,
        ),
    )


def get_watchlist(
    suburb_slug: Optional[str] = None,
    strategy: Optional[str] = None,
    state: Optional[str] = None,
    watch_status: Optional[str] = None,
    latest_outcome: Optional[str] = None,
    group_by: Literal["none", "state", "strategy"] = "strategy",
    dal: DataAccessLayer = _DAL,
) -> WatchlistResponse:
    items = dal.watchlist.list_entries(
        WatchlistQuery(
            suburb_slug=suburb_slug,
            strategy=strategy,
            state=state,
            watch_status=watch_status,
        )
    )
    enriched_items = [_enrich_watchlist_entry_context(item, dal=dal) for item in items]
    latest_outcome_breakdown = {
        "escalate_for_closer_review": 0,
        "revisit_later": 0,
        "continue_monitoring": 0,
        "close_for_now": 0,
        "unrecorded": 0,
    }
    for item in enriched_items:
        outcome = str(
            item.latest_context.latest_decision.outcome
            if item.latest_context and item.latest_context.latest_decision
            else ""
        ).strip()
        if outcome in latest_outcome_breakdown and outcome != "unrecorded":
            latest_outcome_breakdown[outcome] += 1
        else:
            latest_outcome_breakdown["unrecorded"] += 1

    if latest_outcome and latest_outcome in _DECISION_OUTCOME_FILTER_VALUES and latest_outcome != "unrecorded":
        enriched_items = [
            item
            for item in enriched_items
            if item.latest_context and item.latest_context.latest_decision and item.latest_context.latest_decision.outcome == latest_outcome
        ]
    enriched_items = _sort_watchlist_entries_for_scan(enriched_items)

    alert_counts = {"info": 0, "watch": 0, "high": 0}
    by_status = {"active": 0, "review": 0, "paused": 0, "archived": 0}
    by_strategy = {"yield": 0, "owner-occupier": 0, "balanced": 0}
    action_counts = {"needs_review": 0, "ready_to_progress": 0, "on_hold": 0, "archived": 0}
    for item in enriched_items:
        by_status[item.watch_status] += 1
        by_strategy[item.strategy] += 1
        if item.watch_status == "review":
            action_counts["needs_review"] += 1
        elif item.watch_status == "active":
            action_counts["ready_to_progress"] += 1
        elif item.watch_status == "paused":
            action_counts["on_hold"] += 1
        else:
            action_counts["archived"] += 1
        for alert in item.alerts:
            alert_counts[alert.severity] += 1

    summary = WatchlistSummary(
        total_entries=len(enriched_items),
        active_entries=by_status["active"],
        grouped_view=group_by,
        alert_counts=alert_counts,
        by_status=by_status,
        by_strategy=by_strategy,
        action_counts=action_counts,
        latest_outcome_breakdown=latest_outcome_breakdown,
        latest_outcome_distribution=_build_outcome_distribution(latest_outcome_breakdown),
        active_latest_outcome_filter=(
            latest_outcome if latest_outcome in _DECISION_OUTCOME_FILTER_VALUES and latest_outcome != "unrecorded" else None
        ),
        latest_outcome_focus_cue=(
            _DECISION_OUTCOME_LABELS.get(latest_outcome, latest_outcome.replace("_", " "))
            if latest_outcome and latest_outcome in _DECISION_OUTCOME_FILTER_VALUES and latest_outcome != "unrecorded"
            else "All latest outcomes"
        ),
        next_step_scan_cue=_build_action_scan_default_cue(latest_outcome_breakdown),
        next_step_batching_cue=_build_next_step_batching_cue(latest_outcome_breakdown),
        compact_follow_up_grouping_cue=(
            f"{_build_compact_follow_up_grouping_cue(latest_outcome_breakdown)} — "
            f"{_build_compact_rationale_language_cue(latest_outcome_breakdown)}"
        ),
        investor_brief=(
            "Focus this week on review and paused suburbs with high-severity pricing alerts; archive only after outcomes are captured."
            if alert_counts["high"] > 0
            else "No critical alerts detected; continue weekly monitoring cadence."
        ),
    )
    return WatchlistResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist", upstream_repositories={"suburbs": dal.suburbs}),
        summary=summary,
        items=enriched_items,
        groups=_build_watchlist_groups(group_by, enriched_items),
        summary_cards=[
            SummaryCard(title="Action queue", value=str(action_counts["needs_review"]), detail="Suburbs needing manual review now."),
            SummaryCard(title="High-severity alerts", value=str(alert_counts["high"]), detail="Potential stop/go blockers."),
            SummaryCard(title="Ready to progress", value=str(action_counts["ready_to_progress"]), detail="Candidates for deeper due diligence."),
        ],
        workflow_links=_product_workflow_links(suburb_slug=suburb_slug, source_surface="watchlist"),
        workflow_snapshot=_workflow_snapshot(
            stage="watchlist",
            primary_suburb_slug=(suburb_slug if suburb_slug else (enriched_items[0].suburb_slug if enriched_items else None)),
            next_step="Open advisor for a review-status suburb and confirm whether it can progress this week.",
            next_href=(f"/advisor?query={suburb_slug or enriched_items[0].suburb_slug}&query_type=slug" if (suburb_slug or enriched_items) else "/advisor"),
            investor_message="Watchlist converts insights into weekly action: review, progress, or hold.",
        ),
    )


def get_watchlist_detail(suburb_slug: str, dal: DataAccessLayer = _DAL) -> Optional[WatchlistDetailResponse]:
    item = dal.watchlist.get_entry(suburb_slug)
    if not item:
        return None
    return WatchlistDetailResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist detail", upstream_repositories={"suburbs": dal.suburbs}),
        item=_enrich_watchlist_entry_context(item, dal=dal),
    )


def _latest_decision_for_watchlist(orchestration: OrchestrationReviewResponse, suburb_slug: str) -> Optional[DecisionOutcomeSummary]:
    suburb_token = suburb_slug.strip().lower()
    for plan in orchestration.plans:
        record = plan.reviewer_decision_record
        plan_text = " ".join(
            [
                plan.event_id,
                plan.event_type,
                plan.strategy_summary,
                plan.revisit_reason,
                plan.message or "",
            ]
        ).lower()
        if record is not None and suburb_token and suburb_token in plan_text:
            return record
    return next((plan.reviewer_decision_record for plan in orchestration.plans if plan.reviewer_decision_record is not None), None)


def _latest_plan_for_watchlist(orchestration: OrchestrationReviewResponse, suburb_slug: str) -> Optional[OrchestrationPlanItem]:
    suburb_token = suburb_slug.strip().lower()
    for plan in orchestration.plans:
        plan_text = " ".join(
            [
                plan.event_id,
                plan.event_type,
                plan.strategy_summary,
                plan.revisit_reason,
                plan.message or "",
                plan.reviewer_decision_summary or "",
                plan.reviewer_decision_record.summary if plan.reviewer_decision_record else "",
                plan.reviewer_decision_record.rationale if plan.reviewer_decision_record else "",
            ]
        ).lower()
        if suburb_token and suburb_token in plan_text:
            return plan
    return orchestration.plans[0] if orchestration.plans else None


def _classify_watchlist_follow_up_posture(
    *,
    watch_status: Optional[str],
    high_alert_count: int,
    outcome: Optional[str],
    reviewer_action_state: Optional[str],
    decision_support_state: Optional[str],
) -> Literal["do_now", "batch_later", "recently_closed"]:
    normalized_outcome = (outcome or "").strip()
    normalized_reviewer_state = (reviewer_action_state or "").strip()
    normalized_decision_state = (decision_support_state or "").strip()
    normalized_watch_status = (watch_status or "").strip()
    if normalized_outcome == "close_for_now" or normalized_reviewer_state == "closed":
        return "recently_closed"
    if normalized_decision_state in {"active_attention", "reopen_for_closer_review"}:
        return "do_now"
    if normalized_outcome in {"escalate_for_closer_review", "revisit_later"}:
        return "do_now"
    if normalized_watch_status in {"review", "paused"} or high_alert_count > 0:
        return "do_now"
    return "batch_later"


def _enrich_watchlist_entry_context(item: WatchlistEntry, dal: DataAccessLayer = _DAL) -> WatchlistEntry:
    advice = get_property_advice(query=item.suburb_slug, query_type="slug", dal=dal)
    comparables = get_comparables(query=item.suburb_slug, max_items=5, dal=dal)
    orchestration = get_orchestration_review_status(limit=3)

    advisory_context = f"{advice.advice.recommendation} ({advice.advice.confidence}) — {advice.advice.headline}"
    if advice.advice.fallback_state and advice.advice.fallback_state != "none":
        advisory_context = f"{advisory_context} | thin-data: {advice.advice.fallback_state}"

    if comparables.summary.sample_state in {"empty", "low"}:
        comparables_context = (
            f"{comparables.summary.count} comps ({comparables.summary.sample_state}); pricing signal is directional only."
        )
    else:
        comparables_context = (
            f"{comparables.summary.count} comps, avg ${comparables.summary.average_price:,}, state={comparables.summary.sample_state}"
        )
    latest_decision = _latest_decision_for_watchlist(orchestration, item.suburb_slug)
    high_alert_count = sum(1 for alert in item.alerts if alert.severity == "high")
    if item.watch_status in {"review", "paused"} or high_alert_count > 0:
        emphasis_reason = f"{_reason_label_phrase('active_follow_up')}; prioritize now for status/alert follow-up"
    else:
        emphasis_reason = f"{_reason_label_phrase('weekly_monitor')}; queue later in monitor-later treatment"

    return item.model_copy(
        update={
            "latest_context": WatchlistContextSummary(
                advisory=advisory_context,
                comparables=comparables_context,
                orchestration=f"{orchestration.summary.current_state}; review_required={orchestration.summary.review_required_count}",
                latest_decision=latest_decision,
                latest_decision_triage_cue=(_format_decision_triage_cue(latest_decision) if latest_decision else None),
                latest_decision_next_step_cue=(
                    _decision_next_step_cue(latest_decision.outcome if latest_decision else None)
                ),
                latest_decision_batch_cue=_decision_batch_cue(latest_decision.outcome if latest_decision else None),
                latest_decision_rationale_cue=_build_compact_evidence_hint(
                    outcome=(latest_decision.outcome if latest_decision else None),
                    emphasis_reason=emphasis_reason,
                    grouping_reason=(
                        f"high alerts={high_alert_count}, watch status={item.watch_status}"
                    ),
                ),
                updated_at=datetime.now(timezone.utc),
            )
        }
    )


def upsert_watchlist_action(payload: WatchlistActionRequest, dal: DataAccessLayer = _DAL) -> WatchlistActionResponse:
    action, item = dal.watchlist.upsert_entry(
        WatchlistUpsertRequest(
            suburb_slug=payload.suburb_slug,
            source_surface=payload.source_surface,
            strategy=payload.strategy,
            watch_status=payload.watch_status,
            notes=payload.notes,
        )
    )
    return WatchlistActionResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist action", upstream_repositories={"suburbs": dal.suburbs}),
        action=action,
        item=_enrich_watchlist_entry_context(item, dal=dal),
    )


def get_watchlist_alerts(severity: Optional[str] = None, dal: DataAccessLayer = _DAL) -> WatchlistAlertsResponse:
    items = dal.watchlist.list_alerts(severity=severity)
    return WatchlistAlertsResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist alerts", upstream_repositories={"suburbs": dal.suburbs}),
        total=len(items),
        items=items,
    )


def get_watchlist_events(limit: int = 12, dal: DataAccessLayer = _DAL) -> WatchlistEventsResponse:
    entries = dal.watchlist.list_entries(WatchlistQuery())
    events: list[WatchlistEventItem] = []
    orchestration = get_orchestration_review_status(limit=30)

    for entry in entries:
        latest_decision = _latest_decision_for_watchlist(orchestration, entry.suburb_slug)
        latest_plan = _latest_plan_for_watchlist(orchestration, entry.suburb_slug)
        high_alert_count = sum(1 for alert in entry.alerts if alert.severity == "high")
        event_posture = _classify_watchlist_follow_up_posture(
            watch_status=entry.watch_status,
            high_alert_count=high_alert_count,
            outcome=(latest_decision.outcome if latest_decision else None),
            reviewer_action_state=(latest_plan.reviewer_action_state if latest_plan else None),
            decision_support_state=(latest_plan.decision_support_state if latest_plan else None),
        )
        if entry.alerts:
            latest_alert = sorted(entry.alerts, key=lambda alert: alert.observed_at, reverse=True)[0]
            events.append(
                WatchlistEventItem(
                    event_id=f"alert:{entry.suburb_slug}:{latest_alert.metric}:{latest_alert.observed_at}",
                    category="alert",
                    occurred_at=_parse_timestamp(latest_alert.observed_at) or datetime.now(timezone.utc),
                    title=f"{entry.suburb_name}: {latest_alert.title}",
                    detail=f"{latest_alert.detail} (severity: {latest_alert.severity})",
                    suburb_slug=entry.suburb_slug,
                    suburb_name=entry.suburb_name,
                    latest_decision=latest_decision,
                    latest_decision_triage_cue=(_format_decision_triage_cue(latest_decision) if latest_decision else None),
                    reviewer_action_state=(latest_plan.reviewer_action_state if latest_plan else None),
                    follow_up_state=(latest_plan.follow_up_state if latest_plan else None),
                    decision_support_state=(latest_plan.decision_support_state if latest_plan else None),
                    follow_up_posture=event_posture,
                    follow_up_href=(
                        f"/watchlist?group_by=strategy&detail_slug={entry.suburb_slug}&suburb_slug={entry.suburb_slug}"
                        f"&latest_outcome={(latest_decision.outcome if latest_decision else 'unrecorded')}"
                    ),
                    follow_up_label="Open detail in current review pass",
                )
            )

        events.append(
            WatchlistEventItem(
                event_id=f"watchlist:{entry.suburb_slug}:{entry.watch_status}",
                category="watchlist",
                occurred_at=datetime.now(timezone.utc),
                title=f"{entry.suburb_name}: watchlist status is {entry.watch_status}",
                detail=f"Strategy={entry.strategy}; target band ${entry.target_buy_range_min:,}-${entry.target_buy_range_max:,}.",
                suburb_slug=entry.suburb_slug,
                suburb_name=entry.suburb_name,
                latest_decision=latest_decision,
                latest_decision_triage_cue=(_format_decision_triage_cue(latest_decision) if latest_decision else None),
                reviewer_action_state=(latest_plan.reviewer_action_state if latest_plan else None),
                follow_up_state=(latest_plan.follow_up_state if latest_plan else None),
                decision_support_state=(latest_plan.decision_support_state if latest_plan else None),
                follow_up_posture=event_posture,
                follow_up_href=(
                    f"/watchlist?group_by=strategy&detail_slug={entry.suburb_slug}&suburb_slug={entry.suburb_slug}"
                    f"&latest_outcome={(latest_decision.outcome if latest_decision else 'unrecorded')}"
                ),
                follow_up_label="Continue watchlist review loop",
            )
        )

        events.append(
            WatchlistEventItem(
                event_id=f"advisory:{entry.suburb_slug}",
                category="advisory",
                occurred_at=datetime.now(timezone.utc),
                title=f"{entry.suburb_name}: advisory refresh recommended",
                detail=f"Re-check recommendation for {entry.strategy} strategy before progressing this suburb.",
                suburb_slug=entry.suburb_slug,
                suburb_name=entry.suburb_name,
                latest_decision=latest_decision,
                latest_decision_triage_cue=(_format_decision_triage_cue(latest_decision) if latest_decision else None),
                reviewer_action_state=(latest_plan.reviewer_action_state if latest_plan else None),
                follow_up_state=(latest_plan.follow_up_state if latest_plan else None),
                decision_support_state=(latest_plan.decision_support_state if latest_plan else None),
                follow_up_posture=event_posture,
                follow_up_href=(
                    f"/advisor?query={entry.suburb_slug}&query_type=slug&from=watchlist_events"
                    f"&intent={(event_posture if event_posture != 'recently_closed' else 'monitor')}"
                ),
                follow_up_label=(
                    "Run advisor/comparables now" if event_posture == "do_now" else "Refresh advisor context"
                ),
            )
        )

    for plan in orchestration.plans:
        occurred_at = _parse_timestamp(plan.queued_at or plan.created_at) or datetime.now(timezone.utc)
        latest_decision = plan.reviewer_decision_record
        follow_up_posture = _classify_watchlist_follow_up_posture(
            watch_status=None,
            high_alert_count=0,
            outcome=(latest_decision.outcome if latest_decision else None),
            reviewer_action_state=plan.reviewer_action_state,
            decision_support_state=plan.decision_support_state,
        )
        events.append(
            WatchlistEventItem(
                event_id=f"orchestration:{plan.event_id}",
                category="orchestration",
                occurred_at=occurred_at,
                title=f"Orchestration event: {plan.event_type}",
                detail=(
                    f"{plan.strategy_summary} Pending action: {plan.action}."
                    if plan.strategy_summary
                    else f"Pending action: {plan.action}."
                ),
                latest_decision=latest_decision,
                latest_decision_triage_cue=(_format_decision_triage_cue(latest_decision) if latest_decision else None),
                reviewer_action_state=plan.reviewer_action_state,
                follow_up_state=plan.follow_up_state,
                decision_support_state=plan.decision_support_state,
                follow_up_posture=follow_up_posture,
                follow_up_href=(
                    f"/orchestration?view=actionable"
                    f"&reviewer_action_state_focus={plan.reviewer_action_state}"
                    f"&follow_up_state_focus={plan.follow_up_state}"
                    f"&outcome_focus={(latest_decision.outcome if latest_decision else 'unrecorded')}"
                ),
                follow_up_label=(
                    "Resume do-now orchestration pass"
                    if follow_up_posture == "do_now"
                    else ("Review recently closed orchestration item" if follow_up_posture == "recently_closed" else "Open batch-later orchestration pass")
                ),
            )
        )

    events.sort(key=lambda event: event.occurred_at, reverse=True)
    limited = events[: max(limit, 0)]

    return WatchlistEventsResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(
            dal,
            dal.watchlist,
            "Watchlist events",
            upstream_repositories={"suburbs": dal.suburbs},
        ),
        total=len(limited),
        items=limited,
    )


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _normalize_event_type(value: object) -> str:
    return str(value or "").strip().lower()


def get_orchestration_review_status(
    *,
    artifact_path: Path = Path(".dev_pipeline/notifications"),
    limit: int = 10,
    outcome_focus: Optional[str] = None,
    reviewer_action_state_focus: Optional[str] = None,
    follow_up_state_focus: Optional[str] = None,
) -> OrchestrationReviewResponse:
    state_path = artifact_path / "bridge_state.json"
    state_payload: dict[str, object] = {}
    if state_path.exists():
        loaded = json.loads(state_path.read_text())
        if isinstance(loaded, dict):
            state_payload = loaded

    delivered_state = state_payload.get("delivered_event_ids", {})
    queued_state = state_payload.get("queued_event_ids", {})
    if not isinstance(delivered_state, dict):
        delivered_state = {}
    if not isinstance(queued_state, dict):
        queued_state = {}

    records: list[dict[str, object]] = []
    if artifact_path.exists():
        for path in sorted(artifact_path.glob("*.json")):
            if path == state_path:
                continue
            artifact = json.loads(path.read_text())
            if not isinstance(artifact, dict):
                continue
            event_type = _normalize_event_type(artifact.get("event_type"))
            event_id = str(artifact.get("event_id") or "")
            if not event_id or event_type not in _ORCHESTRATION_EVENT_TYPES or event_id in delivered_state:
                continue
            records.append(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "session_key": (artifact.get("origin") or {}).get("session_key") if isinstance(artifact.get("origin"), dict) else None,
                    "message": str(artifact.get("summary") or ""),
                    "created_at": artifact.get("created_at"),
                    "queued_at": queued_state.get(event_id),
                }
            )

    all_plans = _build_orchestration_queue(records)
    all_plans = _apply_reviewer_action_state(all_plans, _load_review_state(artifact_path))
    decision_outcome_cue, decision_outcome_breakdown = _build_decision_outcome_grouping(all_plans)
    action_scan_default_cue = _build_action_scan_default_cue(decision_outcome_breakdown)
    next_step_batching_cue = _build_next_step_batching_cue(decision_outcome_breakdown)
    compact_follow_up_grouping_cue = (
        f"{_build_compact_follow_up_grouping_cue(decision_outcome_breakdown)} — "
        f"{_build_compact_rationale_language_cue(decision_outcome_breakdown)}"
    )
    filtered_by_outcome = _filter_plans_by_decision_outcome(all_plans, outcome_focus)
    filtered_plans = _sort_orchestration_plans_for_scan(
        _filter_plans_by_execution_state(
            filtered_by_outcome,
            reviewer_action_state_focus=reviewer_action_state_focus,
            follow_up_state_focus=follow_up_state_focus,
        )
    )
    plans = filtered_plans[:limit] if limit > 0 else filtered_plans

    review_required_count = sum(1 for plan in plans if plan.get("requires_human_review"))
    auto_continue_count = sum(1 for plan in plans if plan.get("auto_continue"))
    queued_count = sum(1 for plan in plans if plan.get("queued_at"))

    latest_event_at = max(
        (
            ts
            for ts in (_parse_timestamp(plan.get("queued_at")) or _parse_timestamp(plan.get("created_at")) for plan in plans)
            if ts is not None
        ),
        default=None,
    )

    now = datetime.now(timezone.utc)
    if latest_event_at is None:
        freshness = "empty"
    elif now - latest_event_at <= timedelta(hours=24):
        freshness = "fresh"
    else:
        freshness = "stale"

    if review_required_count > 0:
        current_state = "awaiting_review"
        review_plans = [
            plan
            for plan in plans
            if bool(plan.get("requires_human_review")) and str(plan.get("reviewer_action_state") or "pending") != "closed"
        ]
        state_cue = _build_follow_up_state_cue(review_plans)
        carry_forward_summary = _build_carry_forward_summary(review_plans)
        revisit_guidance_cue = _build_revisit_guidance_cue(review_plans)
        notification_boundary_cue = _build_notification_boundary_cue(plans)
        next_action = (
            "Review highest-priority carry-forward follow-up, apply reviewer action state, then continue the orchestration loop."
            + (f" Active follow-up states: {state_cue}." if state_cue else "")
            + (f" Carry-forward summary: {carry_forward_summary}." if carry_forward_summary else "")
            + (f" Revisit guidance: {revisit_guidance_cue}." if revisit_guidance_cue else "")
            + (f" Notification boundaries: {notification_boundary_cue}" if notification_boundary_cue else "")
            + (f" Outcome triage: {decision_outcome_cue}." if decision_outcome_cue else "")
            + (f" {action_scan_default_cue}" if action_scan_default_cue else "")
            + (
                f" Active outcome focus: {outcome_focus.replace('_', ' ')} ({len(plans)} of {len(all_plans)} visible)."
                if outcome_focus and outcome_focus in _DECISION_OUTCOME_FILTER_VALUES
                else ""
            )
            + (
                f" Active reviewer action state: {reviewer_action_state_focus.replace('_', ' ')}."
                if reviewer_action_state_focus and reviewer_action_state_focus in _REVIEWER_ACTION_STATE_FILTER_VALUES
                else ""
            )
            + (
                f" Active follow-up state: {follow_up_state_focus.replace('_', ' ')}."
                if follow_up_state_focus and follow_up_state_focus in _FOLLOW_UP_STATE_FILTER_VALUES
                else ""
            )
        )
    elif plans:
        current_state = "auto_progressing"
        state_cue = _build_follow_up_state_cue(plans)
        carry_forward_summary = _build_carry_forward_summary(plans)
        revisit_guidance_cue = _build_revisit_guidance_cue(plans)
        notification_boundary_cue = _build_notification_boundary_cue(plans)
        next_action = (
            "No manual blocker active; monitor auto-progress outcomes and revisit flagged items after downstream surfaces refresh."
            + (f" Active follow-up states: {state_cue}." if state_cue else "")
            + (f" Carry-forward summary: {carry_forward_summary}." if carry_forward_summary else "")
            + (f" Revisit guidance: {revisit_guidance_cue}." if revisit_guidance_cue else "")
            + (f" Notification boundaries: {notification_boundary_cue}" if notification_boundary_cue else "")
            + (f" Outcome triage: {decision_outcome_cue}." if decision_outcome_cue else "")
            + (f" {action_scan_default_cue}" if action_scan_default_cue else "")
            + (
                f" Active outcome focus: {outcome_focus.replace('_', ' ')} ({len(plans)} of {len(all_plans)} visible)."
                if outcome_focus and outcome_focus in _DECISION_OUTCOME_FILTER_VALUES
                else ""
            )
            + (
                f" Active reviewer action state: {reviewer_action_state_focus.replace('_', ' ')}."
                if reviewer_action_state_focus and reviewer_action_state_focus in _REVIEWER_ACTION_STATE_FILTER_VALUES
                else ""
            )
            + (
                f" Active follow-up state: {follow_up_state_focus.replace('_', ' ')}."
                if follow_up_state_focus and follow_up_state_focus in _FOLLOW_UP_STATE_FILTER_VALUES
                else ""
            )
        )
    else:
        current_state = "idle"
        next_action = "No pending orchestration events. Wait for next runtime cycle, then restart review when new outcomes arrive."

    return OrchestrationReviewResponse(
        summary=OrchestrationReviewSummary(
            current_state=current_state,
            latest_event_at=(latest_event_at.isoformat() if latest_event_at else None),
            generated_at=now,
            freshness=freshness,
            review_needed=review_required_count > 0,
            review_required_count=review_required_count,
            auto_continue_count=auto_continue_count,
            queued_count=queued_count,
            pending_count=len(plans),
            total_pending_count=len(all_plans),
            next_action=next_action,
            decision_outcome_cue=decision_outcome_cue,
            decision_outcome_breakdown=decision_outcome_breakdown,
            latest_outcome_distribution=_build_outcome_distribution(decision_outcome_breakdown),
            active_decision_outcome_filter=(
                outcome_focus if outcome_focus and outcome_focus in _DECISION_OUTCOME_FILTER_VALUES else None
            ),
            active_reviewer_action_state_filter=(
                reviewer_action_state_focus
                if reviewer_action_state_focus and reviewer_action_state_focus in _REVIEWER_ACTION_STATE_FILTER_VALUES
                else None
            ),
            active_follow_up_state_filter=(
                follow_up_state_focus
                if follow_up_state_focus and follow_up_state_focus in _FOLLOW_UP_STATE_FILTER_VALUES
                else None
            ),
            action_scan_default_cue=action_scan_default_cue,
            next_step_batching_cue=next_step_batching_cue,
            compact_follow_up_grouping_cue=compact_follow_up_grouping_cue,
        ),
        plans=[
            OrchestrationPlanItem(
                event_id=str(plan.get("event_id") or ""),
                event_type=str(plan.get("event_type") or ""),
                bucket=str(plan.get("bucket") or "other"),
                action=str(plan.get("action") or "notify_only"),
                requires_human_review=bool(plan.get("requires_human_review")),
                auto_continue=bool(plan.get("auto_continue")),
                created_at=plan.get("created_at"),
                queued_at=plan.get("queued_at"),
                strategy_summary=str(plan.get("strategy_summary") or ""),
                follow_up_state=str(plan.get("follow_up_state") or "monitor"),
                next_step_outcome=str(plan.get("next_step_outcome") or ""),
                revisit_reason=str(plan.get("revisit_reason") or ""),
                is_carry_forward_follow_up=bool(plan.get("is_carry_forward_follow_up")),
                reviewer_action_state=str(plan.get("reviewer_action_state") or "pending"),
                reviewer_available_actions=[
                    str(action)
                    for action in plan.get("reviewer_available_actions", [])
                    if str(action) in {"acknowledge", "close_follow_up"}
                ],
                reviewer_last_action_at=(
                    str(plan.get("reviewer_last_action_at"))
                    if plan.get("reviewer_last_action_at")
                    else None
                ),
                reviewer_last_action=(
                    str(plan.get("reviewer_last_action"))
                    if str(plan.get("reviewer_last_action") or "") in {"acknowledge", "close_follow_up"}
                    else None
                ),
                reviewer_last_action_rationale=(
                    str(plan.get("reviewer_last_action_rationale")).strip()
                    if str(plan.get("reviewer_last_action_rationale") or "").strip()
                    else None
                ),
                reviewer_decision_outcome=(
                    str(plan.get("reviewer_decision_outcome"))
                    if str(plan.get("reviewer_decision_outcome") or "") in {"continue_monitoring", "revisit_later", "close_for_now", "escalate_for_closer_review"}
                    else None
                ),
                reviewer_decision_summary=(
                    str(plan.get("reviewer_decision_summary")).strip()
                    if str(plan.get("reviewer_decision_summary") or "").strip()
                    else None
                ),
                reviewer_decision_record=(
                    DecisionOutcomeSummary(**plan.get("reviewer_decision_record"))
                    if isinstance(plan.get("reviewer_decision_record"), dict)
                    else None
                ),
                revisit_guidance=str(plan.get("revisit_guidance") or ""),
                next_review_cue=str(plan.get("next_review_cue") or ""),
                next_step_action_cue=_decision_next_step_cue(str(plan.get("reviewer_decision_outcome") or "")),
                next_step_batch_cue=_decision_batch_cue(str(plan.get("reviewer_decision_outcome") or "")),
                decision_support_state=(
                    str(plan.get("decision_support_state"))
                    if str(plan.get("decision_support_state") or "") in {"active_attention", "mostly_stable", "reopen_for_closer_review"}
                    else "active_attention"
                ),
                compact_rationale_cue=_build_plan_compact_rationale_cue(plan),
                message=plan.get("message"),
            )
            for plan in plans
        ],
    )


def apply_orchestration_review_action(
    payload: OrchestrationReviewActionRequest,
    *,
    artifact_path: Path = Path(".dev_pipeline/notifications"),
) -> OrchestrationReviewActionResponse:
    status = get_orchestration_review_status(artifact_path=artifact_path, limit=200)
    target = next((plan for plan in status.plans if plan.event_id == payload.event_id), None)
    if target is None:
        raise ValueError(f"Event '{payload.event_id}' is not available in the orchestration review queue.")
    if not target.is_carry_forward_follow_up:
        raise ValueError(f"Event '{payload.event_id}' is not a carry-forward follow-up item.")
    if payload.action not in target.reviewer_available_actions:
        raise ValueError(
            f"Action '{payload.action}' is not valid for event '{payload.event_id}' in state '{target.reviewer_action_state}'."
        )

    review_actions = _load_review_state(artifact_path)
    rationale = _build_reviewer_action_rationale(target.model_dump(mode="json"), payload.action)
    decision_outcome = _build_reviewer_decision_outcome(target.model_dump(mode="json"), payload.action, rationale)
    review_actions[payload.event_id] = {
        "action": payload.action,
        "acted_at": datetime.now(timezone.utc).isoformat(),
        "rationale": rationale,
        "decision_outcome": decision_outcome["outcome"],
        "decision_summary": decision_outcome["summary"],
    }
    _save_review_state(artifact_path, review_actions)

    refreshed = get_orchestration_review_status(artifact_path=artifact_path, limit=200)
    updated = next((plan for plan in refreshed.plans if plan.event_id == payload.event_id), None)
    if updated is None:
        raise ValueError(f"Event '{payload.event_id}' disappeared after action '{payload.action}'.")
    return OrchestrationReviewActionResponse(summary=refreshed.summary, updated_plan=updated)
