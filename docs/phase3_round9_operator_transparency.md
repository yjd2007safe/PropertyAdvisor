# Phase 3 Round 9: Operator transparency and thin-data controls

This slice follows the watchlist action loop and keeps scope narrow: page-level transparency/provenance/freshness and low-noise operator indicators, without broad shell redesign.

## What changed

- Added a reusable **Transparency panel** on workflow pages (suburbs, advisor, comparables, watchlist) to surface:
  - latest refresh timestamp
  - snapshot generated timestamp
  - snapshot count where meaningful
  - thin-data/fallback warning when metadata indicates non-live data or insufficient evidence
  - low-confidence warning where already represented in existing response metadata
- Extended backend/API response envelopes so advisor/comparables include `generated_at`, aligning page-level freshness signals with other workflow surfaces.
- Preserved existing data semantics:
  - no change to mock/postgres/fallback decision logic
  - no change to watchlist action loop behavior
  - no broad visual overhaul

## Why this round

Operators need fast trust checks before acting:

- **What mode/source am I seeing?** (provenance)
- **How fresh is this snapshot?** (timestamp)
- **How much evidence is behind this?** (snapshot/sample counts)
- **Should I treat this as directional only?** (thin-data/low-confidence signals)

This round surfaces those checks at the page level while reusing existing metadata contracts.

## Out of scope (intentionally unchanged)

- No new admin shell or separate operator UI.
- No redesign of page layout system/styles beyond inserting existing panel patterns.
- No change to core advisory/comparable/watchlist business logic.
