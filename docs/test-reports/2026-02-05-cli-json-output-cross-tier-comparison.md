# CLI JSON Output: Cross-Tier Quality & Cost Comparison

**Date**: 2026-02-05
**Branch**: debate-hall-refinements
**Purpose**: Determine optimal CLI output format strategy via multi-tier debate

---

## Executive Summary

Two debate tiers evaluated whether CLI tools should provide JSON output by default or require explicit flags:

| Tier | Cost | Consensus | Status | Pattern Name | Key Insight |
|------|------|-----------|--------|--------------|-------------|
| **Standard** | ~$0.35 | No | stalemate | "Responsive Data Signal" | Output is Polymorphic Fidelity (TTY=Table, Pipe=JSON) |
| **Premium** | ~$0.55 | Yes | synthesis | "Stable Core Explicit Projection" | Format is Type Signature, not runtime preference |

**Key Finding**: Premium tier provides the more rigorous specification with explicit constraint mapping and deterministic layer separation.

---

## Topic Debated

> Should CLI tools provide --json output by default or require explicit flags? Context: Building a CLI tool that outputs structured data. Users include both humans reading terminal output and scripts parsing results. Options: (A) Human-readable default, --json flag for machine output. (B) JSON default, --pretty flag for human output. (C) Auto-detect TTY - pretty for terminal, JSON for pipes. Trade-offs: discoverability, backward compatibility, scripting ergonomics, user expectations from tools like jq, kubectl, gh.

---

## Tier Configurations

| Setting | Standard | Premium |
|---------|----------|---------|
| max_turns | 12 | 16 |
| max_refinement_loops | 4 | 5 |
| consensus_required | false | **true** |
| Wind Model | Claude Sonnet 4.5 | Claude Opus 4.5 |
| Wall Model | GPT-5.2 | GPT-5.2 Pro |
| Door Model | Gemini 3 Pro Preview | Gemini 3 Pro Preview |
| Wind Agent | ideator | edge-optimizer |
| Wall Agent | validator | critical-engineer |
| Door Agent | synthesizer | technical-architect |

---

## Synthesis Comparison

### Standard Tier: "Responsive Data Signal" / "Polymorphic Fidelity"

**Status**: Stalemate (Wall blocked on missing evidence)
**Turns**: 6

**Core Insight**: The CLI is a "Responsive Data Signal" - it detects the "Viewport" (TTY vs Pipe) and renders the highest fidelity format for that viewport.

**Key Innovation**:
- **Paradigm Shift**: "Human Default vs JSON Default" debate is obsolete
- The "Default" comes from the *Environment*, not the *Tool*
- Pattern from Web Design: "Responsive Interface"

**Resolution**:
```
IF flag_specified: RENDER(flag_format)
ELSE IF isatty(stdout): RENDER(Human_Table)
ELSE: RENDER(JSON_Lines)
```

**Safety Valve**:
- Standard flags: `--json`, `--table` (or `--format=...`)
- Env Var: `[TOOL]_NO_ADAPT=1` to disable magic for strict CI

**Unique Contribution**: "Contextual Determinism" - behavior is strictly `f(isatty)`, providing ergonomics of magic with predictability of physics.

---

### Premium Tier: "Stable Core Explicit Projection"

**Status**: Synthesis with Consensus
**Turns**: 6

**Core Insight**: The conflict arises from treating "Format" as a runtime preference. Architecture requires treating "Format" as a **Type Signature**.

**Key Innovation**:
- **Separation of Concerns**: Content (Data) vs Presentation (View)
- **Explicit Dispatch** over runtime inference
- **Three-Layer Architecture**:

**System Model**:
```
LAYER_1[CORE]:
  LOGIC: Execute_Command → Result<Struct>
  INVARIANT: "Data structure identical regardless of environment"

LAYER_2[DISPATCH]:
  INPUT: Result<Struct> + Config
  LOGIC:
    CASE explicit_flag?
      --json → RENDER::Serializer(JSON)
      --yaml → RENDER::Serializer(YAML)
      --template=X → RENDER::Template(X)
    CASE default
      → RENDER::Human_View(Struct)

LAYER_3[DECORATION]:
  SCOPE: "Human_View ONLY"
  LOGIC: isatty(stdout) ? Apply_ANSI : Strip_ANSI
  CONSTRAINT: "Zero structural changes allowed based on isatty"
```

**Constraint Mapping**:

| Constraint | Risk | Mitigation | Proof |
|------------|------|------------|-------|
| C1 TTY_Reliability | "Auto-detect creates Heisenbugs in CI" | TTY checks restricted to Layer 3 (Decoration only) | Hash(Output_Pipe) == Hash(Output_File) (excluding ANSI) |
| C2 Stdout_API | "Default output breaks consumers" | Default is Human (non-API). JSON is opt-in (Strict API) | Scripts must use --json. Parsing default is unsupported |
| C3 Dual_Stream | "Stderr pollution breaks wrappers" | Dual-stream REJECTED. Stderr reserved for OOB errors only | - |
| C4 Schema_Stability | "Internal changes break structured output" | Internal Structs versioned. JSON follows SemVer. Human output advisory | - |

