# debate-hall-mcp

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/elevanaltd/debate-hall-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/elevanaltd/debate-hall-mcp/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/debate-hall-mcp.svg)](https://badge.fury.io/py/debate-hall-mcp)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

MCP server for Wind/Wall/Door multi-perspective debate orchestration with production-oriented design patterns.

> **Production Status**: This server implements production-minded patterns (validation, bounded operation, atomic persistence) suitable for development and small-scale deployments. For larger production deployments, see [production deployment considerations](#production-deployment-considerations).

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
DEV_BOOTSTRAP::scripts/dev-bootstrap.sh
DEV_HOOKS_OPT_IN::scripts/install-git-hooks.sh[core.hooksPath=.githooks]→DEBATE_HALL_AUTO_BOOTSTRAP=1
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
- **OCTAVE export**: Semantic compression format with tamper-proof sealing (v1.0.0)

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
./scripts/dev-bootstrap.sh
uv pip install -e ".[dev]"
```

### Development bootstrap (worktrees/branches)

One-command setup:
```bash
./scripts/dev-bootstrap.sh
```

Optional: enable repo-local git hooks (prints reminder, or auto-runs bootstrap when `DEBATE_HALL_AUTO_BOOTSTRAP=1`):
```bash
./scripts/install-git-hooks.sh
```

## MCP Tools

### Core Tools

| Tool | Purpose |
|------|---------|
| `init_debate` | Create debate: `thread_id`, `topic`, `mode?`, `max_turns?` |
| `add_turn` | Record turn: `thread_id`, `role`, `content` |
| `get_debate` | View state: `thread_id`, `include_transcript?` |
| `close_debate` | Finalize: `thread_id`, `synthesis`, `output_format?`, `seal?` |

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

### Auto-Orchestration Tools

| Tool | Purpose |
|------|---------|
| `run_debate` | Run complete Wind→Wall→Door debate automatically |
| `resume_debate` | Resume a PAUSED debate after failure |

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

### Tier Configuration (Auto-Orchestration)

The `run_debate` tool uses tier configurations to determine which AI providers to use for each role.

**Quick Start:**
```bash
# Copy the template and add your API key
cp tiers.yaml.example tiers.yaml
export OPENROUTER_API_KEY=your-key-here
```

**Resolution order:**
1. `DEBATE_HALL_TIERS_FILE` environment variable
2. `./tiers.yaml` (project root)
3. `~/.debate-hall/tiers.yaml` (user home)
4. Built-in defaults

See `tiers.yaml.example` for all configuration options including CLI providers and custom prompts.

**Example tier configuration:**
```yaml
# ~/.debate-hall/tiers.yaml
standard:
  wind:
    provider: cli      # Use external CLI (claude, codex, gemini)
    cli: claude
    role: wind-agent   # Optional: role for PAL MCP
  wall:
    provider: cli
    cli: codex
  door:
    provider: cli
    cli: gemini
  settings:
    consensus_required: true   # Wind/Wall must approve synthesis
    max_turns: 12
    max_refinement_loops: 3

premium:
  wind:
    provider: openrouter       # Use OpenRouter API
    model: anthropic/claude-3-opus
  wall:
    provider: openrouter
    model: openai/gpt-4-turbo
  door:
    provider: openrouter
    model: google/gemini-pro
  settings:
    consensus_required: true
    max_turns: 20
    max_refinement_loops: 5
```

**Provider options:**
- `cli`: External AI CLIs (requires `claude`, `codex`, or `gemini` CLI installed)
- `openrouter`: OpenRouter API (requires `OPENROUTER_API_KEY` env var)

**Settings:**
- `consensus_required`: If true, Wind and Wall must approve Door's synthesis
- `max_turns`: Maximum total turns in debate
- `max_refinement_loops`: How many times Door can refine after rejection

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

## Production Deployment Considerations

While debate-hall-mcp implements production-minded patterns (validation, bounded operation, atomic persistence), there are considerations for larger-scale production deployments:

### Current Strengths
- ✅ **Deterministic behavior**: Rule-based validation with no LLM dependency
- ✅ **Resource limits**: Hard turn/round limits prevent runaway sessions
- ✅ **Atomic persistence**: File writes use atomic replace with fsync
- ✅ **GitHub integration**: Rate-limit handling and feature toggles

### Known Limitations for Large-Scale Production

| Area | Current Behavior | Recommendation |
|------|------------------|----------------|
| **State Storage** | Defaults to file-based (`debates/` directory) | Configure `DEBATE_HALL_STATE_DIR` to dedicated location outside repo. For multi-instance: use shared filesystem or database backend ([#106](https://github.com/elevanaltd/debate-hall-mcp/issues/106)) |
| **Concurrency** | Exclusive file locks (readers block readers) | Acceptable for single-instance. For multi-worker: see read/write lock enhancement ([#106](https://github.com/elevanaltd/debate-hall-mcp/issues/106)) |
| **Hash Verification** | Link continuity only (not content re-computation) | Enhancement planned for stronger integrity ([#105](https://github.com/elevanaltd/debate-hall-mcp/issues/105)) |
| **Secrets Management** | `.env` auto-load (dev-oriented) | Use explicit environment variables or secret management system in production |

### Production Checklist

Before deploying at scale:

- [ ] Configure `DEBATE_HALL_STATE_DIR` to dedicated path outside repository
- [ ] Set proper file permissions (600 for state files, 700 for directory)
- [ ] Use explicit secret injection (avoid `.env` in production)
- [ ] Plan for state backup/retention
- [ ] Monitor file lock contention if using multiple workers
- [ ] Consider database backend for >10 concurrent instances

See [Issue #108](https://github.com/elevanaltd/debate-hall-mcp/issues/108) for comprehensive production deployment guide (work in progress).

### Recommended Use Cases

**Well-suited for:**
- Development and testing workflows
- Single-instance or low-concurrency deployments
- Scripted automation with sequential debates
- Research and experimentation

**Requires additional work for:**
- High-concurrency multi-instance production environments
- Strict security compliance requiring full content verification
- Large-scale orchestration with 10+ concurrent debates

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and guidelines.

```bash
# Quick dev setup
git clone https://github.com/elevanaltd/debate-hall-mcp
cd debate-hall-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests (800+ tests)
pytest

# Quality checks
ruff check src tests && mypy src && black --check src tests
```

## License

Apache-2.0 — Built with [HestAI](https://github.com/hestai) and [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
