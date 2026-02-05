# ADR-0005: Skill Hierarchy Architecture ("Router + Focused Skills")

## Status

Accepted (Revised)

## Context

The debate-hall skill is currently ~210 lines (~9KB, ~3000 tokens) covering all functionality. This creates two problems:

1. **Token waste**: Agents loading the skill get ALL content even when they only need `run_debate`
2. **Attention dilution**: Per odyssean-anchor issue #64, larger skill payloads reduce effective attention

A proposal was made to decompose into 5 smaller skills:
1. debate-hall-index (dispatcher, ~30 lines)
2. debate-hall-auto (~80 lines) - run_debate, resolve_question
3. debate-hall-manual (~60 lines) - init/add_turn/get/close
4. debate-hall-github (~30 lines) - sync/ratify_rfc
5. debate-hall-admin (~20 lines) - force_close/tombstone

Four multi-tier debates evaluated this proposal.

## Decision

**Adopt the "Router + Focused Skills" pattern**: Create a small index skill that routes agents to load the appropriate focused skill based on their task.

### Why This Works (Behavioral Insight)

Observational evidence shows:
- **"Read this reference file if needed"** → Agents almost never do
- **"Load /skill-name"** → Agents reliably execute skill invocations

The router skill gives agents explicit, actionable triggers: "When you need X, MUST load Y skill."

### Architecture

```
debate-hall (index/router) - ~30 lines, always loaded
├── "Running automated debates" → MUST load /debate-hall-auto
├── "Manual turn-by-turn control" → MUST load /debate-hall-manual
├── "GitHub sync/ratification" → MUST load /debate-hall-github
└── "Admin operations (force close, tombstone)" → MUST load /debate-hall-admin
```

### Skill Structure

**debate-hall** (index) - ~30 lines
- Gravity mapping (low/medium/high → fast/standard/premium)
- Routing table with explicit MUST load triggers
- Core concept overview (multi-perspective decision support)

**debate-hall-auto** - ~80 lines
- `run_debate`, `resolve_question`, `resume_debate`
- Tier selection guidance
- Output expectations (synthesis, rationale, validation)

**debate-hall-manual** - ~60 lines
- `init_debate`, `add_turn`, `get_debate`, `close_debate`
- Fixed vs mediated mode rules
- Turn ordering constraints

**debate-hall-github** - ~30 lines
- `github_sync_debate`, `ratify_rfc`
- Repo/target_id conventions
- ADR PR workflow

**debate-hall-admin** - ~20 lines
- `force_close_debate`, `tombstone_turn`
- Safety/permissions notes

## Rationale

### What the Debates Got Right

Four tiers unanimously agreed:
1. **Issue #133 only affects agents INSIDE run_debate** - the orchestrating agent CAN load skills
2. **Discovery complexity is solvable** - a router skill provides clear triggers
3. **Token savings are real** - ~80 lines vs ~210 lines for the 80% case

### What the Debates Over-Complicated

The debates proposed "Holographic Monolith" with JIT slicing - infrastructure that doesn't exist. The simpler solution uses existing skill loading mechanics.

### Key Behavioral Insight

Agents don't read reference files. They DO execute skill invocations. The router pattern leverages this behavior rather than fighting it.

### Alignment with odyssean-anchor #64

This approach aligns with the skill sizing guidelines from issue #64:
- **Index skill**: ~30 lines (~100 tokens) - micro skill
- **Focused skills**: ~60-80 lines (~200-300 tokens) - standard skills
- **Total if all loaded**: Still less than current monolith

## Consequences

### Positive

- **~75% token reduction** for 80% case (30 + 80 = 110 lines vs 210)
- **Works with existing infrastructure** - no new loader logic needed
- **Clear mental model** - router tells agent exactly what to load
- **Security benefit** - admin tools in separate skill, not accidentally loaded
- **Maintenance clarity** - each skill has single responsibility

### Negative

- 5 files to maintain instead of 1
- Agents must make one extra skill load (router → specific skill)
- Risk of skills drifting if shared types change

### Mitigations

- Shared types defined in router skill (loaded first)
- CI checks for skill consistency
- Router skill versioned with focused skills

## Implementation

1. Create `debate-hall/SKILL.md` (index/router)
2. Create `debate-hall-auto/SKILL.md`
3. Create `debate-hall-manual/SKILL.md`
4. Create `debate-hall-github/SKILL.md`
5. Create `debate-hall-admin/SKILL.md`
6. Deprecate old monolithic skill (keep for transition period)
7. Update documentation to reference new skill structure

## References

- Debate threads: `2026-02-04-skill-hierarchy-{fast,standard,premium}`, `2026-02-05-skill-hierarchy-premium-gpt52`
- odyssean-anchor issue #64: Skills auto-loading and sizing guidelines
- Cross-tier comparison: `docs/test-reports/2026-02-05-skill-hierarchy-cross-tier-comparison.md`
- GitHub Issue #145: Implementation tracking
