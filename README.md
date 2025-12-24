# debate-hall-mcp

Production-grade MCP server for Wind/Wall/Door multi-perspective debate orchestration.

## Overview

A deterministic crucible where subjective cognitive friction is transmuted into objective structural truth through finite, governed, and verifiable dialectic.

### The Pattern

- **WIND** (PATHOS): The expansive voice - "What if..."
- **WALL** (ETHOS): The grounding voice - "Yes, but..."
- **DOOR** (LOGOS): The synthesizing voice - "Therefore..."

## Installation

```bash
pip install debate-hall-mcp
```

## Quick Start

Configure in your MCP client (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "debate-hall": {
      "command": "debate-hall-mcp",
      "args": []
    }
  }
}
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `debate_init` | Create new debate thread |
| `debate_turn` | Record a turn |
| `debate_next` | Get prompt for next role |
| `debate_status` | View debate state |
| `debate_close` | Close with synthesis |
| `debate_pick` | Pick next role (mediated mode) |

## Modes

- **Fixed**: Wind → Wall → Door → Wind → Wall → Door → ...
- **Mediated**: Orchestrator picks next role

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests

# Type check
mypy src
```

## License

MIT
