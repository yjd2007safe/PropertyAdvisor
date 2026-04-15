# PropertyAdvisor Phase 6: Review execution packets

## Why this phase now

PropertyAdvisor Phase 5 materially improved decision-memory, queue ordering, grouped scan defaults, and low-noise repeated-review cues across orchestration review and watchlist surfaces.

The next real bottleneck is no longer basic visibility. It is **execution clarity during repeated review**.

The product can already tell an operator what happened and which items are more important, but it still asks the operator to mentally translate those cues into a practical review pass:
- what to review now
- what can be batched for later
- what was recently closed
- how to move between watchlist and orchestration review without losing the active focus state

This phase keeps the scope deliberately small for orchestrator validation. It is meant to be a realistic but bounded next phase that can run through **4 sequential rounds**.

## Phase objective

Turn the current repeated-review cues into a clearer execution loop so an operator can work a review session in compact, intention-preserving packets instead of re-scanning the full queue every time.

## Entry condition

The repo already has:
- Phase 5 decision-outcome memory and triage cues
- orchestration review action handling (`acknowledge`, `close_follow_up`)
- watchlist latest decision context
- actionable-first queue ordering
- passing backend tests and web build readiness

## Phase-level success criteria

Phase 6 is done when:
- orchestration review can be focused by explicit execution state, not only by outcome
- watchlist and orchestration surfaces preserve focus context through deep links
- recent reviewer actions are visible as compact execution history, not only as row-local state
- review pages expose a compact session-level split between do-now, batch-later, and recently-closed work
- tests and web build still pass

## Constraints

- keep the phase within existing watchlist/orchestration workflow boundaries
- no new task-management system or CRM expansion
- no broad schema redesign unless a very small persistence addition is clearly required
- prefer service/API and UI additions that stay additive and mergeable
- every round must remain narrow enough to validate multi-round orchestrator continuation

## Recommended round sequence

### Phase 6 Round 1: Execution-state filters and deep-link contract

**Goal**
Make repeated review focusable by explicit execution state, not only by decision outcome.

**In scope**
- add orchestration-review filtering for reviewer action state and/or follow-up state
- preserve active filters in review actions and cross-surface links where practical
- align watchlist → orchestration deep links with the same filter vocabulary
- add service/API/UI coverage for the new focus contract

**Success criteria**
- operators can narrow orchestration review to a meaningful execution slice without manual rescanning
- links preserve the intended focus state after navigation or action submission
- tests cover the new filter behavior and routing contract

**Non-goals**
- no batch mutation actions
- no workflow-engine redesign

### Phase 6 Round 2: Decision-aware watchlist event packets

**Goal**
Make watchlist event flow feel like review packets rather than a flat mixed timeline.

**In scope**
- enrich watchlist events with latest decision/reviewer-state context where available
- classify event follow-up posture into compact buckets such as do-now, batch-later, and recently-closed
- improve event follow-up labels and links so they land the operator in the right review state
- add regression coverage for event packet semantics

**Success criteria**
- watchlist events better reflect what kind of review pass they belong to
- event links land with enough context to continue the review loop efficiently
- repeated-review cues stay explicit in tests

**Non-goals**
- no alert-delivery engine changes
- no large visual redesign of the watchlist page

### Phase 6 Round 3: Reviewer action history snapshot

**Goal**
Expose a compact recent-action memory so operators can tell what was just handled without reopening every row.

**In scope**
- add a recent reviewer-action summary or snapshot to orchestration review
- surface recent action memory in watchlist detail where it materially helps repeated review
- keep the representation compact, text-forward, and aligned with existing reviewer-action records
- add tests for ordering, empty-state behavior, and summary wording contracts where practical

**Success criteria**
- operators can quickly see what was recently acknowledged or closed
- recent-action memory is available across the main repeated-review surfaces
- no divergence between service/schema/UI reviewer-action terminology

**Non-goals**
- no full audit-log subsystem
- no unrelated persistence work

### Phase 6 Round 4: Review session packet summary

**Goal**
Close the phase by making each review surface communicate a compact session-level split of active work.

**In scope**
- add a compact session summary that separates do-now, batch-later, and recently-closed work
- make orchestration review and watchlist summary language use the same packet framing
- tighten empty-state / low-volume wording so the packet model still feels coherent when queues are small
- update docs and acceptance coverage as needed

**Success criteria**
- review pages communicate the session workload at a glance
- packet framing is consistent across orchestration review and watchlist surfaces
- the phase lands as a coherent operator-facing improvement rather than four isolated tweaks

**Non-goals**
- no homepage/dashboard expansion unless required for consistency
- no broad navigation rewrite

## Recommended execution order

1. Round 1, establish execution-state filtering and deep-link contract.
2. Round 2, reuse that contract to improve watchlist event packeting.
3. Round 3, layer recent reviewer-action memory on top of the now-clearer execution flow.
4. Round 4, consolidate the packet framing into a compact review-session summary.

## Auto-dev execution note

This file is intended to act as the approved phase input for auto-dev-orchestrator. The orchestrator should treat Phase 6 as a multi-round phase, select the next dependency-unblocked round, and continue through the full phase unless a real blocker appears.
