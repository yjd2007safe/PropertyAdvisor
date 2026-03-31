# Phase 3 Round 13: Weekly review default and follow-up cue coherence

This slice applies a narrow polish pass after repeated-review friction cleanup, focused on small, visible consistency wins without redesign.

## Scope (this round)

1. Make repeated weekly review defaults more coherent on existing surfaces.
2. Clarify follow-up cues where operators repeatedly revisit comparables/watchlist.
3. Keep changes local to existing page behavior and helper copy only.

## What changed

- Comparables now applies an intent-aware default sort:
  - defaults to **most recent sale** for weekly/review/triage intent handoffs
  - keeps **best match score** as the standard default otherwise
- Comparables “Quick weekly filters” now prioritize **Weekly refresh** first and explicitly show the active default sort cue when no sort is provided.
- Watchlist now defaults grouping to **strategy** when no grouping is specified, and saved review views prioritize **Active weekly queue** before escalation views.
- Watchlist adds a compact weekly default hint when no explicit filters are set.

## Out of scope

- No backend/API contract changes.
- No schema/model changes.
- No broad layout or navigation redesign.
