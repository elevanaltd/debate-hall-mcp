# Multi-Model Debate Examples

Real debates using debate-hall-mcp for architectural decisions. These demonstrate the Wind/Wall/Door pattern producing emergent solutions.

> For configuration guidance (recipes, agent tiers, tuning), see [Usage Patterns](../guides/usage-patterns.md).
> For empirical validation of the methodology, see [Evidence](../evidence/).

---

## Example 1: OCTAVE Integration Strategy

**Thread:** `debates/octave-integration-strategy-2024-12-28.json`

**Question:** How should debate-hall-mcp integrate OCTAVE skills for token efficiency?

**Participants (pre-study assignments):**
- Wind (Gemini) - Explored possibilities
- Wall (GPT-5.1-Codex) - Identified failure modes
- Door (Claude Opus 4.5) - Synthesized solution

> **Note:** This debate used model assignments before the M019 study. For optimal results, see [Model Cognitive Optimization Study](../evidence/model-cognitive-optimization-study.md) which recommends: Claude→Wind, GPT→Wall, Gemini→Door.

### The Dialectic

```
WIND proposed: Cognitive Thermostat (dynamic injection based on token load)
WALL blocked: No token telemetry infrastructure exists
DOOR synthesized: View-layer preamble that teaches by example without dependencies
```

### Emergent Solution

"OCTAVE-Aware, Not OCTAVE-Dependent" - a third way that neither Wind nor Wall proposed alone. The synthesis transcended the original either/or framing.

**Lesson:** Multi-model debates find emergent solutions that single-model exploration misses.

---

## Example 2: Archetype Differentiation

**Threads:**
- `debates/octave-visibility-wind-variants-2024-12-28.json`
- `debates/wind-archetype-replication-2024-12-28.json`

**Question:** Do different Wind archetypes (same model, different prompts) produce meaningfully different outputs?

**Participants (all Gemini-3-Pro):**
| Archetype | Role | Behavioral Pattern |
|-----------|------|-------------------|
| `wind-agent` | Standard explorer | Explores obvious paths |
| `edge-optimizer` | Boundary finder | Finds hidden vectors |
| `ideator` | Creative catalyst | Converges to minimal solutions |

### Results (Replicated Across 2 Runs)

| Archetype | Consistent Output Pattern |
|-----------|--------------------------|
| wind-agent | Tool descriptions, Genesis Turn, Mirror Response |
| edge-optimizer | Error message formatting, Identity as structure, Timestamps |
| ideator | Holographic Preamble (~10 lines, same both runs) |

**Lesson:** Archetype framing produces consistent behavioral differentiation even with the same underlying model. Specialist agents search different solution spaces.

---

## Example 3: Recipe-Based Configuration

**Thread:** `debates/2024-12-31-agent-configuration-tiers.json`

**Question:** What are the optimal agent configuration tiers for debate-hall-mcp?

**Participants:**
- Wind (Gemini-3-Pro) - Explored configuration topologies
- Wall (Codex) - Validated against implementation constraints
- Door (Claude Opus 4.5) - Synthesized recipe-based approach

### Wind's Proposals

1. **T-Shirt Sizing** - Static tiers (Speed/Standard/Deep) via init params
2. **Asymmetric Roster** - Fortress (3 Walls), Laboratory (3 Winds), Council (3 Doors)
3. **Cognitive Fluidity** - Agents shift cognition between debate phases

### Wall's Verdicts

| Proposal | Verdict | Reason |
|----------|---------|--------|
| T-Shirt Sizing | **GO** | Implementable today as caller-side presets |
| Asymmetric Roster | **CONDITIONAL GO** | Only via mediated mode + `agent_role`/`model` metadata |
| Cognitive Fluidity | **BLOCKED** | `ROLE_COGNITION_MAP` binds Wind→PATHOS, Wall→ETHOS, Door→LOGOS permanently |

### Door's Synthesis

**RECIPE-BASED CONFIGURATION** - neither internal tiers (Wind) nor Hall modifications (impossible per Wall) but declarative orchestrator-level templates that compose existing Hall primitives.

```yaml
# Example: recipes/fortress.yaml
name: fortress
description: "3-Wall defensive configuration"
hall_config:
  mode: mediated
  max_turns: 9
  strict_cognition: true

roster:
  - {role: Wind, agent_role: "ideator", count: 1}
  - {role: Wall, agent_role: "security-specialist", count: 1}
  - {role: Wall, agent_role: "critical-engineer", count: 1}
  - {role: Wall, agent_role: "requirements-steward", count: 1}
  - {role: Door, agent_role: "technical-architect", count: 1}

sequence: [Wind, Wall, Wall, Wall, Door]
```

**The 1+1=3:** Hall rigidity becomes a feature—the stable substrate upon which infinite orchestration patterns can be composed.

**Lesson:** When constraints seem to block desired functionality, lift abstraction level. The Hall doesn't need to change; recipes live *above* it.

---

## Example 4: OCTAVE Compression Tier Comparison

**Thread:** `docs/examples/compression-tier-comparison.oct.md`

**Question:** What compression tier should debate-hall use for context injection?

**Methodology:** Same topic debated 4 times with different OCTAVE compression levels:
- **D (No OCTAVE)**: Prose output, 11,051 chars
- **C (Basic OCTAVE)**: Literacy primer only, 10,378 chars (-6%)
- **A (AGGRESSIVE)**: Drop nuance, keep causality, 4,513 chars (-59%)
- **B (ULTRA)**: Atoms only, 1,737 chars (-84%)

**Participants:** Wind (Claude Opus), Wall (Codex), Door (Gemini 3 Pro)

### Key Finding

All four debates converged on **identical solutions** despite vastly different output sizes:

| Tier | Solution Name | Core Mechanism |
|------|--------------|----------------|
| D | "Pre-emptive State Injection" | Orchestrator pre-fetches → injects |
| C | "Virtual Tool Preload (VTP)" | Inject the RESULT not the LOG |
| A | "System-Side Tooling" | Tools for State Mgmt, not Cognition |
| B | "Phantom Tool Protocol" | Context Injection + Synthetic Trace |

**Lesson:** OCTAVE compression preserves decision-relevant atoms. 84% reduction is achievable without quality loss. AGGRESSIVE tier is optimal for typical debates.

---

## Raw Debate Files

All debates are stored in the `debates/` directory:
- **JSON format**: Full transcript with hashes, speaker metadata (gitignored)
- **OCTAVE format**: Committed decision records (`.oct.md`)

These serve as both examples and audit trail.
