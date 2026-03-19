# Phase 1 — Real Data Production / Update Tasks

## Objective

Convert the existing postgres-aware application into a real data system that can ingest, normalize, persist, refresh, and expose production-shaped property data for at least one target market slice.

## Assumptions from current repo state

- Supabase/Postgres exists and schema is already available.
- Read repositories already support postgres mode for some surfaces.
- Current bottleneck is not schema creation; it is repeatable population and refresh.

## Current implementation status (WIP round: source contract + ingest foundation)

Completed in this round:
- First production slice frozen as **Southport, QLD, 4215**.
- Written source contract added in `docs/phase1_source_contract.md`.
- Canonical ingest MVP command added (`python -m property_advisor.ingest`) with:
  - file-based payload input
  - structured run metadata counts
  - canonical suburb/property/listing upsert flow
  - listing snapshot append on every observation

Still pending for later Phase 1 rounds:
- sales/rental event persistence
- refresh orchestration command with locking
- expanded production breadth beyond the Southport demo slice

## Round 6 closure notes (Southport demo slice)

- Southport now has a code-driven backfill + verification command path (`backfill-verify-southport`) that runs ingest, refresh, market metrics, and row-count verification without manual SQL edits.
- Verification output explicitly reports canonical row counts for the phase-1 slice tables and can be re-run independently.
- Known data-quality limits for the demo slice are documented in `docs/phase1_source_contract.md` for Phase 1 handoff evidence.

## Round 7 closure notes (operator observability / legibility)

- Southport refresh and verification artifacts now separate `proof_slice_evidence` from `production_readiness`, so operators can see what is backed by persisted Southport rows versus what is still broader rollout work.
- `refresh-southport`, `verify-southport-demo`, and `backfill-verify-southport` now emit aligned operator summaries with rerun guidance and explicit proof-slice boundaries.
- Regression tests now pin the artifact contract so future rounds do not blur proof-slice evidence with broader production-readiness claims.

## Ordered task list

### 1. Freeze the first production slice
**Tasks**
1. Pick the first target geography/suburb slice for real rollout.
2. Define which source types are in scope for this slice:
   - suburb master data
   - property/address facts
   - sale listings
   - rental listings
   - sold/leased events if available
3. Write the minimum required field contract per source.
4. Document source identifiers used for idempotency (`source_name`, `source_listing_id`, `source_event_id`).

**Dependencies**
- none

**Success criteria**
- one written source contract exists
- one target slice is explicitly named
- all downstream rounds can develop against that slice without ambiguity

### 2. Create raw import entrypoints
**Tasks**
1. Add `scripts/` or `src/property_advisor/ingest` entrypoints for source imports.
2. Support file-based or HTTP-fetched source payload ingestion, whichever current access path allows.
3. Standardize run metadata:
   - started_at
   - source_name
   - target_slice
   - input record count
   - inserted/updated/skipped/error counts
4. Ensure failures are surfaced with actionable logs.

**Dependencies**
- Task 1

**Success criteria**
- a developer can run a documented ingest command locally
- ingest emits structured counts and non-silent failures

### 3. Implement canonical suburb/property normalization and matching
**Tasks**
1. Finalize normalization helpers for address/suburb/state/postcode formatting.
2. Define canonical property matching order, e.g.:
   - exact source-linked property if already known
   - normalized address + suburb/postcode
   - fallback manual review bucket if confidence is too low
3. Populate or update `suburbs` and `properties` idempotently.
4. Set `source_confidence` rules consistently.

**Dependencies**
- Task 2

**Success criteria**
- rerunning the same source does not duplicate canonical properties excessively
- representative fixtures/tests cover normalization and matching edge cases

### 4. Implement listing upsert + snapshot history
**Tasks**
1. Upsert current listing rows into `listings` using source identity.
2. On every observation, write `listing_snapshots` rows capturing status/price/headline/description deltas.
3. Normalize status vocabulary into schema-supported values.
4. Preserve `first_seen_at`, update `last_seen_at`, and set off-market fields when applicable.

