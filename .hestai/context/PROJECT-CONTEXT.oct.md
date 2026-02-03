===PROJECT_CONTEXT===

META:
  TYPE::PROJECT_CONTEXT
  VERSION::"4.0"
  GENERATED::"2026-02-03"
  STATUS::LAYER_3_QUERY_COMPLETE

§1::IDENTITY

NAME::debate-hall-mcp
PURPOSE::"Production-grade MCP server for Wind/Wall/Door debate orchestration with auto-orchestration"
NORTH_STAR::.hestai/workflow/000-DEBATE-HALL-MCP-NORTH-STAR.oct.md
NORTH_STAR_STATEMENT::"To construct a deterministic crucible where subjective cognitive friction is transmuted into objective structural truth through finite, governed, and verifiable dialectic."

§2::BUILD_STATUS

CURRENT_PHASE::LAYER_3_QUERY_COMPLETE[PR_#137]

THREE_LAYER_ARCHITECTURE::[
  LAYER_1::PRIMITIVES[COMPLETE][init_debate+add_turn+get_debate+close_debate+admin],
  LAYER_2::COGNITION[COMPLETE][run_debate+resume_debate+VTP+consensus],
  LAYER_3::QUERY[COMPLETE][PR_#137][resolve_question+extract_decision_record+DecisionRecord]
]

ORIGINAL_BUILD_PHASES::[
  B0::WORKSPACE_SETUP[COMPLETE],
  B1::FOUNDATION[COMPLETE],
  B2::FEATURE_IMPLEMENTATION[COMPLETE],
  B3::INTEGRATION[COMPLETE],
  B4::DOCUMENTATION[COMPLETE],
  B5::RELEASE_PREP[COMPLETE]
]

ISSUE_111_AUTO_ORCHESTRATION::[
  P1::FOUNDATION[COMPLETE][PR_#113][events.py+config.py+PAUSED_status],
  P2::PROVIDERS[COMPLETE][PR_#114][ModelProvider+CliProvider+OpenRouterProvider],
  P3::ORCHESTRATOR[COMPLETE][PR_#116][DebateOrchestrator+run_debate+prompts],
  P4::CONSENSUS[COMPLETE][PR_#117][Wind/Wall_approval+refinement_loops+resume_debate],
  P5::EVENT_DELIVERY[DEFERRED][streaming+callbacks]
]

LAYER_3_QUERY_PR_137::[
  FIX::truncation_bug[#131][remove_500_char_truncation],
  FEAT::ConsensusMetadata[persisted_in_DebateRoom],
  FEAT::DecisionRecord[schema_for_extracted_decisions],
  FEAT::extract_decision_record[MCP_tool],
  FEAT::resolve_question[high_level_API]
]

§3::QUALITY_METRICS

TESTS::[
  TOTAL::864_tests,
  STATUS::ALL_PASSING,
  NEW_TESTS::130[Layer_3_coverage]
]

TYPE_SAFETY::mypy_strict[0_errors]

LINT::ruff+black[0_violations]

§4::IMMUTABLES_IMPLEMENTED

I1::COGNITIVE_STATE_ISOLATION[
  IMPLEMENTATION::state.py[DebateRoom_model]+prompts[get_debate_instruction],
  VERIFICATION::all_state_server_side+agents_call_get_debate
]

I2::UNIVERSAL_OCTAVE_BINDING[
  IMPLEMENTATION::COMPLETE[output_format_parameter+octave_formatter.py],
  STATUS::cognition_validation_implemented+octave_export_functional,
  VERIFICATION::test_octave_formatter.py+test_octave_output.py
]

I3::FINITE_DIALECTIC_CLOSURE[
  IMPLEMENTATION::engine.py[max_turns+max_rounds]+orchestrator.py[max_refinement_loops],
  VERIFICATION::test_limits_enforcement.py+test_orchestrator_consensus.py
]

I4::VERIFIABLE_EVENT_LEDGER[
  IMPLEMENTATION::state.py[sha256_hash_chain]+events.py[CONSENSUS_VOTE],
  VERIFICATION::test_hash_chain+test_tombstone+event_log_files
]

I5::SOVEREIGN_SAFETY_OVERRIDE[
  IMPLEMENTATION::tools/admin.py[force_close+tombstone]+orchestrator.py[PAUSED_status],
  VERIFICATION::test_admin_functions.py+resume_debate_tool
]

§5::MCP_TOOLS_SUMMARY

CORE_TOOLS::[
  init_debate::create_debate_room,
  add_turn::record_agent_turn,
  get_debate::view_state_and_transcript,
  close_debate::finalize_with_synthesis
]

MEDIATED_TOOLS::[
  pick_next_speaker::set_next_speaker
]

ADMIN_TOOLS::[
  force_close_debate::I5_kill_switch,
  tombstone_turn::I4_redaction
]

AUTO_ORCHESTRATION_TOOLS::[
  run_debate::fully_automated_Wind_Wall_Door_debate,
  resume_debate::resume_PAUSED_debates_after_failure
]

LAYER_3_QUERY_TOOLS::[
  extract_decision_record::extract_DecisionRecord_from_closed_debate,
  resolve_question::high_level_API_debate_to_decision_in_one_call
]

GITHUB_TOOLS::[
  github_sync_debate::sync_turns_to_GitHub_Discussion,
  ratify_rfc::generate_ADR_from_synthesis,
  human_interject::inject_human_comment_into_debate
]

TOTAL_MCP_TOOLS::14

§6::AUTO_ORCHESTRATION_ARCHITECTURE

PROVIDERS::[
  ModelProvider::protocol_interface,
  CliProvider::claude+codex+gemini_CLI_integration,
  OpenRouterProvider::any_OpenRouter_model
]

TIER_CONFIGURATION::[
  LOCATION::~/.debate-hall/tiers.yaml_or_env_var_or_defaults,
  FIELDS::wind+wall+door[provider+cli_or_model+role]+settings[consensus_required+max_turns+max_refinement_loops]
]

CONSENSUS_MECHANISM::[
  FLOW::Wind_approves->Wall_approves->synthesis_OR_reject->Door_refines,
  PARSER::fuzzy_APPROVE_REJECT_matching+fail_safe_defaults_to_REJECT,
  EVENTS::CONSENSUS_VOTE_emitted_for_each_approval
]

FAILURE_RECOVERY::[
  STATUS::PAUSED_on_provider_failure,
  TOOL::resume_debate_continues_from_pause_point,
  CE_FIX::handles_turn_count_0_through_3_cases
]

§7::KEY_FILES

SOURCE_CODE::[
  src/debate_hall_mcp/server.py[14_MCP_tools_registered],
  src/debate_hall_mcp/orchestrator.py[DebateOrchestrator+consensus_loop+ConsensusMetadata],
  src/debate_hall_mcp/consensus.py[ConsensusResult+parse_consensus_response],
  src/debate_hall_mcp/config.py[TierConfig+RoleConfig+TierSettings],
  src/debate_hall_mcp/decision.py[DecisionRecord+extract_decision_record],
  src/debate_hall_mcp/providers/__init__.py[ModelProvider+create_provider],
  src/debate_hall_mcp/providers/cli.py[CliProvider],
  src/debate_hall_mcp/providers/openrouter.py[OpenRouterProvider],
  src/debate_hall_mcp/prompts/__init__.py[Wind_Wall_Door_approval_prompts],
  src/debate_hall_mcp/events.py[EventType+append_event],
  src/debate_hall_mcp/state.py[DebateRoom+DebateStatus+ConsensusMetadata],
  src/debate_hall_mcp/tools/orchestrate.py[run_debate+resume_debate],
  src/debate_hall_mcp/tools/decision.py[extract_decision_record+resolve_question]
]

TESTS::[
  tests/unit/test_consensus.py[28_tests],
  tests/unit/test_prompts_consensus.py[17_tests],
  tests/unit/test_orchestrator_consensus.py[10_tests],
  tests/unit/tools/test_orchestrate_resume.py[13_tests],
  tests/unit/test_decision.py[23_tests],
  tests/unit/tools/test_decision_tool.py[10_tests],
  tests/unit/test_providers.py,
  tests/unit/test_config.py
]

§8::RELATED_ISSUES

COMPLETED::[
  Issue_#111::feat_run_debate_auto_orchestration[CLOSED][all_phases_complete],
  Issue_#131::fix_truncation_bug[CLOSED][PR_#137],
  Issue_#136::cognitive_notary_architecture[DOCUMENTED]
]

OPEN::[
  Issue_#138::Layer_3_enhancements[decision_indexing+BM25_search]
]

DEPENDENT::[
  Issue_#112::Debate_Hall_App[depends_on_#111]
]

§9::REPO_INFO

REPO_URL::https://github.com/elevanaltd/debate-hall-mcp
BRANCH::new-alignment-2[Layer_3_implementation]
MERGED_PRS::[#113,#114,#116,#117,#118]
PENDING_PRS::[#137[Layer_3_Query_Infrastructure]]

===END_PROJECT_CONTEXT===
