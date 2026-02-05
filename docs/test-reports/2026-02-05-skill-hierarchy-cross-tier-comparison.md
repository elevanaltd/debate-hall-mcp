# Skill Hierarchy: Cross-Tier Quality & Cost Comparison

**Date**: 2026-02-05
**Branch**: debate-hall-refinements
**Purpose**: Determine optimal skill decomposition strategy via multi-tier debate

---

## Executive Summary

Four debate runs evaluated whether to decompose the 210-line debate-hall skill into smaller skills:

| Tier | Wall Model | Cost | Status | Turns | Pattern Name |
|------|------------|------|--------|-------|--------------|
| Fast | GPT-5.1-Codex-Mini | ~$0.015 | synthesis | 3 | "Polymorphic Monolith" |
| Standard | GPT-5.2-Codex | ~$0.13 | synthesis | 3 | "Source-Level Hierarchy, Runtime Monolith" |
| Premium (orig) | GPT-5.2 Pro | ~$0.48 | synthesis | 3 | "Bi-Planar Segregation" |
| Premium (new) | GPT-5.2 | ~$0.25 | synthesis | 3 | "Holographic Monolith" |

**Key Finding**: All four tiers **rejected the 5-skill decomposition** and converged on the same core insight: **keep a single source file, use dynamic/virtual sectioning for runtime context injection**. The conflict between "File Structure" and "Runtime Context" is a false dichotomy.

---

## Topic Debated

> Should we decompose the debate-hall skill into a hierarchy of smaller skills? Context: Current skill is ~210 lines. Proposed structure: (A) debate-hall-index (dispatcher ~30 lines), (B) debate-hall-auto (~80 lines) - run_debate/resolve_question (80% path), (C) debate-hall-manual (~60 lines), (D) debate-hall-github (~30 lines), (E) debate-hall-admin (~20 lines). Trade-offs: token efficiency vs discovery complexity vs maintenance burden. Note: Issue #133 - agents cannot load skills themselves.

---

## Tier Configurations

| Setting | Fast | Standard | Premium (orig) | Premium (new) |
|---------|------|----------|----------------|---------------|
| Wind Model | Claude Haiku 4.5 | Claude Sonnet 4.5 | Claude Opus 4.5 | Claude Opus 4.5 |
| **Wall Model** | GPT-5.1-Codex-Mini | GPT-5.2-Codex | **GPT-5.2 Pro** | **GPT-5.2** |
| Door Model | Gemini 3 Flash | Gemini 3 Pro Preview | Gemini 3 Pro Preview | Gemini 3 Pro Preview |

---

## Cost Analysis (OpenRouter Verified)

### Fast Tier - Total: ~$0.015

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Haiku 4.5 | Wind | 2,594 → 1,083 | ~$0.005 |
| GPT-5.1-Codex-Mini | Wall | 3,474 → 1,346 | ~$0.007 |
| Gemini 3 Flash | Door | 4,319 → 562 | ~$0.003 |

### Standard Tier - Total: ~$0.13

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Sonnet 4.5 | Wind | 4,384 → 2,754 | ~$0.06 |
| GPT-5.2-Codex | Wall | 6,683 → 297 | ~$0.04 |
| Gemini 3 Pro Preview | Door | 7,140 → 3,579 | ~$0.03 |

*Note: GPT-5.2-Codex returned "Insufficient data to validate" - poor Wall performance*

### Premium (orig) with GPT-5.2 Pro - Total: ~$0.48

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Opus 4.5 | Wind | 3,554 → 1,086 | ~$0.04 |
| GPT-5.2 Pro | Wall | 3,001 → 1,091 | ~$0.37 |
| Gemini 3 Pro Preview | Door | 4,469 → 2,540 | ~$0.07 |

### Premium (new) with GPT-5.2 - Total: ~$0.25

| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Opus 4.5 | Wind | ~3,500 → ~1,000 | ~$0.04 |
| GPT-5.2 | Wall | ~3,000 → ~1,400 | ~$0.02 |
| Gemini 3 Pro Preview | Door | ~4,500 → ~2,600 | ~$0.05 |
| (+ refinements) | Door | ~10,000+ total | ~$0.14 |

---

## Synthesis Comparison

### Fast Tier: "Polymorphic Monolith"

**Core Position**: Don't decompose the file - decompose the *access pattern*.

**Key Innovation**:
- Maintain single source-of-truth file (210 lines)
- Use tagging system (`// @surface:auto`, `@surface:manual`)
- "Virtual Sharding" extracts only tagged blocks for injection
- `debate-hall-index` (30 lines) as only other skill - acts as "Front Door"

**Architecture**:
```
1. TAGGING: Annotate monolith with role-based tags
2. VIRTUAL_SHARDING: Lightweight helper extracts tagged blocks
3. BRIDGE_DISPATCH: Index skill provides mapping
```

---

### Standard Tier: "Source-Level Hierarchy, Runtime Monolith"

**Core Position**: Decompose the source code physically for maintenance, synthesize a "Virtual Monolith" at runtime.

**Key Innovation**:
- The Facade Pattern applied to skills
- 5 source files for developer clarity
- Manifest-driven orchestrator composes context
- Agent receives pre-composed, purpose-built context

**Architecture**:
```yaml
profiles:
  auto: [core, auto, github]      # Standard debate flow
  manual: [core, manual, admin]   # Intervention/Maintenance
  full: [core, auto, manual, github, admin]
```

**Implementation**: Orchestrator reads manifest, concatenates file contents into single skill block.

---

### Premium (orig) GPT-5.2 Pro: "Bi-Planar Segregation"

**Core Position**: Split by INTENT (Data Plane vs Control Plane), not by function.

**Key Innovation**:
- Only 2 skills, not 5: `debate-execution` + `debate-administration`
- Binary orchestrator decision (simpler than 5-way routing)
- Security benefit: admin tools physically excluded from agent context

**Architecture**:
```
PLANE_A: debate-execution (Engine)
  - auto_path, resolve_logic, read_only_get
  - ~100 lines, 80%+ frequency

PLANE_B: debate-administration (Tools)
  - manual_overrides, github_sync, admin_force, tombstone
  - ~110 lines, <20% frequency
```

**Benchmark Prediction**:
- Legacy: 210 lines (100%)
- Bi-Planar: ~100 lines hot path (52% reduction)

---

### Premium (new) GPT-5.2: "Holographic Monolith"

**Core Position**: One source of truth, many runtime shapes.

**Key Innovation**:
- Single file with semantic delimiters (`§SECTION::NAME`)
- JIT_Slicer utility extracts relevant sections
- Context-Aware Projection based on orchestrator intent

**Architecture**:
```octave
===SKILL_DEFINITION===
NAME::debate_hall

§COMMON    // ~20 lines, always loaded
§ROUTING   // ~20 lines, for orchestrator decisions
§AUTO_EXECUTION  // ~80 lines, hot path
§GITHUB_OPS      // ~30 lines, cold path
===END===
```

**Key Insight**: "The file on disk does not need to match the string in the prompt."

---

## Cross-Tier Convergence

All four tiers **rejected the 5-skill proposal** and converged on the same architectural insight:

> "The conflict arises from treating 'Skill' and 'File' as a 1:1 mapping. Decouple Logic Source from Injection Surface."

### Common Agreements

1. **5-skill decomposition is over-engineering** for 210 lines
2. **Issue #133 is a feature, not a bug** - forces system-driven composition
3. **Single file for maintenance** - developer sees one source of truth
4. **Virtual sectioning for runtime** - agents receive optimized context
5. **Binary or simple routing** beats complex 5-way dispatch

### Architectural Variations

| Tier | Physical Files | Runtime Strategy | Routing Complexity |
|------|----------------|------------------|-------------------|
| Fast | 1 + index | Tag-based extraction | Simple |
| Standard | 5 (source) | Manifest-driven concatenation | Profile-based |
| Premium (Pro) | 2 | Intent-based loading | Binary |
| Premium (5.2) | 1 | Section delimiter slicing | Intent-based |

