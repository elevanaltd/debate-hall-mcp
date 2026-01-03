---
description: Testing patterns and conventions for debate-hall-mcp
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
---

# Testing Rules

## Test Markers

- `@pytest.mark.unit` - Fast isolated unit tests (no external dependencies)
- `@pytest.mark.e2e` - End-to-end system behavior tests
- `@pytest.mark.integration` - Tests requiring external services

## Test Structure

```
tests/
  unit/           # Component-level tests
    tools/        # Individual tool tests
  conftest.py     # Shared fixtures
```

## TDD Protocol

1. RED: Write failing test first
2. GREEN: Minimal implementation to pass
3. REFACTOR: Improve while green
4. Commit sequence: `test:` → `feat:` → `refactor:`

## Coverage

- 90% threshold in CI (enforced)
- Focus on behavioral coverage, not line coverage
- Mock GitHub API calls, not internal debate logic

## Async Testing

- `asyncio_mode = "auto"` in pytest config
- Use `pytest-asyncio` for async tools
- All MCP tools are async functions

## Debate Testing Pattern

```python
@pytest.mark.unit
async def test_debate_flow():
    # Initialize debate
    result = await init_debate_async(thread_id, topic)
    # Add turns
    await add_turn_async(thread_id, "Wind", content, "PATHOS")
    # Validate state
    state = await get_debate_async(thread_id)
    assert state["current_round"] == 1
```
