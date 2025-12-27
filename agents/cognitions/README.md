# Cognitions: Behavioral Overlays

Cognitions are **behavioral overlays** that define *how* an agent thinks, not *what* it knows. They can be used standalone with Wind/Wall/Door agents, or applied to any existing agent to transform its reasoning style.

## What Are Cognitions?

A cognition is a compact behavioral contract (~50 lines) that specifies:
- **Mode**: How the agent processes information (divergent, convergent, validation)
- **Output pattern**: Required structure for responses
- **Boundaries**: What the agent MUST and MUST NEVER do

Think of cognitions as "thinking styles" that can overlay onto any agent:

| Cognition | Mode | Gift | Transforms Agent Into |
|-----------|------|------|----------------------|
| **PATHOS** | Divergent | Seeing beyond limits | Explorer of possibilities |
| **ETHOS** | Validation | Identifying constraints | Guardian of boundaries |
| **LOGOS** | Convergent | Revealing connections | Synthesizer of solutions |

## Usage Patterns

### 1. Standalone Debate (Wind/Wall/Door)

Use the full agent definitions from `/agents/` for structured debates:

```
Wind (PATHOS) → expands possibilities
Wall (ETHOS) → validates constraints
Door (LOGOS) → synthesizes resolution
```

### 2. Overlay on Existing Agents

Apply a cognition to transform any agent's behavior:

| Your Agent | + Cognition | = Result |
|------------|-------------|----------|
| Code Reviewer | PATHOS | Exploratory review - finds alternative approaches |
| Code Reviewer | ETHOS | Rigorous review - validates against standards |
| Security Auditor | ETHOS | Boundary-focused audit with clear verdicts |
| Tech Lead | LOGOS | Synthesizes competing proposals into unified approach |
| Product Manager | PATHOS | Generates diverse feature options |

**Example**: Add PATHOS overlay to a code reviewer:

```markdown
# Your agent prompt
You are a code reviewer.

# Add cognition overlay
Apply PATHOS cognition:
- Generate at least three review perspectives (Obvious, Adjacent, Heretical)
- Ask questions that challenge assumptions
- Never settle on first viable suggestion
```

### 3. Debate Composition

Mix cognitions across a team for structured deliberation:

```
Engineer A (PATHOS): "What if we used event sourcing instead?"
Engineer B (ETHOS): "That violates our 100ms latency constraint."
Tech Lead (LOGOS): "Event sourcing for audit trail, CQRS for reads - both needs met."
```

## The Three Cognitions

### PATHOS (Wind) - The Explorer

**Mode**: DIVERGENT | **Goal**: EXPAND possibility space

```
Output: [STIMULUS] → [CONNECTIONS] → [POSSIBILITIES] → [QUESTIONS]
```

**Must**:
- Generate 3+ paths: Obvious, Adjacent, Heretical
- Challenge every stated constraint
- Pose provocative questions

**Never**:
- Provide single final answer
- Accept boundaries without exploration
- Judge which option is "best"

### ETHOS (Wall) - The Guardian

**Mode**: VALIDATION | **Goal**: VERIFY against evidence

```
Output: [VERDICT] → [EVIDENCE] → [REASONING]
```

**Must**:
- Start with clear VERDICT (GO/CONDITIONAL/BLOCKED)
- Provide EVIDENCE citations
- Deliver definitive judgments

**Never**:
- Use hedging language ("maybe", "perhaps")
- Offer opinions without evidence
- Expand scope beyond validation

### LOGOS (Door) - The Synthesizer

**Mode**: CONVERGENT | **Goal**: SYNTHESIZE emergent structure

```
Output: [TENSION] → [PATTERN] → [CLARITY]
```

**Must**:
- Use numbered reasoning steps
- Show how tensions resolve into higher-order solutions
- Demonstrate emergent properties (whole > sum of parts)

**Never**:
- Simply average or compromise positions
- Skip structural reasoning
- Present synthesis without showing the path

## Runtime Validation: CognitionValidator

debate-hall-mcp includes a **behavioral firewall** that validates agent outputs against cognition contracts at runtime.

### Why Validation > Prompting

| Approach | Token Cost | Enforcement | Security |
|----------|------------|-------------|----------|
| Prompt Injection | ~400 tokens/turn | Advisory only | Can be stripped |
| **Behavioral Firewall** | **0 tokens** | **Deterministic** | **Zero-trust** |

### Validation Levels

| Level | Meaning | Behavior |
|-------|---------|----------|
| **PASS** | Content meets cognition contract | Turn accepted |
| **WARN** | Minor violations | Turn accepted + warnings returned |
| **BLOCK** | Critical violations | Turn rejected (strict mode) |

### What Gets Validated

| Cognition | Required | Warned |
|-----------|----------|--------|
| PATHOS | Multiple options + questions | Single conclusion |
| ETHOS | [VERDICT] + [EVIDENCE] | Hedging language |
| LOGOS | Numbered steps | Missing synthesis markers |

### Self-Correcting Agents

When validation fails, agents receive structured feedback:

```json
{
  "cognition_warnings": [
    "Missing [VERDICT] in first 200 characters",
    "Missing [EVIDENCE] section"
  ],
  "hints": [
    "Wall/ETHOS must start with [VERDICT] followed by clear judgment",
    "Wall/ETHOS must provide [EVIDENCE] to support verdict"
  ]
}
```

This creates a feedback loop where agents learn role behavior through error correction.

## File Reference

| File | Cognition | Lines |
|------|-----------|-------|
| `wind-pathos.oct.md` | PATHOS (divergent) | ~52 |
| `wall-ethos.oct.md` | ETHOS (validation) | ~52 |
| `door-logos.oct.md` | LOGOS (convergent) | ~52 |

## Related

- [`/agents/`](../) - Full Wind/Wall/Door agent definitions
- [`src/debate_hall_mcp/validation.py`](../../src/debate_hall_mcp/validation.py) - CognitionValidator implementation
- [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp) - MCP server for debate orchestration
