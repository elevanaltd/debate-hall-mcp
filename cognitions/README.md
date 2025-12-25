# Debate Hall Cognitions

This directory contains the **cognition overlays** for the three debate roles. These define the behavioral contracts that shape how agents participate in debates.

## Current Status

| Feature | Status |
|---------|--------|
| Cognition overlay files | ✅ Implemented |
| Speaker identity metadata (`cognition` field) | ✅ Implemented (Issue #4) |
| `CognitionValidator` behavioral firewall | ⏳ **Planned** |
| Turn rejection on cognition violation | ⏳ **Planned** |

**Currently**: The `cognition` field is recorded as audit metadata on each turn, but content is NOT validated against cognition contracts. Turns are accepted regardless of whether they follow their role's behavioral pattern.

## Target Architecture: Behavioral Firewall

> **This section describes PLANNED architecture, not current behavior.**

The cognition system will use a **validation-first architecture** - the Hall enforces cognition through OUTPUT validation, not INPUT injection.

> **Core Insight**: Cognition integration = Validation layer extension, NOT prompt distribution system

### Why Validation > Prompting

| Approach | Token Cost | Enforcement | Security |
|----------|------------|-------------|----------|
| Prompt Injection | ~400 tokens/turn | None (advisory) | Weak (can be stripped) |
| **Behavioral Firewall** | **0 tokens** | **Deterministic** | **Zero-trust** |

**Projected token savings**: 4,800 tokens per 12-turn debate.

## The Three Cognitions

### Wind (PATHOS) - The Explorer
- **Mode**: DIVERGENT
- **Goal**: EXPAND possibility space
- **Output Pattern**: `[STIMULUS] → [CONNECTIONS] → [POSSIBILITIES] → [QUESTIONS]`
- **Validation Rules** (planned):
  - REQUIRED: Multiple options (detect numbered lists or bullets)
  - REQUIRED: Question marks (exploration signal)
  - FORBIDDEN: Single conclusion without alternatives

### Wall (ETHOS) - The Guardian
- **Mode**: VALIDATION
- **Goal**: VERIFY against evidence
- **Output Pattern**: `[VERDICT] → [EVIDENCE] → [REASONING]`
- **Validation Rules** (planned):
  - REQUIRED: `[VERDICT]` or `VERDICT:` in first 200 chars
  - REQUIRED: `[EVIDENCE]` section with citations
  - FORBIDDEN: Hedging language ("maybe", "perhaps", "could be")

### Door (LOGOS) - The Architect
- **Mode**: CONVERGENT
- **Goal**: SYNTHESIZE into emergent structure
- **Output Pattern**: `[TENSION] → [PATTERN] → [CLARITY]`
- **Validation Rules** (planned):
  - REQUIRED: Synthesis markers ("TENSION", "PATTERN", "STRUCTURE")
  - REQUIRED: Numbered reasoning steps
  - FORBIDDEN: Simple A+B without emergence explanation

## Planned: Validation Behavior

When implemented, the `CognitionValidator` will operate as a firewall extension:

```
debate_turn()
  → validate role order      (existing firewall)
  → validate_cognition()     (PLANNED - behavioral firewall)
  → engine.add_turn()        (existing)
```

### Planned: Rejection Response

When validation fails, agents will receive structured feedback:

```json
{
  "error": "COGNITION_VIOLATION",
  "role": "Wall",
  "violation": "MISSING_VERDICT_MARKER",
  "hint": "Wall/ETHOS must start with [VERDICT] followed by evidence",
  "retry_allowed": true
}
```

This will create **self-correcting agents** - learning role behavior through error feedback.

## Planned: Emergent Properties

The behavioral firewall will create three emergent benefits:

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

If your agent has a `§3::SHANK_OVERLAY` section, you can pass `cognition="PATHOS"` (etc.) to `add_turn()` for audit tracking. Currently this is metadata only - validation enforcement is planned.

## Implementation Roadmap

1. **Phase 1** (current): Cognition overlay files + metadata tracking
2. **Phase 2**: `CognitionValidator` class with deterministic rules
3. **Phase 3**: Integration into `debate_turn()` with rejection/retry protocol
4. **Phase 4**: Metrics and compliance reporting

## Key Lesson

> Wall's job is to validate against REAL constraints (physics, logic, security) - not against "it doesn't exist yet". We are engineers. We BUILD things.

This architecture emerged from a Wind/Wall/Door debate. The overlay files exist; the enforcement firewall is the next build phase.
