===ENHANCEMENT_ROADMAP===

META:
  TYPE::IMPLEMENTATION_PLAN
  VERSION::"1.0"
  STATUS::ACTIVE
  CREATED::"2026-02-06"
  AUTHOR::holistic-orchestrator
  SESSION_ID::"0634b77f-9159-4dcf-9ccc-0d9cf71c6ede"

§1::OVERVIEW

PURPOSE::"Prioritized enhancement plan for debate-hall-mcp synthesizing technical architect review, validated features from project-ideas.oct.md, and 15 open GitHub issues"

SOURCES::[
  TECH_REVIEW::"Technical architect review (fa44786) - 4 recommendations",
  PROJECT_IDEAS::".hestai/context/project-ideas.oct.md - 4 validated features",
  GITHUB_ISSUES::"15 open issues across architecture, features, observability"
]

PRIORITIZATION_CRITERIA::[
  1::RISK_MITIGATION[tech_debt_causing_production_issues],
  2::VALUE_DELIVERY[validated_features_with_measured_impact],
  3::ARCHITECTURAL_COHERENCE[foundational_work_enabling_others],
  4::STRATEGIC_ALIGNMENT[North_Star_alignment]
]

§2::TIER_0_CRITICAL_PRODUCTION_SAFETY

STATUS::COMPLETED
RISK::PRODUCTION_INCIDENTS_IF_NOT_ADDRESSED
COMPLETED_DATE::"2026-02-06"

ITEMS::[
  {
    id::"0.1",
    title::"Race condition fix in save_debate_state()",
    source::"Tech Review",
    priority::"CRITICAL",
    issue::149,
    rationale::"Concurrent writers can corrupt state - implement CAS with file hash verification",
    effort::"1-2 days",
    status::"COMPLETED",
    commit::"d35663b",
    resolution::"Added ConcurrencyError, compute_state_hash(), save_debate_state_with_retry() with exponential backoff. 11 new tests."
  },
  {
    id::"0.2",
    title::"Status management investigation",
    source::"GitHub Issue #100",
    priority::"HIGH",
    issue::100,
    rationale::"Related to state persistence - failing E2E tests indicate fragile lifecycle",
    effort::"1-2 days",
    status::"COMPLETED",
    resolution::"Investigation found all E2E tests passing (5/5). Status management working correctly - tombstone doesn't change status, force_close sets FORCE_CLOSED, turn addition validates ACTIVE. No code changes needed."
  },
  {
    id::"0.3",
    title::"Hash verification content re-computation",
    source::"GitHub Issue #105",
    priority::"HIGH",
    issue::105,
    rationale::"Security - current verification doesn't detect content tampering",
    effort::"1 day",
    status::"COMPLETED",
    commit::"c93ddee",
    resolution::"Added IntegrityError, verify_turn_content_hash(), verify_all_turn_content_hashes(). Extended load_debate_state() with verify_content parameter. 8 new tests."
  }
]

§3::TIER_1_FOUNDATION_FOR_SCALABILITY

STATUS::COMPLETED
RATIONALE::UNBLOCKS_FUTURE_ENHANCEMENTS_AND_PRODUCTION_DEPLOYMENTS
COMPLETED_DATE::"2026-02-07"

ITEMS::[
  {
    id::"1.1",
    title::"Production deployment documentation",
    source::"GitHub Issue #108",
    priority::"HIGH",
    issue::108,
    rationale::"Documentation debt - production-grade claim needs deployment guidance",
    effort::"2-3 days",
    status::"COMPLETED",
    commit::"d0a75f6",
    resolution::"Created docs/production-deployment.md with state storage, secrets management, multi-instance guidance, and systemd/Docker examples. Updated README production section."
  },
  {
    id::"1.2",
    title::"Concurrency model improvement",
    source::"GitHub Issue #106 + Tech Review",
    priority::"MEDIUM",
    issue::106,
    rationale::"Read/write lock pattern for multi-instance deployments",
    effort::"2-3 days",
    status::"COMPLETED",
    commit::"f3e3622",
    resolution::"Added fasteners dependency for inter-process read/write locking. load_debate_state() uses read lock, save_debate_state() uses write lock. 6 new tests."
  },
  {
    id::"1.3",
    title::"Provider timeout zombie cleanup",
    source::"Tech Review",
    priority::"MEDIUM",
    issue::150,
    rationale::"asyncio.wait_for() can leave orphan processes",
    effort::"1 day",
    status::"COMPLETED",
    commit::"1c9d2e6",
    resolution::"Added graceful terminate() before force kill() in CLI provider. Finally block ensures cleanup. 5 new tests."
  }
]

§4::TIER_2_HIGH_VALUE_VALIDATED_FEATURES

STATUS::COMPLETED
RATIONALE::EMPIRICALLY_VALIDATED_WITH_TOKEN_SAVINGS_METRICS
COMPLETED_DATE::"2026-02-08"