**Implementation Steps**:
1. DEFINE `PublicAPI_Struct` (The JSON contract)
2. BUILD `HumanPresenter` (Consumes PublicAPI_Struct, emits text)
3. WIRE `Main()`: Default → HumanPresenter, Flag(--json) → json.Marshal
4. TEST CI_Matrix:
   - Assert `cmd | jq` fails (unless --json used)
   - Assert `cmd > file` contains same text as `cmd`

**Verdict**: ADOPT_EXPLICIT_PROJECTION_MODEL
- **REJECT** formatting auto-detection (preserves Wall C1)
- **ADOPT** Human Default for discoverability (preserves Wind UX)
- **ENFORCE** `--json` as the only supported automation interface
- **MANDATE** Schema Versioning for the JSON projection

---

## Architectural Divergence

Unlike previous debates (Feature Flags, Decision Search), these two tiers reached **different conclusions**:

| Aspect | Standard | Premium |
|--------|----------|---------|
| **Auto-detect TTY?** | Yes (core feature) | **No** (restricted to ANSI decoration only) |
| **Default output format** | Depends on context | **Always human-readable** |
| **JSON activation** | Automatic when piped | **Explicit flag required** |
| **Philosophy** | "Magic that works" | "Contract over inference" |

**Premium tier's key distinction**: TTY detection is allowed **only for cosmetic changes** (ANSI colors), not structural changes. The data format remains constant.

---

## Quality Analysis

### Wall Agent Comparison

| Metric | Standard (validator/GPT-5.2) | Premium (critical-engineer/GPT-5.2 Pro) |
|--------|------------------------------|----------------------------------------|
| Verdict | Blocked on missing evidence | **CONDITIONAL** (with explicit gates) |
| Hard Constraints | Implicit | **4 explicit (C1-C4)** |
| Risk Assessment | Narrative | **Structured** |
| Mitigations | Implicit | **Proof-based** |
| Layer Separation | Not specified | **3-layer architecture mandated** |

**Key Observation**: GPT-5.2 Pro provided significantly more structured constraint analysis with explicit proof requirements. GPT-5.2 engaged but didn't force explicit constraint mapping.

---

## Cost Analysis

### Per-Tier Breakdown (Estimated)

**Standard Tier** (~$0.35 total):
| Model | Role | Cost (est.) |
|-------|------|-------------|
| Claude Sonnet 4.5 | Wind | ~$0.04 |
| GPT-5.2 | Wall | ~$0.05 |
| Gemini 3 Pro Preview | Door | ~$0.26 |

**Premium Tier** (~$0.55 total):
| Model | Role | Cost (est.) |
|-------|------|-------------|
| Claude Opus 4.5 | Wind | ~$0.06 |
| GPT-5.2 Pro | Wall | ~$0.32 |
| Gemini 3 Pro Preview | Door | ~$0.17 |

### Cost Summary

| Tier | Cost | Turns | Status | Consensus |
|------|------|-------|--------|-----------|
| Standard | ~$0.35 | 6 | stalemate | No |
| Premium | ~$0.55 | 6 | synthesis | Yes |
| **Total** | **~$0.90** | 12 | **1/2 synthesis** | - |

**Note**: Costs are estimates based on typical token usage patterns. OpenRouter verification pending.

---

## Optimal Solution

### Recommendation: Premium Tier's "Explicit Projection Model"

The Premium tier solution is recommended because:

1. **Deterministic**: No Heisenbugs from TTY detection affecting data format
2. **Contract-based**: JSON output is a versioned API contract
3. **Testable**: Clear pass/fail criteria (`cmd | jq` should fail without `--json`)
4. **Industry-aligned**: Matches `kubectl` pattern (human default, `--output=json` for automation)

While Standard tier's "auto-detect" pattern is elegant and matches `gh` CLI behavior, the Premium tier's constraint analysis revealed the architectural risk: TTY detection is unreliable in CI environments and creates debugging nightmares.

### Implementation Path

1. **Define Public API Struct**: Version the JSON contract separately from human output
2. **Human Default**: Pretty tables/text for terminal users
3. **Explicit Flag**: `--json` (or `--output=json`) for automation
4. **ANSI Detection Only**: `isatty()` controls colors, not data format
5. **Test Matrix**: CI tests that `cmd | jq` fails and `cmd --json | jq` passes

---

## Artifacts

- Standard Thread: `2026-02-04-cli-json-standard`
- Premium Thread: `2026-02-04-cli-json-premium`

---

## Conclusions

1. **Premium and Standard reached different conclusions**: Rare case of tier divergence
2. **Premium's constraint analysis was decisive**: TTY detection for format = Heisenbugs
3. **Contract over magic**: Explicit `--json` flag is more reliable than auto-detection
4. **ANSI-only TTY detection**: The safe middle ground
5. **GPT-5.2 Pro justified here**: Structured constraint mapping changed the decision
6. **Total debate cost**: ~$0.90 for architectural clarity
