# Phase 3 Round 4: Watchlist action hub (minimal loop)

This slice makes watchlist usable as a repeated decision checkpoint instead of a read-only status surface.

## What changed

- Added a minimal action endpoint (`POST /api/watchlist/actions`) so major workflow surfaces can save/update a suburb into watchlist triage.
- Added workflow link affordance from advisor/comparables/watchlist contexts to this watchlist save action.
- Enriched watchlist entries/detail with latest context snippets:
  - advisory summary (recommendation/confidence/headline),
  - comparable snapshot summary (count/avg/sample state),
  - orchestration review summary (state + review queue count).

## Loop now supported

`inspect (advisor/comparables) -> decide -> save -> review (watchlist with latest context)`

## Scope guardrails

- No broad watchlist redesign.
- No heavy persistence rewrite; behavior remains compatible with mock/postgres fallback repository shell.
