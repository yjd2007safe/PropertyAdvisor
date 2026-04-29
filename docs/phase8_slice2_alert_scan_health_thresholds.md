# Phase8 Slice2: Alert Scan Health Thresholds and Stale-Run Warnings

## Health semantics

Slice2 adds health classification over the Slice1 alert scan run ledger.

Statuses:
- `healthy`: latest run exists, succeeded, is within threshold, and has expected non-zero scan/persist activity.
- `no_recent_run`: no local ledger run exists.
- `failed`: latest run failed.
- `stale`: latest successful/failed run is older than the staleness threshold.
- `warning`: latest run succeeded but looks suspicious (for example zero entries/persisted output or fallback/degraded mode).

Health payload includes:
- latest run summary
- reasons
- recommended exact regenerate command
- age in minutes and stale threshold minutes

## Threshold defaults

- Default stale threshold: `180` minutes.
- Implemented as a simple service constant with optional function parameter support (no heavy config system).
- Safe for local/manual operation where operators run scans ad hoc.

## Operator workflow

1. Open Watchlist or Orchestration page.
2. Check alert scan health card.
3. If status is `stale`, `failed`, `warning`, or `no_recent_run`, run the exact command shown in `recommended_command`.
4. Re-open page and verify `healthy`.

## Path to Slice3

Slice3 can build local operator acknowledgement on top of this by recording:
- who acknowledged warning/failure states,
- why deferred,
- and when acknowledgement expires.

This keeps the loop evidence-driven while remaining local-first (no external scheduler/email/push in this slice).
