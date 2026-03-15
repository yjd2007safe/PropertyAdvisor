# PropertyAdvisor Phase Plan v2

Updated after the real-DB integration rounds.

## Current baseline

Already in place:
- Supabase/Postgres project exists and schema has been applied.
- API supports `mock | auto | postgres` data modes.
- Several read paths already resolve from Postgres-backed repositories when data exists, with fallback metadata when not.
- Current product surfaces already expose the main workflow shells: suburb overview, property advisor, comparables, watchlist, alerts.
- Latest known automated round passed local evaluation (`pytest`, web build).

This means the next work is not “start the app”. The next work is to turn the existing DB-aware MVP into a reliable data-producing advisory product.

## Confirmed delivery phases

1. **Phase 1 — real data production/update pipeline**
   Goal: make the database reliably populated and refreshed from real source inputs.
2. **Phase 2 — advisory logic deepening**
   Goal: upgrade advisory outputs from lightweight placeholders into explainable, testable recommendation logic using persisted evidence.
3. **Phase 3 — product UX/workflow enhancement**
   Goal: turn the working read surfaces into a coherent operator/investor workflow that supports repeated use.

## Execution rules for auto_dev

- Keep each round scoped to one vertical slice that can be tested end to end.
- Prefer additive schema changes and idempotent jobs.
- Every data-producing round must include observable outputs: rows written, job logs, and regression tests.
- Do not remove mock mode until postgres mode can support demo-critical paths consistently.
- For workflow/UI rounds, only deepen surfaces that are already fed by real or clearly-labeled fallback data.

## Phase dependencies

### Phase 1 must establish
- canonical ingest entrypoints
- idempotent upsert rules
- refresh scheduling/manual rerun path
- minimum production-ready dataset for at least one target suburb slice
- enough historical records to support metrics/comparables/advice inputs

### Phase 2 depends on
- Phase 1 data completeness for listings, snapshots, and at least one event history path
- reproducible comparable candidate selection inputs
- stable latest-market-metrics query path

### Phase 3 depends on
- Phase 2 advisory outputs having stable fields and confidence/rationale semantics
- watchlist and workflow state being reliable enough to drive repeated user action

## Recommended immediate round sequence

Run these next, in order, starting now:

1. **Round A: Data inventory + source contract pass**
   - document target real sources, required fields, source-specific identifiers, and current gaps
   - create/confirm raw-to-canonical mapping rules
   - define one target suburb/subset for first production slice

2. **Round B: Canonical ingest pipeline for listings/properties/suburbs**
   - implement source import command(s)
   - write idempotent upsert logic for suburb/property/listing layers
   - persist listing snapshots on each observation
   - verify postgres reads show live rows for target slice

3. **Round C: Event history and market metrics generation**
   - backfill or derive sales/rental/listing event history needed for downstream logic
   - implement market metric rollups and latest-metric queries
   - connect suburb overview to latest persisted metrics in postgres mode

4. **Round D: Comparable generation on persisted evidence**
   - move comparable candidate selection and scoring fully onto stored data
   - persist comparable sets/members and expose latest set reads

5. **Round E: Advice snapshot generation v1 on real evidence**
   - compute recommendation, confidence, ranges, reasons, and risks from stored metrics/comps/property facts
   - persist property advice snapshots and wire advisor page to latest snapshot

6. **Round F: Workflow/product hardening**
   - improve watchlist/action loop, evidence navigation, filters, empty states, and run transparency

## Exit criteria by phase

### Exit Phase 1 when
- target suburb slice can be refreshed without manual SQL edits
- rerunning ingest is idempotent
- postgres mode returns real rows for overview/comparables/watchlist-critical read paths
- there is enough persisted history to support at least a first-pass metrics/comps pipeline

### Exit Phase 2 when
- advisor output is generated from persisted evidence, not placeholder composition
- recommendation/rationale behavior is regression-tested
- comparable quality and advisory confidence are explainable from code + data

### Exit Phase 3 when
- a user can move from suburb signal → property review → comparable validation → watch decision with minimal ambiguity
- app clearly communicates data freshness, confidence, and next action
- repeated weekly use is practical without engineering assistance

## Notes for planning discipline

- Do not open too many fronts at once. Phase 1 is the bottleneck.
- The best near-term leverage is one narrow real-data slice that exercises the whole chain.
- If source friction appears, prefer stabilizing one source deeply before adding more breadth.
