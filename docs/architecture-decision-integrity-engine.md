# Architecture Decision: Integrity Engine Integration

**Date**: 2026-01-10
**Status**: Proposed
**Decision**: Should Integrity Engine be part of debate-hall-mcp or a separate MCP server?

## TL;DR

**Recommendation**: **Start monolithic (integrated into debate-hall), plan for future extraction**

**Rationale**:
1. The Integrity Engine concept **does NOT exist in current tools**
2. It **expands debate-hall's scope** beyond pure deliberation
3. But the expansion is **conceptually aligned** (governance decisions)
4. **Monolithic is faster to implement** and validate
5. **Clean extraction path exists** if scope grows too large

---

## Research Findings: Does This Already Exist?

### What Exists Today

**Technical Debt Tracking**:
- ✅ SonarQube/SonarCloud: "New code" quality gates, debt quantification
- ✅ CodeClimate: Maintainability scoring, debt hours
- ✅ Snyk/Dependabot: Dependency vulnerability tracking

**Pre-Commit Enforcement**:
- ✅ Pre-commit framework: Local hooks for linting, secrets scanning
- ✅ Husky/Lefthook: Git hook management
- ✅ Server-side hooks: Branch protection, required checks

**Emergency Bypass Systems**:
- ✅ GitHub Environments: Protected environments with manual approvals
- ✅ OPA/Conftest: Policy-as-code for CI/CD gating
- ✅ Break-glass workflows: Multi-party approval for emergency deploys

### What Does NOT Exist

**❌ Conversational Emergency Approval**:
- No system uses AI debate for emergency bypass decisions
- No "Wind vs Wall vs Door" deliberation model
- No OCTAVE-formatted debt records

**❌ Integrated Debt Lock Mechanism**:
- Existing systems track debt OR enforce quotas, not both with debate
- No "debate outcome → debt record → pre-commit enforcement" pipeline
- No "quota as credit limit with repayment SLA" model

**❌ Debate-Driven Governance**:
- Break-glass is manual approvals (humans in UI)
- Not automated deliberation with AI agents
- No semantic debate transcript as audit trail

### The Gap: Integrity Engine Fills

**Novel Contribution**:
1. **AI-mediated emergency approval** (Wind/Wall/Door debate)
2. **Conversational justification** (not just checkbox approval)
3. **Semantic debt tracking** (OCTAVE records linked to decisions)
4. **Token-efficient governance** (1,850 tokens vs manual meetings)

**Conclusion**: **This is genuinely novel**. Closest analogs are:
- GitHub Environments (manual) + OPA (policy) + SonarQube (debt tracking)
- But NO integration and NO conversational deliberation

---

## Question 1: Does This Expand Debate Hall Beyond "Debate"?

### Current Debate Hall Scope

**What it is today**:
- A **deliberation system** for multi-perspective decision-making
- Wind explores possibilities, Wall validates constraints, Door synthesizes
- Output: Decision records (OCTAVE format)

**Core value**: Structured thinking through dialectic process

### With Integrity Engine

**Expanded scope**:
1. **Deliberation** (existing): "Should we use PostgreSQL?"
2. **Governance** (new): "Can I bypass tests for this emergency?"
3. **Enforcement** (new): Pre-commit hooks checking debt quotas
4. **Tracking** (new): Debt records with repayment SLAs

**New responsibilities**:
- Policy enforcement (blocking commits)
- Debt lifecycle management (creation, tracking, verification)
- Integration with git workflow (pre-commit hooks)

### Is "Debate Hall" the Right Name?

**Arguments it's still appropriate**:
- ✅ Core mechanism is still **debate** (Wind/Wall/Door)
- ✅ Integrity Engine is a **specialized debate mode**
- ✅ Output is still **decision records** (plus debt tracking)
- ✅ Philosophy unchanged: Multi-perspective deliberation

**Arguments it's outgrown the name**:
- ⚠️ "Hall" implies passive space, not active enforcement
- ⚠️ Debt tracking/enforcement feels like "governance engine"
- ⚠️ Pre-commit hooks are execution, not just deliberation
- ⚠️ RACI mode already stretched "debate" concept

### Alternative Names (if scope broadens further)

**Option 1**: **Governance Bus** (from project ideas)
- Pro: Accurately describes routing + decision + enforcement
- Pro: Aligns with "communication bus" architecture
- Con: Loses "debate" heritage and brand

**Option 2**: **Decision Engine**
- Pro: Covers all decision types (debate, RACI, integrity)
- Pro: Neutral about implementation mechanism
- Con: Generic, doesn't convey multi-perspective philosophy

**Option 3**: **Dialectic Engine**
- Pro: Philosophical accuracy (thesis/antithesis/synthesis)
- Pro: Covers debate AND governance decisions
- Con: Harder to explain to non-technical stakeholders

