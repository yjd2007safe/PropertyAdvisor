# Phase 4 Round 1: Decision-to-follow-up loop foundation

This round is a narrow, mergeable slice focused on carrying operator review outcomes forward more clearly across existing orchestration/watchlist/advisor flows.

## Goals

1. Clarify follow-up state semantics after review (`follow_up_state`).
2. Make next-step outcomes explicit (`next_step_outcome`) so operators know what result to produce.
3. Improve revisit visibility (`revisit_reason`) so delayed checks stay explainable.

## Implemented changes

- Extended orchestration plan items with three lightweight fields:
  - `follow_up_state`
  - `next_step_outcome`
  - `revisit_reason`
- Added event-type outcome framing in the existing orchestration service policy layer.
- Tightened summary `next_action` messaging so it frames outcomes, not only queue status.
- Updated `/orchestration` page to surface:
  - a top-line “Next-step outcome framing” cue,
  - per-row outcome + revisit rationale columns,
  - follow-up state visibility in the action cell.
- Reused current surfaces/contracts without introducing a task system or broad redesign.

## Non-goals

- No new persistence layer or task engine.
- No major orchestration schema redesign.
- No policy expansion beyond existing event types.

## Validation

- Service tests updated to assert the new follow-up semantics.
- API smoke tests updated to verify response shape carries new fields.
