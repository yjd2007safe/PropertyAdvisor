# Phase 6 Round 4: Review session packet summary

This round closes the Phase 6 execution-loop work by adding a compact, shared review-session packet summary across orchestration review and watchlist surfaces.

## What changed

- Added a **shared session packet framing** model with explicit counts for:
  - `do_now`
  - `batch_later`
  - `recently_closed`
- Added **consistent summary language** on both review surfaces:
  - `Review-session packets: do-now ×N · batch-later ×N · recently-closed ×N.`
  - A low-volume/empty-state companion note that keeps packet framing coherent when queues are small.
- Updated **orchestration review summary payload** with:
  - `review_session_packet_cue`
  - `review_session_packet_low_volume_note`
  - `review_session_packet_breakdown`
- Updated **watchlist summary payload** with the same fields and wording contract.
- Updated watchlist and orchestration UI copy so packet framing remains explicit in regular, low-volume, and empty states.

## Why this is narrow and safe

- No homepage/dashboard expansion.
- No broad navigation rewrite.
- No schema persistence redesign.
- Changes are additive to existing API response contracts and rely on already-available review-state signals.

## Validation

- Extended service and acceptance tests to cover packet-summary fields and empty-state packet behavior.
- Ran backend tests and web build to confirm round-level regression safety.