**Recommendation**: **Keep "Debate Hall" for now**
- Rationale: Integrity Engine is still fundamentally debate-driven
- Revisit if we add non-debate features (e.g., automated policy checks without deliberation)
- Consider "Debate Hall Governance Platform" as full name if needed

---

## Question 2: Monolithic vs Separate Server?

### Option A: Integrated (Monolithic)

**Architecture**:
```
debate-hall-mcp/
├── src/debate_hall_mcp/
│   ├── tools/
│   │   ├── init.py        (existing)
│   │   ├── turn.py        (existing)
│   │   ├── close.py       (existing)
│   │   └── integrity.py   (NEW)
│   ├── engine.py          (existing)
│   ├── state.py           (existing)
│   ├── integrity/         (NEW)
│   │   ├── metrics.py
│   │   ├── detector.py
│   │   └── debt.py
│   └── hooks/             (NEW)
│       └── pre-commit.py
```

**Pros**:
1. ✅ **Faster to implement** (no new server setup)
2. ✅ **Shared infrastructure** (state management, OCTAVE formatter)
3. ✅ **Single deployment** (one MCP server to manage)
4. ✅ **Conceptual cohesion** (all governance in one place)
5. ✅ **Easier testing** (integrated end-to-end tests)
6. ✅ **Lower overhead** (no inter-server communication)

