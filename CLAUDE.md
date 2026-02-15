# debate-hall-mcp — Agent Instructions

## Quality Gates (MANDATORY before every commit)

Run `./scripts/ci-lint.sh` before committing. This runs the EXACT checks CI runs:

```bash
ruff check src tests      # Lint ALL code — not just src, BOTH src AND tests
black --check src tests   # Format check ALL code
mypy src                  # Type check production code
```

**CRITICAL**: Always lint `src tests` together — never just `src` alone.
CI will reject PRs that fail any of these checks.

### Quick reference

```bash
./scripts/ci-lint.sh          # Check everything (matches CI exactly)
./scripts/ci-lint.sh --fix    # Auto-fix ruff issues, then check
pytest                         # Run tests (after lint passes)
```

## Project Structure

- `src/debate_hall_mcp/` — Production code
- `tests/` — Test files (unit, e2e, integration)
- `scripts/` — Developer tooling (ci-lint.sh, dev-bootstrap.sh)
- `.github/workflows/ci.yml` — CI definition (source of truth)

## Rules

- Python 3.11+ required
- No `__init__.py` in `tests/` directories
- Coverage must stay above 90%
