===PROJECT_CONTEXT===

META:
  TYPE::PROJECT_CONTEXT
  VERSION::"2.1"
  GENERATED::"2025-12-31"
  STATUS::POST_BUILD_MAINTENANCE

§1::IDENTITY

NAME::debate-hall-mcp
PURPOSE::"Production-grade MCP server for Wind/Wall/Door debate orchestration"
NORTH_STAR::.hestai/workflow/000-DEBATE-HALL-MCP-NORTH-STAR.oct.md
NORTH_STAR_STATEMENT::"To construct a deterministic crucible where subjective cognitive friction is transmuted into objective structural truth through finite, governed, and verifiable dialectic."

§2::BUILD_STATUS

ALL_PHASES_COMPLETE::[
  B0::WORKSPACE_SETUP[COMPLETE],
  B1::FOUNDATION[COMPLETE],
  B2::FEATURE_IMPLEMENTATION[COMPLETE],
  B3::INTEGRATION[COMPLETE],
  B4::DOCUMENTATION[COMPLETE],
  B5::RELEASE_PREP[COMPLETE]
]

§3::QUALITY_METRICS

TESTS::[
  UNIT::89_tests,
  E2E::5_tests,
  TOTAL::94_tests,
  STATUS::ALL_PASSING
]

COVERAGE::91.44%[exceeds_90%_requirement]

TYPE_SAFETY::mypy_strict[0_errors]

LINT::ruff+black[0_violations]

§4::IMMUTABLES_IMPLEMENTED

I1::COGNITIVE_STATE_ISOLATION[
  IMPLEMENTATION::state.py[DebateRoom_model],
  VERIFICATION::all_state_server_side
]

I2::UNIVERSAL_OCTAVE_BINDING[
  IMPLEMENTATION::PLANNED[Issue_#29_auto_generate_octave_on_close],
  STATUS::cognition_validation_implemented+octave_export_pending,
  VERIFICATION::north_star_debate_used_octave
]

I3::FINITE_DIALECTIC_CLOSURE[
  IMPLEMENTATION::engine.py[max_turns+max_rounds],
  VERIFICATION::test_limits_enforcement.py
]

I4::VERIFIABLE_EVENT_LEDGER[
  IMPLEMENTATION::state.py[sha256_hash_chain],
  VERIFICATION::test_hash_chain+test_tombstone
]

I5::SOVEREIGN_SAFETY_OVERRIDE[
  IMPLEMENTATION::tools/admin.py[force_close+tombstone],
  VERIFICATION::test_admin_functions.py
]

§5::ARTIFACTS_CREATED

SOURCE_CODE::[
  src/debate_hall_mcp/__init__.py,
  src/debate_hall_mcp/state.py,
  src/debate_hall_mcp/engine.py,
  src/debate_hall_mcp/server.py,
  src/debate_hall_mcp/tools/__init__.py,
  src/debate_hall_mcp/tools/init.py,
  src/debate_hall_mcp/tools/turn.py,
  src/debate_hall_mcp/tools/next.py,
  src/debate_hall_mcp/tools/status.py,
  src/debate_hall_mcp/tools/close.py,
  src/debate_hall_mcp/tools/pick.py,
  src/debate_hall_mcp/tools/admin.py
]

TESTS::[
  tests/conftest.py,
  tests/unit/test___init__.py,
  tests/unit/test_tools_init.py,
  tests/unit/test_state.py,
  tests/unit/test_engine.py,
  tests/unit/test_server.py,
  tests/unit/tools/test_init.py,
  tests/unit/tools/test_turn.py,
  tests/unit/tools/test_next.py,
  tests/unit/tools/test_status.py,
  tests/unit/tools/test_close.py,
  tests/unit/tools/test_pick.py,
  tests/unit/tools/test_admin.py,
  tests/e2e/test_debate_flow.py,
  tests/e2e/test_mediated_mode.py,
  tests/e2e/test_limits_enforcement.py,
  tests/e2e/test_admin_functions.py
]

DOCUMENTATION::[
  README.md,
  pyproject.toml,
  .gitignore,
  .github/workflows/ci.yml
]

GOVERNANCE::[
  .hestai/workflow/000-DEBATE-HALL-MCP-NORTH-STAR.oct.md,
  .hestai/workflow/orchestration-plan.oct.md,
  .hestai/context/PROJECT-CONTEXT.oct.md,
  debates/north-star/transcript.md
]

§6::MCP_TOOLS_SUMMARY

CORE_TOOLS::[
  debate_init::create_debate_room,
  debate_turn::record_agent_turn,
  debate_next::get_next_speaker_prompt,
  debate_status::view_debate_state,
  debate_close::finalize_with_synthesis
]

MEDIATED_TOOLS::[
  debate_pick::set_next_speaker
]

ADMIN_TOOLS::[
  debate_force_close::I5_kill_switch,
  debate_tombstone::I4_redaction
]

§7::META_VALIDATION

PROOF_OF_CONCEPT_SUCCESS::[
  CLAIM::"Use debate-hall to build debate-hall-mcp",
  EVIDENCE::debates/north-star/[
    WIND::proposed_6_immutables,
    WALL::challenged_with_reality,
    DOOR::synthesized_to_5_final_immutables
  ],
  RESULT::NORTH_STAR_derived_from_Wind/Wall/Door_debate
]

§8::NEXT_STEPS

RELEASE_READY::[
  PyPI::pip_install_debate-hall-mcp,
  GitHub::release_v0.1.0,
  MCP_Registry::submission_pending
]

§9::OPEN_ISSUES

PRIORITY::[
  Issue_#29::OCTAVE_auto_generate_on_close[implements_I2_fully],
  Issue_#33::storage_location_documentation[clarify_worktree_relative_behavior],
  Issue_#26::OCTAVE_format_support[broader_integration_scope]
]

CLOSED_PRS::[
  PR_#23::CLOSED[Wind_exploration_no_code],
  PR_#25::CLOSED[superseded_CLI+wrong_I2_removal+stale_agents],
  PR_#34::OPEN[quality_report_valid_for_review]
]

REPO_URL::https://github.com/elevanaltd/debate-hall-mcp

===END_PROJECT_CONTEXT===
