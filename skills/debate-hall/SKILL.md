---
name: debate-hall
description: Wind/Wall/Door multi-perspective debate orchestration using debate-hall-mcp tools. Use when facilitating structured debates, architectural decisions, or multi-perspective analysis.
triggers: ["debate", "wind wall door", "dialectic", "multi-perspective", "structured decision", "architecture decision"]
allowed-tools: ["Read", "Write", "Edit", "Bash", "mcp__debate-hall__*"]
---

# Debate Hall Orchestration

Orchestrate Wind/Wall/Door debates using debate-hall-mcp MCP tools.

## The Pattern

Three cognitive voices in tension produce emergent synthesis:

| Role | Cognition | Voice | Purpose |
|------|-----------|-------|---------|
| **WIND** | PATHOS | "What if..." | Expansive, visionary, proposes possibilities |
| **WALL** | ETHOS | "Yes, but..." | Grounding, critical, tests against reality |
| **DOOR** | LOGOS | "Therefore..." | Synthesizing, decisive, forges actionable truth |

## Core Workflow

```
1. INIT    → init_debate(thread_id, topic, mode?)
2. TURN    → add_turn(thread_id, role, content) [repeat Wind→Wall→Door]
3. GET     → get_debate(thread_id) [view state, check next speaker]
4. CLOSE   → close_debate(thread_id, synthesis, output_format?)
```

## Tool Reference

### init_debate
Create a new debate room.

Parameters:
- `thread_id` (required): Unique identifier for this debate
- `topic` (required): The question or issue being debated
- `mode`: "fixed" (default) or "mediated"
- `max_turns`: Maximum turns allowed (default: 12)
- `max_rounds`: Maximum complete cycles (default: 4)
- `strict_cognition`: Enforce PATHOS/ETHOS/LOGOS contracts (default: false)

### add_turn
Record a debate turn.

Parameters:
- `thread_id` (required): The debate to add to
- `role` (required): "Wind", "Wall", or "Door"
- `content` (required): The turn content
- `cognition`: Override cognition label (PATHOS/ETHOS/LOGOS)
- `agent_role`: Specialist agent identity for audit trail
- `model`: Model identifier for audit trail

### get_debate
View current debate state and transcript.

Parameters:
- `thread_id` (required): The debate to view
- `include_transcript`: Include full transcript (default: true)
- `context_lines`: Number of recent turns to show (default: all)

### close_debate
Finalize debate with synthesis.

Parameters:
- `thread_id` (required): The debate to close
- `synthesis` (required): Door's final synthesis text
- `output_format`: "json" (default), "octave", or "both"

## Mode Selection

### Fixed Mode (Default)
Turn sequence is automatic: Wind → Wall → Door → repeat

Use for:
- Structured decision-making
- Guaranteed coverage of all perspectives
- Standard architectural debates

### Mediated Mode
You explicitly pick each speaker with `pick_next_speaker`.

Use for:
- Dynamic debates
- Breaking deadlocks
- Skipping roles when appropriate
- Multiple agents of same cognition type

**Warning**: Mediated mode can bias outcomes if roles are starved.

## Best Practices

### 1. Single-Agent Self-Dialogue
For quick decisions, adopt each role's prompt in sequence:

```
Wind: "What if we..." [generate options]
Wall: "Yes, but..." [identify risks]
Door: "Therefore..." [synthesize decision]
```

### 2. Multi-Agent Debates
Assign different models or specialist agents to each role:

```
Wind → ideator or edge-optimizer (creative models)
Wall → validator or critical-engineer (analytical models)
Door → synthesizer or technical-architect (balanced models)
```

### 3. Let Door Find the Third Way
The best debates don't pick Wind OR Wall's position—Door synthesizes something neither proposed alone.

### 4. Use OCTAVE Output for Decisions
For permanent records, use `output_format='octave'` on close. This creates auditable `.oct.md` transcripts.

## Example: Architecture Decision

