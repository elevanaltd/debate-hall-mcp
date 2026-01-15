#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
QUIET="${QUIET:-0}"

log() {
  if [[ "$QUIET" != "1" ]]; then
    echo "$@"
  fi
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

ensure_toolchain() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  die "Need either 'uv' or 'python3' on PATH"
}

ensure_venv() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    return 0
  fi

log "Creating venv at $VENV_DIR"
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.11 "$VENV_DIR" >/dev/null 2>&1 || uv venv "$VENV_DIR" >/dev/null 2>&1
    return 0
  fi

  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
}

install_deps() {
  log "Installing editable package + dev deps"
  if command -v uv >/dev/null 2>&1; then
    uv pip install -e ".[dev]" >/dev/null 2>&1
    return 0
  fi
  "$VENV_DIR/bin/python" -m pip install -e ".[dev]" >/dev/null 2>&1
}

main() {
  ensure_toolchain
  ensure_venv
  install_deps
  log "OK: bootstrap complete"
  log "Activate with: source $VENV_DIR/bin/activate"
}

main "$@"

