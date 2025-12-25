# Debate Hall Cognitions

This directory contains the **cognition overlays** for the three debate roles. These define the behavioral contracts that shape how agents participate in debates.

## Current Status

| Feature | Status |
|---------|--------|
| Cognition overlay files | ✅ Implemented |
| Speaker identity metadata (`cognition` field) | ✅ Implemented (Issue #4) |
| `CognitionValidator` behavioral firewall | ✅ **Implemented** |
| Turn rejection on cognition violation | ✅ **Implemented** (strict mode) |

**Status**: The cognition validation system is fully operational. The `cognition` field is recorded as audit metadata, AND content is validated against cognition contracts before turn commitment. Validation operates in two modes:

- **Default (non-strict)**: WARN/BLOCK violations return `cognition_warnings`, turn accepted
- **Strict mode**: BLOCK violations raise `ValueError`, turn rejected

## Architecture: Behavioral Firewall

The cognition system uses a **validation-first architecture** - the Hall enforces cognition through OUTPUT validation, not INPUT injection.

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

## Validation Behavior

The `CognitionValidator` operates as a firewall extension:

```
debate_turn()
  → validate role order      (existing firewall)
  → validate_cognition()     (✅ IMPLEMENTED - behavioral firewall)
  → engine.add_turn()        (existing)
```

### Rejection Response

When validation fails, agents receive structured feedback:

**Non-strict mode (default)**:
```json
{
  "thread_id": "test-thread",
  "turn_count": 1,
  "role": "Wind",
  "status": "active",
  "cognition_warnings": [
    "Single conclusion without alternatives detected"
  ]
}
```

**Strict mode** (`strict_cognition=True`):
```python
ValueError: Cognition validation failed:
  - Missing [VERDICT] or VERDICT: in first 200 characters
  - Missing [EVIDENCE] section

Hints:
  - Wall/ETHOS must start with [VERDICT] or VERDICT: followed by clear judgment
  - Wall/ETHOS must provide [EVIDENCE] to support verdict
```

This creates **self-correcting agents** - learning role behavior through error feedback.

## Emergent Properties

The behavioral firewall creates three emergent benefits:

1. **Self-Correcting Agents**: Error feedback becomes training signal
2. **Observable Cognition Drift**: Warning counts = measurable compliance metric
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

If your agent has a `§3::SHANK_OVERLAY` section, you can pass `cognition="PATHOS"` (etc.) to `add_turn()` for validation and audit tracking. Validation is active and will return warnings or reject turns based on `strict_cognition` setting.

## Implementation Status

1. ✅ **Phase 1**: Cognition overlay files + metadata tracking
2. ✅ **Phase 2**: `CognitionValidator` class with deterministic rules (23 tests)
3. ✅ **Phase 3**: Integration into `debate_turn()` with rejection/retry protocol
4. ⏳ **Phase 4**: Metrics and compliance reporting (planned)

## Key Lesson

> Wall's job is to validate against REAL constraints (physics, logic, security) - not against "it doesn't exist yet". We are engineers. We BUILD things.

This architecture emerged from a Wind/Wall/Door debate. The overlay files exist; the enforcement firewall is the next build phase.
