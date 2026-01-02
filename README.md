# debate-hall-mcp

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Production-grade MCP server for Wind/Wall/Door multi-perspective debate orchestration.

> A deterministic crucible where subjective cognitive friction is transmuted into objective structural truth through finite, governed, and verifiable dialectic.

## The Pattern

Three cognitive voices work in tension to produce emergent synthesis:

| Role | Cognition | Voice | Purpose |
|------|-----------|-------|---------|
| **WIND** | PATHOS | "What if..." | Expansive, visionary, proposes possibilities |
| **WALL** | ETHOS | "Yes, but..." | Grounding, critical, tests against reality |
| **DOOR** | LOGOS | "Therefore..." | Synthesizing, decisive, forges actionable truth |

## Execution Model

**Debate Hall orchestrates roles, not agents.** It provides deterministic state management and role prompts—clients decide how to implement execution.

| Model | Description | Use When |
|-------|-------------|----------|
| **Single-Agent** | One LLM adopts Wind→Wall→Door prompts in sequence | Default. Simple setup, self-dialogue |
| **Multi-Agent** | Three distinct agents, each bound to one role | Team decisions, specialized cognition |
| **Hybrid** | Mix of AI agents and human participants | Human-in-loop governance, final authority |

Debate Hall provides: `state management`, `turn sequencing`, `hash chain`, `role prompts`, `limit enforcement`

Clients implement: `agent architecture`, `content generation`, `orchestration logic`, `synthesis intelligence`

## Installation

```bash
pip install debate-hall-mcp
```

Or with uv:
```bash
uv pip install debate-hall-mcp
```

## Quick Start

### 1. Configure MCP Client

Add to your Claude Desktop config (`claude_desktop_config.json`) or Claude Code config (`~/.claude.json`):

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

**For GitHub integration**, add your token to the server's environment:

```json
{
  "mcpServers": {
    "debate-hall": {
      "command": "debate-hall-mcp",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

> **Note**: MCP servers run as separate processes and cannot read `.env` files from your project directory. Environment variables must be passed via the `env` configuration.

### 2. Start a Debate

```
User: Use init_debate to start a debate about whether to rewrite our backend in Rust

Claude: [calls init_debate with thread_id="rust-rewrite", topic="Should we rewrite our backend in Rust?"]
```

### 3. Run the Dialectic

In **fixed mode**, the sequence is automatic: Wind → Wall → Door → (repeat)

```
Client (Claude/Agent)
  ├── init_debate(topic)      → creates debate room
  ├── get_debate()            → view state and next speaker
  ├── [generates content]     → add_turn(role, content)
  ├── [repeat for Wall, Door]
  └── close_debate(synthesis) → finalizes with decision
