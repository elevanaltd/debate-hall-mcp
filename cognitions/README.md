# Debate Hall Cognitions

This directory contains the **cognition overlays** for the three debate roles. These define the behavioral contracts that shape how agents participate in debates.

## Architecture: Three-Layer Separation

The cognition system operates across three orthogonal layers:

| Layer | Responsibility | Enforcement |
|-------|---------------|-------------|
| **Protocol** | Role ordering, turn limits, hash chain | MANDATORY (Hall enforces) |
| **Content** | Turn structure, required markers | SELECTIVE (warnings) |
| **Prompting** | Cognition overlays, context framing | ADVISORY (orchestrator chooses) |

## The Three Cognitions

### Wind (PATHOS) - The Explorer
- **Mode**: DIVERGENT
- **Goal**: EXPAND possibility space
- **Output Pattern**: `[STIMULUS] → [CONNECTIONS] → [POSSIBILITIES] → [QUESTIONS]`
- **Must**: Generate three paths (Obvious, Adjacent, Heretical)
- **Never**: Provide single final answer or judge which is "best"

### Wall (ETHOS) - The Guardian
- **Mode**: VALIDATION
- **Goal**: VERIFY against evidence
- **Output Pattern**: `[VERDICT] → [EVIDENCE] → [REASONING]`
- **Must**: Verdict first, evidence second, citations always
- **Never**: Speculate or hedge when evidence exists

### Door (LOGOS) - The Architect
- **Mode**: CONVERGENT
- **Goal**: SYNTHESIZE into emergent structure
- **Output Pattern**: `[TENSION] → [PATTERN] → [CLARITY]`
- **Must**: Show organizing principle explicitly, demonstrate emergence
- **Never**: Just add A+B without showing multiplicative integration

## Overlay Modes

Orchestrators can select how much cognition guidance to inject:

```python
OVERLAY_MODES = {
    "none": "You are {role}.",
    "minimal": "[ROLE::{role}|COGNITION::{cognition}|MODE::{mode}|GOAL::{goal}]",
    "standard": "<full overlay from cognitions/*.oct.md>"
}
```

### When to Use Each Mode

| Mode | Use Case | Token Cost |
|------|----------|------------|
| `none` | HestAI agents with built-in SHANK overlays | ~5 tokens |
| `minimal` | HestAI agents needing role reminder | ~20 tokens |
| `standard` | Generic LLMs without cognition training | ~200 tokens |

## For HestAI Agents

If your agent already has a `§3::SHANK_OVERLAY` section (e.g., `PATHOS_SHANK_OVERLAY` in edge-optimizer), use `overlay_mode: "none"` or `"minimal"`. The Hall will recognize your cognition from the turn content structure.

**The Hall should be promiscuous with guidance but tyrannical with validation.**

## File Structure

```
cognitions/
├── README.md           # This file
├── wind-pathos.oct.md  # Full PATHOS overlay for Wind role
├── wall-ethos.oct.md   # Full ETHOS overlay for Wall role
└── door-logos.oct.md   # Full LOGOS overlay for Door role
```

## Cognition Detection (Future)

The Hall may implement optional cognition mismatch warnings:
- Wind turn without divergent structure → WARN
- Wall turn without VERDICT/EVIDENCE → WARN
- Door turn without synthesis markers → WARN

These are **advisory** (do not block), allowing experimentation while providing feedback.
