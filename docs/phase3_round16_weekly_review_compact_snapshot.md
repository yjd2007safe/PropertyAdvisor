# Phase 3 Round 16: Weekly review compact snapshot + review-first ordering

This slice advances the next narrow Phase 3 polish step after scan-mode refinement, focused on reducing operator friction during repeated weekly follow-up decisions on the existing orchestration surface.

## Scope (this round)

1. Add a compact, at-a-glance review summary on `/orchestration` so operators can orient faster without scanning the full table first.
2. Apply a small review-first ordering improvement on currently visible events to make follow-up decisions easier.
3. Keep scope confined to existing frontend surfaces (no backend endpoint/schema changes).

## What changed

- **Compact review snapshot**: `/orchestration` status panel now includes a concise line summarizing:
  - visible event count,
  - how many of those are queued for delivery,
  - most recent visible event timestamp.
- **Review-first ordering cue**: visible orchestration rows are now consistently ordered by:
  1) human-review required first,
  2) most recent queued/created timestamp,
  3) event id tie-break.
- **No API contract changes**: all improvements are view-level polish using existing response fields.

## Out of scope

- No orchestration policy or decision-logic changes.
- No new persistence/repeated-review state tracking.
- No redesign of page layout or additional workflow surfaces.
