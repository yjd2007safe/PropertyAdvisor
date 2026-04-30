# Phase 8 Slice 3 — Alert Scan Acknowledgement Loop

Slice 3 closes the local operator acknowledgement gap for unhealthy alert scan states.

## What this slice adds

### 1) Durable local acknowledgement record

- Stores acknowledgement state in a local artifact adjacent to the alert scan ledger.
- Records:
  - `acknowledged_by`
  - `reason`
  - `acknowledged_at`
  - `deferred_until` (optional)
  - `expires_at` (optional)
  - `acknowledged_for_run_id` (when available)

### 2) Acknowledgement lifecycle semantics

Acknowledgement state remains local-first and should support these operator-readable outcomes:

- `active`: acknowledgement currently applies to the latest unhealthy state.
- `expired`: acknowledgement timed out.
- `superseded`: a newer scan run invalidated the prior acknowledgement context.
- `none`: no acknowledgement recorded.

### 3) API and operator-surface visibility

- Watchlist and orchestration-facing API payloads include current acknowledgement state when relevant.
- Operators can see:
  - current health problem,
  - acknowledgement status,
  - who acknowledged,
  - why it was deferred,
  - when the acknowledgement should be revisited.

### 4) Local action path

- Adds a local API action to acknowledge/defer unhealthy scan states.
- Healthy scan states should not require acknowledgement.

## Operator workflow

1. Open Watchlist or Orchestration page.
2. Inspect alert scan health state.
3. If the state is `failed`, `stale`, `warning`, or drift-related, acknowledge locally with a reason and optional defer/expiry.
4. Revisit when expiry is reached or a newer run supersedes the acknowledgement.

## Verification expectations

- Regression coverage for:
  - acknowledgement creation,
  - expiry behavior,
  - superseded behavior after a new run,
  - API/read-model surfacing.

## Non-goals preserved

- No external notifications.
- No auth system.
- No scheduler install.
- No destructive schema migration.

## Follow-on

Slice 4 should build on this by making repeated local operation easier through a lightweight scheduled-runner wrapper, while preserving all ledger/health/acknowledgement semantics already delivered.
