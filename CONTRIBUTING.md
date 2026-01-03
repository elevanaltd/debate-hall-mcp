# Contributing to debate-hall-mcp

Thank you for your interest in contributing to debate-hall-mcp!

## Development Setup

```bash
# Clone and install
git clone https://github.com/elevanaltd/debate-hall-mcp
cd debate-hall-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Testing

```bash
# Run all tests (500+ tests, 90%+ coverage required)
pytest

# Run with coverage report
pytest --cov=debate_hall_mcp --cov-report=term-missing

# Run specific test categories
pytest -m unit          # Fast unit tests
pytest -m e2e           # End-to-end tests
pytest -m integration   # Integration tests
```

## Quality Checks

All checks must pass before merging:

```bash
# Linting
ruff check src tests

# Type checking (strict mode)
mypy src

# Formatting
black --check src tests
```

Or run everything:

```bash
ruff check src tests && mypy src && black --check src tests
```

## Code Style

- **Python**: 3.11+, strict mypy, ruff + black formatting
- **Line length**: 100 characters
- **Imports**: isort ordering (handled by ruff)

## Project Structure

```
debate-hall-mcp/
├── src/debate_hall_mcp/
│   ├── __init__.py
│   ├── state.py      # DebateRoom, Turn, persistence
│   ├── engine.py     # Turn logic, limits, modes
│   ├── server.py     # FastMCP server
│   ├── validation.py # Cognition validation
│   ├── github.py     # GitHub API integration
│   └── tools/        # MCP tool implementations
├── tests/
│   ├── unit/         # Fast isolated tests
│   └── e2e/          # End-to-end system tests
├── agents/           # Wind/Wall/Door agent definitions
│   └── cognitions/   # PATHOS/ETHOS/LOGOS overlays
├── skills/           # AI agent skills
├── docs/             # Extended documentation
│   ├── architecture/ # OCTAVE specifications
│   ├── evidence/     # Research studies
│   └── examples/     # Multi-model debate patterns
└── debates/          # Persisted debate transcripts
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new MCP tool for X
fix: correct turn validation logic
docs: update README quick start
test: add coverage for mediated mode
refactor: simplify hash chain calculation
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes with tests
4. Ensure all quality checks pass
5. Submit a PR with clear description

## Architecture Immutables

These principles are unchangeable — PRs that violate them will be rejected:

| ID | Principle | What It Means |
|----|-----------|---------------|
| **I1** | Cognitive State Isolation | State managed by server only, never clients |
| **I2** | OCTAVE Binding | Transcripts must be exportable as OCTAVE |
| **I3** | Finite Closure | Hard turn/round limits, no infinite debates |
| **I4** | Verifiable Ledger | SHA-256 hash chain for all turns |
| **I5** | Safety Override | Admin kill switch must always work |

## Persistence Model

Debates use dual-format persistence:

| Format | Pattern | Git Status | Purpose |
|--------|---------|------------|---------|
| **JSON** | `{thread_id}.json` | Gitignored | Working state |
| **OCTAVE** | `{thread_id}.oct.md` | Committed | Permanent record |

- JSON files are ephemeral and can be deleted after close
- OCTAVE transcripts are the source of truth for decisions

## GitHub Integration

GitHub tools require a `GITHUB_TOKEN` environment variable:

```bash
# Copy example and add your token
cp .env.example .env
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env
```

Token scopes needed:
- `repo` — for repository access
- `write:discussion` — for Discussion comments

Rate limits are handled automatically with exponential backoff.

## Questions?

Open an issue or start a Discussion on GitHub.
