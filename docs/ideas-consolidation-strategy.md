# Ideas Consolidation Strategy

**Date**: 2026-01-10
**Context**: Two project-ideas documents growing independently

## Current State

### Document 1: HestAI-MCP Ideas
**Location**: `/Volumes/HestAI-MCP/worktrees/context-steward-benefits/.hestai/context/project-ideas.oct.md`

**Scope**: Cross-cutting HestAI ecosystem concepts
- Context Consistency Checker
- Decision Gravity Framework
- RACI Dialogue Mode (duplicate)
- Integrity Engine Pivot (system-level)
- Odyssean Anchor
- HestAI-MCP Secretary

**Audience**: System architects, HestAI ecosystem builders

### Document 2: Debate Hall Ideas
**Location**: `/Volumes/HestAI-Projects/debate-hall-mcp/worktrees/token-usage/.hestai/context/project-ideas.oct.md`

**Scope**: Debate Hall specific features
- RACI Dialogue Mode (validated)
- Decision Gravity Integration (validated)
- Integrity Engine (validated, separate project decision)
- Context Compiler Integration (validated)

**Audience**: Debate Hall contributors, governance teams

## Analysis

### Overlap Detection

**1. RACI Dialogue Mode**
- ❌ **Duplicated** in both documents
- HestAI-MCP version: Conceptual
- Debate Hall version: Empirically validated (550 tokens)
- **Decision**: Debate Hall owns implementation, HestAI-MCP references

**2. Decision Gravity**
- ⚠️ **Overlapping** but different scopes
- HestAI-MCP: System-wide routing framework
- Debate Hall: Integration as routing destination
- **Decision**: Both keep, cross-reference

**3. Integrity Engine**
- ⚠️ **Different perspectives**
- HestAI-MCP: "Pivot" (Intent vs Reality framework)
- Debate Hall: Emergency bypass approval system
- **Decision**: Split ownership (system vs implementation)

### What's Unique to Each?

**HestAI-MCP Only**:
- Context Consistency Checker
- Odyssean Anchor access control
- HestAI Secretary document routing
- System-level architecture concepts

**Debate Hall Only**:
- RACI implementation details
- Context Compiler (OCTAVE export)
- Token usage metrics
- Empirical validation data

---

## Three Options

### Option 1: Separate Project-Specific Docs ✅ RECOMMENDED

**Structure**:
```
/Volumes/HestAI-MCP/
└── .hestai/context/
    └── project-ideas.oct.md        (HestAI system ideas)

/Volumes/HestAI-Projects/debate-hall-mcp/
└── .hestai/context/
    └── project-ideas.oct.md        (Debate Hall features)

/Volumes/HestAI-Projects/integrity-engine-mcp/  (future)
└── .hestai/context/
    └── project-ideas.oct.md        (Integrity Engine features)
```

**Pros**:
- ✅ Clear ownership (each project owns its ideas)
- ✅ Focused scope (contributors see relevant ideas)
- ✅ Independent evolution (projects can pivot)
- ✅ Distributed governance (no central bottleneck)

**Cons**:
- ⚠️ Requires cross-referencing for overlaps
- ⚠️ Risk of divergence without coordination

**Best for**: Open source projects with independent roadmaps

---

### Option 2: Consolidated Top-Level Doc

**Structure**:
```
/Volumes/HestAI-Projects/
└── project-ideas.oct.md            (All HestAI ideas)

Projects reference this central doc
```

**Pros**:
- ✅ Single source of truth
- ✅ No duplication
- ✅ Easier to see big picture

**Cons**:
- ❌ Confusing for external contributors
- ❌ "Whose idea is this?" ownership unclear
- ❌ Single file becomes massive
- ❌ Merge conflicts between teams

**Best for**: Monolithic projects with centralized control

---

### Option 3: Hybrid (Project Docs + System Index)

**Structure**:
```
/Volumes/HestAI-Projects/
└── ideas-index.oct.md              (Registry, not content)

/Volumes/HestAI-MCP/
└── .hestai/context/
    └── project-ideas.oct.md        (System concepts)

/Volumes/HestAI-Projects/debate-hall-mcp/
└── .hestai/context/
    └── project-ideas.oct.md        (Debate Hall features)
```

**ideas-index.oct.md**:
```octave
===IDEAS_REGISTRY===

SYSTEM_IDEAS::
  SOURCE::/Volumes/HestAI-MCP/.hestai/context/project-ideas.oct.md
  SCOPE::Cross-cutting_architecture

DEBATE_HALL_IDEAS::
  SOURCE::/Volumes/HestAI-Projects/debate-hall-mcp/.hestai/context/project-ideas.oct.md
  SCOPE::Governance_deliberation

INTEGRITY_ENGINE_IDEAS::
  SOURCE::/Volumes/HestAI-Projects/integrity-engine-mcp/.hestai/context/project-ideas.oct.md
  SCOPE::Emergency_bypass_approval

===END===
```

**Pros**:
- ✅ Distributed ownership preserved
- ✅ Discoverable via index
- ✅ No content duplication
- ✅ Clear navigation

**Cons**:
- ⚠️ Extra indirection layer
- ⚠️ Index maintenance required

**Best for**: Growing ecosystem with multiple projects

---

## Recommendation: **Option 1 with Cross-References**

### Rationale

**Why separate docs win**:

1. **Open source separation principle**
   - Debate Hall contributors shouldn't care about Odyssean Anchor
   - Integrity Engine contributors shouldn't care about Secretary patterns
   - Each project attracts different audiences

