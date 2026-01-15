#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found" >&2
  exit 1
fi

git config core.hooksPath .githooks
echo "OK: enabled repo hooks via core.hooksPath=.githooks"
echo "NOTE: set DEBATE_HALL_AUTO_BOOTSTRAP=1 to auto-run scripts/dev-bootstrap.sh on checkout/merge"

