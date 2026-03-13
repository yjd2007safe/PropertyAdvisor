#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA_PATH="$ROOT_DIR/db/schema_v1.sql"
DATA_MODE="${PROPERTY_ADVISOR_DATA_MODE:-auto}"

if [[ ! -f "$SCHEMA_PATH" ]]; then
  echo "Schema file not found: $SCHEMA_PATH" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required but was not found on PATH." >&2
  echo "Install a local Postgres client, then rerun this script." >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
DATABASE_URL is not set.
Example:
  export PROPERTY_ADVISOR_DATA_MODE=mock
  export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
  ./db/scripts/apply_schema.sh

Notes:
  - PROPERTY_ADVISOR_DATA_MODE defaults to auto; keep it on mock until real DB queries are wired.
  - Legacy toggle PROPERTY_ADVISOR_USE_DB is still accepted by the app, but PROPERTY_ADVISOR_DATA_MODE is preferred.
EOF
  exit 1
fi

echo "Applying schema in local-prep mode..."
echo "  data mode hint: $DATA_MODE"
echo "  schema path: $SCHEMA_PATH"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_PATH"

echo "Applied schema: $SCHEMA_PATH"
echo "Next step: keep PROPERTY_ADVISOR_DATA_MODE=mock for now, then add the first read-only Postgres repository query."
