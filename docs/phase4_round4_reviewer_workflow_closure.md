# Phase 4 Round 4: Reviewer-operable carry-forward workflow closure

This round closes the Phase 4 carry-forward follow-up loop by making carry-forward items explicitly operable in orchestration review, while preserving low-noise weekly review defaults.

## Goal

Turn carry-forward follow-up from passive summary-only context into explicit reviewer actions with visible state progression.

## Implemented slice

- Added reviewer-operable action flow for orchestration carry-forward items:
  - `acknowledge`
  - `close_follow_up`
- Added carry-forward closure state fields to orchestration plan items:
  - `is_carry_forward_follow_up`
  - `reviewer_action_state` (`pending`, `acknowledged`, `closed`)
  - `reviewer_available_actions`
  - `reviewer_last_action_at`
- Added backend API contract and service behavior to apply reviewer actions:
  - `POST /api/orchestration/review/actions`
  - action validation against current state
  - persisted review action state in notification artifact workspace (`review_state.json`)
- Updated orchestration UI queue table to show:
  - explicit carry-forward marking
  - reviewer action state column
  - workflow closure action buttons for valid transitions
- Kept weekly review low-noise behavior:
  - actionable view remains the default
  - summary grouping ignores closed manual carry-forward items

## Why this is narrow

- No ingestion changes.
- No database or infra changes.
- No redesign outside orchestration review closure controls.
- Uses existing orchestration review surface and extends current contracts coherently.

## Validation

- Added/updated tests for orchestration service and API response shape.
- Validation run includes:
  - `pytest`
  - web build (`npm run build` in `web/`)
