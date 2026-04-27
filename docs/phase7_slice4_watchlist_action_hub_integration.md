# Phase 7 Slice 4: Watchlist / Action Hub lifecycle-aware alert event integration

## What this slice delivers

Slice 4 makes persisted `alert_events` a first-class part of watchlist/action-hub workflow behavior.

Previously, watchlist surfaces could show evidence-driven alerts with persisted metadata, but lifecycle/action state was still mostly a display aid. This slice promotes that state into explicit review context and action APIs.

## Delivered capabilities

### 1) Additive lifecycle/action context on watchlist reads

- `WatchlistEntry` and `latest_context` now include an additive `alert_event_summary` object with:
  - total
  - active (`status=open`)
  - unresolved (`status=open` + non-actioned)
  - status buckets (`open`, `dismissed`, `archived`)
  - lifecycle buckets (`new`, `changed`, `unchanged`)
- `WatchlistSummary` includes aggregate `alert_event_summary` across returned entries.
- `latest_context.advisory` now carries compact active/unresolved event cues to make repeated-review urgency obvious.

All additions are backward-compatible and preserve existing fields.

### 2) Alert event action endpoint for handling state transitions

Added:

- `POST /api/watchlist/alert-events/actions`

Request:

- `event_key`
- `action` in:
  - `review` → `status=open`, `action_state=seen`
  - `acknowledge` → `status=open`, `action_state=actioned`
  - `resolve` → `status=archived`, `action_state=actioned`
  - `dismiss` → `status=dismissed`, `action_state=actioned`
  - `reopen` → `status=open`, `action_state=seen`

Response includes:

- updated event snapshot (`WatchlistAlert` shape)
- `suburb_slug`
- refreshed suburb-level `alert_event_summary`

Deterministic update behavior is implemented in both mock and postgres repositories via `update_event_state(...)`.

### 3) Watchlist events/action-hub read-model linkage

- Alert category rows in `/api/watchlist/events` now include additive persisted fields:
  - `alert_event_status`
  - `alert_event_action_state`
  - `alert_event_change_state`
  - `alert_event_occurrence_count`
- Alert event detail text now explicitly includes lifecycle state (`new`/`changed`/`unchanged`) so reviewers can see *why* an item needs attention.

## Compatibility notes

- Existing watchlist/watchlist-detail/watchlist-events consumers remain valid.
- All response changes are additive.
- No schema-destructive migration introduced.

## Tests added/updated

- Repository tests:
  - mock alert-event state update transitions
  - postgres alert-event state update mapping
- Service tests:
  - watchlist alert-event action application + summary update
  - watchlist response lifecycle/action summary presence
- API smoke:
  - watchlist summary additive `alert_event_summary`
  - alert-event action route behavior

## Follow-on UI implications (minimal)

- Action hub can now expose per-alert buttons (`review`, `acknowledge`, `dismiss`, `resolve`, `reopen`) directly against `event_key`.
- Watchlist rows can prioritize by:
  - unresolved open events
  - changed lifecycle count
- Event timeline badges can be rendered from persisted lifecycle/action fields without extra derivation.

