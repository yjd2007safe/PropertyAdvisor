# Phase 3 Round 18: Weekly review grouped follow-up cue

This slice advances the next narrow Phase 3 weekly-review polish step after follow-up summary refinement, focused on reducing repeated reading burden on the existing orchestration review surface.

## Scope (this round)

1. Add one lightweight grouped follow-up cue so operators can spot repeated action clusters faster.
2. Keep all changes on existing `/orchestration` status content using current event fields.
3. Avoid backend logic expansion, schema changes, and broad UI redesign.

## What changed

- **Grouped follow-up cue line**: the orchestration status panel now includes a `Grouped follow-up cue` line that groups visible manual-review events by action.
- **Compact cluster labels**: each group uses concise `action ×count (event types)` formatting to reduce repeated row-by-row reading.
- **Review-first ordering inside groups**: groups are prioritized by largest count first, then by most recent event timestamp.
- **Overflow cue for breadth**: if more than three groups exist, the cue appends a `+N more groups` suffix.
- **No API contract changes**: this is presentation-only logic built from already returned event fields.

## Out of scope

- No orchestration policy updates.
- No state tracking for prior review sessions.
- No additional routes or controls.