ITEMS::[
  {
    id::"2.1",
    title::"Context Compiler Integration",
    source::"project-ideas.oct.md",
    priority::"HIGHEST",
    issue::138,
    rationale::"98% token savings, 1 week effort, export to .hestai/context/decisions/",
    effort::"1 week",
    token_savings::"98%",
    status::"COMPLETED",
    commit::"c12f8b1",
    resolution::"Added context_compiler.py with OCTAVE export, export_decision parameter in close_debate, unique filename format with short_id suffix. 21 new tests."
  },
  {
    id::"2.2",
    title::"RACI Dialogue Mode",
    source::"project-ideas.oct.md + GitHub Issue #139",
    priority::"HIGH",
    issue::139,
    rationale::"550 tokens vs 90k (99.4% reduction), fast-path for low-gravity decisions",
    effort::"2-3 weeks",
    token_savings::"99.4%",
    status::"COMPLETED",
    commit::"261a09e",
    resolution::"Added DebateMode.RACI with enforced limits (max_turns=3, max_rounds=1), RACI prompts, Wall YIELD option, run_raci() orchestration, mode-aware resume(). 29 new tests."
  },
  {
    id::"2.3",
    title::"Decision indexing & BM25 search",
    source::"GitHub Issues #144, #138",
    priority::"HIGH",
    issue::144,
    rationale::"Enables decision discovery - field-weighted OCTAVE search",
    effort::"1-2 weeks",
    status::"COMPLETED",
    commit::"859c772",
    resolution::"Added BM25 search engine with field weighting (TOPIC 10.0, SYNTHESIS 5.0), lazy indexing, search_decisions MCP tool, find_precedent() agent interface. 33 new tests."
  }
]

§5::TIER_3_ARCHITECTURE_EVOLUTION

STATUS::COMPLETED
RATIONALE::MAJOR_ARCHITECTURAL_IMPROVEMENTS_REQUIRING_DESIGN
COMPLETED_DATE::"2026-02-09"

ITEMS::[
  {
    id::"3.1",
    title::"Router + Focused Skills",
    source::"GitHub Issue #145, ADR-0005",
    priority::"HIGH",
    issue::145,
    rationale::"48-76% token overhead reduction, modular skill architecture",
    effort::"1-2 weeks",
    status::"COMPLETED",
    commit::"3113a07",
    pr::154,
    resolution::"Decomposed 336-line monolithic skill into router (49 lines) + 4 focused skills. Token savings 59-74%."
  },
  {
    id::"3.2",
    title::"Cognitive Notary evolution",
    source::"GitHub Issue #136",
    priority::"MEDIUM",
    issue::136,
    rationale::"Three-layer architecture refinement already partially complete",
    effort::"2-3 weeks",
    status::"COMPLETED",
    resolution::"Already complete from Sprint 3-4. DecisionRecord schema, resolve_question tool, BM25 search all implemented."
  },
  {
    id::"3.3",
    title::"Role/Cognition/Identity documentation",
    source::"GitHub Issue #146",
    priority::"MEDIUM",
    issue::146,
    rationale::"Clarifies Wind/Wall/Door vs PATHOS/ETHOS/LOGOS confusion",
    effort::"2-3 days",
    status::"COMPLETED",
    commit::"aa64f83",
    resolution::"Added three-layer identity model docs to agents/README.md, skills/debate-hall/SKILL.md, tiers.yaml.example, docs/production-deployment.md."
  }
]

§6::TIER_4_OBSERVABILITY_AND_DX

STATUS::QUALITY_OF_LIFE
RATIONALE::DEVELOPER_EXPERIENCE_IMPROVEMENTS

ITEMS::[
  {
    id::"4.1",
    title::"Audit log enrichment",
    source::"GitHub Issue #147",
    priority::"MEDIUM",
    issue::147,
    rationale::"Full turn content for cost/quality analysis pipelines",
    effort::"1-2 days",
    status::"PENDING"
  },
  {
    id::"4.2",
    title::"Token counting per turn",
    source::"GitHub Issue #135",
    priority::"LOW",
    issue::135,
    rationale::"Visibility into debate costs via VTP injection",
    effort::"1 day",
    status::"PENDING"
  },
  {
    id::"4.3",
    title::"Context files parameter",
    source::"GitHub Issue #133",
    priority::"MEDIUM",
    issue::133,
    rationale::"Codebase-aware debates with CODEBASE_CONTEXT block",
    effort::"2-3 days",
    status::"PENDING"
  }
]

§7::TIER_5_FUTURE_SCOPE

STATUS::Q2_PLUS_OR_DEFERRED
RATIONALE::STRATEGIC_BUT_NOT_IMMEDIATE_PRIORITY

