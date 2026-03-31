# Phase 3 Round 19: Weekly review low-noise follow-up emphasis

This slice advances the next narrow Phase 3 weekly-review polish step after grouped follow-up cue refinement, focused on helping operators review faster by cutting repeated rationale text on the existing orchestration surface.

## Scope (this round)

1. Reduce repeated follow-up summary noise when many actionable rows share the same rationale.
2. Keep the change limited to existing `/orchestration` status content and current API fields.
3. Avoid backend expansion, schema changes, and broad UI redesign.

## What changed

- **Low-noise follow-up emphasis line**: replaced the previous `Follow-up summary` with `Follow-up emphasis` in the orchestration status panel.
- **De-duplicated rationale grouping**: manual-review events are now grouped by normalized strategy rationale so repeated text appears once with an `×N` count.
- **Compact overflow cue**: when more than two rationale groups are present, the line appends a concise `+N more follow-up reasons` suffix.
- **No contract changes**: this is presentation-only logic using already returned orchestration plan fields.

## Out of scope

- No orchestration policy or queue-priority logic changes.
- No persistence/state tracking across review sessions.
- No new routes, controls, or schema updates.
