# Phase 4 Round 2: Follow-up intent clarity on orchestration review

This round is a small, mergeable refinement after Round 1. It improves how active follow-up intent is expressed on existing orchestration review surfaces, without changing persistence or API schema.

## Goal

Make it easier for operators to understand **why an item remains active** by tightening carry-forward cues and state expression.

## Implemented slice

- Added a compact follow-up-state cue to orchestration summary `next_action` text.
  - In review-required mode, cue is built from manual-review plans.
  - In auto-progressing mode, cue is built from visible plans.
- Updated orchestration UI state wording to show human-readable follow-up state labels.
- Reframed revisit column content as an “active reason” expression:
  - `<state label>: <revisit rationale>`

## Why this is narrow

- No backend expansion (reuses existing plan fields).
- No schema changes.
- No route contract changes.
- No redesign of table structure or review workflow.

## Validation

- Extended orchestration review service tests to verify follow-up-state cue appears in summary messaging for:
  - manual-review queue
  - auto-progressing queue
