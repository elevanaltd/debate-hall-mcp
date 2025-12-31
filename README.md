# debate-hall-mcp

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

Add to your Claude Desktop config (`claude_desktop_config.json`):

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

### 2. Start a Debate

```
User: Use debate_init to start a debate about whether to rewrite our backend in Rust

Claude: [calls debate_init with thread_id="rust-rewrite", topic="Should we rewrite our backend in Rust?"]
```

### 3. Run the Dialectic

In **fixed mode**, the sequence is automatic: Wind → Wall → Door → (repeat)

```
Client (Claude/Agent)
  ├── init_debate(topic)      → creates debate room
  ├── get_next_prompt()       → receives "You are WIND..."
  ├── [generates content]     → add_turn(role, content)
  ├── [repeat for Wall, Door]
  └── close_debate(synthesis) → finalizes with decision
```

## MCP Tools

### Core Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `debate_init` | `thread_id`, `topic`, `mode?`, `max_turns?`, `max_rounds?` | Create new debate |
| `debate_turn` | `thread_id`, `role`, `content` | Record a turn |
| `debate_next` | `thread_id`, `context_lines?` | Get prompt for next role |
| `debate_status` | `thread_id` | View current state |
| `debate_close` | `thread_id`, `synthesis` | Finalize with synthesis |

### Mediated Mode Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `debate_pick` | `thread_id`, `role` | Override next role (mediated mode only) |

### Admin Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `debate_force_close` | `thread_id`, `reason` | Emergency shutdown (I5 kill switch) |
| `debate_tombstone` | `thread_id`, `turn_index`, `reason` | Redact turn (preserves hash chain) |

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

State is held **in-memory** by default. Debates do not survive server restart.

| Aspect | Current | Future |
|--------|---------|--------|
| Storage | In-memory dict | Pluggable backends |
| Survival | Lost on restart | Configurable persistence |
| Export | Via `close_debate` | OCTAVE transcript files |

For production use requiring persistence, export transcripts on close or implement a custom storage backend.

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

# Run tests (94 tests, 91%+ coverage)
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
│   ├── unit/         # 89 unit tests
│   └── e2e/          # 5 E2E tests
└── .hestai/
    └── workflow/     # NORTH STAR and orchestration
```

## License

MIT

---

Built with the [HestAI methodology](https://github.com/hestai) and the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
