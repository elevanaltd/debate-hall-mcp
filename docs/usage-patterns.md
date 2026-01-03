# Usage Patterns & Recipes

Detailed guidance for configuring debate-hall-mcp debates.

## Table of Contents

- [When to Use Each Mode](#when-to-use-each-mode)
- [Pre-built Recipes](#pre-built-recipes)
- [Tuning Guide](#tuning-guide)
- [Agent Tiers](#agent-tiers)
- [Cognition Prompts](#cognition-prompts)

## When to Use Each Mode

| Scenario | Mode | Why |
|----------|------|-----|
| Standard architectural decisions | Fixed | Guaranteed coverage of all perspectives |
| Security reviews | Fixed | Wall (critical analysis) must not be skipped |
| Brainstorming/innovation | Mediated | May want multiple Wind turns before critique |
| Breaking deadlocks | Mediated | Can call Door early to synthesize |
| Time-constrained decisions | Fixed + low turns | Predictable, fast completion |

## Pre-built Recipes

Start with a recipe, then adjust based on results:

| Recipe | Config | Best For |
|--------|--------|----------|
| **SPEED** | 3 turns, fixed, 1:1:1 ratio | Quick decisions, low-stakes choices |
| **STANDARD** | 12 turns, fixed, 4:4:4 ratio | Default for most debates |
| **DEEP** | 36 turns, fixed, 12:12:12 ratio | Complex architectural decisions, thorough exploration |
| **FORTRESS** | 9 turns, mediated, 1:3:1 ratio (Wall-heavy) | Security reviews, risk assessment |
| **LABORATORY** | 9 turns, mediated, 3:1:1 ratio (Wind-heavy) | Innovation, creative exploration |
| **COUNCIL** | 12 turns, mediated, 2:2:3 ratio (Door-heavy) | Consensus building, multiple synthesis attempts |

### Recipe Examples

**SPEED** - Quick 3-turn decision:
```
init_debate(thread_id, topic, max_turns=3, max_rounds=1)
```

**FORTRESS** - Security-focused (Wall-heavy):
```
init_debate(thread_id, topic, mode="mediated", max_turns=9)
# Sequence: Wind → Wall → Wall → Wall → Door
```

**LABORATORY** - Innovation-focused (Wind-heavy):
```
init_debate(thread_id, topic, mode="mediated", max_turns=9)
# Sequence: Wind → Wind → Wind → Wall → Door
```

## Tuning Guide

### If debates feel shallow
- Increase `max_turns` (12 → 24)
- Use DEEP recipe
- Switch to Tier 2 specialist agents

### If one perspective dominates
- Switch to mediated mode for manual balance
- Or use fixed mode to guarantee equal coverage

### If synthesis is weak
- Try `synthesizer` specialist agent for Door role
- Ensure Wind/Wall have genuinely conflicting positions
- Add more rounds before closing

### If debates drag on
- Reduce `max_turns`
- Use SPEED recipe for quick decisions
- Set stricter `max_rounds` limit

## Agent Tiers

Different debates benefit from different agent configurations. Choose based on decision complexity.

### Tier 1: Basic

| Agent | Role | Behavior |
|-------|------|----------|
| `wind-agent` | Wind | Balanced, explores obvious paths |
| `wall-agent` | Wall | Balanced judgment |
| `door-agent` | Door | Balanced integration |

**Use for:** Quick decisions, standard debates

### Tier 2: Specialist

| Cognition | Agents | Behavioral Difference |
|-----------|--------|----------------------|
| **PATHOS** | `ideator` | Converges to minimal elegant solutions |
| **PATHOS** | `edge-optimizer` | Finds hidden vectors others miss |
| **ETHOS** | `validator` | Cold truth enforcement |
| **ETHOS** | `critical-engineer` | Production readiness focus |
| **LOGOS** | `synthesizer` | Breakthrough third-way solutions |

**Use for:** Architectural decisions, security reviews, innovation exploration

### Tier 3: Domain Specialists

Mix specialists based on the debate topic:

| Topic | Wind | Wall | Door |
|-------|------|------|------|
| Security debates | `edge-optimizer` | `critical-engineer` | `technical-architect` |
| Innovation debates | `ideator` | `validator` | `synthesizer` |
| Architecture debates | `ideator` | `critical-engineer` | `holistic-orchestrator` |

**Mapping:** Specialists map to roles by cognition: PATHOS→Wind, ETHOS→Wall, LOGOS→Door.

See [agents/README.md](../agents/README.md) for full agent definitions.

## Cognition Prompts

For best results, instruct your agents with role-specific cognition.

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

> **Content Contract**: When blocking, Wall should distinguish between *constraints* (immutable reality) and *opportunities* (things that could be built). See [Wall Content Contract](architecture/wall-content-contract.oct.md) for the semantic structure that transforms blocking into construction specification.

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

### Ready-to-Use Cognition Files

Pre-built cognition overlays are available in [agents/cognitions/](../agents/cognitions/):

- `wind-pathos.oct.md` - Full Wind cognition specification
- `wall-ethos.oct.md` - Full Wall cognition specification
- `door-logos.oct.md` - Full Door cognition specification

---

See also:
- [Execution Tiers](architecture/execution-tiers.oct.md) - Two-tier execution model (Generic vs Bespoke)
- [Multi-Model Debate Patterns](examples/multi-model-debate-patterns.md) - Real-world examples
- [Evidence](evidence/README.md) - Empirical research validating the approach
