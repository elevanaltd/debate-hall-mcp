===DEBATE_HALL_PROJECT_IDEAS===

META:
  TYPE::IDEAS_DOCUMENT
  VERSION::2.0
  STATUS::ACTIVE_RESEARCH
  VISIBILITY::PROJECT_INTERNAL
  CONTEXT::"Transferred from HestAI-MCP context-steward-benefits"
  LAST_UPDATE::2026-01-10
  VALIDATION_STATUS::EMPIRICALLY_TESTED

## Overview
This document captures high-level ideas, potential features, and future directions for Debate Hall MCP, specifically regarding its integration into the broader HestAI "Integrity Engine" architecture.

## Product Vision: The Governance Communication Bus
Debate Hall evolves from a "Conflict Resolution Tool" into the central "Governance Communication Bus" for HestAI. It becomes the structural mechanism for high-gravity decisions and cross-role alignment.

## Potential Features

### 1. RACI Dialogue Mode (Recipe) ✅ VALIDATED
- **Status**: Empirically tested (2026-01-10)
- **Token Usage**: 550 tokens (99.4% reduction vs full debate)
- **Duration**: <10 seconds
- **Concept**: A lightweight debate mode designed for rapid decision alignment, mapping Debate Hall roles to RACI roles.
- **Mapping**:
  - **Wind (Responsible)**: Proposes the action.
  - **Wall (Consulted)**: Validates constraints/risks (or yields).
  - **Door (Accountable)**: Ratifies the decision.
  - **Informed**: Receives the immutable transcript.
- **Mechanism**:
  - Single-Round / Speed Mode.
  - "Zero-Friction" option where Wall yields immediately if no objections.
- **Value**: Front-loaded alignment. Prevents "revert later" chaos by enforcing "check now" structure.
- **Test Results**: See `docs/research-findings-project-ideas.md`
- **Recommendation**: IMMEDIATE IMPLEMENTATION (Priority: HIGH)

### 2. Decision Gravity Integration ✅ VALIDATED
- **Status**: Architecture validated (2026-01-10)
- **Feasibility**: Compatible with existing validation system
- **Concept**: Debate Hall acts as the routing destination for High-Gravity decisions.
- **Trigger**: HestAI System Steward detects a "High Gravity" change (Score > 60).
- **Action**: Routes the agent to `debate-hall-mcp` to resolve the path.
- **Output**: The Debate ID becomes the "Decision Record" required to proceed.
- **Token Efficiency**: RACI mode makes routing overhead acceptable (550 tokens)
- **Infrastructure**: ValidationResult already has PASS/WARN/BLOCK levels
- **Metadata Support**: Can add gravity_score field to DebateRoom
- **Test Results**: See `docs/research-findings-project-ideas.md`
- **Recommendation**: PHASED IMPLEMENTATION (Priority: MEDIUM)
  - Phase 1: Add gravity metadata fields
  - Phase 2: Define scoring algorithm (separate ADR)
  - Phase 3: System Steward integration

### 3. Integrity Engine (Coherence Debates) ✅ VALIDATED + 🚀 STRATEGIC PIVOT
- **Status**: Fully designed and empirically tested (2026-01-10)
- **Token Usage**: 1,850 tokens (98.2% reduction vs full debate)
- **Duration**: <30 seconds
- **Novel Contribution**: No existing tool combines AI debate + debt tracking + enforcement
- **Concept**: Specialized system to resolve "Coherence vs. Velocity" conflicts (The 3AM Dilemma).
- **Scenario**: 3AM Hotfix vs. Strict Integrity.
- **Mechanism**:
  - **Wind**: Argues for Velocity (Emergency justification with cost-benefit).
  - **Wall**: Argues for Integrity (Risk assessment, conditions).
  - **Door**: Grants "Debt Lock" (Bypass + Mandatory Repayment + SLA).
- **Complete Design**: See `docs/integrity-engine-design.md`
- **Test Results**: See `docs/integrity-engine-test-results.md`
- **Empirical Validation**:
  - Thread: `2026-01-10-integrity-critical-production-api-fix`
  - Debt Lock: DEBT-2026-001 created and tracked
  - Full debt lifecycle demonstrated

