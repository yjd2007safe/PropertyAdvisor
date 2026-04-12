# Phase 5 Round 1: Decision outcome ledger

## Goal

Turn repeated review actions into a compact decision memory so PropertyAdvisor preserves what was decided, why it was decided, and what should happen next.

## Why this round

Phase 4 made the reviewer workflow more operational and easier to revisit, but the product still leans heavily on current queue state. It is weaker at preserving explicit decision outcomes across repeated review.

This round should make the product feel less like a queue that gets processed and more like an operating system that remembers prior review outcomes.

## Intended slice

Keep this round narrow and mergeable.

- add explicit decision outcome semantics to reviewer actions without introducing a broad task system
- preserve a compact decision summary alongside reviewer action state
- surface the latest decision outcome in orchestration review and watchlist detail where it helps repeated review
- keep backend/service, API schema, and UI aligned on the same decision-memory concept

## Example outcome framing

Examples may include compact outcomes such as:
- continue monitoring
- revisit later
- close for now
- escalate for closer review

The exact labels can be refined during implementation, but the slice should stay compact and avoid becoming a full workflow engine.

## Success criteria

- reviewer action state is paired with an explicit, compact decision outcome record
- orchestration review can show the most recent decision summary for carry-forward items
- watchlist detail can show the latest known decision context when available
- the new fields remain understandable in both mock/demo and fallback paths
- tests and web build still pass

## Constraints

- no broad redesign of watchlist or orchestration workflow
- no new task management system or CRM expansion
- no major schema migration unless a very small persistence shape is clearly required
- keep the slice implementation-focused and mergeable
