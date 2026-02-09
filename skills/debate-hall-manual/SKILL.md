---
name: debate-hall-manual
description: Manual turn-by-turn debate control for custom orchestration scenarios.
triggers: ["manual debate", "turn by turn", "init debate", "add turn", "custom orchestration", "mediated mode"]
allowed-tools: ["Read", "mcp__debate-hall__init_debate", "mcp__debate-hall__add_turn", "mcp__debate-hall__get_debate", "mcp__debate-hall__close_debate", "mcp__debate-hall__pick_next_speaker"]
---

===DEBATE_HALL_MANUAL===

META:
  TYPE::SKILL[FOCUSED]
  VERSION::"1.0"
  PURPOSE::"Manual turn-by-turn debate control"
  ROUTER::debate-hall

§1::WORKFLOW
  SEQUENCE::INIT→TURN→GET→CLOSE

§2::TOOLS

  INIT_DEBATE::[
    thread_id::REQUIRED[FORMAT:"YYYY-MM-DD-descriptor"],
    topic::REQUIRED,
    mode::"fixed"|"mediated"[default:fixed],
    max_turns::12[default],
    max_rounds::4[default],
    strict_cognition::false[default]
  ]

  ADD_TURN::[
    thread_id::REQUIRED,
    role::REQUIRED["Wind"|"Wall"|"Door"],
    content::REQUIRED,
    cognition::PATHOS|ETHOS|LOGOS[optional],
    agent_role::STRING[audit_trail],
    model::STRING[audit_trail]
  ]

  GET_DEBATE::[
    thread_id::REQUIRED,
    include_transcript::true[default],
    context_turns::INTEGER[optional_limit]
  ]

  CLOSE_DEBATE::[
    thread_id::REQUIRED,
    synthesis::REQUIRED[Door_final_text],
    output_format::"json"|"octave"|"both"
  ]

  PICK_NEXT_SPEAKER::[
    thread_id::REQUIRED,
    role::"Wind"|"Wall"|"Door",
    USE_IN::mediated_mode_only
  ]

§3::MODES

  FIXED::[
    SEQUENCE::Wind→Wall→Door→repeat,
    USE_FOR::[structured_decisions,guaranteed_coverage]
  ]

  MEDIATED::[
    SEQUENCE::pick_next_speaker_determines_order,
    USE_FOR::[dynamic_debates,breaking_deadlocks],
    WARNING::"Can bias outcomes if roles starved"
  ]

§4::EXAMPLE
  init_debate("2026-02-09-api-design","REST vs GraphQL?")
  add_turn(thread_id,"Wind","What if GraphQL? Single endpoint, client flexibility...")
  add_turn(thread_id,"Wall","Yes, but complexity. Team experience, caching challenges...")
  add_turn(thread_id,"Door","Therefore: REST for public API, GraphQL for internal dashboard...")
  close_debate(thread_id,synthesis,output_format:"octave")

§5::PARALLEL_AGENTS
  // Restored from monolith §4.1, §7.4, §11

  DEFINITIONS::[
    PARALLEL_THINKING::"Generate candidate turns concurrently off-server (multiple models/processes)",
    SEQUENTIAL_COMMIT::"Persist turns in strict order via add_turn (one committed head at a time)"
  ]

  HARD_RULES::[
    DOOR_NEVER_SYNTHESIZES_BEFORE_WIND_AND_WALL_COMMITTED,
    WALL_REALITY_TESTS_CONCRETE_WIND_OUTPUT,
    ONE_COMMIT_PER_THREAD_AT_A_TIME[avoid_lost_updates],
    RETRY_ON_STALE_STATE::get_debate→regenerate→add_turn
  ]

  BARRIER_PROTOCOL::[
    ROUND::Rk[
      STEP_1::snapshot=get_debate(thread_id),
      STEP_2::spawn_parallel_drafts[Wind_draft,Wall_draft],
      STEP_3::serial_commit::add_turn(Wind)→add_turn(Wall),
      STEP_4::Door_reads_latest=get_debate(thread_id)→synthesize→add_turn(Door),
      STEP_5::repeat_or_close
    ]
  ]

  BEST_PRACTICES::[
    DEFAULT::parallel_draft_sequential_commit,
    DOOR_BARRIER::"Door must read latest state after Wind+Wall commits",
    WALL_FRAMEWORK_MODE::"If drafting early, write constraints then apply post-Wind"
  ]

  DEPLOYMENT::REQUIRE::DEBATE_HALL_STATE_DIR_set_to_shared_location[avoid_split_brain]

===END===