ITEMS::[
  {
    id::"5.1",
    title::"Decision Gravity Integration",
    source::"project-ideas.oct.md",
    priority::"MEDIUM",
    issue::null,
    rationale::"Requires separate ADR for scoring algorithm",
    effort::"4 weeks",
    status::"DEFERRED"
  },
  {
    id::"5.2",
    title::"Feature Flag Architecture",
    source::"GitHub Issue #143",
    priority::"LOW",
    issue::143,
    rationale::"8-week implementation, depends on stable base",
    effort::"8 weeks",
    status::"DEFERRED"
  },
  {
    id::"5.3",
    title::"GitHub Label Automation",
    source::"GitHub Issue #73",
    priority::"LOW",
    issue::73,
    rationale::"Investigation needed - architectural decision blocker",
    effort::"TBD",
    status::"INVESTIGATION_REQUIRED"
  },
  {
    id::"5.4",
    title::"Debate Hall App",
    source::"GitHub Issue #112",
    priority::"FUTURE",
    issue::112,
    rationale::"Vision/future - depends on stable auto-orchestration",
    effort::"TBD",
    status::"FUTURE_VISION"
  },
  {
    id::"5.5",
    title::"Integrity Engine extraction",
    source::"project-ideas.oct.md",
    priority::"STRATEGIC",
    issue::null,
    rationale::"Extract as separate project integrity-engine-mcp for open source reach",
    effort::"4-8 weeks",
    status::"STRATEGIC_DECISION"
  }
]

§8::SPRINT_PLAN

SPRINT_1::STABILITY[
  ITEMS::[0.1, 0.2, 0.3],
  GOAL::"Production safety and state management reliability",
  DURATION::"1 week",
  STATUS::COMPLETED,
  COMPLETED_DATE::"2026-02-06",
  COMMITS::["d35663b", "c93ddee"],
  TESTS_ADDED::19,
  TESTS_TOTAL::916
]

SPRINT_2::FOUNDATION[
  ITEMS::[1.1, 1.2, 1.3],
  GOAL::"Production readiness documentation and scalability unblock",
  DURATION::"1 week",
  STATUS::COMPLETED,
  COMPLETED_DATE::"2026-02-07",
  COMMITS::["d0a75f6", "f3e3622", "1c9d2e6"],
  TESTS_ADDED::11,
  TESTS_TOTAL::927
]

SPRINT_3_4::VALUE_DELIVERY[
  ITEMS::[2.1, 2.2, 2.3],
  GOAL::"Context Compiler, RACI Mode, Decision Search",
  DURATION::"2-3 weeks",
  STATUS::COMPLETED,
  COMPLETED_DATE::"2026-02-08",
  COMMITS::["c12f8b1", "261a09e", "859c772"],
  TESTS_ADDED::83,
  TESTS_TOTAL::1013
]

SPRINT_5_TIER_3::ARCHITECTURE[
  ITEMS::[3.1, 3.2, 3.3],
  GOAL::"Router + Skills, Cognitive Notary, Identity Docs",
  DURATION::"1 day",
  STATUS::COMPLETED,
  COMPLETED_DATE::"2026-02-09",
  COMMITS::["3113a07", "aa64f83"],
  PR::154,
  TESTS_TOTAL::1013
]

SPRINT_5_TIER_4::OBSERVABILITY[
  ITEMS::[4.1, 4.2, 4.3],
  GOAL::"Audit log enrichment, Token counting, Context files",
  DURATION::"1-2 weeks",
  STATUS::PENDING
]

§9::SUCCESS_METRICS

TIER_0::[
  "Zero race condition failures in concurrent tests",
  "E2E status management tests passing",
  "Hash verification detects content tampering"
]

TIER_1::[
  "Production deployment guide published",
  "Read/write locks improve concurrent throughput by 50%+",
  "Zero zombie processes after provider timeout"
]

TIER_2::[
  "50+ decision records exported in first month",
  "90% of debates use RACI fast-path",
  "Decision search latency under 100ms"
]

§10::CHANGE_LOG

ENTRIES::[
  {date::"2026-02-06", action::"Created", author::"holistic-orchestrator", note::"Initial roadmap from synthesis session"},
  {date::"2026-02-06", action::"Sprint 1 Complete", author::"implementation-lead", note::"Completed Tier 0 (0.1, 0.2, 0.3). Issues #100, #105, #149 closed. 19 new tests, 916 total."},
  {date::"2026-02-07", action::"Sprint 2 Complete", author::"implementation-lead", note::"Completed Tier 1 (1.1, 1.2, 1.3). Issues #106, #108, #150 closed. 11 new tests, 927 total."},
  {date::"2026-02-08", action::"Sprint 3-4 Complete", author::"holistic-orchestrator", note::"Completed Tier 2 (2.1, 2.2, 2.3). Context Compiler, RACI Mode, BM25 Search. Issues #138, #139, #144 closed. 83 new tests, 1013 total."},
  {date::"2026-02-09", action::"Sprint 5 Tier 3 Complete", author::"holistic-orchestrator", note::"Completed Tier 3 (3.1, 3.2, 3.3). Router + Focused Skills (PR #154), Identity Docs, Cognitive Notary closed. Issues #145 (PR), #146, #136 addressed. 1013 tests maintained."}
]

===END===
