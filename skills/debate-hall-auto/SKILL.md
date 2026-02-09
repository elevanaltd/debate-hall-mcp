---
name: debate-hall-auto
description: Automated Wind/Wall/Door debate orchestration with tier-based model selection.
triggers: ["run debate", "resolve question", "automated debate", "resume debate", "tier selection"]
allowed-tools: ["Read", "mcp__debate-hall__run_debate", "mcp__debate-hall__resolve_question", "mcp__debate-hall__resume_debate", "mcp__debate-hall__search_decisions"]
---

===DEBATE_HALL_AUTO===

META:
  TYPE::SKILL[FOCUSED]
  VERSION::"1.0"
  PURPOSE::"Automated debate orchestration via run_debate and resolve_question"
  ROUTER::debate-hall

§1::TOOLS

  RUN_DEBATE::[
    PURPOSE::"Single-call automated Wind/Wall/Door debate",
    PARAMS::[
      topic::REQUIRED[question_or_decision],
      tier::"fast"|"standard"|"premium"[default:standard],
      thread_id::OPTIONAL[auto_generated_if_omitted],
      compression_tier::"none"|"basic"|"aggressive"|"ultra",
      primer_tier::"none"|"literacy"|"standard"|"advanced"
    ],
    RETURNS::synthesis+turn_count+status
  ]

  RESOLVE_QUESTION::[
    PURPOSE::"Highest-level API - debate + decision record in one call",
    PARAMS::[topic::REQUIRED,tier::OPTIONAL,thread_id::OPTIONAL],
    RETURNS::DecisionRecord[thread_id,synthesis,rationale,validation,provenance]
  ]

  RESUME_DEBATE::[
    PURPOSE::"Continue PAUSED debates after provider timeouts",
    PARAMS::[thread_id::REQUIRED,tier::OPTIONAL],
    USE_WHEN::status="PAUSED"
  ]

  SEARCH_DECISIONS::[
    PURPOSE::"Find past decisions by topic",
    PARAMS::[query::REQUIRED,limit::10,min_score::0.0],
    RETURNS::ranked_results[thread_id,topic,synthesis,score]
  ]

§2::TIER_CONFIGURATIONS

  FAST::[
    COST::~$0.02,
    MODELS::[gemini-3-flash,gpt-5.1-codex-mini,claude-haiku-4.5],
    MAX_TURNS::6,
    CONSENSUS::false,
    USE_FOR::[exploration,low_stakes,rapid_iteration]
  ]

  STANDARD::[
    COST::~$0.30,
    MODELS::[gemini-3-pro,gpt-5.2-codex,claude-sonnet-4.5],
    MAX_TURNS::12,
    REFINEMENT_LOOPS::4,
    USE_FOR::[design_decisions,medium_complexity]
  ]

  PREMIUM::[
    COST::~$0.60,
    MODELS::[claude-opus-4.5,gpt-5.2-pro,gemini-3-pro],
    MAX_TURNS::16,
    REFINEMENT_LOOPS::5,
    CONSENSUS::true,
    USE_FOR::[production_decisions,high_stakes]
  ]

§3::EXAMPLES

  QUICK::run_debate("Redis vs Memcached for sessions?",tier:"fast")
  STANDARD::run_debate("API versioning strategy?",tier:"standard")
  PREMIUM::resolve_question("Migrate PostgreSQL to CockroachDB?",tier:"premium")

§4::BEST_PRACTICES
  TIER_SELECTION::"Match tier to decision gravity"
  ESCALATION::"If fast insufficient, re-run with premium"
  THIRD_WAY::"Best debates synthesize what neither Wind nor Wall proposed alone"

===END===
