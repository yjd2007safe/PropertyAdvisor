# PropertyAdvisor

PropertyAdvisor is a web application for turning raw property and market data into normalized records, comparable sets, advisory outputs, and user-facing alerts.

This repository now includes an implementation-ready MVP scaffold aligned to the v1 product and architecture docs, with:

- `web/` for the Next.js frontend shell
- `src/property_advisor/` for backend/domain Python modules
- `db/` for schema and database-oriented notes
- `scripts/` for local bootstrap helpers and setup notes
- `tests/` for lightweight backend smoke coverage

## Repository Layout

```text
.
|-- db/
|-- docs/
|-- scripts/
|-- src/property_advisor/
|-- tests/
`-- web/
```

Key backend modules:

- `ingest`: input adapters and raw record intake
- `normalize`: canonical property and listing normalization
- `advisory`: recommendation snapshot assembly
- `comparables`: comparable-set construction helpers
- `market_metrics`: market rollups and derived indicators
- `alerts`: alert rule evaluation and notification preparation

## MVP Setup

### 1. Frontend

```bash
cd web
npm install
npm run dev
```

The frontend uses the Next.js App Router and currently exposes a product-aligned homepage placeholder for the first implementation pass.

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

The Python package is intentionally light. It establishes clean module boundaries for ingestion, normalization, comparables, market metrics, advisory logic, and alerts without overcommitting to infrastructure too early.

### 3. Environment

Copy `.env.example` to `.env` and fill only the values needed for the workflow you are implementing.

## Notes

- Existing product and schema documentation remain under `docs/` and `db/schema_v1.sql`.
- This scaffold is aimed at MVP delivery, not deployment.
- Dependencies are intentionally minimal so the next engineer can add only what the implementation actually needs.