**Cons**:
1. ⚠️ **Scope creep risk** (debate-hall becomes "do everything")
2. ⚠️ **Coupling** (integrity changes affect debate features)
3. ⚠️ **Naming confusion** ("Why is debt tracking in debate-hall?")
4. ⚠️ **Harder to disable** (can't simply turn off integrity server)

### Option B: Separate Server

**Architecture**:
```
integrity-engine-mcp/
├── src/integrity_engine_mcp/
│   ├── tools/
│   │   ├── request_bypass.py
│   │   ├── track_debt.py
│   │   └── verify_repayment.py
│   ├── metrics/
│   │   ├── coverage.py
│   │   ├── types.py
│   │   └── architecture.py
│   ├── detector.py
│   ├── debt.py
│   └── hooks/
│       └── pre-commit.py

debate-hall-mcp/
├── (existing structure)
└── integrations/
    └── integrity_client.py  (calls integrity-engine-mcp)
```

**Pros**:
1. ✅ **Clear separation of concerns** (debate vs enforcement)
2. ✅ **Independent scaling** (can disable integrity without affecting debate)
3. ✅ **Clearer naming** (each server has focused purpose)
4. ✅ **Easier to extract later** (already separated)
5. ✅ **Team ownership** (different teams can own each server)

**Cons**:
1. ❌ **Slower to implement** (setup new server, MCP registration)
2. ❌ **Duplication risk** (OCTAVE formatting, state management)
3. ❌ **Integration complexity** (cross-server communication)
4. ❌ **Operational overhead** (two servers to deploy, monitor)
5. ❌ **Debugging difficulty** (errors span multiple servers)
6. ❌ **User confusion** (which server do I call?)

### Hybrid Option C: Monolithic with Clear Modules

**Architecture**:
```
debate-hall-mcp/
├── src/debate_hall_mcp/
│   ├── debate/           (EXISTING - renamed for clarity)
│   │   ├── engine.py
│   │   ├── tools/
│   │   └── validation.py
│   ├── integrity/        (NEW - clearly separated module)
│   │   ├── __init__.py
│   │   ├── engine.py     (separate from debate engine)
│   │   ├── metrics.py
│   │   ├── detector.py
│   │   ├── debt.py
│   │   └── tools/
│   │       ├── request.py
│   │       └── verify.py
│   ├── shared/           (NEW - shared utilities)
│   │   ├── octave.py
│   │   ├── state.py
│   │   └── schemas.py
│   └── server.py         (orchestrates both modules)
```

**Pros**:
1. ✅ **Fast to implement** (monolithic benefits)
2. ✅ **Clear boundaries** (debate vs integrity modules)
3. ✅ **Easy extraction path** (modules → separate servers later)
4. ✅ **Shared infrastructure** (OCTAVE, state management)
5. ✅ **Single deployment** (operational simplicity)
6. ✅ **Modularity** (can disable integrity via config)

**Cons**:
1. ⚠️ **Still one server** (naming ambiguity remains)
2. ⚠️ **Requires discipline** (enforce module boundaries)

---

## Decision Matrix

| Criteria | Monolithic (A) | Separate (B) | Hybrid (C) |
|----------|----------------|--------------|------------|
| **Speed to Market** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Conceptual Clarity** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Operational Simplicity** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Future Flexibility** | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Code Reuse** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Team Ownership** | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Testing Simplicity** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Naming Accuracy** | ⭐ | ⭐⭐⭐ | ⭐⭐ |

**Winner**: **Hybrid (Option C)** - Best balance of speed and future flexibility

---

## Recommendation

### Phase 1: Monolithic with Clear Modules (Hybrid)

**Immediate actions**:
1. Implement Integrity Engine as a **module** within debate-hall-mcp
2. Structure code for **easy extraction** (separate directories, clear interfaces)
3. Add **config flag** to enable/disable integrity features
4. Document as "Debate Hall Governance Platform"

**Directory structure**:
```
src/debate_hall_mcp/
├── debate/          # Core debate functionality
├── integrity/       # Integrity Engine module
├── shared/          # Shared utilities (OCTAVE, state)
└── server.py        # MCP server orchestration
```

**Benefits**:
- ✅ Fast implementation (weeks, not months)
- ✅ Validate concept before extraction
- ✅ Easy to disable if not adopted
- ✅ Clear extraction path if scope grows

### Phase 2: Evaluate Extraction (After 6 Months)

**Trigger for extraction**:
- Integrity Engine is widely adopted (>50% of projects)
- Feature requests diverge (debate vs integrity roadmaps)
- Different teams want to own each component
- Performance bottlenecks from shared server

**Extraction plan**:
1. Move `integrity/` module → new `integrity-engine-mcp` repo
2. Keep `shared/` utilities in library package
3. Debate Hall calls Integrity Engine via MCP client
4. Maintain backward compatibility (integrated mode still works)

### Naming Strategy

**Now**: "Debate Hall MCP" (keep existing brand)
**Documentation**: "Debate Hall Governance Platform"
**Future**: Consider rename only if extraction happens

**Module names**:
- `debate_hall_mcp.debate` - Core deliberation
- `debate_hall_mcp.integrity` - Emergency governance
- `debate_hall_mcp.shared` - Common utilities

---

## Comparison to Existing Systems

### What Makes This Different?

**vs SonarQube**:
- SonarQube: Passive debt tracking, manual review
- Integrity Engine: Active deliberation, automated approval

**vs GitHub Environments**:
- GitHub: Manual human approvals in UI
- Integrity Engine: AI-mediated debate with semantic justification

**vs OPA/Conftest**:
- OPA: Static policy evaluation
- Integrity Engine: Dynamic deliberation with context

**vs Pre-commit Hooks**:
- Pre-commit: Fixed rules, binary pass/fail
- Integrity Engine: Contextual debate, conditional approval

**Novel Integration**:
```
Existing: Debt Tracking OR Enforcement OR Approval
Integrity: Debt Tracking AND Enforcement AND AI Approval

Existing: Manual process (meetings, emails, tickets)
Integrity: Automated debate (1,850 tokens, <30 seconds)
```

---

## Risk Analysis

### Monolithic Risks

**Risk**: Scope creep makes debate-hall unwieldy
**Mitigation**: Clear module boundaries, extraction plan ready

**Risk**: Naming confusion ("Why debt tracking in debate hall?")
**Mitigation**: Documentation, "Governance Platform" positioning

**Risk**: Performance impact (integrity slows debate)
**Mitigation**: Separate engine instances, async processing

### Separation Risks (if we go straight to separate server)

**Risk**: Premature optimization (overhead before validation)
**Mitigation**: Start monolithic, extract if needed

**Risk**: Integration complexity (cross-server communication)
**Mitigation**: Use MCP client protocol, shared schemas

**Risk**: Duplication (OCTAVE formatting in both servers)
**Mitigation**: Extract to shared library package

---

## Success Metrics

### Phase 1 (Monolithic Module)
- [ ] Integrity module implemented in <4 weeks
- [ ] Zero impact on existing debate features
- [ ] Config flag allows clean disable
- [ ] 100% test coverage for integrity module

### Decision Point (6 months)
- [ ] >50% adoption OR
- [ ] Feature divergence OR
- [ ] Performance bottleneck

### Phase 2 (Extraction - if triggered)
- [ ] Extraction complete in <2 weeks
- [ ] Backward compatibility maintained
- [ ] No feature regressions
- [ ] Independent deployment successful

---

## Conclusion

**Recommendation**: **Monolithic with clear module separation (Hybrid Option C)**

**Rationale**:
1. **Integrity Engine is novel** - nothing like it exists
2. **Conceptually aligned** - still governance deliberation
3. **Fast to validate** - monolithic speeds implementation
4. **Clean extraction path** - modules enable future separation
5. **Keep "Debate Hall" name** - integrity is a debate mode

**Next Steps**:
1. Implement `src/debate_hall_mcp/integrity/` module
2. Add config flag: `INTEGRITY_ENGINE_ENABLED`
3. Document as "Debate Hall Governance Platform"
4. Set 6-month review date for extraction decision

**Answer to original questions**:
- **Does this exist?** No, it's genuinely novel
- **Does it expand scope?** Yes, but aligned expansion
- **Right to integrate?** Yes for now, extract if grows
- **Right terminology?** Keep "Debate Hall", clarify as "Governance Platform"
