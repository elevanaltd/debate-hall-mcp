---
name: debate-hall
description: Wind/Wall/Door multi-perspective debate orchestration using debate-hall-mcp tools. Use when facilitating structured debates, architectural decisions, or multi-perspective analysis.
triggers: ["debate", "wind wall door", "dialectic", "multi-perspective", "structured decision", "architecture decision"]
allowed-tools: ["Read", "Write", "Edit", "Bash", "mcp__debate-hall__*"]
---

===DEBATE_HALL===

META:
  TYPE::SKILL
  VERSION::"2.0"
  PURPOSE::"Wind/Wall/Door debate orchestration via MCP tools"
  DOMAIN::ATHENA[strategic_decisions]⊕HERMES[orchestration]

§1::PATTERN
  TRIAD::[
    WIND::PATHOS["What if..."|expansive|visionary|possibilities],
    WALL::ETHOS["Yes, but..."|grounding|critical|reality_testing],
    DOOR::LOGOS["Therefore..."|synthesizing|decisive|actionable_truth]
  ]
  DYNAMIC::WIND⇌WALL→DOOR[tension_produces_emergence]

§2::WORKFLOW
  SEQUENCE::INIT→TURN→GET→CLOSE
  TOOLS::[
    init_debate(thread_id,topic,mode?,max_turns?,max_rounds?,strict_cognition?),
    add_turn(thread_id,role,content,cognition?,agent_role?,model?),
    get_debate(thread_id,include_transcript?,context_lines?),
    close_debate(thread_id,synthesis,output_format?)
  ]

§3::TOOL_PARAMS
  INIT_DEBATE::[
    thread_id::REQUIRED[unique_identifier],
    topic::REQUIRED[question_or_issue],
    mode::"fixed"|"mediated"[default:fixed],
    max_turns::12[default],
    max_rounds::4[default],
    strict_cognition::false[default]
  ]
  ADD_TURN::[
    thread_id::REQUIRED,
    role::REQUIRED["Wind"|"Wall"|"Door"],
    content::REQUIRED,
    cognition::PATHOS|ETHOS|LOGOS[optional_override],
    agent_role::STRING[audit_trail],
    model::STRING[audit_trail]
  ]
  GET_DEBATE::[
    thread_id::REQUIRED,
    include_transcript::true[default],
    context_lines::all[default]
  ]
  CLOSE_DEBATE::[
    thread_id::REQUIRED,
    synthesis::REQUIRED[Door_final_text],
    output_format::"json"|"octave"|"both"[default:json]
  ]

§4::MODES
  FIXED::[
    SEQUENCE::Wind→Wall→Door→repeat,
    USE_FOR::[structured_decisions,guaranteed_coverage,standard_debates]
  ]
  MEDIATED::[
    SEQUENCE::pick_next_speaker(thread_id,role),
    USE_FOR::[dynamic_debates,breaking_deadlocks,role_skipping,multi_agent_same_cognition],
    WARNING::"Can bias outcomes if roles starved"
  ]

§5::PATTERNS
  FLASH_DEBATE::[
    PURPOSE::"Quick 3-turn decision cycle",
    SEQUENCE::init→wind_turn→wall_turn→door_turn→close,
    CONSTRAINT::"Server orchestrates state, caller supplies content"
  ]
  SOCRATIC::[
    PURPOSE::"Premise clarification before positions",
    ROUND_1::"Questions only (What does X mean? Do we have metrics?)",
    ROUND_2+::"Positions after definitions established",
    ENFORCEMENT::"Convention, not server-enforced"
  ]
  MULTI_MODEL::[
    WIND::clink(gemini,ideator)→PATHOS_exploration,
    WALL::clink(codex,validator)→ETHOS_validation,
    DOOR::Claude_synthesis→LOGOS_integration,
    AUDIT::agent_role+model_in_turn_metadata
  ]

§6::TRIGGERS
  // When to escalate to debate-hall
  CONDITIONS::[
    complex_architectural_decision,
    multiple_valid_approaches,
    unclear_tradeoffs,
    reviewer_disagreement[CE⇌CRS],
    high_risk_implementation
  ]
  INTEGRATION::[
    IF::complexity_trigger_detected,
    THEN::init_debate(thread_id:"ho-{task}-{ts}",topic:decision_point,mode:"mediated"),
    RUN::Wind→Wall→Door_cycle,
    APPLY::synthesis_to_task
  ]

§7::ADMIN
  FORCE_CLOSE::[
    PURPOSE::"I5 safety kill switch",
    CALL::force_close_debate(thread_id,reason)
  ]
  TOMBSTONE::[
    PURPOSE::"Redact turn preserving hash chain",
    CALL::tombstone_turn(thread_id,turn_index,reason)
  ]

§8::BEST_PRACTICES
  SINGLE_AGENT::adopt_each_role_in_sequence["What if..."|"Yes, but..."|"Therefore..."]
  MULTI_AGENT::assign_models_per_cognition[creative→Wind,analytical→Wall,balanced→Door]
  THIRD_WAY::"Best debates synthesize what neither Wind nor Wall proposed alone"
  PERSISTENCE::output_format:'octave'→auditable_.oct.md_transcripts

§9::EXAMPLE
  // Microservices decision
  INIT::init_debate("microservices-decision","Should we migrate to microservices?")
  WIND::"What if we decomposed? Independent scaling, tech diversity, team autonomy..."
  WALL::"Yes, but 3 developers. Operational complexity, distributed transactions..."
  DOOR::"Therefore: Modular monolith. Design boundaries now, deploy unified. Extract when team grows."
  CLOSE::close_debate(thread_id,synthesis,output_format:"octave")

§10::RESOURCES
  AGENTS::agents/README.md[Wind/Wall/Door_definitions]
  CONTRACTS::docs/wall-content-contract.oct.md[blocking_semantics]
  PATTERNS::docs/examples/multi-model-debate-patterns.md[real_debates]
  ORCHESTRATION::ho-orchestrate[HestAI_integration]

===END===
