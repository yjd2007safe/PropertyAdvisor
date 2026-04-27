# Phase 7 Slice 2: Evidence Change Detection + Alert Lifecycle Semantics

## Scope delivered
Slice 2 upgrades persisted watchlist evidence alerts from simple repeat snapshots into lifecycle-aware event records that can distinguish:
- **new evidence**
- **unchanged recurring evidence**
- **meaningfully changed evidence**

This implementation stays additive and compatible with existing endpoints.

## What changed

### 1) Deterministic evidence fingerprints
Each generated watchlist evidence alert now includes a deterministic fingerprint derived from:
- alert identity (`suburb_slug`, `metric`, `severity`, `title`)
- advisory evidence (`recommendation`, `confidence`, `fallback_state`, `freshness`)
- comparable evidence (`sample_size`, `sample_state`, `price_position`)
- market evidence (`demand_signal`, `supply_signal`)

The fingerprint is persisted in event payload context and remains stable across identical runs.

### 2) Additive alert lifecycle fields
`alert_events` now carries additive lifecycle fields:
- `change_state` (`new | unchanged | changed`)
- `last_changed_at`
- `last_seen_at`

These are populated in both mock and postgres repositories.

### 3) Upsert semantics for actionable change lifecycle
On repeated upsert for the same `event_key`:
- same fingerprint -> `change_state=unchanged`, `occurrence_count` increments, `last_seen_at` refreshes
- different fingerprint -> `change_state=changed`, `occurrence_count` increments, `last_changed_at` updates

This suppresses noisy duplicate alerts while preserving signal when evidence actually shifts.

### 4) Service-level change comparison helpers
Service logic now computes current fingerprint payloads and compares against the last persisted payload before upsert.
The comparison is used to:
- set lifecycle semantics in persisted records
- attach read-time context (`event_change_state`, `event_change_summary`)
- render alert detail prefixes distinguishing `New/Changed/Stable evidence alert`

### 5) Watchlist response lifecycle context
Watchlist alert models now expose additional optional lifecycle metadata:
- `event_action_state`
- `event_change_state`
- `event_last_changed_at`
- `event_last_seen_at`
- `event_change_summary`

`latest_context.advisory` also includes a compact evidence lifecycle summary (`new`, `changed`, `continuing`).

## Compatibility
- Additive schema only (no destructive migration).
- Existing endpoints remain shape-compatible.
- Mock and postgres/fallback modes continue to work.

## Follow-on slices enabled
- Slice 3 scan/regeneration jobs can now reason over `change_state` + timestamps.
- Later action-hub slices can bind reviewer actions to lifecycle-aware alert event history.