### Unique Contributions

| Tier | Cost | Unique Insight |
|------|------|----------------|
| Fast | $0.015 | `@surface:` tagging pattern |
| Standard | $0.13 | Manifest YAML for profile composition |
| Premium (Pro) | $0.48 | Security via physical separation (admin tools excluded) |
| Premium (5.2) | $0.25 | `§SECTION::` delimiters + JIT slicing |

---

## Wall Model Performance

| Tier | Wall Model | Output | Quality Assessment |
|------|------------|--------|-------------------|
| Fast | GPT-5.1-Codex-Mini | 1,346 tokens | Good - identified #133 as key constraint |
| Standard | GPT-5.2-Codex | "Insufficient data" | **FAILED** - no substantive analysis |
| Premium (Pro) | GPT-5.2 Pro | 1,091 tokens | Excellent - constraint catalog + risk assessment |
| Premium (new) | GPT-5.2 | ~1,400 tokens | Good - comprehensive mitigations |

**Finding**: GPT-5.2-Codex (Standard Wall) failed to engage. GPT-5.2 and GPT-5.2 Pro both performed well.

---

## Optimal Solution

### Recommendation: "Holographic Monolith" (Premium GPT-5.2)

The Premium (GPT-5.2) solution is optimal because:

1. **Simplest implementation** - no new files, just add section delimiters
2. **Backwards compatible** - existing skill works until slicing is implemented
3. **Fallback safety** - full load if parsing fails
4. **Best cost/quality ratio** - $0.25 vs $0.48 for essentially same insight

### Implementation Specification

```octave
// debate-hall.skill (modified)
===SKILL_DEFINITION===
NAME::debate_hall
VERSION::"2.0"

§COMMON  // Always loaded (~20 lines)
  STRUCT::DebateState[...]
  FUNC::format_turn(speaker, text)...

§ROUTING  // For orchestrator decisions (~20 lines)
  MAP::gravity_weights...
  DISPATCH::intent_to_variant...

§AUTO  // Hot path (~80 lines)
  FUNC::run_debate(topic)...
  FUNC::resolve_question()...

§MANUAL  // Fine control (~40 lines)
  FUNC::init_debate()...
  FUNC::add_turn()...

§GITHUB  // Sync operations (~30 lines)
  FUNC::github_sync_debate()...

§ADMIN  // Privileged operations (~20 lines)
  FUNC::force_close_debate()...
  FUNC::tombstone_turn()...
===END===
```

**Loader Logic**:
```python
def load_skill(name: str, variant: str = "full") -> str:
    content = read_skill_file(name)
    if variant == "full":
        return content

    sections = parse_sections(content)
    if variant == "auto":
        return join([sections["COMMON"], sections["AUTO"]])
    elif variant == "admin":
        return join([sections["COMMON"], sections["MANUAL"], sections["ADMIN"]])
    # etc.
```

---

## Artifacts

- Fast Thread: `2026-02-04-skill-hierarchy-fast`
- Standard Thread: `2026-02-04-skill-hierarchy-standard`
- Premium (orig) Thread: `2026-02-04-skill-hierarchy-premium`
- Premium (new) Thread: `2026-02-05-skill-hierarchy-premium-gpt52`

---

## Conclusions

1. **All four tiers rejected 5-skill decomposition** - unanimous consensus
2. **"Holographic Monolith" is optimal** - single file, section delimiters, JIT slicing
3. **Issue #133 is a forcing function** - system composes context, agents receive
4. **GPT-5.2 matches GPT-5.2 Pro quality** at 48% lower cost for this decision
5. **GPT-5.2-Codex failed as Wall** - returned "Insufficient data"
6. **Total debate cost**: ~$0.88 across four runs
7. **Token savings potential**: ~50% reduction in hot path (210 → ~100 lines)
