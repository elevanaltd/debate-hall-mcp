#!/usr/bin/env bash
# ci-lint.sh — Run the EXACT same quality checks that CI runs.
# This is the canonical "will CI pass?" script.
#
# Usage:
#   ./scripts/ci-lint.sh          # Run all checks
#   ./scripts/ci-lint.sh --fix    # Run ruff with --fix before checking
#
# Mirrors: .github/workflows/ci.yml → quality → steps
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Ensure venv is active
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  else
    echo "ERROR: No .venv found. Run: uv venv && uv pip install -e '.[dev]'" >&2
    exit 1
  fi
fi

FIX_FLAG=""
if [[ "${1:-}" == "--fix" ]]; then
  FIX_FLAG="--fix"
fi

echo "=== ruff check src tests ==="
ruff check $FIX_FLAG src tests

echo "=== black --check src tests ==="
black --check src tests

echo "=== mypy src ==="
mypy src

echo ""
echo "OK: All CI lint checks passed."
