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

## Raw Debate Files

All debates are stored as JSON in the `debates/` directory:
- Full transcript with hashes
- Speaker metadata (agent_role, model, cognition)
- Final synthesis

These serve as both examples and audit trail.
