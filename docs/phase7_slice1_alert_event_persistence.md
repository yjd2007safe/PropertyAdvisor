# Phase 7 Slice 1: Alert Event Persistence

## Why this slice exists
Phase 6 Round 7 introduced deterministic evidence-driven watchlist alerts at service time. That improved alert quality, but alert state was still ephemeral: every refresh rebuilt alerts without persisted lifecycle history.

Slice 1 adds a minimal persisted alert-event model so evidence alerts can be tracked over time and safely reused by later Phase 7 slices (change detection, scan jobs, action hub lifecycle).

## What was added

### 1) Additive schema support (`alert_events`)
`db/schema_v1.sql` now includes an additive `alert_events` table with:
- deterministic dedupe key (`event_key`, unique)
- optional references (`alert_rule_id`, `suburb_id`, `property_id`)
- watchlist-friendly scope key (`suburb_slug`)
- alert payload columns (`severity`, `metric`, `title`, `detail`, `observed_at`)
- lifecycle fields (`status`, `action_state`, `occurrence_count`)
- JSON context (`payload`)
- standard timestamps (`created_at`, `updated_at`)

Indexes cover suburb lookup, status+recency review, and metric filtering.

### 2) Repository support (mock + postgres)
New repository abstraction and implementations:
- `AlertEventRepository` protocol
- `MockAlertEventRepository` with in-memory idempotent upsert behavior keyed by `event_key`
- `PostgresAlertEventRepository` with `INSERT ... ON CONFLICT (event_key) DO UPDATE` semantics

Postgres behavior is deliberately tolerant:
- if DB URL is absent -> fallback to mock in-memory behavior
- if table/query is unavailable (e.g., schema not applied yet) -> fallback to mock behavior and mark fallback metadata

### 3) Deterministic event keys for evidence alerts
Evidence-driven watchlist alerts now derive a stable event key using:
- suburb slug
- metric
- severity
- title

This avoids unbounded duplicates when enrichment runs repeatedly.

### 4) Safe write path + read-path context
Normal read endpoints remain read-oriented by default.

A new explicit service function was added:
- `persist_watchlist_alert_events(suburb_slug: Optional[str]) -> int`

This allows controlled persistence runs (manual/explicit) without making every read request write-heavy.

Read-time enrichment now attempts to read matching persisted event rows and attaches optional context to watchlist alerts:
- `event_key`
- `event_status`
- `event_occurrence_count`
- `event_last_observed_at`

This keeps response compatibility while exposing history hooks for later slices.

## How this sets up later Phase 7 slices
- **Slice 2 (change detection/lifecycle):** stable keyed events + status/action fields support compare/dismiss/archive flows.
- **Slice 3 (scan jobs):** explicit persistence function can be called by scheduled scan entrypoints.
- **Slice 4+ (action hub integration):** event metadata can anchor operator actions against persistent IDs/keys.

## Compatibility notes
- Additive-only schema; no destructive migration.
- Existing watchlist/watchlist-alert/watchlist-event responses remain valid.
- Mock mode continues to function without database setup.
