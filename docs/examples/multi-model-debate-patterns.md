# Multi-Model Debate Patterns

Real-world examples of debate-hall-mcp used for architectural decisions.

## Example 1: OCTAVE Integration Strategy

**Debate:** `debates/octave-integration-strategy-2024-12-28.json`

**Question:** How should debate-hall-mcp integrate OCTAVE skills for token efficiency?

**Participants:**
- Wind (Gemini) - Explored possibilities
- Wall (GPT-5.1-Codex) - Identified failure modes
- Door (Claude Opus 4.5) - Synthesized solution

**Key Finding:** The synthesis produced "OCTAVE-Aware, Not OCTAVE-Dependent" - a third way that neither Wind nor Wall proposed alone.

```
WIND proposed: Cognitive Thermostat (dynamic injection based on token load)
WALL blocked: No token telemetry infrastructure exists
DOOR synthesized: View-layer preamble that teaches by example without dependencies
```

**Lesson:** Multi-model debates can find emergent solutions that single-model exploration misses.

---

## Example 2: Archetype Differentiation Study

**Debates:**
- `debates/octave-visibility-wind-variants-2024-12-28.json`
- `debates/wind-archetype-replication-2024-12-28.json`

**Question:** Do different Wind archetypes (same model, different prompts) produce meaningfully different outputs?

**Participants (all Gemini-3-Pro):**
- `wind-agent` - Standard explorer
- `edge-optimizer` - Boundary finder
- `ideator` - Creative catalyst

**Results (replicated across 2 runs):**

| Archetype | Consistent Pattern | Example Ideas |
|-----------|-------------------|---------------|
| wind-agent | Explores obvious insertion points | Tool descriptions, Genesis Turn, Mirror Response |
| edge-optimizer | Finds hidden vectors | Error message formatting, Identity as structure, Timestamps |
| ideator | Converges to minimal solution | Holographic Preamble (~10 lines, same both runs) |

**Lesson:** Archetype framing produces consistent behavioral differentiation even with the same underlying model. Specialist agents search different solution spaces.

---

## Patterns for Effective Debates

### 1. Use Different Models for Different Roles

```
Wind (exploration) → Use creative models (Gemini, Claude)
Wall (critique) → Use analytical models (GPT-Codex, o3)
Door (synthesis) → Use balanced models (Claude Opus, GPT-5)
```

### 2. Mediated Mode for Controlled Experiments

When testing hypotheses about agent behavior, use mediated mode to control turn order and isolate variables.

### 3. Run Replication Studies

One run could be a fluke. Run the same experiment twice to confirm patterns are consistent.

### 4. Let Door Find the Third Way

The best debates don't just pick Wind or Wall's position - Door synthesizes something neither proposed.

---

## Example 3: Agent Configuration Tiers

**Debate:** `debates/2024-12-31-agent-configuration-tiers.json`

**Question:** What are the optimal agent configuration tiers for debate-hall-mcp debates?

**Participants:**
- Wind (Gemini-3-Pro) - Explored configuration topologies
- Wall (Codex) - Validated against implementation constraints
- Door (Claude Opus 4.5) - Synthesized recipe-based approach

**Wind's Proposals:**
1. **T-Shirt Sizing** - Static tiers (Speed/Standard/Deep) via init params
2. **Asymmetric Roster** - Fortress (3 Walls), Laboratory (3 Winds), Council (3 Doors)
3. **Cognitive Fluidity** - Agents shift cognition between debate phases

**Wall's Verdict:**
- T-Shirt Sizing: **GO** - Implementable today as caller-side presets
- Asymmetric Roster: **CONDITIONAL GO** - Only via mediated mode + `agent_role`/`model` metadata
- Cognitive Fluidity: **BLOCKED** - `ROLE_COGNITION_MAP` binds Wind→PATHOS, Wall→ETHOS, Door→LOGOS permanently

**Key Finding:** Door synthesized **RECIPE-BASED CONFIGURATION** - neither internal tiers (Wind) nor Hall modifications (impossible per Wall) but declarative orchestrator-level templates that compose existing Hall primitives.

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

## Agent Configuration Tiers

Different debates benefit from different agent configurations. Evidence from replication studies shows specialist agents consistently produce different outputs than generic agents.

### Tier 1: Basic (wind-agent / wall-agent / door-agent)
**Use case:** Quick decisions, standard architectural debates

