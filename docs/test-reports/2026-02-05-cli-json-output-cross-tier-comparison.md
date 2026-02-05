# CLI JSON Output: Cross-Tier Quality & Cost Comparison

**Date**: 2026-02-05
**Branch**: debate-hall-refinements
**Purpose**: Determine optimal CLI output format strategy via multi-tier debate + compare GPT-5.2 vs GPT-5.2 Pro for Wall role

---

## Executive Summary

Four debate runs evaluated CLI output format strategy:

| Run | Tier | Wall Model | Cost | Status | Turns | Pattern Name |
|-----|------|------------|------|--------|-------|--------------|
| 1 | **Fast** | GPT-5-Mini | **$0.020** | synthesis | 3 | "Deterministic Polyglot Core" |
| 2 | Standard | GPT-5.2 | $0.35 | stalemate | 6 | "Polymorphic Fidelity" |
| 3 | Premium (orig) | GPT-5.2 Pro | $0.55 | synthesis | 6 | "Stable Core Explicit Projection" |
| 4 | Premium (new) | GPT-5.2 | $0.25 | synthesis | 5 | "Strict Negotiation Layer" |

**Key Finding**: All four tiers converged on the same core insight: **structured data internally, resolution hierarchy for output format**. Fast tier achieved synthesis in just 3 turns at $0.02, demonstrating the lighter models can reach valid architectural conclusions.

---

## Topic Debated

> Should CLI tools provide --json output by default or require explicit flags? Context: Building a CLI tool that outputs structured data. Users include both humans reading terminal output and scripts parsing results. Options: (A) Human-readable default, --json flag for machine output. (B) JSON default, --pretty flag for human output. (C) Auto-detect TTY - pretty for terminal, JSON for pipes. Trade-offs: discoverability, backward compatibility, scripting ergonomics, user expectations from tools like jq, kubectl, gh.

---

## Tier Configurations

| Setting | Fast | Standard | Premium (orig) | Premium (new) |
|---------|------|----------|----------------|---------------|
| max_turns | 6 | 12 | 16 | 16 |
| max_refinement_loops | 0 | 4 | 5 | 5 |
| consensus_required | false | false | **true** | **true** |
| Wind Model | Claude Haiku 4.5 | Claude Sonnet 4.5 | Claude Opus 4.5 | Claude Opus 4.5 |
| **Wall Model** | GPT-5-Mini | GPT-5.2 | **GPT-5.2 Pro** | **GPT-5.2** |
| Door Model | Gemini 3 Flash | Gemini 3 Pro Preview | Gemini 3 Pro Preview | Gemini 3 Pro Preview |

---

## Cost Analysis (OpenRouter Verified)

### Fast Tier - Total: $0.020

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Haiku 4.5 | Wind | 2,352 → 931 | $0.00701 |
| GPT-5-Mini | Wall | 3,092 → 4,315 | $0.0094 |
| Gemini 3 Flash Preview | Door | 4,513 → 561 | $0.00394 |
| **Total** | | | **$0.020** |

---

### Premium (orig) with GPT-5.2 Pro - Total: ~$0.55

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Opus 4.5 | Wind | 3,312 → 1,137 | $0.045 |
| **GPT-5.2 Pro** | **Wall** | 2,814 → 1,826 | **$0.366** |
| Gemini 3 Pro Preview | Door | 4,518 → 3,178 | $0.047 |
| Gemini 3 Pro Preview | Door (refine) | 5,483 → 2,632 | $0.043 |
| Gemini 3 Pro Preview | Door (refine) | 6,415 → 3,097 | $0.050 |
| Claude Opus 4.5 | Consensus | 2,518 → 286 | $0.020 |
| GPT-5.2 Pro | Consensus | 1,154 → 170 | $0.053 |
| **Subtotal** | | | **~$0.55** |

### Premium (new) with GPT-5.2 - Total: ~$0.25

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Opus 4.5 | Wind | 3,320 → 929 | $0.040 |
| **GPT-5.2** | **Wall** | 2,657 → 1,388 | **$0.024** |
| Gemini 3 Pro Preview | Door | 4,123 → 2,778 | $0.042 |
| Gemini 3 Pro Preview | Door (refine) | 5,010 → 2,854 | $0.044 |
| Gemini 3 Pro Preview | Door (refine) | 6,116 → 2,614 | $0.044 |
| Claude Opus 4.5 | Consensus | 2,522 → 298 | $0.020 |
| GPT-5.2 | Consensus (×3) | ~3,471 → ~846 | ~$0.018 |
| **Subtotal** | | | **~$0.25** |

