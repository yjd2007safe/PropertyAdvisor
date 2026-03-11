#!/usr/bin/env bash
set -euo pipefail

if python3 -m venv .venv 2>/dev/null; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -e .[dev]
  echo "Backend environment ready in .venv. Activate with: source .venv/bin/activate"
else
  echo "python3-venv is unavailable; falling back to a user-site install via pip3." >&2
  pip3 install --user -e .[dev]
  echo "Backend dependencies installed to the user site-packages."
fi

echo "Run API with: ./scripts/start_api.sh"