**Dependencies**
- Task 3

**Success criteria**
- repeated imports update the same listing row
- price/status changes create usable historical snapshots
- comparables and DOM calculations have snapshot history to build on

### 5. Add event persistence for sales and rentals
**Tasks**
1. Persist sold events into `sales_events` when source data supports it.
2. Persist lease/rental outcome data into `rental_events` when available.
3. Link events to canonical properties and listings where possible.
4. Define fallback behavior when only partial event data exists.

**Dependencies**
- Task 4

**Success criteria**
- at least one event path (sales preferred) has real rows in postgres for the target slice
- duplicate source events do not create duplicate canonical events

### 6. Add refresh orchestration and rerun safety
**Tasks**
1. Create one repeatable pipeline command that runs the required ingest stages in order.
2. Support safe reruns for the same slice/date window.
3. Add basic locking or operator guidance to avoid overlapping writes.
4. Record high-level run summaries.

**Dependencies**
- Tasks 2-5

**Success criteria**
- a single command can refresh the target slice
- running it twice produces stable counts and no harmful duplication

### 7. Verify postgres-backed read paths on real rows
**Tasks**
1. Ensure suburb overview queries can resolve real suburb rows and latest metrics placeholders/fallbacks cleanly.
2. Ensure comparables source queries can at least read candidate base data from postgres, even before full scoring is complete.
3. Ensure watchlist detail can reference real suburb/property identifiers where relevant.
4. Add integration tests proving postgres mode returns real data for seeded rows.

**Dependencies**
- Tasks 3-6

**Success criteria**
- tests demonstrate postgres reads on real inserted rows
- UI/API metadata correctly reports `source=postgres` where expected

### 8. Backfill a demo-grade dataset for one slice
**Tasks**
1. Load enough historical/current data for one target suburb to support meaningful demos.
2. Validate row counts across:
   - suburbs
   - properties
   - listings
   - listing_snapshots
   - sales_events / rental_events
3. Spot-check several records manually.
4. Document known data quality limits.

**Dependencies**
- Tasks 1-7

**Success criteria**
- there is one stable real-data demo slice
- phase 2 can start without needing more foundational schema work

## Recommended auto_dev round breakdown

1. source contract + ingest command scaffolding
2. canonical suburb/property/listing upserts
3. listing snapshot history + event persistence
4. refresh orchestration + postgres integration tests
5. demo-slice backfill + docs cleanup

## Round 7 reset (2026-03-19)

Round 6 established the Southport demo slice foundation, including code-driven backfill, refresh orchestration, first-pass market metrics, and verification evidence. That means the next round should not continue adding low-level ingest plumbing by inertia.

Round 7 is redefined as a **Phase 1 productionization / observability correction round**.

### New Round 7 objective

Make the frozen Southport slice operationally legible and ready for recurring refresh, so later Phase 1 work can expand data breadth or deepen product usage without losing operator visibility.

### Round 7 priorities

1. **Operator-visible evidence**
   - standardize run-summary and verification outputs so a human can quickly see what refreshed, what failed, and what remains demo-only
2. **Refresh-contract hardening**
   - make the Southport refresh/backfill command path clearer to run repeatedly, including explicit expectations for inputs, outputs, and safe reruns
3. **Product-facing real-data readiness**
   - document which current surfaces are genuinely supported by Southport postgres data versus still relying on placeholder/fallback behavior
4. **Selection rationale + scope boundaries**
   - document why Southport was chosen for Phase 1 and clarify that it is the current proof slice, not a permanent market commitment

### Round 7 acceptance criteria

- Southport selection rationale is written down
- Phase 1 docs clearly distinguish demo-slice proof from broader production readiness
- refresh/backfill artifacts are described clearly enough for repeated operator use
- repo docs identify what real-data evidence currently exists and where fallback behavior still remains

## Phase 1 done when

- one real suburb slice refreshes through code, not manual SQL
- key canonical tables receive idempotent writes
- postgres-backed read paths visibly operate on real data
- downstream metric/comparable/advice work has enough persisted evidence to proceed
