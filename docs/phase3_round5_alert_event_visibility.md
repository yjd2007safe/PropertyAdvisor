# Phase 3 Round 5: Minimal alert/event visibility slice

This slice adds a compact, workflow-oriented event timeline so users can quickly see **what changed**, **when**, and **what to do next** without building a broad notification center.

## What changed

- Added a minimal API endpoint: `GET /api/watchlist/events?limit=`.
- Built event items with lightweight categories aligned to follow-up workflow:
  - `watchlist`
  - `alert`
  - `advisory`
  - `orchestration`
- Reused existing watchlist + orchestration service surfaces to generate actionable events.
- Added a compact timeline panel on the watchlist page showing recent events with direct follow-up links.

## Repeated-use loop now supported

`watchlist review -> inspect recent change timeline -> jump to follow-up surface (advisor/watchlist detail/orchestration)`

## Scope guardrails

- No generalized notification center redesign.
- No heavy persistence redesign for event storage.
- Event feed remains a minimal derived visibility layer over existing runtime/watchlist/orchestration data.
