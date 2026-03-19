# Phase 1 Real-Data Readiness (Southport slice)

Updated: 2026-03-19

This note explains what the current Southport Phase 1 slice already supports with persisted Postgres-backed evidence, and which product surfaces are still partially demo/fallback driven.

## What is already real-data backed

The current Southport slice has a code-driven path for:

- canonical suburb/property/listing upsert
- listing snapshot history persistence
- sold / leased event persistence when provided by source payloads
- repeatable refresh orchestration via `refresh-southport`
- demo-slice backfill + verification via `backfill-verify-southport`
- first-pass market metrics generation for the frozen slice
- row-count verification across canonical Phase 1 tables

Primary evidence paths:

- `python -m property_advisor.ingest refresh-southport ...`
- `python -m property_advisor.ingest backfill-verify-southport ...`
- `python -m property_advisor.ingest verify-southport-demo ...`

Generated artifacts:

- `.refresh/runs/southport_refresh_runs.json`
- `.refresh/runs/southport_demo_verification.json`

## What has been proven so far

Round 6 established the minimum demo-grade proof that:

- the Southport slice can be populated through code instead of manual SQL edits
- the refresh path is designed for safe reruns with lock protection
- canonical row counts can be collected for the frozen slice
- automated local evaluation has passed for the implemented phase-1 work

This is enough to treat Southport as the current Phase 1 proof slice.

## What is not yet fully production-ready

The current implementation should still be treated as **Phase 1 proof / operator-guided readiness**, not a broad unattended production rollout.

Known remaining gaps:

1. **Input realism and coverage**
   - the documented sample payload is intentionally small and operator-supplied
   - completeness and source breadth are still limited

2. **Operational transparency**
   - refresh and verification artifacts exist, but the repo still needs clearer operator-facing guidance on how to interpret them quickly

3. **Surface-by-surface product cutover**
   - some product surfaces can read Postgres-backed rows, but not every experience is guaranteed to be fully real-data-native end to end
   - fallback/mock-safe behavior still exists by design while the app remains in mixed maturity

4. **Breadth beyond the frozen slice**
   - Southport is currently the only frozen proof slice
   - broader market rollout requires additional slice expansion decisions and data-quality validation

## Current interpretation by surface

### Safe to describe as real-data-supported for the Southport proof slice

- ingest / refresh / verification command path
- canonical row persistence and row-count evidence
- first-pass market-metrics generation for the slice
- postgres-mode regression evidence for the implemented Phase 1 tasks

### Should still be described cautiously

- full advisory quality and recommendation depth
- comparable quality beyond first-pass persisted evidence
- broad market completeness outside the frozen slice
- unattended production-grade operations without operator review

## Why this note exists

Round 7 was reset because the next useful step is not more plumbing by default. The repo needs a clear line between:

- **what has already been proven**
- **what is still demo-grade**
- **what must be hardened before broader rollout**

That distinction is required before expanding to more slices or moving deeper into advisory/product work.
