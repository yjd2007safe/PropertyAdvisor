#!/usr/bin/env bash
set -euo pipefail

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m uvicorn property_advisor.api.app:app --reload --host 0.0.0.0 --port "${API_PORT:-8000}"
else
  python3 -m uvicorn property_advisor.api.app:app --reload --host 0.0.0.0 --port "${API_PORT:-8000}"
fi