### Standard with GPT-5.2 - Total: ~$0.35

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Sonnet 4.5 | Wind | 4,142 → 3,072 | $0.059 |
| GPT-5.2 | Wall | 6,717 → 3,410 | $0.060 |
| Gemini 3 Pro Preview | Door (×4) | ~44,395 → ~15,787 | ~$0.23 |
| **Subtotal** | | | **~$0.35** |

### Cost Comparison

| Metric | GPT-5.2 Pro (Premium) | GPT-5.2 (Premium) | Difference |
|--------|----------------------|-------------------|------------|
| Wall Cost | $0.366 | $0.024 | **15x cheaper** |
| Total Debate Cost | ~$0.55 | ~$0.25 | **55% cheaper** |
| Consensus Voting | $0.053 per vote | $0.006 per vote | **9x cheaper** |
| Turns to Synthesis | 6 | 5 | 1 fewer |

---

## Synthesis Comparison

### Fast Tier: "Deterministic Polyglot Core"

**Core Position**: Layered Execution Architecture - separate data production from visual presentation

**Key Innovation**:
- Core binary emits **structured data exclusively** (JSON-by-default at engine level)
- "Shell-Aware Shim" handles UI/UX decisions
- Resolution hierarchy: `Flag > Env Var > Config > TTY-Detection`

**Unique Contributions**:
1. **"Silent Script" Contract**: In pipe mode, emit JSON + `X-CLI-Format: json` metadata in stderr
2. **Interactive Guardrails**: TTY → Human view + stderr hint: `(Tip: Use --json for machine-readable output)`
3. **Architectural separation**: Core = 100% structured, Shim = presentation layer

**Wall Constraints** (GPT-5-Mini provided surprisingly comprehensive analysis):
- C1: Determinism for scripts
- C2: Reliable detection limits (isatty fallible)
- C3: Backward compatibility
- C4: Discoverability

---

### Premium (orig) GPT-5.2 Pro: "Stable Core Explicit Projection"

**Core Position**: Format is a Type Signature, not runtime preference.

**Architecture**:
- LAYER 1 (Core): Execute → Result<Struct>, invariant across environments
- LAYER 2 (Dispatch): Explicit flags only (--json, --yaml, --template)
- LAYER 3 (Decoration): TTY controls ANSI only, never structure

**Decision**:
- **REJECT** auto-detection entirely
- **ENFORCE** `--json` as only automation interface
- **MANDATE** Schema Versioning

**Constraint Handling**: Binary - auto-detect is rejected outright.

---

### Premium (new) GPT-5.2: "Strict Negotiation Layer"

**Core Position**: Replace "auto-detection" (guessing) with "context negotiation" (rules).

**Architecture**:
```
PRIORITY_1: Explicit Flag (--format=x) >> OVERRIDES ALL
PRIORITY_2: Control Env (TOOL_OUTPUT=x) >> OVERRIDES CONTEXT
PRIORITY_3: CI Signal (CI=true) >> RELAXES TO JSON
PRIORITY_4: Interactive Proof (isatty(1)) >> RELAXES TO TABLE
DEFAULT: JSON (safe fallback)
```

**Decision**:
- **ACCEPT** context-aware output BUT with strict priority rules
- CI environment detection ranks ABOVE TTY detection
- Explicit flag always wins
- Includes `--show-decision-logic` debug mode

**Constraint Handling**: Nuanced - auto-detect allowed but governed by explicit precedence rules.

---

## Quality Analysis

### Wall Output Comparison

| Aspect | GPT-5.2 Pro | GPT-5.2 |
|--------|-------------|---------|
| **Output Length** | 1,826 tokens | 1,388 tokens |
| **Constraint Catalog** | 4 Hard (C1-C4), 3 Soft (S1-S3) | Similar structure |
| **Evidence Citations** | Extensive (POSIX, Windows, kubectl, gh) | Adequate |
| **Risk Assessment** | HIGH/MEDIUM categorized | Implicit in constraints |
| **Verdict Style** | Binary REJECT of auto-detect | Nuanced CONDITIONAL |
| **Unique Value** | Security focus (AUTHZ mentioned) | Pragmatic middle ground |

