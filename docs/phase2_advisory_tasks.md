# Phase 2 — Advisory Logic Deepening Tasks

## Objective

Replace thin placeholder advisory composition with persisted, explainable, regression-tested market intelligence, comparables, and property recommendation outputs.

## Entry condition

Phase 1 has produced a usable real-data slice with enough persisted property/listing/event history to generate metrics and comparables from postgres.

## Ordered task list

### 1. Finalize advisory input model
**Tasks**
1. Define the exact inputs required by the advisory engine:
   - canonical property facts
   - latest listing state
   - recent listing history / DOM context
   - suburb market metrics
   - latest sales/rental comparables
   - optional strategy context (`buyer`, `seller`, `investor`)
2. Separate required vs optional inputs.
3. Define behavior when one input group is missing.

**Dependencies**
- Phase 1 complete enough to expose these inputs

**Success criteria**
- advisory generation has a stable contract
- missing-data behavior is explicit, not accidental

### 2. Build market metric rollups from persisted events
**Tasks**
1. Implement rollup logic for weekly/monthly metrics from sales, rentals, and listings.
2. Write latest metric rows to `market_metrics`.
3. Define temperature/demand/supply scoring thresholds.
4. Add tests for metric calculations and classification boundaries.

**Dependencies**
- Phase 1 event/listing history available

**Success criteria**
- target slice has persisted latest market metrics
- suburb overview can read meaningful postgres-backed metrics

### 3. Implement comparable candidate selection on stored data
**Tasks**
1. Build candidate queries from `properties`, `sales_events`, `listings`, and `rental_events`.
2. Apply practical filters:
   - same property type first
   - same suburb, then nearby expansion if sample is thin
   - recency window
   - feature banding for beds/baths/parking/area
3. Support use-case-specific bases: sales, rentals, mixed.
4. Add query-level tests for edge cases and small sample sizes.

**Dependencies**
- Task 2 and Phase 1 data completeness

**Success criteria**
- candidate sets come from stored evidence rather than fixture-only logic
- empty and low-sample conditions are handled deliberately

### 4. Implement comparable scoring and persistence
**Tasks**
1. Score candidates by recency, distance, feature similarity, and price/rent relevance.
2. Persist `comparable_sets` and `comparable_members`.
3. Generate per-member rationale strings/data.
4. Store overall comparable set quality score.
5. Define regeneration behavior for repeated runs.

**Dependencies**
- Task 3

**Success criteria**
- latest comparable set can be regenerated deterministically for the same inputs/version
- comparables API can read persisted latest sets

### 5. Implement advice snapshot generation v1
**Tasks**
1. Define transparent rule-based recommendation outcomes for initial contexts.
2. Calculate:
   - recommendation
   - confidence
   - target value range
   - estimated rent weekly when relevant
   - headline summary
   - rationale list
   - risk list
   - supporting metrics blob
3. Persist outputs to `property_advice_snapshots`.
4. Version the algorithm so future changes are auditable.

**Dependencies**
- Tasks 2-4

**Success criteria**
- advisor output is generated from persisted evidence and stored as snapshots
- latest snapshot read path exists and is test-covered

### 6. Improve confidence and fallback semantics
**Tasks**
1. Make confidence sensitive to sample depth, data freshness, and evidence agreement.
2. Distinguish low confidence due to weak evidence from negative recommendation due to bad fundamentals.
3. Ensure API/UI can show why confidence is low.
4. Keep source provenance metadata attached where useful.

**Dependencies**
- Task 5

**Success criteria**
- advisory output is explainable to an operator
- confidence no longer behaves like a static label

### 7. Add regression scenarios for recommendation quality
**Tasks**
1. Create test fixtures for several representative scenarios:
   - strong buy evidence
   - buy only below range
   - watch due to uncertainty
   - avoid due to stretched pricing / weak market
   - investor-specific yield tension case
2. Lock expected recommendation/confidence/rationale behavior with regression tests.
3. Add snapshot or golden-output tests where useful.

**Dependencies**
- Tasks 2-6

**Success criteria**
- advisory behavior changes become deliberate and reviewable
- future rounds can iterate safely without silent logic drift

### 8. Connect alerts to advisory and comparable changes
**Tasks**
1. Define first triggerable alert rules based on advice/comparable changes.
2. Evaluate alerts when new snapshots or comparable sets are generated.
3. Persist enough trigger context for product display, even if delivery remains basic.

**Dependencies**
- Tasks 4-5

**Success criteria**
- watchlist/alerts gain real evidence-driven meaning
- product can surface actionable deltas rather than static placeholders

## Recommended auto_dev round breakdown

1. advisory input contract + DB-backed comparable candidate selection
2. comparable scoring + comparable set persistence + API read path
3. advice snapshot generation + regression suite
4. confidence / fallback semantics hardening
5. alert rule integration for evidence changes

## Phase 2 Round 1 slice (start here)

### Round objective

Establish a stable advisory input contract and replace the current placeholder comparable lookup with deliberate DB-backed candidate selection on persisted evidence.

### In scope

1. **Advisory input contract**
   - define the advisory engine input shape explicitly
   - separate required inputs from optional inputs
   - define missing-data behavior for each input group
2. **Comparable candidate selection on stored data**
   - select candidates from persisted property / sales data rather than a thin recent-sales dump
   - prefer same-suburb / same-property-type evidence first
   - add practical recency and basic feature-banding rules
   - make low-sample and empty-sample behavior explicit
3. **API/service wiring**
   - route comparables reads through the new candidate-selection layer
   - keep response semantics deliberate when DB evidence is thin
4. **Regression coverage**
   - add query-level tests for candidate selection, empty samples, and low-sample fallback behavior
   - add tests for advisory input contract / missing-input behavior where practical

### Out of scope

- comparable scoring weights
- `comparable_sets` / `comparable_members` persistence
- `property_advice_snapshots` generation
- alert rule integration
- broad market expansion beyond the Southport proof slice

### Success criteria

- advisory generation has a stable input contract instead of ad-hoc service-layer assembly
- comparable candidates come from deliberate persisted-evidence rules
- comparables API no longer behaves like a raw recent-sales dump
- low-sample and empty-sample cases are explicit and regression-tested
- the next round can focus only on scoring/persistence instead of redefining inputs

## Phase 2 done when

- suburb metrics, comparable sets, and advice snapshots are all persisted from real data
- advisor and comparables pages primarily read generated evidence rather than fixture assembly
- recommendation outputs are explainable, versioned, and regression-tested
