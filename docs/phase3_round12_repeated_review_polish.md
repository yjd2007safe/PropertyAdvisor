# Phase 3 Round 12: Repeated-review friction polish

This slice advances **Phase 3 task 7** immediately after weekly-use workflow refinement, with a narrow scope focused on reducing repeated operator scanning friction.

## Scope (this round)

1. Remove repeated/inconsistent next-step phrasing across advisor, comparables, and watchlist detail handoffs.
2. Tighten thin-data and empty-state wording so warnings are shorter and easier to action during weekly review.
3. Add one small local scanning affordance on an existing surface (comparables sort order) without backend or schema changes.
4. Keep changes mergeable and local; avoid redesign and business-logic churn.

## What changed

- Added shared `workflowNextStepCopy` helper for consistent “Next step” phrasing across workflow surfaces.
- Added local comparables sorting options (`best match`, `most recent sale`, `closest distance`, `highest price`, `lowest price`) and carried sort defaults into quick weekly filter links.
- Shortened thin-data and empty-sample wording in comparables/watchlist transparency messaging and comparables empty state.

## Out of scope

- No API or schema updates.
- No new data pipelines, recommendation changes, or alerting redesign.
- No UI shell/navigation overhaul.
