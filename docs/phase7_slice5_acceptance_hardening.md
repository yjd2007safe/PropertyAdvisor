# Phase 7 Slice 5 — Evidence-driven alerts acceptance hardening

Slice 5 closes Phase 7 with a lightweight product hardening pass that makes persisted evidence-alert lifecycle state understandable in watchlist/action-hub review flows and adds regression protection for the full loop.

## What this slice adds

### 1) Lightweight lifecycle/action readability on watchlist surfaces

- Watchlist page now surfaces a compact evidence-alert lifecycle panel sourced from persisted `alert_event_summary`:
  - `new`, `changed`, `continuing` counts
  - unresolved/actionable count
  - active + total persisted counts
- The panel includes operator-friendly scan regeneration commands:
  - portfolio scan: `python -m property_advisor.alert_scan --mode auto --json`
  - scoped scan (detail selected): `python -m property_advisor.alert_scan --mode auto --suburb-slug <slug> --json`
- Watchlist table/detail alert rows now expose persisted lifecycle/action context in-place:
  - `event_change_state` (`new`, `changed`, `unchanged`)
  - `event_action_state` (`new`, `seen`, `actioned`)
  - `event_status` (`open`, `dismissed`, `archived`)
  - `event_last_changed_at` and `event_last_seen_at`

This is additive only; existing endpoint shapes remain compatible.

### 2) End-to-end acceptance/regression test for the full Phase 7 loop

- Added `tests/test_phase7_workflow_acceptance.py` to cover:
  1. evidence alert generation + persistence via scan job,
  2. repeated scan idempotency and lifecycle stability,
  3. alert-event action handling (`acknowledge`) and state update,
  4. watchlist/read-model surfacing of lifecycle/action timestamps and summary,
  5. watchlist event timeline carrying alert lifecycle/action fields.

### 3) Low-risk duplication tidy

- Consolidated repeated evidence fingerprint payload lookup logic behind a shared helper in services:
  - `_build_alert_fingerprint_payload_lookup(...)`
- Used by both:
  - watchlist context enrichment path
  - standalone scan/regeneration path

## Operator/dev checklist

### Run scan command

- Full portfolio scan:
  - `python -m property_advisor.alert_scan --mode auto --json`
- Single suburb scan:
  - `python -m property_advisor.alert_scan --mode auto --suburb-slug southport-qld-4215 --json`
- Optional filters:
  - `--severity info|watch|high`
  - `--limit N`
  - `--mode auto|mock|postgres`

### Endpoints/fields to validate quickly

- `GET /api/watchlist`
  - `summary.alert_event_summary`
  - `items[].alert_event_summary`
  - `items[].alerts[].event_change_state`
  - `items[].alerts[].event_action_state`
  - `items[].alerts[].event_last_changed_at`
  - `items[].alerts[].event_last_seen_at`
- `POST /api/watchlist/alert-events/actions`
  - verify mapped state transitions and returned `alert_event_summary`
- `GET /api/watchlist/events`
  - verify `alert_event_action_state`, `alert_event_change_state`, `alert_event_occurrence_count`

### Lifecycle/action semantics reminder

- Lifecycle:
  - `new`: first persisted occurrence for event key
  - `changed`: fingerprint delta vs prior persisted event
  - `unchanged`: fingerprint stable vs prior persisted event (continuing evidence)
- Action state:
  - `new`: created/unreviewed
  - `seen`: reviewed but not action-complete
  - `actioned`: explicit reviewer action completed
- Status:
  - `open`: active
  - `archived`: resolved
  - `dismissed`: intentionally suppressed

### Acceptance coverage

- Command scan path and JSON output are covered by `tests/test_alert_scan.py`.
- Full Phase 7 loop coverage (scan → persist → idempotent rerun → action update → watchlist/event surfacing) is covered by `tests/test_phase7_workflow_acceptance.py`.

## Non-goals and follow-ons (unchanged)

- No external email/push notification delivery.
- No scheduler/cron installation.
- No major watchlist UI redesign.
- No destructive schema migrations.
