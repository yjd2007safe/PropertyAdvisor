# PropertyAdvisor

PropertyAdvisor is a pure web application for turning property and market data into suburb dashboards, comparable evidence, and property-level advisory workflows.

This repository now includes a usable MVP foundation aligned to the v1 product and architecture docs, with:

- `web/` for the Next.js frontend MVP shell
- `src/property_advisor/` for backend/domain modules and a lightweight FastAPI service
- `db/` for the canonical schema reference and local bootstrap helpers
- `scripts/` for backend/web startup utilities
- `tests/` for smoke coverage across domain and API layers

## Repository Layout

```text
.
|-- db/
|   |-- schema_v1.sql
|   `-- scripts/apply_schema.sh
|-- docs/
|-- scripts/
|-- src/property_advisor/
|   `-- api/
|-- tests/
`-- web/
```

## Local MVP Setup

### 1. Backend bootstrap

```bash
python3 -m venv .venv
source .venv/bin/activate
./scripts/bootstrap_backend.sh
```

Or just run the helper directly on a clean checkout:

```bash
./scripts/bootstrap_backend.sh
```

### 2. Database bootstrap

Create a local Postgres database, then apply the checked-in schema:

```bash
export PROPERTY_ADVISOR_DATA_MODE=mock
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
./db/scripts/check_database_env.sh
./db/scripts/apply_schema.sh
```

This uses `db/schema_v1.sql` locally only. No external deployment flow is configured in this repository.
Keep the app in `mock` mode until the first real read-only repository queries are wired.

### 3. Run the API

```bash
source .venv/bin/activate
./scripts/start_api.sh
```

Default API base URL: `http://localhost:8000`

Useful endpoints:

- `GET /api/health`
- `GET /api/suburbs/overview`
- `GET /api/advisor/property`
- `GET /api/comparables`

### 4. Run the web app

```bash
./scripts/bootstrap_web.sh
./scripts/start_web.sh
```

Default web URL: `http://localhost:3000`

### 5. Run smoke tests

```bash
pytest
```


## Phase 1 ingest MVP (real-data foundation)

The first Phase 1 slice now includes a practical canonical ingest command for one target suburb slice.

- Source contract + target slice: `docs/phase1_source_contract.md`
- Example payload: `docs/phase1_sample_payload.json`

Run in-memory (validation + structured counts):

```bash
python -m property_advisor.ingest \
  --source-name realestate_export \
  --target-slice southport-qld-4215 \
  --input docs/phase1_sample_payload.json
```

Run against Postgres (idempotent upserts + listing snapshots):

```bash
python -m property_advisor.ingest \
  --source-name realestate_export \
  --target-slice southport-qld-4215 \
  --input docs/phase1_sample_payload.json \
  --database-url "$DATABASE_URL"
```


Run the Southport refresh orchestration (locking + operator-facing run summary append):

```bash
python -m property_advisor.ingest refresh-southport \
  --source-name realestate_export \
  --input docs/phase1_sample_payload.json \
  --database-url "$DATABASE_URL"
```

Notes:
- `refresh-southport` acquires a lock file (`.refresh-southport.lock` by default) and fails fast if one already exists.
- Run summaries are appended to `.refresh/runs/southport_refresh_runs.json` by default (override with `--summary-path`).
- Persisted refresh artifacts now separate `proof_slice_evidence` from `production_readiness`, so operators can distinguish real Southport evidence from broader rollout work still pending.
- Sold/leased outcome payload fields now persist idempotently to `sales_events` / `rental_events` keyed by `(source_name, source_event_id)`; if no explicit source event id is provided, a deterministic fallback id is generated from source listing identity.

Current real-data-backed status for the frozen Southport slice:
- Real-data-backed now: canonical suburb/property/listing persistence, snapshot history, outcome events when present, first-pass market metrics, and row-count verification for `Southport, QLD, 4215`.
- Still fallback/demo-only: broader market completeness, additional suburbs, operator-independent feed acquisition, and product-wide postgres readiness outside the Southport proof slice.

Safe rerun flow for operators:
1. Confirm `DATABASE_URL` points at the intended environment.
2. Run `refresh-southport` with the canonical Southport payload.
3. Review the latest artifact in `.refresh/runs/southport_refresh_runs.json`.
4. Run `backfill-verify-southport` or `verify-southport-demo` to confirm proof-slice minimums still pass.

## Developer Notes

- The FastAPI service is intentionally lightweight and placeholder-backed so real data services can plug in later without rewriting the app boundary.
- The frontend focuses on product information architecture first: Home, Suburb Dashboard, Property Advisor, and Comparables.
- Existing architecture and scope documentation remain under `docs/` and should continue guiding deeper implementation passes.


### Repository and DB mode toggles

- API services now read through internal repository abstractions (suburbs, advisory inputs, comparables).
- Preferred toggle: `PROPERTY_ADVISOR_DATA_MODE=mock|auto|postgres`.
- Safe default: `PROPERTY_ADVISOR_DATA_MODE=mock` keeps the app on fixture-backed repositories while local schema/bootstrap work advances.
- `PROPERTY_ADVISOR_DATA_MODE=auto` resolves to `postgres` only when `DATABASE_URL` is present; otherwise it falls back to `mock`.
- `PROPERTY_ADVISOR_DATA_MODE=postgres` is the explicit cutover switch once repository SQL reads are implemented.
- Legacy `PROPERTY_ADVISOR_USE_DB=0|1` is still accepted for compatibility, but new setup should use `PROPERTY_ADVISOR_DATA_MODE`.
