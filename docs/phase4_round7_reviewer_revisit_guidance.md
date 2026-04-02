# Phase 4 Round 7: Reviewer revisit guidance and decision support

This round extends the reviewer action rationale work from Round 6 by helping repeated review answer the next practical question: what should the reviewer focus on now?

## Goal

Turn reviewer decision context into compact revisit guidance so repeated review is faster and more actionable.

## Intended slice

- Add concise revisit guidance / next-review cues for carry-forward follow-up items.
- Help reviewers quickly understand whether an item still needs active attention, is mostly stable, or should be re-opened for closer review.
- Preserve low-noise orchestration defaults while improving repeated-review decision support.

## Success criteria

- carry-forward follow-up items expose compact revisit guidance / next-review cues
- operators can more quickly judge whether an item still needs active follow-up or is effectively stable
- backend/service and UI stay aligned on revisit guidance context
- tests are updated for the new behavior
- validation includes `pytest` and web build success

## Constraints

- keep the slice narrow and mergeable
- no scoring engine, task system, or broad workflow redesign
- no ingestion/database/infra expansion unless strictly required for current review-state continuity

## Implemented slice

- Extended orchestration review plan items with compact revisit decision-support context:
  - `decision_support_state` (`active_attention`, `mostly_stable`, `reopen_for_closer_review`)
  - `next_review_cue` (short operator cue)
  - `revisit_guidance` (compact explanation tied to current follow-up rationale)
- Added service-side guidance classification to keep API and UI consistent without introducing new workflow systems.
- Included summary-level low-noise revisit guidance rollup in `summary.next_action`.
- Updated orchestration UI to surface:
  - queue-level decision-support counts
  - per-item decision state, cue, and compact guidance
- Added/updated tests for service behavior and API shape to validate the new guidance fields.