2. **Independent evolution**
   - Debate Hall can pivot without affecting HestAI-MCP roadmap
   - Integrity Engine extraction proves this (separate project)
   - System-level ideas evolve slower than implementation ideas

3. **Clear ownership**
   - Each project owns its roadmap
   - No "whose idea is this?" confusion
   - Maintainers can prioritize independently

4. **Contribution friction**
   - New contributor to Debate Hall sees focused, relevant ideas
   - Not overwhelmed by system-level architecture concepts
   - Easier to understand and contribute

### Implementation

**Maintain separate documents with explicit cross-references**:

**HestAI-MCP project-ideas.oct.md**:
```octave
### Decision Gravity Framework
- **Integration**: See debate-hall-mcp for routing implementation
- **Reference**: /Volumes/HestAI-Projects/debate-hall-mcp/.hestai/context/project-ideas.oct.md
```

**Debate Hall project-ideas.oct.md**:
```octave
### Decision Gravity Integration
- **System Context**: See HestAI-MCP for gravity calculation framework
- **Reference**: /Volumes/HestAI-MCP/.hestai/context/project-ideas.oct.md
```

---

## Cross-Reference Strategy

### How to Handle Overlap

**RACI Dialogue Mode**:
- **HestAI-MCP**: Remove implementation details, link to Debate Hall
- **Debate Hall**: Keep full implementation, note system context

**Decision Gravity**:
- **HestAI-MCP**: Own scoring framework, link to Debate Hall for routing
- **Debate Hall**: Own routing integration, link to HestAI-MCP for scores

**Integrity Engine**:
- **HestAI-MCP**: Keep "Pivot" concept (Intent vs Reality philosophy)
- **Debate Hall**: Keep emergency approval implementation
- **Future**: Extract to integrity-engine-mcp (owns all details)

### Template for Cross-References

```octave
### [Feature Name]
- **Status**: [VALIDATED/PLANNED/etc]
- **Ownership**: [This project/Other project]
- **Related**: [Link to other doc]
  - **Scope**: What the other doc covers
  - **Reference**: Absolute path
```

---

## Migration Plan

### Step 1: Update HestAI-MCP Ideas (Today)

**Changes**:
1. Remove RACI implementation details
2. Add link to Debate Hall validated version
3. Keep Decision Gravity framework (system-level)
4. Keep Integrity Engine "Pivot" concept (philosophy)

**Example change**:
```octave
- **Debate Hall: RACI Dialogue Mode**
  - **Status**: ✅ IMPLEMENTED in debate-hall-mcp
  - **Validation**: 550 tokens, 99.4% reduction vs full debate
  - **Reference**: /Volumes/HestAI-Projects/debate-hall-mcp/.hestai/context/project-ideas.oct.md
  - **Integration**: Use as routing destination for Medium-High gravity decisions
```

### Step 2: Update Debate Hall Ideas (Today)

**Changes**:
1. Add cross-references to system-level concepts
2. Note Integrity Engine will become separate project
3. Link to HestAI-MCP for Decision Gravity scoring

**Example change**:
```octave
### Decision Gravity Integration
- **System Framework**: Gravity scoring algorithm defined in HestAI-MCP
- **Reference**: /Volumes/HestAI-MCP/.hestai/context/project-ideas.oct.md
- **This Project**: Integration as routing destination (validated)
```

### Step 3: Future - Integrity Engine Extraction

**When extracted**:
1. Create `/Volumes/HestAI-Projects/integrity-engine-mcp/.hestai/context/project-ideas.oct.md`
2. Move implementation details from both docs
3. Update both to reference new location

---

## Governance Rules

### Ownership Principles

**1. Feature Ownership**:
- Implementation = Project that builds it
- Concept = Project that originated it
- Integration = Both projects cross-reference

**2. Update Protocol**:
- When updating a feature, check if it's referenced elsewhere
- Update cross-references if scope changes
- Notify affected projects if dependencies shift

**3. Duplication Detection**:
- Monthly scan for overlap (grep for common terms)
- Consolidate or split as needed
- Keep "one source of truth" for each concept

**4. Extraction Protocol**:
- When extracting to new project, update all references
- Old docs link to new location
- New doc becomes authoritative

---

## Success Metrics

**Good separation**:
- Each project's ideas doc is <200 lines
- <20% overlap between docs
- Cross-references are clear and current
- Contributors find relevant ideas quickly

**Bad separation**:
- Duplicate content drifts (same idea, different descriptions)
- Missing cross-references (contributors unaware of dependencies)
- Confusion about ownership ("Who owns this feature?")

---

## Recommendation Summary

**Decision**: **Keep separate project-specific idea docs with explicit cross-references**

**Why**:
- Supports open source model (focused contributions)
- Enables independent evolution (projects can pivot)
- Clear ownership (no ambiguity)
- Scales with ecosystem growth (new projects get their own docs)

**How**:
- Update both docs with cross-references (today)
- Establish ownership principles (documented)
- Monitor for drift (monthly review)
- Extract on project creation (integrity-engine-mcp)

**Not recommended**:
- ❌ Single `/Volumes/HestAI-Projects/project-ideas.oct.md`
- Reason: Creates bottleneck, confuses contributors, doesn't scale

**Optional future enhancement**:
- Create `/Volumes/HestAI-Projects/ideas-index.oct.md` if ecosystem grows >5 projects
- For now, 2-3 projects = manageable with cross-references
