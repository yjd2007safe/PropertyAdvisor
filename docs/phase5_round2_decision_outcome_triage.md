# Phase 5 Round 2: Decision outcome triage cues

## Goal

Turn the new decision-outcome memory into a practical repeated-review aid by surfacing simple triage cues and grouping signals across watchlist and orchestration review.

## Why this round

Phase 5 Round 1 added explicit decision outcome memory, but the product still makes the operator scan row by row. The next smallest useful slice is to make those decision outcomes easier to act on during repeated weekly review.

## Intended slice

Keep this round narrow and mergeable.

- add lightweight outcome-based summary/triage cues where repeated review happens most often
- improve watchlist readability by showing grouped or summarized latest decision outcome patterns
- improve orchestration review readability with compact outcome aggregation or queue-level cueing
- keep backend/service, API schema, UI, and tests aligned

## Success criteria

- watchlist exposes compact, understandable decision-outcome triage cues
- orchestration review exposes compact outcome grouping or prioritization cues
- no broad workflow engine expansion or major schema redesign
- tests and web build still pass

## Constraints

- no major persistence redesign
- no broad navigation rewrite
- no unrelated product work outside the repeated-review loop
- keep the round small enough to validate both product progress and orchestrator round continuity
