---
description: Python code style for debate-hall-mcp
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python Style Rules

## Type Hints

- All functions require type hints (enforced by strict mypy)
- Use `from __future__ import annotations` for forward refs
- Prefer `list`, `dict`, `set` over `List`, `Dict`, `Set`

## Imports

- Use absolute imports from `debate_hall_mcp`
- ruff handles isort-style ordering
- Group: stdlib, third-party, local

## Error Handling

- Raise specific exceptions from `validation.py`:
  - `InvalidThreadIdError`
  - `CognitionMismatchError`
  - `DebateNotFoundError`
- Document exceptions in docstrings

## Docstrings

- Google-style docstrings
- Required for public functions/classes
- Include Args, Returns, Raises sections

## Line Length

- 100 characters max
- Enforced by black and ruff

## Project-Specific

- Thread IDs: Date-first format `YYYY-MM-DD-subject` (e.g., `2025-12-28-debate-topic`)
  - Validated via `validate_thread_id()` in `tools/init.py`
  - Security: Rejects path traversal (`..`) and directory separators (`/`, `\`)
- Cognition types: `PATHOS` (Wind), `ETHOS` (Wall), `LOGOS` (Door)
- Role names: `Wind`, `Wall`, `Door` (case-sensitive)