The default Wind/Wall/Door agents provide solid debate quality for most use cases.

### Tier 2: Specialist (ideator / validator / synthesizer)
**Use case:** Complex decisions requiring deeper analysis

Evidence from the Archetype Differentiation Study shows these specialists search **different solution spaces**:

| Role | Basic Agent | Specialist | Behavioral Difference |
|------|-------------|------------|----------------------|
| Wind | `wind-agent` | `ideator` | Converges to minimal solutions vs. exploring all paths |
| Wind | `wind-agent` | `edge-optimizer` | Finds hidden vectors vs. obvious insertion points |
| Wall | `wall-agent` | `validator` | Cold truth enforcement vs. balanced judgment |
| Wall | `wall-agent` | `critical-engineer` | Production readiness focus vs. general constraints |
| Door | `door-agent` | `synthesizer` | Breakthrough transcendence vs. balanced integration |

**Recommended for:** Architectural decisions, security reviews, innovation exploration

### Tier 3: Domain Specialists
**Use case:** Domain-specific decisions requiring expertise

Mix specialists based on the debate topic:
- **Security debates:** edge-optimizer (find attack vectors) + critical-engineer (production risks) + technical-architect
- **Innovation debates:** ideator (breakthrough ideas) + validator (reality check) + synthesizer (third-way)
- **Architecture debates:** ideator + critical-engineer + holistic-orchestrator (system coherence)

---

## Recipe Library Reference

Pre-defined configurations for common debate scenarios:

| Recipe | Turns | Mode | Wind:Wall:Door | Recommended Agents |
|--------|-------|------|----------------|-------------------|
| `speed` | 3 | fixed | 1:1:1 | Basic tier |
| `standard` | 12 | fixed | 4:4:4 | Basic or Specialist |
| `deep` | 36 | fixed | 12:12:12 | Specialist tier |
| `fortress` | 9 | mediated | 1:3:1 | edge-optimizer + critical-engineer×3 + technical-architect |
| `laboratory` | 9 | mediated | 3:1:1 | ideator + edge-optimizer + wind-agent + validator + synthesizer |
| `council` | 12 | mediated | 2:2:3 | Specialist tier with multiple Doors |

### Specialist Agent Mappings

When using specialist agents, map them to their cognition's debate role:

**PATHOS (Wind):**
- `wind-agent` - Standard explorer (explores obvious paths)
- `ideator` - Creative catalyst (converges to minimal elegant solutions)
- `edge-optimizer` - Boundary finder (discovers hidden vectors)

**ETHOS (Wall):**
- `wall-agent` - Standard validator (balanced judgment)
- `validator` - Cold truth enforcer (uncompromising reality)
- `critical-engineer` - Production readiness (will-it-break focus)

**LOGOS (Door):**
- `door-agent` - Standard synthesizer (balanced integration)
- `synthesizer` - Third-way breakthrough (transcendent solutions)
- `holistic-orchestrator` - System-wide coherence (cross-boundary)
- `technical-architect` - Architectural synthesis (pattern-focused)

---

## Patterns for Effective Debates

### 1. Use Different Models for Different Roles

```
Wind (exploration) → Use creative models (Gemini, Claude)
Wall (critique) → Use analytical models (GPT-Codex, o3)
Door (synthesis) → Use balanced models (Claude Opus, GPT-5)
```

### 2. Mediated Mode for Controlled Experiments

When testing hypotheses about agent behavior, use mediated mode to control turn order and isolate variables.

### 3. Run Replication Studies

One run could be a fluke. Run the same experiment twice to confirm patterns are consistent.

### 4. Let Door Find the Third Way

The best debates don't just pick Wind or Wall's position - Door synthesizes something neither proposed.

### 5. Match Recipe to Risk Profile

- High-risk decisions → `fortress` (more Walls, more scrutiny)
- Creative exploration → `laboratory` (more Winds, more options)
- Stakeholder alignment → `council` (more Doors, more synthesis)

### 6. Use `agent_role` for Audit Trails

Always populate `agent_role` and `model` metadata when using specialists. This creates an auditable record of which specific agent archetype spoke in each turn.

---

## Raw Debate Files

All debates are stored as JSON in the `debates/` directory:
- Full transcript with hashes
- Speaker metadata (agent_role, model, cognition)
- Final synthesis

These serve as both examples and audit trail.
