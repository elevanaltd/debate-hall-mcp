# ADR-0005: Skill Hierarchy Architecture ("Holographic Monolith")

## Status

Accepted

## Context

The debate-hall skill is currently ~210 lines covering all functionality. A proposal was made to decompose it into 5 smaller skills:
1. debate-hall-index (dispatcher, ~30 lines)
2. debate-hall-auto (~80 lines) - run_debate, resolve_question
3. debate-hall-manual (~60 lines) - init/add_turn/get/close
4. debate-hall-github (~30 lines) - sync/ratify_rfc
5. debate-hall-admin (~20 lines) - force_close/tombstone

Trade-offs considered:
- Token efficiency (smaller skills loaded on demand)
- Discovery complexity (5 skills to find vs 1)
- Maintenance burden (5 files vs 1)
- Agent cognitive load (partial context vs complete context)

**Critical constraint**: Issue #133 - agents in run_debate cannot load skills themselves; skill content must be injected via prompts.

## Decision

**Adopt the "Holographic Monolith" pattern**: Maintain a single source file with semantic section delimiters, enabling JIT (just-in-time) slicing to inject only relevant sections based on orchestrator intent.

### Architecture

```octave
===SKILL_DEFINITION===
NAME::debate_hall
VERSION::"2.0"

§COMMON  // Always loaded (~20 lines)
§ROUTING // Orchestrator decisions (~20 lines)
§AUTO    // Hot path (~80 lines)
§MANUAL  // Fine control (~40 lines)
§GITHUB  // Sync operations (~30 lines)
§ADMIN   // Privileged operations (~20 lines)
===END===
```

### Loader Logic

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
```

## Rationale

Four multi-tier debates (fast, standard, premium×2) unanimously rejected the 5-skill decomposition and converged on the same insight:

> "The conflict arises from treating 'Skill' and 'File' as a 1:1 mapping. Decouple Logic Source from Injection Surface."

### Why Not 5 Skills?

1. **Over-engineering** - 210 lines doesn't justify 5-file coordination overhead
2. **Discovery tax** - Agents/users must find the right skill among 5
3. **Routing complexity** - 5-way dispatch logic exceeds token savings
4. **Issue #133 constraint** - Agents can't load skills anyway; system must inject

### Why Holographic Monolith?

1. **Single source of truth** - Developer maintains one file
2. **Virtual sectioning** - Runtime context is optimized per use case
3. **Backwards compatible** - Existing skill works until slicing implemented
4. **Fallback safety** - Full load if parsing fails
5. **Security benefit** - Admin functions can be excluded from agent context
6. **~50% token reduction** in hot path (210 → ~100 lines)

### Key Insight from Debates

Issue #133 ("agents cannot load skills") is a **forcing function, not a blocker**. It establishes that the **system** composes context, agents receive. This pattern:
- Works today (prompt injection)
- Scales to `context_files` parameter (future)
- Enables capability-based loading without agent navigation

## Consequences

### Positive

- Token savings ~50% on hot path without file sprawl
- Simplified maintenance (1 file vs 5)
- Binary orchestrator decision (auto vs admin) vs complex routing
- Security: privileged tools can be excluded from standard agents
- Future-proof: section delimiters enable fine-grained evolution

### Negative

- Requires implementing section delimiter parser
- Requires orchestrator changes to pass `variant` parameter
- Initial complexity in slicing logic (mitigated by fallback to full load)

### Neutral

- No immediate change to existing behavior (additive feature)
- Manifest/profile system can be added later if needed

## Implementation

1. Add `§SECTION::` delimiters to existing skill file
2. Implement `SkillLoader.load(name, variant)` with section extraction
3. Update orchestrator to pass `variant='auto'` for run_debate calls
4. Add tests verifying section isolation (no admin in auto variant)
5. Add fallback test (variant=null returns full content)

## References

- Debate threads: `2026-02-04-skill-hierarchy-{fast,standard,premium}`, `2026-02-05-skill-hierarchy-premium-gpt52`
- Issue #133: Agent skill loading constraint
- Cross-tier comparison: `docs/test-reports/2026-02-05-skill-hierarchy-cross-tier-comparison.md`
