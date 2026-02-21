===D2_SOLUTION_APPROACH===

META:
  TYPE::PHASE_ARTIFACT
  PHASE::D2
  ISSUE::#173
  TITLE::"Governance Chat Headless API Surface — Solution Approach"
  DATE::"2026-02-21"
  AUTHOR::HO[session::831d8cfe]
  D1_REF::.hestai/workflow/173-D1-north-star-assessment.oct.md

§1::PROBLEM_STATEMENT

NEED::"debate-hall-mcp requires advisory consultation and committee decision tools for governance chat. The workbench (P5) will render these as a chat UI. debate-hall provides the headless API."

BLOCKING_CONSTRAINT::"pick_next_speaker validates role in ('Wind', 'Wall', 'Door'). Governance chat requires arbitrary named roles (CRS, CE, TMG, etc.) in mediated sessions."

CURRENT_STATE::[
  "14 MCP tools, 864 tests, all passing",
  "MEDIATED mode exists but locked to Wind/Wall/Door triad",
  "RACI mode allows custom roles but requires rigid TurnManifest pre-compilation",
  "No consult/convene tools exist — clean slate"
]

§2::APPROACH_SELECTED

NAME::"Semantic Layer over Flexible Mediated Mode"

SYNTHESIS::[
  "consult and convene are thin semantic wrappers over existing primitives",
  "The core unlock is removing the Wind/Wall/Door restriction in pick_next_speaker",
  "Session types (debate/consultation/committee) are metadata on DebateRoom, not new engines",
  "The workbench handles provider dispatch; debate-hall handles session lifecycle and transcript integrity"
]

KEY_INSIGHT::"The existing mediated mode infrastructure already supports flexible turn ordering. The expected_next_role field accepts any string. The ONLY gate is the role validation in tools/pick.py line 26: `if role not in ('Wind', 'Wall', 'Door')`. Removing this restriction unlocks governance chat with minimal code change."

ARCHITECTURE::[
  LAYER_1::FOUNDATION — flexible roles in mediated mode (pick.py + turn.py changes),
  LAYER_2::STATE_EXTENSIONS — SessionType enum, Participant model, CommitteeMetadata,
  LAYER_3::TOOLS — consult() and convene() as convenience wrappers over init_debate + add_turn + pick_next_speaker
]

WHY_THIS_WORKS::[
  "Backward compatible: Wind/Wall/Door still work, cognition validation preserved for triad",
  "Minimal surface area: 2 new tools, 3 new models, 2 modified files",
  "Inherits all existing guarantees: I1 (state isolation), I3 (finite closure), I4 (hash chain), I5 (kill switch)",
  "No new engine or mode needed — mediated mode semantics are 'orchestrator picks next role'"
]

§3::ALTERNATIVES_CONSIDERED

ALTERNATIVE_1::PARALLEL_SESSION_TYPE[
  DESCRIPTION::"Create a GovernanceSession model separate from DebateRoom, with its own engine and tools",
  PROS::[
    "Clean separation of concerns",
    "No risk of breaking existing debate functionality",
    "Purpose-built for governance patterns"
  ],
  CONS::[
    "Massive code duplication (turn recording, hash chain, state persistence, mode handling)",
    "Two parallel state systems to maintain",
    "Does not follow OCTAVE principle of extending existing structures",
    "Violates MIP pattern — accumulative orchestration without value"
  ],
  VERDICT::REJECTED["duplication cost far exceeds separation benefit; DebateRoom IS the deliberation container"]
]

ALTERNATIVE_2::EXTEND_RACI_MODE[
  DESCRIPTION::"Make RACI mode more flexible — remove TurnManifest rigidity, allow dynamic role addition",
  PROS::[
    "RACI already supports custom role names",
    "Reuses existing auto-orchestration infrastructure"
  ],
  CONS::[
    "RACI mode couples role sequence to TurnManifest at init time — fundamentally rigid",
    "RACI uses single provider for all roles — wrong for governance chat where workbench dispatches per-role",
    "Modifying RACI to be dynamic would break its core invariant (pre-compiled manifest)",
    "Consultation is 2-party, not RACI 4-party — forcing RACI mapping is awkward"
  ],
  VERDICT::REJECTED["RACI's rigidity is by design; governance chat needs flexibility that mediated mode already provides"]
]

ALTERNATIVE_3::NEW_MODE_GOVERNANCE[
  DESCRIPTION::"Add a new DebateMode.GOVERNANCE mode with custom role handling",
  PROS::[
    "Explicit mode for governance operations",
    "Can have governance-specific validation rules"
  ],
  CONS::[
    "Mediated mode already means 'orchestrator controls turn order with arbitrary roles' — a new mode adds nothing",
    "Would require changes to engine.py get_next_speaker, add_turn validation, etc.",
    "Session type metadata achieves the same semantic distinction without mode proliferation"
  ],
  VERDICT::REJECTED["mediated mode + session_type metadata achieves the same result without mode proliferation"]
]

§4::RISK_ASSESSMENT

RISK_1::BACKWARD_COMPATIBILITY[
  LIKELIHOOD::LOW,
  IMPACT::MEDIUM,
  DESCRIPTION::"Removing role restriction in pick_next_speaker could allow invalid roles in existing debate flows",
  MITIGATION::"In FIXED mode, engine.get_next_speaker() returns the expected triad role — pick_next_speaker is only for MEDIATED mode. No FIXED mode regression. Existing test suite (864 tests) provides safety net."
]

RISK_2::COGNITION_VALIDATION_REGRESSION[
  LIKELIHOOD::LOW,
  IMPACT::LOW,
  DESCRIPTION::"Non-triad roles skip cognition validation, which could allow invalid cognition values",
  MITIGATION::"Cognition field is optional (str | None). For non-triad roles, cognition is simply not validated. For triad roles, existing validation preserved. This is the correct behavior — CRS doesn't have a cognition archetype."
]

RISK_3::STATE_MODEL_MIGRATION[
  LIKELIHOOD::LOW,
  IMPACT::LOW,
  DESCRIPTION::"Adding fields to DebateRoom could break deserialization of existing JSON state files",
  MITIGATION::"All new fields have defaults (session_type=DEBATE, participants=None, committee_metadata=None). Pydantic v2 handles missing fields gracefully with defaults."
]

§5::DEPENDENCY_MAP

PHASE_ORDER::[
  "Phase 1 (Foundation) BLOCKS Phase 2 (consult) and Phase 3 (convene)",
  "Phase 1a (#174: flexible roles) and Phase 1b (#175: state models) are PARALLEL",
  "Phase 2 (consult) and Phase 3 (convene) are PARALLEL after Phase 1",
  "Phase 4 (integration tests) requires Phase 2 + Phase 3",
  "Phase 5 (housekeeping) is independent"
]

CROSS_REPO::[
  "workbench#16 CONSUMES the API contract — can begin UI work once contract is ratified",
  "HestAI-MCP#262 PROVIDES agent identity — debate-hall does NOT depend on it (P6)",
  "No blocking cross-repo dependencies for debate-hall implementation"
]

===END===
