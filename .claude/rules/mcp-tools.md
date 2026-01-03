---
description: MCP tool implementation patterns for debate-hall
paths:
  - "src/debate_hall_mcp/tools/**/*.py"
  - "src/debate_hall_mcp/server.py"
---

# MCP Tool Implementation

## Tool Structure

Tools live in `src/debate_hall_mcp/tools/` and return dicts:

```python
async def my_tool_async(
    thread_id: str,
    required_param: str,
    optional_param: str | None = None,
) -> dict[str, Any]:
    """Tool description."""
    # Validate thread_id first
    validate_thread_id(thread_id)
    # Business logic
    return {"status": "success", "data": result}
```

## Debate Flow Tools

- `init_debate` - Create debate room (mode: fixed|mediated)
- `add_turn` - Record turn (validates cognition matches role)
- `get_debate` - Fetch state + optional transcript
- `close_debate` - Finalize with Door synthesis
- `pick_next_speaker` - Mediated mode only

## GitHub Integration

- `github_sync_debate` - Sync turns to Discussion/Issue comments
- `ratify_rfc` - Generate ADR from synthesis, create PR
- `human_interject` - Inject GitHub comment into active debate

## Key Directories

- `debates/` - JSON debate state files (gitignored)
- `cognitions/` - Cognition validation schemas
- `src/debate_hall_mcp/state.py` - Core state management
- `src/debate_hall_mcp/engine.py` - Debate orchestration logic

## Validation Pattern

Thread IDs use date-first format: `YYYY-MM-DD-subject`
- Example: `2025-12-28-debate-topic`
- Validated in `tools/init.py` via `validate_thread_id()`
- Security: Rejects `..`, `/`, `\` to prevent path traversal

Cognition validation in `validation.py`:
- Role-cognition alignment: Wind→PATHOS, Wall→ETHOS, Door→LOGOS
- Content validation: Pattern matching for cognition contracts
- Turn limit enforcement