### Key Difference in Approach

**GPT-5.2 Pro** took a **purist stance**: "Auto-detect is unreliable, reject it entirely."

**GPT-5.2** took a **pragmatic stance**: "Auto-detect has risks, but explicit precedence rules can make it safe."

The GPT-5.2 synthesis is arguably **more sophisticated** because:
1. It acknowledges the CI environment edge case explicitly
2. It provides a clear priority hierarchy (Flag > Env > CI > TTY)
3. It includes a debug mode for traceability
4. It still reaches consensus despite being less absolutist

---

## Architectural Divergence

| Aspect | GPT-5.2 Pro Solution | GPT-5.2 Solution |
|--------|---------------------|------------------|
| **TTY Detection** | ANSI decoration only | Allowed for format IF no CI signal |
| **CI Handling** | Implicit (scripts use --json) | Explicit (CI=true → JSON) |
| **Default** | Human readable | JSON (in non-interactive) |
| **Escape Hatch** | None needed (explicit only) | `--show-decision-logic` |
| **Philosophy** | "Contract over inference" | "Deterministic magic" |

---

## Verdict: Is GPT-5.2 Pro Worth 15x the Cost?

### Arguments FOR GPT-5.2 Pro

1. **Security consciousness**: Explicitly mentioned AUTHZ data leak risks
2. **Exhaustive constraint catalog**: More thorough enumeration
3. **Simpler architecture**: Binary rejection avoids edge case complexity
4. **Matches industry standard**: kubectl pattern (explicit --output=json)

### Arguments AGAINST GPT-5.2 Pro (for this use case)

1. **Cost**: 15x more expensive for Wall role alone
2. **Less nuanced**: Binary rejection vs pragmatic middle ground
3. **GPT-5.2 reached consensus faster**: 5 turns vs 6 turns
4. **The "better" answer depends on context**: For debate-hall-mcp's own CLI, the negotiation pattern may be more user-friendly

### Recommendation

**For high-gravity security decisions**: GPT-5.2 Pro justified (explicit security focus)

**For architectural/UX decisions**: GPT-5.2 is sufficient and more cost-effective

**For this specific question**: GPT-5.2's "Strict Negotiation Layer" is arguably the better solution because it:
- Addresses the CI environment edge case explicitly
- Provides deterministic rules while preserving UX convenience
- Costs 55% less overall

---

## Artifacts

- Fast Thread: `2026-02-05-cli-json-fast`
- Standard Thread: `2026-02-04-cli-json-standard`
- Premium (orig) Thread: `2026-02-04-cli-json-premium`
- Premium (new) Thread: `2026-02-05-cli-json-premium-gpt52`

---

## Cross-Tier Convergence

All four tiers independently arrived at the **same core architectural insight**:

> "Internally, always work with structured data. Output format is a presentation concern, governed by a resolution hierarchy."

**Common Agreements**:
1. **Priority hierarchy**: Flag > Env > (CI/TTY) > Default
2. **Structured core**: Internal data model should be typed
3. **Stream hygiene**: stdout = data, stderr = diagnostics
4. **Schema versioning**: JSON output should have stability contracts

**Unique Contributions by Tier**:

| Tier | Cost | Unique Insight |
|------|------|----------------|
| Fast | $0.02 | stderr hint for discoverability |
| Standard | $0.35 | "Polymorphic Fidelity" framing |
| Premium (Pro) | $0.55 | 3-layer architecture (Core/Dispatch/Decoration) |
| Premium (5.2) | $0.25 | CI detection in hierarchy + debug mode |

---

## Conclusions

1. **All four tiers converged** on the same core insight despite different models and costs
2. **Fast tier achieved valid synthesis** in 3 turns at $0.02 - proving lighter models can reach architectural conclusions
3. **GPT-5.2 is a viable replacement for GPT-5.2 Pro** with 55% cost savings and comparable quality
4. **The optimal solution is a hybrid**: Premium (Pro)'s 3-layer architecture + Premium (5.2)'s CI detection + Fast's stderr hint
5. **Resolution hierarchy**: Flag > Env > CI > TTY > Default is the consensus pattern
6. **Total cost for full comparison**: ~$1.17 across all four runs