```

## MCP Tools

### Core Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `init_debate` | `thread_id`, `topic`, `mode?`, `max_turns?`, `max_rounds?`, `strict_cognition?` | Create new debate |
| `add_turn` | `thread_id`, `role`, `content`, `cognition?` | Record a turn |
| `get_debate` | `thread_id`, `include_transcript?`, `context_lines?` | View state and transcript |
| `close_debate` | `thread_id`, `synthesis`, `output_format?` | Finalize with synthesis (json/octave/both) |

### Mediated Mode Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `pick_next_speaker` | `thread_id`, `role` | Set next speaker (mediated mode only) |

### Admin Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `force_close_debate` | `thread_id`, `reason` | Emergency shutdown (I5 kill switch) |
| `tombstone_turn` | `thread_id`, `turn_index`, `reason` | Redact turn (preserves hash chain) |

### GitHub Integration Tools

These tools connect debates to GitHub Discussions and Issues, enabling team collaboration:

| Tool | Parameters | Purpose |
|------|------------|---------|
| `github_sync_debate` | `thread_id`, `repo`, `target_id`, `target_type?` | Sync debate turns to GitHub as comments |
| `ratify_rfc` | `thread_id`, `repo`, `adr_number`, `target_id?`, `adr_path?` | Generate ADR from synthesis and create PR |
| `human_interject` | `thread_id`, `repo`, `target_id`, `comment_id` | Inject human GitHub comment into debate |

**Requirements**: Set `GITHUB_TOKEN` environment variable with appropriate permissions:
- `discussions:write` for Discussion comments
- `issues:write` for Issue comments
- `contents:write` and `pull_requests:write` for `ratify_rfc`

**Rate Limits**: GitHub has rate limits that these tools respect:
- Primary: 5000 requests/hour for authenticated users
- Secondary: ~80 content-creating requests/minute
- Tools implement automatic retry with exponential backoff on 429/403

**Feature Toggle**: Disable all GitHub tools by setting `GITHUB_TOOLS_ENABLED=false`

See `.env.example` for configuration options.

## Modes

### Fixed Mode (Default)

Strict turn sequence:
```
Wind → Wall → Door → Wind → Wall → Door → ...
```

Use for: Structured decision-making with guaranteed coverage of all perspectives.

### Mediated Mode

Orchestrator explicitly picks each speaker:
```
[Pick Wind] → Wind → [Pick Door] → Door → ...
```

Use for: Dynamic debates, breaking deadlocks, skipping roles when appropriate.

**Mediated mode risk:** Can bias outcomes by starving roles (e.g., never calling Wall). Use fixed mode when balanced coverage is required.

## Persistence

Debates are persisted in `./debates/` with a dual-format strategy:

| Format | Pattern | Git Status | Purpose |
|--------|---------|------------|---------|
| **JSON** | `{thread_id}.json` | Gitignored | Working state, survives restarts |
| **OCTAVE** | `{thread_id}.oct.md` | Committed | Permanent record, decision artifact |

### Dual-Format Lifecycle

1. **During debate**: State saved to `{thread_id}.json` (ephemeral working file)
2. **On close**: Use `output_format='octave'` or `'both'` to generate `.oct.md` transcript
3. **After close**: JSON files can be deleted; OCTAVE files are the permanent record

### Gitignore Pattern

JSON files are gitignored; OCTAVE transcripts are committed:

```gitignore
# JSON files are ephemeral, OCTAVE transcripts are committed
debates/*.json
```

This pattern applies consistently across HestAI:
- `debates/*.json` → gitignored (working state)
- `debates/*.oct.md` → committed (decision records)
- `.hestai/sessions/archive/*.jsonl` → gitignored (raw logs)
- `.hestai/sessions/archive/*.oct.md` → committed (compressed sessions)

## Resource Limits (I3 Immutable)

Every debate has hard limits to ensure termination:

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_turns` | 12 | Maximum individual turns |
| `max_rounds` | 4 | Maximum complete Wind→Wall→Door cycles |

When limits are reached, the debate is marked as `exhaustion`.

## Hash Chain Verification (I4 Immutable)

Every turn is cryptographically linked to the previous turn via SHA-256 hash chain:

```python
turn.hash = sha256(f"{turn.role}:{turn.content}:{turn.previous_hash}")
```

This provides:
- Tamper-evident history
- Audit trail for decisions
- Verifiable transcript integrity

## Cognition Prompts

For best results, instruct your agents with role-specific cognition:

### Wind (PATHOS)
```
You are WIND, the expansive voice. Your cognition is PATHOS.

Your role:
- Propose possibilities ("What if...")
- Explore without constraint initially
- Generate creative options
- Advocate for potential
- Push boundaries of what's possible

You speak first, opening the space of solutions.
```

### Wall (ETHOS)
```
You are WALL, the grounding voice. Your cognition is ETHOS.

Your role:
- Challenge proposals ("Yes, but...")
- Apply constraints and reality
- Identify risks and blockers
- Enforce integrity requirements
- Pressure-test assumptions

You speak second, testing ideas against truth.
```

> **Content Contract**: When blocking, Wall should distinguish between *constraints* (immutable reality) and *opportunities* (things that could be built). See [Wall Content Contract](docs/wall-content-contract.oct.md) for the semantic structure that transforms blocking into construction specification.

### Door (LOGOS)
```
You are DOOR, the synthesizing voice. Your cognition is LOGOS.

Your role:
- Integrate perspectives ("Therefore...")
- Forge actionable decisions
- Resolve tensions between Wind and Wall
- Produce executable outcomes
- Create structural clarity

You speak third, closing the dialectic into decision.
```

## Architecture Immutables

debate-hall-mcp is built on five unchangeable principles:

| ID | Immutable | Enforcement |
|----|-----------|-------------|
| **I1** | Cognitive State Isolation | State managed by server only |
| **I2** | Universal OCTAVE Binding | Transcripts exportable as OCTAVE format |
| **I3** | Finite Dialectic Closure | Hard turn/round limits |
| **I4** | Verifiable Event Ledger | SHA-256 hash chain |
| **I5** | Sovereign Safety Override | Admin kill switch |

## Development

```bash
# Clone and install
git clone https://github.com/elevanaltd/debate-hall-mcp
cd debate-hall-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests (450+ tests, 91%+ coverage)
pytest

# Quality checks
ruff check src tests
mypy src
black --check src tests
```

## Example: Architecture Decision

```
Thread: "microservices-vs-monolith"
Topic: "Should we migrate to microservices?"

[WIND] "What if we decomposed into services? We'd get independent scaling,
        technology diversity, and team autonomy..."

[WALL] "Yes, but we have 3 developers. Microservices add operational complexity.
        Network latency. Distributed transactions. We don't have the team..."

[DOOR] "Therefore: Start with a modular monolith. Design service boundaries
        now, but keep deployment unified. Extract services only when team
        grows or specific scaling needs emerge. This captures the upside
        while avoiding premature complexity."
```

## Example: GitHub-Connected Debate Workflow

Share AI debates with your team on GitHub and turn decisions into official docs:

```
1. Start debate
   → init_debate(thread_id="api-versioning", topic="How should we version our API?")

2. Run the dialectic (Wind → Wall → Door)
   → add_turn(...) for each perspective

3. Sync to GitHub Discussion
   → github_sync_debate(thread_id="api-versioning", repo="myorg/myrepo",
                        target_id="D_kwDOxxxx", target_type="discussion")

   Team sees formatted comments:
   ## 💨 Wind (PATHOS)
   **Model**: claude-3 | **Turn**: 1/12
   "What if we used URL versioning like /v1/users..."

4. Human teammate comments on Discussion
   → human_interject(thread_id="api-versioning", repo="myorg/myrepo",
                     target_id="D_kwDOxxxx", comment_id="DC_kwDOyyyy")

   Their input is now part of the debate context

5. Close debate with synthesis
   → close_debate(thread_id="api-versioning", synthesis="Use header versioning...")

6. Create official ADR
   → ratify_rfc(thread_id="api-versioning", repo="myorg/myrepo",
                adr_number=15, adr_path="docs/adr/")

   Creates PR with docs/adr/ADR-015-api-versioning.md
```

## Project Structure

```
debate-hall-mcp/
├── src/debate_hall_mcp/
│   ├── __init__.py
│   ├── state.py      # DebateRoom, Turn, persistence
│   ├── engine.py     # Turn logic, limits, modes
│   ├── server.py     # FastMCP server
│   └── tools/        # MCP tool implementations
├── tests/
│   ├── unit/         # 450+ unit tests
│   └── e2e/          # 5 E2E tests
└── .hestai/
    └── workflow/     # NORTH STAR and orchestration
```

## License

Apache-2.0

---

Built with the [HestAI methodology](https://github.com/hestai) and the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
