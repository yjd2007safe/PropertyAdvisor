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
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
./db/scripts/apply_schema.sh
```

This uses `db/schema_v1.sql` locally only. No external deployment flow is configured in this repository.

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

## Developer Notes

- The FastAPI service is intentionally lightweight and placeholder-backed so real data services can plug in later without rewriting the app boundary.
- The frontend focuses on product information architecture first: Home, Suburb Dashboard, Property Advisor, and Comparables.
- Existing architecture and scope documentation remain under `docs/` and should continue guiding deeper implementation passes.
