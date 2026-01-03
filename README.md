# debate-hall-mcp

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/elevanaltd/debate-hall-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/elevanaltd/debate-hall-mcp/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/debate-hall-mcp.svg)](https://badge.fury.io/py/debate-hall-mcp)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Production-grade MCP server for Wind/Wall/Door multi-perspective debate orchestration.

## Table of Contents

- [What It Does](#what-it-does)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [MCP Tools](#mcp-tools)
- [Configuration](#configuration)
- [Example](#example)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## For AI Agents

```octave
===AGENT_BOOTSTRAP===
SKILL::skills/debate-hall/SKILL.md
WORKFLOW::init→turn→get→close
AGENTS::agents/README.md[Wind/Wall/Door definitions]
COGNITIONS::agents/cognitions/[PATHOS|ETHOS|LOGOS overlays]
RECIPES::[SPEED(3)|STANDARD(12)|DEEP(36)|FORTRESS|LABORATORY]
===END===
```

---

## What It Does

- **Structured debates** with Wind (explore) → Wall (constrain) → Door (synthesize)
- **Deterministic state** with turn limits, hash chain, and verifiable transcripts
- **Multiple modes**: Fixed sequence or mediated orchestration
- **GitHub integration**: Sync debates to Discussions, create ADRs from synthesis
- **OCTAVE export**: Semantic compression format for decision records

## Quick Start

### 1. Install

```bash
pip install debate-hall-mcp
```

### 2. Configure MCP Client

Add to Claude Desktop (`claude_desktop_config.json`) or Claude Code (`~/.claude.json`):

```json
{
  "mcpServers": {
    "debate-hall": {
      "command": "debate-hall-mcp"
    }
  }
}
```

### 3. Start a Debate

```
User: Start a debate about whether to rewrite our backend in Rust

Claude: [calls init_debate with thread_id="rust-rewrite",
         topic="Should we rewrite our backend in Rust?"]
```

### 4. Run the Dialectic

```
Wind → "What if we rewrote in Rust? Memory safety, performance..."
Wall → "Yes, but: team expertise, ecosystem maturity, timeline..."
Door → "Therefore: Profile hotspots first, consider Rust for specific components..."
```

That's it. For GitHub integration, see [Configuration](#configuration).

## Installation

**PyPI:**
```bash
pip install debate-hall-mcp
# or
uv pip install debate-hall-mcp
```

**From source:**
```bash
git clone https://github.com/elevanaltd/debate-hall-mcp
cd debate-hall-mcp
uv pip install -e ".[dev]"
```

## MCP Tools

### Core Tools

| Tool | Purpose |
|------|---------|
| `init_debate` | Create debate: `thread_id`, `topic`, `mode?`, `max_turns?` |
| `add_turn` | Record turn: `thread_id`, `role`, `content` |
| `get_debate` | View state: `thread_id`, `include_transcript?` |
| `close_debate` | Finalize: `thread_id`, `synthesis`, `output_format?` |

### Mode Tools

| Tool | Purpose |
|------|---------|
| `pick_next_speaker` | Set next speaker (mediated mode) |

### Admin Tools

| Tool | Purpose |
|------|---------|
| `force_close_debate` | Emergency shutdown (I5 kill switch) |
| `tombstone_turn` | Redact turn (preserves hash chain) |

### GitHub Tools

| Tool | Purpose |
|------|---------|
| `github_sync_debate` | Sync turns to GitHub Discussion/Issue |
| `ratify_rfc` | Generate ADR from synthesis, create PR |
| `human_interject` | Inject human GitHub comment into debate |

## Configuration

### Minimal (No GitHub)

The MCP config above is sufficient for local debates.

### With GitHub Integration

1. Copy `.env.example` to `.env`
2. Add your GitHub token:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   ```

> **Token scopes needed:** `repo`, `write:discussion`
> Get one at: GitHub → Settings → Developer settings → Personal access tokens

See [Usage Patterns](docs/guides/usage-patterns.md) for detailed configuration options.

## Example

```
Thread: "microservices-vs-monolith"
Topic: "Should we migrate to microservices?"

[WIND] "What if we decomposed into services? Independent scaling,
        technology diversity, team autonomy..."

[WALL] "Yes, but we have 3 developers. Microservices add operational
        complexity, network latency, distributed transactions..."

[DOOR] "Therefore: Start with a modular monolith. Design service
        boundaries now, but keep deployment unified. Extract services
        only when team grows or specific scaling needs emerge."
```

## Documentation

| Doc | Content |
|-----|---------|
| [Usage Patterns](docs/guides/usage-patterns.md) | Recipes, tuning, agent tiers, cognition prompts |
| [Evidence](docs/evidence/) | Empirical research validating the approach |
| [Architecture](docs/architecture/) | Execution tiers, Wall content contract |
| [Examples](docs/examples/) | Real multi-model debate patterns |
| [Agents](agents/README.md) | Wind/Wall/Door agent definitions |
| [Skills](skills/README.md) | AI agent skill installation |

### The Pattern

Three cognitive voices in tension:

| Role | Cognition | Voice |
|------|-----------|-------|
| **Wind** | PATHOS | "What if..." — expansive, visionary |
| **Wall** | ETHOS | "Yes, but..." — grounding, critical |
| **Door** | LOGOS | "Therefore..." — synthesizing, decisive |

### Architecture Immutables

| ID | Principle |
|----|-----------|
| I1 | Cognitive State Isolation — server manages state |
| I2 | OCTAVE Binding — exportable semantic transcripts |
| I3 | Finite Closure — hard turn/round limits |
| I4 | Verifiable Ledger — SHA-256 hash chain |
| I5 | Safety Override — admin kill switch |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and guidelines.

```bash
# Quick dev setup
git clone https://github.com/elevanaltd/debate-hall-mcp
cd debate-hall-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests (500+ tests, 90%+ coverage)
pytest

# Quality checks
ruff check src tests && mypy src && black --check src tests
```

## License

Apache-2.0 — Built with [HestAI](https://github.com/hestai) and [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
