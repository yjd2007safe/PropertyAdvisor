# Phase 5 Round 5: Review queue ordering and grouped scan defaults

This round tightens repeated decision-outcome review scanning by making default ordering and grouping emphasize actionable latest outcomes first across both watchlist and orchestration review.

## What changed

- **Unified actionable-first outcome ranking** for repeated review scan order:
  - Escalate
  - Revisit later
  - No recorded outcome
  - Continue monitoring
  - Close for now
- **Watchlist defaults now align with grouped recurring review behavior**:
  - Service/API default `group_by` now uses `strategy`.
  - Watchlist entries are sorted by latest decision-outcome priority, then watch-status urgency, then recency.
  - Group blocks are ranked by actionable-outcome density, then action-required count, then high-alert count.
- **Orchestration queue scan ordering now applies decision-outcome triage by default**:
  - Plans are sorted with human-review-required first, then outcome priority, then recency.
  - Outcome focus filtering still works and is applied before paging/limit.

## Why this is narrow and safe

- No navigation redesign.
- No workflow-engine changes.
- No persistence schema changes.
- Existing decision outcome model and response contracts are preserved.
- Behavior remains clear in mock/demo and fallback-backed paths because ordering is applied on already-built in-memory response records.

## Validation

- Added/updated tests to confirm:
  - watchlist default grouping and actionable-first ordering behavior
  - orchestration actionable-first queue ordering behavior
- Existing outcome-distribution and focus-filter tests continue validating model alignment.
