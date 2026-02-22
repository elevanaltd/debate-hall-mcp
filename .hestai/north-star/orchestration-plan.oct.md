===ORCHESTRATION_PLAN===

META:
  TYPE::BUILD_ORCHESTRATION
  VERSION::"1.0"
  STATUS::ACTIVE
  ORCHESTRATOR::holistic-orchestrator
  SESSION::36d2503d

§1::SCOPE

PRODUCT::debate-hall-mcp
GOAL::"Production-grade MCP server for Wind/Wall/Door debate orchestration"
NORTH_STAR_REF::000-DEBATE-HALL-MCP-NORTH-STAR.oct.md

METHODOLOGY::[
  TDD::RED→GREEN→REFACTOR[git_evidence],
  DELEGATION::HO_diagnoses→IL_implements→CE_reviews,
  QUALITY::90%+_coverage+type_safe+lint_clean,
  FORMAT::OCTAVE_everywhere[octave-literacy+octave-mythology]
]

§2::PHASE_SEQUENCE

B0::WORKSPACE_SETUP[
  STATUS::PENDING,
  OWNER::holistic-orchestrator[direct_write_allowed],
  TASKS::[
    T1::git_init,
    T2::pyproject.toml[mcp_sdk+pytest+ruff+black+mypy],
    T3::directory_structure[src/debate_hall_mcp/+tests/],
    T4::CI_config[.github/workflows/ci.yml],
    T5::.hestai/state/context/PROJECT-CONTEXT.oct.md
  ],
  GATE::workspace_ready[can_run_pytest+can_run_ruff]
]

B1::FOUNDATION[
  STATUS::PENDING,
  OWNER::implementation-lead[DELEGATED],
  TASKS::[
    T1::test_state.py→state.py[DebateRoom_model+JSON_persistence],
    T2::test_engine.py→engine.py[turn_logic+mode_handling+limits],
    T3::test_server.py→server.py[MCP_scaffold+tool_registration]
  ],
  SKILLS_REQUIRED::[build-execution, octave-literacy],
  GATE::foundation_tests_pass[pytest_green]
]

B2::FEATURE_IMPLEMENTATION[
  STATUS::PENDING,
  OWNER::implementation-lead[DELEGATED],
  TASKS::[
    T1::test_init.py→tools/init.py,
    T2::test_turn.py→tools/turn.py,
    T3::test_next.py→tools/next.py,
    T4::test_status.py→tools/status.py,
    T5::test_close.py→tools/close.py,
    T6::test_pick.py→tools/pick.py,
    T7::test_admin.py→tools/admin.py
  ],
  SKILLS_REQUIRED::[build-execution, octave-literacy],
  GATE::all_tool_tests_pass+type_check_clean
]

B3::INTEGRATION[
  STATUS::PENDING,
  OWNER::implementation-lead[DELEGATED],
  TASKS::[
    T1::e2e_debate_flow_test,
    T2::MCP_client_compatibility_test,
    T3::OCTAVE_validation_test
  ],
  GATE::e2e_green+manual_MCP_test_pass
]

B4::DOCUMENTATION[
  STATUS::PENDING,
  OWNER::system-steward[DELEGATED],
  TASKS::[
    T1::README.md[quick_start+value_prop],
    T2::docs/usage.md[examples],
    T3::docs/cognition-prompts.md[Wind/Wall/Door_templates]
  ],
  GATE::README_explains_value_in_30s
]

B5::RELEASE[
  STATUS::PENDING,
  OWNER::holistic-orchestrator,
  TASKS::[
    T1::PyPI_package_prep,
    T2::GitHub_release,
    T3::MCP_registry_submission
  ],
  GATE::pip_install_works+external_user_success
]

§3::DELEGATION_MATRIX

CODE_IMPLEMENTATION::[
  DELEGATE_TO::Task(implementation-lead),
  REQUIRE::[build-execution, octave-literacy, octave-mythology],
  CONTEXT::Context7_for_MCP_SDK_docs,
  HANDOFF_TEMPLATE::HO_diagnoses→IL_implements→return_result
]

TEST_REVIEW::[
  DELEGATE_TO::mcp__pal__clink(gemini, test-methodology-guardian),
  REQUIRE::evidence_based_coverage_analysis
]

CODE_REVIEW::[
  GATE_1::mcp__pal__clink(gemini, code-review-specialist),
  GATE_2::mcp__pal__clink(claude, critical-engineer),
  ON_BLOCKING::return_to_IL_with_rework_guidance
]

§4::QUALITY_GATES

GATE_B0::workspace_ready[
  CHECK::pytest_runs,
  CHECK::ruff_configured,
  CHECK::mypy_configured,
  CHECK::git_initialized
]

GATE_B1::foundation_tests_pass[
  CHECK::pytest_green,
  CHECK::coverage_90%+_on_core,
  CHECK::mypy_clean
]

GATE_B2::all_tools_implemented[
  CHECK::all_tool_tests_pass,
  CHECK::type_check_clean,
  CHECK::lint_clean
]

GATE_B3::integration_verified[
  CHECK::e2e_test_pass,
  CHECK::manual_MCP_test_documented
]

GATE_B4::docs_complete[
  CHECK::README_exists,
  CHECK::usage_examples_exist
]

GATE_B5::release_ready[
  CHECK::pip_install_works,
  CHECK::external_test_pass
]

§5::CRITICAL_DECISIONS

DECISION_PROTOCOL::[
  WHEN::architectural_choice_needed,
  DO::invoke_debate-hall_PoC[Wind/Wall/Door],
  AGENTS::[ideator→WIND, critical-engineer→WALL, synthesizer→DOOR],
  RECORD::debates/{decision-id}/transcript.md
]

KNOWN_DECISIONS::[
  D1::NORTH_STAR[RATIFIED::debates/north-star/],
  D2::MCP_SDK_version[PENDING],
  D3::persistence_format[PENDING::JSON_vs_SQLite]
]

§6::RISK_REGISTER

R1::SCOPE_CREEP[
  LIKELIHOOD::MEDIUM,
  IMPACT::HIGH,
  MITIGATION::strict_6_core_tools+feature_freeze
]

R2::MCP_SDK_COMPLEXITY[
  LIKELIHOOD::MEDIUM,
  IMPACT::MEDIUM,
  MITIGATION::Context7_for_current_docs+PoC_reference
]

R3::OCTAVE_OVERHEAD[
  LIKELIHOOD::LOW,
  IMPACT::MEDIUM,
  MITIGATION::control/data_plane_separation[I2_resolution]
]

§7::NEXT_ACTIONS

IMMEDIATE::[
  ACTION::Execute_B0_workspace_setup,
  OWNER::holistic-orchestrator,
  DELIVERABLE::working_dev_environment
]

THEN::[
  ACTION::Delegate_B1_to_implementation-lead,
  HANDOFF::Task(implementation-lead)[build-execution, octave-literacy]
]

===END_ORCHESTRATION_PLAN===
