# Phase 8 Backlog — Alert Scan Local Operations Loop

Use this file as the phase-level execution input for auto-dev continuation.

## Phase status snapshot

- **Phase:** 8
- **Theme:** alert scan local operations loop
- **Phase doc:** `docs/phase8_overview.md`
- **Current phase state:** in progress
- **Continuation rule:** after each released slice, immediately select the next dependency-unblocked slice or record a concrete blocker.

## Slice ledger

| Slice | Title | Depends on | Status | Evidence | Next |
| --- | --- | --- | --- | --- | --- |
| Slice 1 | Alert Scan Operations Ledger and Operator Visibility | Phase 7 complete | released | PR #84, commit `3d604bd` | Slice 2 |
| Slice 2 | Alert Scan Health Thresholds and Stale-Run Warnings | Slice 1 | released | PR #85, commit `b791f4b` | Slice 3 |
| Slice 3 | Alert Scan Acknowledgement Loop | Slice 2 | released | PR #86, commit `eafdcf0` | Slice 4 |
| Slice 4 | Local Scheduled Runner Wrapper | Slice 3 | pending | _not started_ | Phase 8 closeout |

## Detailed slice states

### Slice 1 — released
- **Doc:** `docs/phase8_slice1_alert_scan_operations_ledger.md`
- **Outcome:** local run ledger, latest run visibility, regenerate command surfaced in operator views.
- **Boundary:** released/merged.

### Slice 2 — released
- **Doc:** `docs/phase8_slice2_alert_scan_health_thresholds.md`
- **Outcome:** health classification (`healthy`, `warning`, `stale`, `failed`, `no_recent_run`) with recommended rerun command.
- **Boundary:** released/merged.

### Slice 3 — released
- **Doc:** `docs/phase8_slice3_alert_scan_acknowledgement_loop.md`
- **Outcome:** local acknowledgement/defer lifecycle for unhealthy scan states with expiry and supersession semantics.
- **Boundary:** released/merged.

### Slice 4 — pending
- **Doc:** `docs/phase8_slice4_local_scheduled_runner_wrapper.md`
- **Outcome target:** lightweight local wrapper for repeatable scan operation without installing an OS scheduler.
- **Boundary target:** released/merged, then Phase 8 closeout.

## Next-slice selection rule

When this file is consulted after Slice 3 release:

1. choose **Slice 4** immediately unless a concrete blocker exists,
2. keep the implementation local-first,
3. do not introduce cron/systemd/task-scheduler installation,
4. prefer additive CLI/service/UI work and focused tests,
5. after Slice 4 release, mark Phase 8 complete if the exit criteria in `docs/phase8_overview.md` are satisfied.

## Slice 4 success criteria

- operators have a documented, lightweight local wrapper command for repeated/manual scan execution,
- wrapper can run a single cycle and an optional foreground loop with a simple interval,
- wrapper reuses the existing alert scan ledger/health workflow rather than replacing it,
- wrapper surfaces operator-readable output/status with exact underlying scan command context,
- tests protect the wrapper behavior and no external scheduler install is required.

## Phase closeout rule

Phase 8 may be marked complete after Slice 4 only when:

- the Slice 4 merge is recorded,
- no remaining Phase 8 backlog slice is pending,
- and the phase exit criteria in `docs/phase8_overview.md` are all satisfied.
