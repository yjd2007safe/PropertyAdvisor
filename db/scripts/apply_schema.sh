#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA_PATH="$ROOT_DIR/db/schema_v1.sql"

if [[ ! -f "$SCHEMA_PATH" ]]; then
  echo "Schema file not found: $SCHEMA_PATH" >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
DATABASE_URL is not set.
Example:
  export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
  ./db/scripts/apply_schema.sh
EOF
  exit 1
fi

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_PATH"

echo "Applied schema: $SCHEMA_PATH"
