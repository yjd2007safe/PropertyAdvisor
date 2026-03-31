# Phase 3 Round 17: Weekly review compact follow-up summary

This slice advances the next narrow Phase 3 weekly-review polish step after compact snapshot refinement, focused on helping operators decide faster during repeated review loops on the existing orchestration surface.

## Scope (this round)

1. Add a clearer compact follow-up summary to reduce repeated table scanning.
2. Keep the change limited to existing `/orchestration` status content and current API fields.
3. Avoid backend changes, schema updates, and broad UI redesign.

## What changed

- **Compact follow-up summary line**: the orchestration status panel now includes a `Follow-up summary` sentence that prioritizes manual-review items from the currently visible scope.
- **Top-item condensation**: the summary lists up to two review-first events in a concise `event: action — reason` format.
- **Overflow cue**: when more manual-review events are present, the summary appends a `+N more manual-review events` suffix so the operator can defer deeper scanning until needed.
- **No contract changes**: implemented entirely in page-level presentation logic using existing event fields.

## Out of scope

- No changes to orchestration policy or event generation.
- No persistence/state tracking for prior review sessions.
- No new routes, controls, or workflow surfaces.
