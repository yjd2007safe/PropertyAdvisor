# Notification Artifacts

The shared notification runtime persists local pipeline notification artifacts under `.dev_pipeline/notifications/`.

This runtime is intentionally narrow and app-agnostic:

- notification artifacts are plain JSON files and the local filesystem is the stable source of truth
- the schema is versioned in `src/shared_notifications/artifact_schema.py`
- the writer persists before any external delivery attempt
- external delivery failures are recorded in the artifact and do not block persistence
- the consumer tracks processed `event_id` values in `.dev_pipeline/notifications/.consumer_state.json`
- the relay/replay path renders a durable local delivery log at `.dev_pipeline/notifications/delivery_log.jsonl`

`PropertyAdvisor` is an integration example via a thin adapter layer, not the owner of the shared runtime.

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
from shared_notifications.hooks import PipelineNotificationHooks

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

PropertyAdvisor exposes the shared runtime through `property_advisor.notifications` and uses it in its pipeline hooks, but the runtime is designed to stand alone.

## CLI usage

The shared runtime ships with a shell-friendly CLI entrypoint for pipeline automation.
On success it prints machine-friendly JSON with the artifact or replay summary.

Emit a notification artifact:

```bash
python -m shared_notifications.cli emit \\
  --project PropertyAdvisor \\
  --phase phase2 \\
  --round round5 \\
  --slice-id phase2-round5-notification-artifact-foundation \\
  --event-type round_started \\
  --status started \\
  --summary \"Round started\" \\
  --details-json '{\"notes\": \"hello\"}'
```

Replay pending artifacts and update the local delivery log:

```bash
python -m shared_notifications.cli replay \\
  --artifact-path .dev_pipeline/notifications
```

## Relay / replay

`NotificationRelay` replays pending notification artifacts and writes a durable local delivery log. It is idempotent by `event_id` and safe to rerun for backfills.

```python
from shared_notifications.relay import NotificationRelay

relay = NotificationRelay(artifact_path=".dev_pipeline/notifications")
delivered = relay.replay_pending()
```

Each line in `delivery_log.jsonl` is a JSON record containing `event_id`, `event_type`, `created_at`, `delivered_at`, `rendered_text`, and the rendered `payload`.
