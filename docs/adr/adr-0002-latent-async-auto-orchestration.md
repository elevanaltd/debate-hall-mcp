# ADR-0002: Latent Async Auto-Orchestration Architecture

## Status

**ACCEPTED** (2026-01-29)

## Context

Issue #111 proposes adding `run_debate` auto-orchestration to debate-hall-mcp, enabling fully autonomous multi-model debates without external coordination.

The fundamental architectural question: Should orchestration be synchronous (blocking) or asynchronous (non-blocking)?

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A: Synchronous** | Block until debate completes (30-60s) | Simple, but MCP clients may timeout |
| **B: Async + Polling** | Return immediately, poll for status | Complex state machine, but non-blocking |
| **C: Async + Streaming** | WebSocket/SSE real-time events | Highest complexity, best UX |
| **D: Latent Async** | Event-first persistence, polling v1, streaming later | Future-proof without upfront complexity |

A multi-model debate (Wind/Claude, Wall/Codex, Door/Gemini) surfaced the key tension:

- **Wind's concern**: If we build synchronous now, adding streaming later requires rework
- **Wall's constraint**: Don't commit to streaming complexity without proven demand

## Decision

We adopt **Latent Async Architecture**:

1. **Event-first persistence from day one** - Append-only `debate_events` storage
2. **Polling delivery for v0.2.0** - Simple REST-style `GET /events?after={id}`
3. **Future streaming = transport swap only** - No schema changes required

This resolves the tension by building the async-capable foundation (events) while deferring transport complexity (WebSocket/SSE) until validated.

## Architecture

```
+------------------------------------------------------------------+
|                     Auto-Orchestration Flow                       |
+------------------------------------------------------------------+
|                                                                    |
|  run_debate(topic, tier)                                           |
|       |                                                            |
|       v                                                            |
|  +------------------+                                              |
|  | Orchestrator     |                                              |
|  |                  |                                              |
|  |  1. init_debate  |                                              |
|  |  2. Wind turn    |----> LLM API (OpenRouter)                    |
|  |  3. Wall turn    |----> LLM API (OpenRouter)                    |
|  |  4. Door turn    |----> LLM API (OpenRouter)                    |
|  |  5. Consensus?   |----> Wind/Wall approve Door synthesis        |
|  |  6. close_debate |                                              |
|  +------------------+                                              |
|       |                                                            |
|       v                                                            |
|  +------------------+     +------------------------------------+   |
|  | Event Store      |     | State (existing)                   |   |
|  | (append-only)    |     | {thread_id}.json                   |   |
|  |                  |     |                                    |   |
|  | debate_started   |     | turns: [...]                       |   |
|  | turn_added       |     | status: active/synthesis/...       |   |
|  | consensus_vote   |     | synthesis: "..."                   |   |
|  | debate_closed    |     |                                    |   |
|  +------------------+     +------------------------------------+   |
|       |                                                            |
|       v                                                            |
|  +------------------+     +------------------------------------+   |
|  | v0.2.0: Polling  |     | Future: SSE/WebSocket              |   |
|  | GET /events      |     | SUBSCRIBE /events                  |   |
|  | ?after={id}      |     | (transport swap only)              |   |
|  +------------------+     +------------------------------------+   |
|                                                                    |
+------------------------------------------------------------------+
```

### Event Schema (v0.2.0)

```python
class DebateEvent(BaseModel):
    """Append-only event for latent async delivery."""
    id: str                    # Monotonic event ID
    thread_id: str             # Debate thread
    event_type: str            # debate_started, turn_added, consensus_vote, debate_closed
    timestamp: datetime        # UTC
    payload: dict              # Event-specific data
```

### Polling Interface (v0.2.0)

```python
def get_events(
    thread_id: str,
    after: str | None = None,  # Cursor for pagination
    limit: int = 50
) -> list[DebateEvent]
```

### Future Streaming (v0.3.0+)

```python
# Same events, different transport
async def subscribe_events(thread_id: str) -> AsyncIterator[DebateEvent]
```

## Implementation

### v0.2.0 Scope

| Feature | Status |
|---------|--------|
| `run_debate(topic, tier)` MCP tool | Include |
| Event-based persistence (`debate_events`) | Include |
| Polling delivery (`get_events`) | Include |
| Tier configuration (YAML) | Include |
| Settings UI (reference ingest-assistant pattern) | Include |
| Consensus mechanism (Wind/Wall approve Door) | Include |
| Dual provider architecture (CLI + OpenRouter) | Include |
| SSE/WebSocket streaming | Defer |

### Model Provider Architecture

**Decision**: Support multiple providers from v0.2.0

#### Providers

