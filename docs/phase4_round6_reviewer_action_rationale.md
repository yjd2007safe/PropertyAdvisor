# Phase 4 Round 6: Reviewer action rationale and decision explainability

This round extends the reviewer action history work from Round 5 by making reviewer actions easier to interpret during repeated review.

## Goal

Turn reviewer action history from a simple latest-action trace into an explainable reviewer decision context.

## Intended slice

- Add compact rationale/explanation context for reviewer actions on carry-forward follow-up items.
- Make repeated review easier by showing not only what action happened and when, but also why it was taken.
- Preserve low-noise orchestration defaults while improving decision explainability.

## Success criteria

- carry-forward follow-up items expose compact reviewer action rationale context
- operators can quickly understand whether an item was acknowledged or closed, when it happened, and the associated rationale/explanation
- backend/service and UI stay aligned on the latest reviewer action rationale context
- tests are updated for the new behavior
- validation includes `pytest` and web build success

## Constraints

- keep the slice narrow and mergeable
- no task system or broad workflow redesign
- no ingestion/database/infra expansion unless strictly required for current review-state continuity

## Implemented slice

- Extended orchestration review plan items with latest reviewer action explainability fields:
  - `reviewer_last_action`
  - `reviewer_last_action_rationale`
- Kept reviewer action persistence in the existing `review_state.json` continuity path, now storing a compact rationale string alongside action and timestamp.
- Added compact rationale generation in reviewer action handling so acknowledge/close decisions include an operator-readable explanation tied to follow-up state and revisit reason.
- Updated orchestration review UI to show latest reviewer action, timestamp, and rationale inline in the reviewer-state column for carry-forward follow-up clarity during repeated review.
- Updated tests to validate the new explainability fields and rationale behavior while preserving low-noise queue defaults.
