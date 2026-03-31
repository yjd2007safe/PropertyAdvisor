# Phase 3 Round 10: Workflow-level acceptance and smoke coverage

This slice advances **Phase 3 task 8** with a narrow scope: expand acceptance/smoke tests around real user workflows without broad production redesign.

## Scope (this round)

1. End-to-end smoke coverage for main workflow surfaces already available:
   - suburb screening
   - property advisor
   - comparables
   - watchlist action loop
   - alerts/events
2. Assertions for user-facing workflow semantics introduced in recent rounds:
   - freshness timestamps
   - confidence/fallback semantics
   - provenance visibility
   - next-step messaging
3. Thin-data and empty-state journeys, not only happy path.

## What changed

- Added `tests/test_phase3_workflow_acceptance.py` with two workflow-level smoke journeys:
  - **Main journey smoke** validating handoff continuity from suburbs → advisor → comparables → watchlist action/update → alerts/events.
  - **Thin-data + empty-state smoke** validating baseline advisor fallback, empty comparables semantics, empty watchlist filtering, and no-alert severity filtering.
- Kept implementation strictly in tests/documentation only; no broad product code redesign.

## Coverage intent

These tests are designed to catch regressions at the workflow boundary where users move between pages/actions, while still remaining lightweight and mergeable.

## Out of scope (intentionally unchanged)

- No API contract redesign.
- No visual/layout refactor.
- No new business logic features beyond what is already available in current services.
