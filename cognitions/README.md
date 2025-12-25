# Debate Hall Cognitions

This directory contains the **cognition overlays** for the three debate roles. These define the behavioral contracts that shape how agents participate in debates.

## Architecture: Behavioral Firewall

The cognition system uses a **validation-first architecture** - the Hall enforces cognition through OUTPUT validation, not INPUT injection.

> **Core Insight**: Cognition integration = Validation layer extension, NOT prompt distribution system

### Why Validation > Prompting

| Approach | Token Cost | Enforcement | Security |
|----------|------------|-------------|----------|
| Prompt Injection | ~400 tokens/turn | None (advisory) | Weak (can be stripped) |
| **Behavioral Firewall** | **0 tokens** | **Deterministic** | **Zero-trust** |

**Token savings**: 4,800 tokens per 12-turn debate.

## The Three Cognitions

### Wind (PATHOS) - The Explorer
- **Mode**: DIVERGENT
- **Goal**: EXPAND possibility space
- **Output Pattern**: `[STIMULUS] → [CONNECTIONS] → [POSSIBILITIES] → [QUESTIONS]`
- **Validation Rules**:
  - REQUIRED: Multiple options (detect numbered lists or bullets)
  - REQUIRED: Question marks (exploration signal)
  - FORBIDDEN: Single conclusion without alternatives

### Wall (ETHOS) - The Guardian
- **Mode**: VALIDATION
- **Goal**: VERIFY against evidence
- **Output Pattern**: `[VERDICT] → [EVIDENCE] → [REASONING]`
- **Validation Rules**:
  - REQUIRED: `[VERDICT]` or `VERDICT:` in first 200 chars
  - REQUIRED: `[EVIDENCE]` section with citations
  - FORBIDDEN: Hedging language ("maybe", "perhaps", "could be")

### Door (LOGOS) - The Architect
- **Mode**: CONVERGENT
- **Goal**: SYNTHESIZE into emergent structure
- **Output Pattern**: `[TENSION] → [PATTERN] → [CLARITY]`
- **Validation Rules**:
  - REQUIRED: Synthesis markers ("TENSION", "PATTERN", "STRUCTURE")
  - REQUIRED: Numbered reasoning steps
  - FORBIDDEN: Simple A+B without emergence explanation

## Validation Behavior

The `CognitionValidator` operates as a firewall extension:

```
debate_turn()
  → validate role order      (existing firewall)
  → validate_cognition()     (NEW - behavioral firewall)
  → engine.add_turn()        (existing)
```

### Rejection Response

When validation fails, agents receive structured feedback:

```json
{
  "error": "COGNITION_VIOLATION",
  "role": "Wall",
  "violation": "MISSING_VERDICT_MARKER",
  "hint": "Wall/ETHOS must start with [VERDICT] followed by evidence",
  "retry_allowed": true
}
```

This creates **self-correcting agents** - they learn role behavior through error feedback.

## Emergent Properties

The behavioral firewall creates three emergent benefits:

1. **Self-Correcting Agents**: Error feedback becomes training signal
2. **Observable Cognition Drift**: Rejection counts = measurable compliance metric
3. **Zero-Trust Architecture**: Validates OUTPUT, robust against misconfiguration

## File Structure

```
cognitions/
├── README.md           # This file (architecture documentation)
├── wind-pathos.oct.md  # PATHOS behavioral contract for Wind
├── wall-ethos.oct.md   # ETHOS behavioral contract for Wall
└── door-logos.oct.md   # LOGOS behavioral contract for Door
```

## For HestAI Agents

If your agent already has a `§3::SHANK_OVERLAY` section, the Hall validates your output - no overlay injection needed. Your cognition is proven by your behavior, not claimed by your prompt.

## Key Lesson

> Wall's job is to validate against REAL constraints (physics, logic, security) - not against "it doesn't exist yet". We are engineers. We BUILD things.

This architecture emerged from a Wind/Wall/Door debate where the first attempt failed because Wall blocked on "current code doesn't have X" instead of "X is fundamentally impossible". The reframed debate produced this superior validation-first approach.
