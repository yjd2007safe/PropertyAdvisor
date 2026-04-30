# Phase 8 Slice 4 — Local Scheduled Runner Wrapper

Slice 4 closes Phase 8 by adding a lightweight local wrapper that makes repeated alert scan operation practical without installing an OS scheduler.

## Goal

Provide a local-first command wrapper that can:

- run a single alert scan cycle on demand,
- optionally run in a simple foreground loop with a configurable interval,
- preserve the existing alert scan ledger / health / acknowledgement behavior,
- and surface enough operator-readable status to make repeated use practical.

## Expected shape

A minimal acceptable implementation should include a wrapper CLI/module such as a dedicated runner entrypoint around `property_advisor.alert_scan`.

The wrapper should support:

- **single cycle mode**
  - one-shot local execution
- **foreground loop mode**
  - repeat execution every N minutes while the process is running
- **interval input**
  - simple flag-based configuration; no heavy config system
- **operator-readable output**
  - last run result / health summary / next scheduled local run context, as appropriate
- **exact scan command continuity**
  - preserve or surface the underlying regenerate/scan command so operators can still run the raw command directly

## Constraints

- No cron/systemd/Task Scheduler install.
- No daemon/service manager requirement.
- No external notifications.
- No heavy persistent orchestration framework.
- Keep the implementation additive and local-first.

## Suggested operator workflow

1. Run wrapper once for an immediate cycle.
2. Optionally start the wrapper in foreground loop mode for local monitoring or repeated operation.
3. Check Watchlist or Orchestration page for updated ledger, health, and acknowledgement state.
4. Stop the loop by ending the local process; no machine-level scheduler state should need cleanup.

## Success criteria

- Wrapper entrypoint exists and is documented by code/tests.
- One-shot and loop behavior are covered by focused tests.
- Existing ledger/health/acknowledgement semantics remain intact.
- Phase 8 exit criteria become satisfied after release.

## Closeout expectation

After this slice is released, Phase 8 should be marked complete unless a concrete validation blocker remains.