```
init_debate(thread_id="microservices-decision", topic="Should we migrate to microservices?")

[WIND] "What if we decomposed into services? Independent scaling, technology diversity, team autonomy..."

add_turn(thread_id="microservices-decision", role="Wind", content=...)

[WALL] "Yes, but we have 3 developers. Operational complexity, distributed transactions, network latency..."

add_turn(thread_id="microservices-decision", role="Wall", content=...)

[DOOR] "Therefore: Start with modular monolith. Design service boundaries now, deploy unified. Extract only when team grows."

close_debate(thread_id="microservices-decision", synthesis=..., output_format="octave")
```

## Admin Tools

### force_close_debate
Emergency shutdown (I5 kill switch).

```
force_close_debate(thread_id, reason="Safety concern detected")
```

### tombstone_turn
Redact a turn while preserving hash chain integrity.

```
tombstone_turn(thread_id, turn_index=2, reason="Contained PII")
```

## Advanced Patterns

### Flash Debate (Quick Decisions)

For simple decisions, run a complete 3-turn cycle in one sequence:

```python
# 1. Initialize
init_debate(thread_id="quick-decision-{timestamp}", topic="Which logging library?")

# 2. Generate all three perspectives (caller provides content)
add_turn(thread_id, role="Wind", content="What if we used structlog? Schema-free, context propagation...")
add_turn(thread_id, role="Wall", content="Yes, but stdlib logging is zero-dep, team already knows it...")
add_turn(thread_id, role="Door", content="Therefore: stdlib for now, structlog when we need structured output...")

# 3. Close immediately
close_debate(thread_id, synthesis="Use stdlib logging initially...")
```

**Key constraint**: The server orchestrates state, not content. You supply all turn content.

### Socratic Pattern (Premise Clarification)

Before taking positions, clarify the question:

```
Round 1 (Questions Only):
  Wind: "What does 'scalable' mean here? Users? Data volume? Team size?"
  Wall: "What are the actual load projections? Do we have metrics?"
  Door: "Let me consolidate: We need to define scale dimensions before debating solutions."

Round 2+ (Positions):
  Wind: "Given 10K users target, what if we..."
  Wall: "Yes, but our current infra handles..."
  Door: "Therefore..."
```

This is a **convention**, not server-enforced. Discipline produces better debates.

### Multi-Model Specialist Debates

Use different models for each cognition:

```python
# Wind: Creative exploration (Gemini)
mcp__pal__clink(cli_name="gemini", role="ideator", prompt="PATHOS exploration: {topic}")
add_turn(thread_id, role="Wind", content=ideator_response, agent_role="ideator", model="gemini")

# Wall: Reality validation (Codex)
mcp__pal__clink(cli_name="codex", role="validator", prompt="ETHOS validation: {topic}")
add_turn(thread_id, role="Wall", content=validator_response, agent_role="validator", model="codex")

# Door: Synthesis (Claude)
# Synthesize directly as the calling agent
add_turn(thread_id, role="Door", content=synthesis, agent_role="synthesizer", model="claude")
```

## When to Use Debate-Hall

### Trigger Conditions (from ho-orchestrate)

Use debate-hall when you encounter:

| Trigger | Example |
|---------|---------|
| **Complex architectural decision** | "Microservices vs monolith?" |
| **Multiple valid approaches** | "Redux vs Zustand vs Context?" |
| **Unclear tradeoffs** | "Speed vs safety?" |
| **Disagreement between reviewers** | CE and CRS have conflicting feedback |
| **High-risk implementation** | Security model, data migration |

### Integration with Orchestration

If you're an orchestrating agent (HO, IL), escalate to debate-hall when solo analysis is insufficient:

```python
# Detect complexity trigger
if complex_decision or multiple_approaches or reviewer_disagreement:
    # Escalate to structured debate
    init_debate(thread_id=f"ho-{task}-{timestamp}", topic=decision_point, mode="mediated")
    # Run Wind/Wall/Door cycle
    # Apply synthesis to task
```

## Related Resources

- [Agent Definitions](agents/README.md) - Wind/Wall/Door agent files
- [Wall Content Contract](docs/wall-content-contract.oct.md) - Semantic structure for blocking
- [Multi-Model Patterns](docs/examples/multi-model-debate-patterns.md) - Real debate examples
- ho-orchestrate skill - Orchestration integration (HestAI methodology)
