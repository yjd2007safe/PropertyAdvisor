# Phase 8 Slice 1 — Alert Scan Operations Ledger and Operator Visibility

## What this slice adds
- Durable local run ledger for `property_advisor.alert_scan` executions.
- Automatic ledger append on successful scan runs (default behavior).
- Operator-visible latest run + recent history surface via API responses used by Watchlist and Orchestration pages.
- Compact UI panel showing latest status, counts, timestamp, and exact regenerate command.

## Ledger artifact semantics
- Default path: `.refresh/alert_scan_runs.json`
- Append-only `runs` list with:
  - `run_id`, `timestamp`, `mode`
  - `filters` (`suburb_slug`, `severity`, `limit`)
  - `status`, `error`
  - `persistence_attempted`
  - `counts` (`entries_scanned`, `alerts_scanned`, `persisted`, `new`, `changed`, `unchanged`)
  - `regenerate_command`

## Operator workflow
1. Run scan:
   - `python -m property_advisor.alert_scan --mode auto --json`
2. Verify output (unchanged JSON contract).
3. Open Watchlist or Orchestration page to confirm latest run status and counts.
4. Re-run using shown regenerate command.

## CLI options
- `--no-ledger`: skip writing the run ledger.
- `--ledger-path <path>`: override ledger location.

## Non-goals preserved
- No cron/scheduler installation.
- No email/push/external delivery.
- No destructive schema migration.

## Follow-on Phase 8 slices
- Slice 2: alert scan health thresholds and stale-run warnings.
- Slice 3: local operator acknowledgements for scan failures and drift.
- Slice 4: optional scheduled runner wrapper (still local, no OS scheduler installation).
