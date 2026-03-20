# Notification Artifacts

`PropertyAdvisor` now persists local pipeline notification artifacts under `.dev_pipeline/notifications/`.

This slice is intentionally narrow:

- notification artifacts are plain JSON files and the local filesystem is the stable source of truth
- the schema is versioned in `src/property_advisor/notifications/artifact_schema.py`
- the writer persists before any external delivery attempt
- external delivery failures are recorded in the artifact and do not block persistence
- the consumer tracks processed `event_id` values in `.dev_pipeline/notifications/.consumer_state.json`

## Artifact contract

Each artifact includes:

- `schema_version`
- `event_id`
- `event_type`
- `project`
- `phase`
- `round`
- `slice_id`
- `status`
- `summary`
- `details`
- `artifacts`
- `origin`
- `delivery_targets`
- `delivery`
- `created_at`

Supported `event_type` values in this round:

- `round_started`
- `ready_for_evaluation`
- `evaluated`
- `evaluation_failed`
- `delivered`
- `completed`
- `blocked`
- `interrupted`

`origin` preserves relay/session metadata when available:

- `channel`
- `chat_id`
- `thread_id`
- `session_key`
- `user_id`
- `reply_mode`

`delivery_targets` is reserved for future relay routing, including Telegram and session-based delivery.

## Minimal usage

```python
from property_advisor.pipeline.notification_hooks import PipelineNotificationHooks

hooks = PipelineNotificationHooks(
    project="PropertyAdvisor",
    phase="phase2",
    round="round5",
    slice_id="phase2-round5-notification-artifact-foundation",
    origin={"channel": "telegram", "chat_id": "123"},
    delivery_targets=[{"channel": "telegram", "chat_id": "123"}],
)

hooks.round_started(summary="Round started")
hooks.ready_for_evaluation(summary="Ready for evaluation")
hooks.completed(summary="Round completed")
```

For existing local Southport pipeline entry points, `run_southport_refresh()` now emits `round_started`, `blocked`, `completed`, and `interrupted` artifacts, while `verify_southport_demo_slice()` emits `ready_for_evaluation`, `evaluated`, and `evaluation_failed`.