1. **CliProvider** - Invokes local CLI tools (claude, codex, gemini)
   - Uses existing subscriptions (zero marginal cost)
   - Requires CLI installed locally
   - Supports: `claude --print`, `codex exec`, `gemini`

2. **OpenRouterProvider** - Calls OpenRouter API
   - Pay-per-token pricing
   - Any model available via OpenRouter
   - Requires API key

#### Interface

```python
class ModelProvider(Protocol):
    """Abstract interface for model providers."""
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None
    ) -> str: ...

class CliProvider(ModelProvider):
    """Invokes local CLI tools (claude, codex, gemini)."""
    def __init__(self, cli_name: str, role: str | None = None):
        self.cli_name = cli_name  # "claude", "codex", "gemini"
        self.role = role          # Optional role for system prompt

    async def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        # Spawn CLI process in non-interactive mode
        # claude --print --system-prompt <prompt> --model <model> "<user_prompt>"
        # codex exec --model <model> "<prompt>"
        # gemini --model <model> "<query>"
        ...

class OpenRouterProvider(ModelProvider):
    """Calls OpenRouter API for multi-model access."""
    async def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        # POST to OpenRouter API
        ...
```

#### Rationale

- **Existing infrastructure**: User already has working CLI subscriptions
- **Cost efficiency**: CLI providers = $0 marginal cost vs pay-per-token
- **Minimal abstraction cost**: Simple Protocol interface done upfront
- **Avoid retrofit**: Adding abstraction later requires touching all model-calling code

### Configuration

```yaml
# ~/.debate-hall/tiers.yaml

# CLI-based tier (uses existing subscriptions - $0 marginal cost)
standard:
  wind:
    provider: "cli"
    cli: "claude"
    model: "opus"
    role: "ideator"
  wall:
    provider: "cli"
    cli: "codex"
    role: "validator"
  door:
    provider: "cli"
    cli: "gemini"
    role: "synthesizer"
  settings:
    consensus_required: true
    max_turns: 12
    max_refinement_loops: 3

# OpenRouter tier (pay-per-token, any model)
cheap:
  wind:
    provider: "openrouter"
    model: "anthropic/claude-3-haiku"
  wall:
    provider: "openrouter"
    model: "openai/gpt-4o-mini"
  door:
    provider: "openrouter"
    model: "google/gemini-flash"
  settings:
    consensus_required: true
    max_turns: 12
    max_refinement_loops: 3

# Mixed tier (CLI for expensive roles, OpenRouter for cheap)
mixed:
  wind:
    provider: "cli"
    cli: "claude"
    model: "opus"
    role: "ideator"
  wall:
    provider: "openrouter"
    model: "openai/gpt-4o-mini"
  door:
    provider: "cli"
    cli: "gemini"
    role: "synthesizer"
  settings:
    consensus_required: false
    max_turns: 9
```

### Consensus Mechanism

Door's synthesis requires explicit approval from Wind and Wall:

1. Door produces synthesis
2. Wind reviews: `APPROVE` or `REJECT` (with feedback)
3. Wall reviews: `APPROVE` or `REJECT` (with feedback)
4. If both approve: Close debate with synthesis
5. If either rejects: Door refines synthesis (up to `max_refinement_loops`)
6. If max loops exceeded: Status = EXHAUSTION

### Error Handling

- Model API failure: Persist partial state, emit `error` event, status = EXHAUSTION
- Timeout: Same as model failure
- Consensus failure: After max loops, close with STALEMATE status

## Consequences

### Positive

- **Future-proof**: Event-first design enables streaming without schema changes
- **Incremental complexity**: Polling v0.2.0 is simple; streaming can follow if demanded
- **Auditability**: Append-only events provide complete debate history
- **Resumability**: Events enable resuming interrupted debates
- **Client flexibility**: Clients can poll or (later) subscribe based on capability

### Negative

- **Dual storage**: Events + state files (minor overhead)
- **Polling latency**: v0.2.0 clients must poll; no push updates
- **CLI dependency**: CliProvider requires claude/codex/gemini CLIs installed locally

### Neutral

- **Provider choice**: Users can use CLI (free) or OpenRouter (pay-per-token) based on needs
- **Settings UI**: Adds frontend component (referenced from ingest-assistant pattern)

## References

- [Issue #111](https://github.com/elevanaltd/debate-hall-mcp/issues/111) - Auto-orchestration proposal
- [Debate: 2026-01-29-debate-hall-app-architecture](../../debates/2026-01-29-debate-hall-app-architecture.json) - Multi-model debate that informed this decision
- [ingest-assistant AITab](https://github.com/elevanaltd/ingest-assistant/blob/main/src/components/SettingsModal/AITab.tsx) - Settings UI pattern reference
- [ADR-0001](./adr-0001-skills-based-octave-compression.md) - Skills-based OCTAVE architecture
