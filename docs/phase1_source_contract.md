# Phase 1 Source Contract (MVP Slice)

This document freezes the first production Phase 1 real-data slice, per `docs/phase_plan_v2.md` and `docs/phase1_real_data_tasks.md`.

## Target slice (first rollout)

- **Geography:** Southport, QLD, 4215
- **Country:** AU
- **Scope for this MVP round:** sale + rental listing observations for one suburb slice, with canonical suburb/property/listing upsert and listing snapshot history.

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
