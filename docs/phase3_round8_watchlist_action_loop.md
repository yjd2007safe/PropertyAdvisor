# Phase 3 Round 8: Watchlist action loop (weekly operations)

This slice keeps scope tight: it upgrades watchlist action loops so repeated weekly review is practical without redesigning alerts or the product shell.

## What changed

- Extended watchlist status operations to include `archived` for completed/parked outcomes.
- Added server-side watchlist action bridge (`POST /watchlist/actions` in web app) that reuses existing API `POST /api/watchlist/actions` and supports status/strategy/notes updates.
- Added “save/update watchlist” entry points from major pages with logical context:
  - advisor
  - comparables
  - suburbs dashboard
  - watchlist table/detail
- Upgraded watchlist detail into an action hub:
  - latest advisory/comparables/orchestration context rendered inline
  - status/strategy/notes update form for direct weekly triage
- Improved thin-data honesty in watchlist context summaries:
  - advisory includes explicit fallback indicator when thin evidence is active
  - comparables context calls out directional-only semantics for low/empty samples

## Out of scope (intentionally unchanged)

- No alerts engine expansion.
- No broad page/shell redesign.
- No new standalone watchlist domain model beyond minimal status extension.
