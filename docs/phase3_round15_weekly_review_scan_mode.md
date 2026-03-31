# Phase 3 Round 15: Weekly review scan-mode default for orchestration

This slice is a narrow follow-up after repeated follow-up readability polish, focused on reducing repeated scanning friction in the existing orchestration review surface.

## Scope (this round)

1. Prioritize manual-review items by default during weekly checks.
2. Keep full-queue access available without adding backend endpoints or schema changes.
3. Add compact visibility cues so operators understand what is shown/hidden at a glance.

## What changed

- **Actionable-first default view**: `/orchestration` now defaults to an **Actionable queue** view that shows only items requiring human review.
- **Quick scope toggle**: added inline view links for `Actionable queue` and `All events` so operators can expand to full queue when needed.
- **Hidden-count cue**: when actionable mode hides auto-continue items, the page shows a concise count of hidden events.
- **Empty-state clarity by scope**: actionable-mode empty state now explicitly indicates that no manual-review events are pending and points to `All events` for broader inspection.

## Out of scope

- No backend/API/schema changes.
- No new orchestration controls or policy logic.
- No major layout redesign.
