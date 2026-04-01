# Phase 4 Round 3: Compact carry-forward summary on orchestration review

This round is a narrow follow-up to Round 2 intent clarity. It keeps the same orchestration surfaces and contracts, and adds one cohesive improvement: a compact carry-forward summary in top-line operator guidance.

## Goal

Reduce ambiguity during repeated review by making the revisit rationale easier to scan in one line, so operators can carry decisions forward without reopening every queue row.

## Implemented slice

- Added compact carry-forward summary generation in orchestration review service.
- Summary groups by follow-up state label + revisit rationale and shows counts (for example `awaiting operator outcome: ... ×2`).
- Appended carry-forward summary to `summary.next_action` for:
  - awaiting-review mode (manual-review plans)
  - auto-progressing mode (visible plans)

## Why this is narrow

- No backend expansion.
- No schema or route contract changes.
- No table redesign; existing UI surfaces consume improved summary text automatically.

## Validation

- Extended orchestration review service tests to verify `next_action` includes carry-forward summary text for:
  - manual-review queue
  - auto-progressing queue
