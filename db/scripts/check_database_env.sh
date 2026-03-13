#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA_PATH="$ROOT_DIR/db/schema_v1.sql"
DATA_MODE="${PROPERTY_ADVISOR_DATA_MODE:-auto}"
LEGACY_USE_DB="${PROPERTY_ADVISOR_USE_DB:-}"
DATABASE_URL_VALUE="${DATABASE_URL:-}"

printf 'PropertyAdvisor DB readiness check\n'
printf '  repo: %s\n' "$ROOT_DIR"
printf '  schema: %s\n' "$SCHEMA_PATH"
printf '  PROPERTY_ADVISOR_DATA_MODE: %s\n' "$DATA_MODE"
if [[ -n "$LEGACY_USE_DB" ]]; then
  printf '  PROPERTY_ADVISOR_USE_DB (legacy): %s\n' "$LEGACY_USE_DB"
fi
if [[ -n "$DATABASE_URL_VALUE" ]]; then
  printf '  DATABASE_URL: set\n'
else
  printf '  DATABASE_URL: missing\n'
fi

if [[ ! -f "$SCHEMA_PATH" ]]; then
  echo "Schema file not found." >&2
  exit 1
fi

if command -v psql >/dev/null 2>&1; then
  printf '  psql: %s\n' "$(command -v psql)"
else
  printf '  psql: missing\n'
fi

cat <<'EOF'

Recommended local flow:
  1. export PROPERTY_ADVISOR_DATA_MODE=mock        # default until real queries are wired
  2. export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
  3. ./db/scripts/apply_schema.sh                  # bootstrap local Postgres schema
  4. switch PROPERTY_ADVISOR_DATA_MODE=postgres    # once repository SQL reads are implemented

Current code status:
  - mock mode is the safe default
  - postgres mode currently selects repository scaffolds only
  - no live Supabase deployment is created by this repo
EOF