**🚀 STRATEGIC DECISION: SEPARATE PROJECT**
- **Rationale**: Open source adoption and contribution velocity
- **Market Size**: 10x larger (any git team vs only governance teams)
- **Contribution Barrier**: Lower (focused project vs monolithic)
- **Ecosystem Potential**: Community integrations (GitHub Actions, GitLab, etc.)
- **Architecture**: See `docs/open-source-strategy-integrity-engine.md`
- **Recommendation**: Extract as `integrity-engine-mcp` (separate MCP server)
  - Phase 1: Create separate repo with shared `octave-governance-toolkit`
  - Phase 2: Coordinated 1.0 release of both projects
  - Phase 3: Community ecosystem building
- **Integration**: Optional bridge package shows integration pattern
- **Timeline**: Month 1-2 extraction, Month 3+ community growth

### 4. "Context Compiler" Integration ✅ VALIDATED
- **Status**: Architecture validated (2026-01-10)
- **Feasibility**: OCTAVE output already compatible
- **Token Impact**: 98% savings (read decision vs re-debate)
- **Concept**: Debate Hall transcripts are not just logs; they are *compiled* into the project context.
- **Mechanism**:
  - `close_debate` output is structured OCTAVE (already implemented).
  - This output is injected into `.hestai/context/decisions/` as a "Compiled Decision".
  - Future agents "read" this decision as part of their binding context.
- **Implementation**:
  - Phase 1: Add export logic to `close_debate` (2 days)
  - Phase 2: Context indexing for decision discovery (1 day)
  - Phase 3: Agent binding integration (3 days)
- **Test Results**: See `docs/research-findings-project-ideas.md`
- **Recommendation**: IMMEDIATE IMPLEMENTATION (Priority: HIGHEST)
  - Low effort, high value, zero architectural friction

## Future Roadmap
- **Decision API**: External tools post "Decision Requests" to Debate Hall.
- **Automated Facilitator**: An LLM-based facilitator that actively manages turn-taking and focus (beyond simple `pick_next_speaker`).

## Constraints and Considerations
- **Latency**: RACI mode must be fast (seconds, not minutes).
- **Fatigue**: Must avoid "Debate Fatigue". Low-gravity decisions should bypass this system.

## Validation Requirements
- Ensure new recipes align with Wind/Wall/Door cognitive architectures.
- Validate that "RACI Mode" produces auditable decision records.

## Implementation Priority

**Immediate (Next Sprint)**:
1. ✅ Context Compiler (1 week) - Highest value, lowest risk
2. ✅ RACI Mode (2-3 weeks) - 99% token savings proven

**Planned (Q1 2026)**:
3. ⚠️ Decision Gravity (4 weeks) - Requires scoring algorithm ADR
4. 🚀 Integrity Engine (separate project) - Extract as `integrity-engine-mcp`

**Research Phase (Q2 2026)**:
- Coherence metrics refinement (empirical data collection)
- Community ecosystem building for Integrity Engine
- Cross-project integration patterns

## Success Metrics

**Context Compiler**:
- Target: 50+ decision records in first month
- Measure: 98% token savings vs re-debate

**RACI Mode**:
- Target: 90% of debates use fast-path
- Measure: <1,000 tokens average per decision

**Integrity Engine** (if separate):
- Target: 100+ GitHub stars, 20+ adopters
- Measure: 5+ community integrations within 6 months

## Strategic Insights (2026-01-10 Research)

**Key Finding**: Integrity Engine should be **separate project** for maximum impact
- **Market reach**: 10x larger (any git team vs governance-only teams)
- **Contribution velocity**: Lower barrier enables community growth
- **Ecosystem potential**: Independent integrations (GitHub Actions, GitLab, etc.)
- **Novel value**: No existing tool combines AI debate + debt tracking + enforcement

**Decision**: Extract as `integrity-engine-mcp` with shared `octave-governance-toolkit`

## Documentation References

- Token Usage Analysis: `docs/token-usage-analysis.md`
- Research Validation: `docs/research-findings-project-ideas.md`
- Integrity Engine Design: `docs/integrity-engine-design.md`
- Integrity Engine Testing: `docs/integrity-engine-test-results.md`
- Architecture Decision: `docs/architecture-decision-integrity-engine.md`
- Open Source Strategy: `docs/open-source-strategy-integrity-engine.md`

## Change Log
- 2026-01-10: Empirical validation of all features completed
- 2026-01-10: Strategic decision - Integrity Engine as separate project
- 2026-01-10: Document created (Transferred from HestAI-MCP analysis)

===END===
