# Phase 1 Source Contract (MVP Slice)

This document freezes the first production Phase 1 real-data slice, per `docs/phase_plan_v2.md` and `docs/phase1_real_data_tasks.md`.

## Target slice (first rollout)

- **Geography:** Southport, QLD, 4215
- **Country:** AU
- **Scope for this MVP round:** sale + rental listing observations for one suburb slice, with canonical suburb/property/listing upsert, listing snapshot history, and sold/leased event persistence.

### Why Southport for Phase 1

Southport was chosen as the first frozen slice for Phase 1 to keep the real-data rollout narrow, repeatable, and easy to verify end to end. It is not meant to imply long-term exclusivity or strategic preference for Southport as the only target market.

Selection rationale for the Phase 1 MVP slice:

- one-suburb scope keeps ingest, refresh, verification, and rollback/debug loops tight
- the repo already used Southport heavily in mock fixtures, API defaults, and test flows, making it the cheapest slice to convert into a real-data proof point
- prior Southport-oriented experimentation existed in the broader workspace, so using the same geography reduced setup friction while validating the OpenClaw-driven development workflow

Important project-status note:

- the separate `SouthportMarketAutomation` project was an OpenClaw workflow experiment and is now closed; it should not be treated as an active dependency or future production path for PropertyAdvisor
- Southport remains only the current demo/proof slice for PropertyAdvisor Phase 1 until a broader production expansion decision is made

## Source contract (MVP)

- **Source name:** operator-defined feed name (for example `realestate_export`).
- **Payload transport:** local JSON file containing a single object or list of objects.
- **Identity fields (idempotency):**
  - `source_name` (CLI argument)
  - `source_listing_id` (or fallback `external_id` inside payload)

### Required payload fields

Each record must include:

- `source_listing_id` **or** `external_id`
- `address` (or `address_line_1`)
- `suburb` (or `city`)

### Supported optional fields (current MVP)

- `listing_type` (`sale|rent|buy|rental|lease`)
- `status` (normalized to schema status vocabulary)
- `state` / `state_code`
- `postcode` / `postal_code`
- `property_type`
- `beds` / `bedrooms`
- `baths` / `bathrooms`
- `asking_price`
- `rent_price_weekly`
- `listing_url`
- `headline`
- `description`
- `sold_price` / `sale_price`
- `sold_date` / `sale_date`
- `sale_event_id` / `source_event_id`
- `leased_rent_weekly` / `leased_price_weekly`
- `leased_date` / `lease_date`
- `rental_event_id` / `lease_event_id`

## Canonical mapping summary

- **suburbs**: upsert by (`country_code`, `state_code`, `suburb_name`, `postcode`)
- **properties**: lookup by deterministic `normalized_address` (`address|suburb|state|postcode`)
- **listings**: upsert by (`source_name`, `source_listing_id`)
- **listing_snapshots**: append one snapshot per observation

## Run metadata emitted

The ingest command emits structured run metadata:

- `started_at`
- `source_name`
- `target_slice`
- `input_record_count`
- `inserted_count`
- `updated_count`
- `skipped_count`
- `error_count`

## Example payload

```json
[
  {
    "source_listing_id": "rea-1001",
    "listing_type": "sale",
    "status": "active",
    "address": "10 Marine Parade",
    "suburb": "Southport",
    "state": "qld",
    "postcode": "4215",
    "property_type": "unit",
    "beds": 2,
    "baths": 2,
    "asking_price": 875000,
    "listing_url": "https://example.com/listing/rea-1001"
  }
]
```

## Command

Dry-run (in-memory validation):

```bash
python -m property_advisor.ingest \
  --source-name realestate_export \
  --target-slice southport-qld-4215 \
  --input docs/phase1_sample_payload.json
```

Postgres write mode:

```bash
python -m property_advisor.ingest \
  --source-name realestate_export \
  --target-slice southport-qld-4215 \
  --input docs/phase1_sample_payload.json \
  --database-url "$DATABASE_URL"
```


## Refresh orchestration command

For repeatable Southport refresh runs with lock safety and summary history:

```bash
python -m property_advisor.ingest refresh-southport \
  --source-name realestate_export \
  --input docs/phase1_sample_payload.json \
  --database-url "$DATABASE_URL"
```

- Lock file default: `.refresh-southport.lock` (override with `--lock-path`)
- Run summary default: `.refresh/runs/southport_refresh_runs.json` (override with `--summary-path`)


## Demo-slice backfill + verification flow (Round 6)

Use one command to run ingest + refresh + market metrics + row-count verification for the Southport slice:

```bash
python -m property_advisor.ingest backfill-verify-southport \
  --source-name realestate_export \
  --input docs/phase1_sample_payload.json \
  --database-url "$DATABASE_URL"
```

The command persists:

- refresh summaries in `.refresh/runs/southport_refresh_runs.json`
- verification evidence in `.refresh/runs/southport_demo_verification.json`

Both artifacts now use the same operator-facing contract:

- `scope`: declares the frozen Southport proof-slice boundary and explicitly lists broader production capabilities that are still out of scope.
- `proof_slice_evidence`: contains the actual refresh/verification evidence backed by persisted Southport rows.
- `production_readiness`: explains whether the proof slice is healthy while also clarifying that broader production rollout is still incomplete.
- `operator_summary`: human-readable headlines, proof-slice evidence bullets, and safe rerun steps.

You can run verification independently:

```bash
python -m property_advisor.ingest verify-southport-demo \
  --database-url "$DATABASE_URL"
```

Verification reports row counts for the canonical Phase 1 tables used by this slice:

- `suburbs`
- `properties`
- `listings`
- `listing_snapshots`
- `sales_events`
- `rental_events`
- `market_metrics`

### Known data-quality limits (Phase 1 demo slice)

- The demo payload is intentionally small and operator-supplied; it is suitable for repeatable validation but not market completeness.
- Address matching is deterministic and normalization-based, but ambiguous addresses may still require manual review in broader production data.
- Event history can be sparse if feeds omit sold/leased outcome fields.
- Market metrics are first-pass rollups over the available persisted records and should be treated as directional for demos.


## Operator interpretation guide (Round 7)

### What is real-data-backed now

For the frozen `southport-qld-4215` slice, the following are backed by persisted canonical rows and verification artifacts:

- suburb/property/listing upserts
- listing snapshot history across reruns
- sold/leased event persistence when source payloads contain outcome fields
- first-pass market metrics for Southport when refresh runs with `--database-url`
- row-count verification across the canonical phase-1 Southport tables

### What remains fallback or demo-only

The current artifacts do **not** prove:

- completeness for suburbs beyond Southport
- market-wide coverage or SLA-backed source acquisition
- full product postgres readiness for every API/UI surface
- demo-free operation when payloads omit sold/leased outcomes

### Safe rerun checklist

1. Verify the payload is still scoped to Southport, QLD, 4215.
2. Confirm the target `DATABASE_URL` before running writes.
3. Run `refresh-southport` and inspect the appended `proof_slice_evidence` / `production_readiness` sections.
4. Run `verify-southport-demo` for a read-only check, or `backfill-verify-southport` when you want the refresh plus persisted verification report in one step.
5. Treat any `production_readiness.broader_production_status = not_yet_complete` value as expected for this round; only `proof_slice_ready` should gate the frozen-slice handoff.
