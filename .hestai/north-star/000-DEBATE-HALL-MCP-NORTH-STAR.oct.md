===NORTH_STAR===

META:
  TYPE::PRODUCT_NORTH_STAR
  VERSION::"1.0"
  STATUS::RATIFIED
  DATE::"2025-12-24"
  AUTHORITY::Wind/Wall/Door_Debate[debates/north-star/transcript.md]

§1::IDENTITY

NAME::debate-hall-mcp
PURPOSE::"To construct a deterministic crucible where subjective cognitive friction is transmuted into objective structural truth through finite, governed, and verifiable dialectic."

WHAT_IT_IS::[
  DEFINITION::"Production-grade MCP server implementing Wind/Wall/Door multi-perspective debate orchestration",
  PATTERN::PATHOS[Wind]→ETHOS[Wall]→LOGOS[Door],
  DELIVERY::MCP_tools[JSON-RPC_control_plane+OCTAVE_data_plane],
  TARGET::system_agnostic[any_MCP_client]
]

WHAT_IT_IS_NOT::[
  NOT::governance_system[that_is_HestAI's_job],
  NOT::model_specific[works_with_any_LLM],
  NOT::replacement_for_human_decision[advisory_tool],
  NOT::dependent_on_HestAI-MCP[standalone_product]
]

§2::IMMUTABLES

I1::COGNITIVE_STATE_ISOLATION[
  DEFINITION::"Agents operate as shared-nothing functional units; memory is ephemeral to the turn, state is exclusively managed by the Hall.",
  CONSTRAINT::"No side-channel communication; strict inputs/outputs only.",
  ENFORCEMENT::state_in_server_only+agent_receives_context_per_turn
]

I2::UNIVERSAL_OCTAVE_BINDING[
  DEFINITION::"The OCTAVE protocol is the immutable physical law of the Hall; all exchanges must parse strictly or be rejected.",
  CONSTRAINT::"Semantic validity precedes processing; junk in = rejection out.",
  ENFORCEMENT::turn_content_validation+structured_transcript
]

I3::FINITE_DIALECTIC_CLOSURE[
  DEFINITION::"Every debate instance guarantees termination via synthesis, stalemate, or exhaustion within hard resource bounds.",
  CONSTRAINT::"No infinite loops; max_turns and max_tokens are immutable properties of the room.",
  ENFORCEMENT::configurable_limits[max_turns:12, max_rounds:4]+hard_stop
]

I4::VERIFIABLE_EVENT_LEDGER[
  DEFINITION::"The Debate Transcript is a cryptographic append-only log of truth; history cannot be rewritten, only tombstoned.",
  CONSTRAINT::"Auditability > Privacy; The act of debating is a public commitment to the record.",
  ENFORCEMENT::hash_chain+tombstone_protocol_for_redaction
]

I5::SOVEREIGN_SAFETY_OVERRIDE[
  DEFINITION::"The Hall retains absolute kill-switch authority over any cognitive process violating safety or structural integrity.",
  CONSTRAINT::"System governance supersedes Agent autonomy always.",
  ENFORCEMENT::admin_tools+circuit_breaker+force_close
]

§3::ARCHITECTURE

LAYER_SEPARATION::[
  CONTROL_PLANE::JSON-RPC[MCP_protocol+tool_invocations],
  DATA_PLANE::OCTAVE[debate_content+transcripts+synthesis]
]

TOPOLOGY::HUB_AND_SPOKE[
  HUB::The_Hall[state_manager+orchestrator+arbiter],
  SPOKES::Agents[Wind|Wall|Door+external_context]
]

STATE_MODEL::[
  DEBATE_ROOM::thread_id+topic+mode+status+limits,
  TURN_HISTORY::ordered_list[role+content+timestamp+hash],
  SYNTHESIS::final_door_output+decision_record
]

§4::MCP_TOOLS

CORE_TOOLS::[
  debate_init::[create_room→thread_id+topic+mode+limits],
  debate_turn::[record_turn→role+content→update_state],
  debate_next::[get_prompt→context+history_tail+role_instruction],
  debate_status::[view_state→current_status+turn_count+next_role],
  debate_close::[finalize→synthesis+archive]
]

MEDIATED_TOOLS::[
  debate_pick::[set_next_role→override_fixed_sequence]
]

ADMIN_TOOLS::[
  debate_force_close::[emergency_stop→I5_enforcement],
  debate_tombstone::[redact_turn→I4_compliance]
]

§5::MODES

FIXED_MODE::[
  SEQUENCE::Wind→Wall→Door→Wind→Wall→Door→...,
  TERMINATION::Door_synthesis|max_turns|force_close,
  USE_CASE::structured_decision_making
]

MEDIATED_MODE::[
  SEQUENCE::orchestrator_picks_next_role,
  TERMINATION::explicit_close|max_turns|force_close,
  USE_CASE::dynamic_debates+breakdlock_handling
]

§6::QUALITY_REQUIREMENTS

PRODUCTION_GRADE::[
  TEST_COVERAGE::90%+[core_logic],
  TYPE_SAFETY::strict_mypy[no_any],
  LINT::ruff+black[zero_violations],
  DOCS::complete_tool_schemas+usage_examples
]

PERFORMANCE::[
  LATENCY::sub_100ms[state_operations],
  SCALABILITY::concurrent_debates[thread_isolation],
  PERSISTENCE::crash_recovery[state_not_lost]
]

§7::BUILD_PHASES

B0::WORKSPACE_SETUP[
  git_init+pyproject.toml+directory_structure+CI_config
]

B1::FOUNDATION[TDD][
  state.py[debate_room_model+persistence],
  engine.py[turn_logic+mode_handling+limits],
  server.py[MCP_scaffold+tool_registration]
]

B2::FEATURE_IMPLEMENTATION[TDD][
  tools/init.py[debate_init_tool],
  tools/turn.py[debate_turn_tool],
  tools/next.py[debate_next_tool],
  tools/status.py[debate_status_tool],
  tools/close.py[debate_close_tool],
  tools/pick.py[debate_pick_tool],
  tools/admin.py[force_close+tombstone]
]

B3::INTEGRATION[
  e2e_debate_flow_test,
  MCP_client_compatibility,
  OCTAVE_validation
]

B4::DOCUMENTATION[
  README.md[quick_start],
  usage_examples,
  cognition_prompt_templates
]

B5::RELEASE[
  PyPI_package,
  GitHub_release,
  MCP_registry_submission
]

§8::SUCCESS_CRITERIA

FUNCTIONAL::[
  CAN::init_debate+run_3_turns+close_with_synthesis,
  CAN::persist_state_across_tool_calls,
  CAN::both_fixed_and_mediated_modes,
  CAN::work_with_Claude_Desktop_MCP_config
]

QUALITY::[
  HAS::90%+_test_coverage,
  HAS::all_tests_passing,
  HAS::type_hints_throughout,
  HAS::ruff+black_clean
]

ADOPTION::[
  README::explains_value_in_30_seconds,
  INSTALL::running_in_5_minutes,
  PROVEN::at_least_one_external_debate_completed
]

===END_NORTH_STAR===
