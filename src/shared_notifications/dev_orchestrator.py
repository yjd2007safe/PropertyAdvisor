from __future__ import annotations

from typing import Any, Mapping

DEV_EVENT_POLICY: dict[str, dict[str, Any]] = {
    "ready_for_evaluation": {
        "priority": 100,
        "action": "notify_and_pause_for_review",
        "auto_continue": False,
        "requires_human_review": True,
        "bucket": "review",
    },
    "evaluation_failed": {
        "priority": 90,
        "action": "notify_and_resume_fix",
        "auto_continue": True,
        "requires_human_review": False,
        "bucket": "recovery",
    },
    "blocked": {
        "priority": 80,
        "action": "notify_and_wait_on_blocker",
        "auto_continue": False,
        "requires_human_review": False,
        "bucket": "blocked",
    },
    "interrupted": {
        "priority": 70,
        "action": "notify_and_resume",
        "auto_continue": True,
        "requires_human_review": False,
        "bucket": "recovery",
    },
    "completed": {
        "priority": 60,
        "action": "notify_progress_and_continue",
        "auto_continue": True,
        "requires_human_review": False,
        "bucket": "progress",
    },
    "evaluated": {
        "priority": 50,
        "action": "notify_progress_and_continue",
        "auto_continue": True,
        "requires_human_review": False,
        "bucket": "progress",
    },
    "delivered": {
        "priority": 40,
        "action": "notify_closure",
        "auto_continue": False,
        "requires_human_review": False,
        "bucket": "closure",
    },
}

DEFAULT_POLICY = {
    "priority": 10,
    "action": "notify_only",
    "auto_continue": False,
    "requires_human_review": False,
    "bucket": "other",
}


def _record_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    policy = DEV_EVENT_POLICY.get(str(record.get("event_type") or ""), DEFAULT_POLICY)
    queued_at = record.get("queued_at") or ""
    created_at = record.get("created_at") or ""
    event_id = record.get("event_id") or ""
    return (-int(policy["priority"]), queued_at, created_at, event_id)


def build_dev_orchestration_plan(record: Mapping[str, Any]) -> dict[str, Any]:
    event_type = str(record.get("event_type") or "")
    policy = dict(DEFAULT_POLICY)
    policy.update(DEV_EVENT_POLICY.get(event_type, {}))

    summary = {
        "notify_and_pause_for_review": "通知关键进展，并暂停等待人工复核。",
        "notify_and_resume_fix": "通知失败原因，并自动继续修复链路。",
        "notify_and_wait_on_blocker": "通知阻塞点，等待外部条件解除。",
        "notify_and_resume": "通知中断原因，并尝试自动恢复执行。",
        "notify_progress_and_continue": "反馈阶段性进展，并在已授权前提下继续推进下一步。",
        "notify_closure": "通知该轮结果已正式交付闭环。",
        "notify_only": "仅通知，不自动推进。",
    }[str(policy["action"])]

    return {
        "event_id": record.get("event_id"),
        "event_type": event_type,
        "queued_at": record.get("queued_at"),
        "created_at": record.get("created_at"),
        "session_key": record.get("session_key"),
        "message": record.get("message"),
        "priority": policy["priority"],
        "bucket": policy["bucket"],
        "action": policy["action"],
        "auto_continue": policy["auto_continue"],
        "requires_human_review": policy["requires_human_review"],
        "strategy_summary": summary,
        "ack": dict(record.get("ack") or {}),
    }


def build_dev_orchestration_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plans = [build_dev_orchestration_plan(record) for record in records]
    plans.sort(key=_record_sort_key)
    return plans
