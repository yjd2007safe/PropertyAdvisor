# Phase 8 — Alert Scan Local Operations Loop

## Goal

Close the local-first operator loop around `property_advisor.alert_scan` so scan execution is:

- observable,
- health-classified,
- locally acknowledgeable when degraded,
- and runnable through a lightweight local wrapper without requiring OS scheduler installation.

Phase 8 is about making repeated scan operation practical for a human operator using the app and local CLI tools.

## Why this phase exists

By the end of Phase 7, alert generation and watchlist/action-hub integration existed, but the operational loop still had gaps:

- operators could not easily inspect recent scan history,
- stale/failed/suspicious runs were not classified consistently,
- degraded states had no local acknowledgement trail,
- and there was no lightweight local wrapper for repeated/manual operation short of invoking the raw scan command each time.

Phase 8 closes those gaps while keeping the solution local-first.

## In-scope outcomes

1. Durable alert scan run ledger and operator-visible recent history.
2. Alert scan health classification with exact rerun guidance.
3. Local acknowledgement/defer loop for unhealthy scan states.
4. Lightweight local scheduled-runner wrapper for repeatable scan operation without installing cron/system services.
5. Regression coverage protecting the end-to-end operator loop.

## Non-goals

- No cron/systemd/Windows Task Scheduler installation.
- No email/push/external notification delivery.
- No auth/identity system beyond simple operator-provided acknowledgement fields.
- No destructive schema migration.
- No major watchlist redesign.

## Exit criteria

Phase 8 is complete when:

- operators can see recent scan run history and latest status,
- unhealthy scan states are classified with reasons and exact rerun command,
- unhealthy states can be locally acknowledged/deferred with expiry/supersession semantics,
- a local wrapper exists to run scan cycles on-demand or in a lightweight local loop,
- and tests cover the main operator lifecycle with minimal ambiguity.

## Delivery shape

Phase 8 is executed as a sequence of narrow, releasable slices. Each slice should be independently testable and mergeable, but Phase 8 is not considered complete until the backlog status reaches the terminal slice and the phase exit criteria are satisfied.
