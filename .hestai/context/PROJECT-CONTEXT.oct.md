===PROJECT_CONTEXT===

META:
  TYPE::PROJECT_CONTEXT
  VERSION::"1.0"
  GENERATED::"2025-12-24"
  STATUS::B0_COMPLETE

§1::IDENTITY

NAME::debate-hall-mcp
PURPOSE::"Production-grade MCP server for Wind/Wall/Door debate orchestration"
NORTH_STAR::.hestai/workflow/000-DEBATE-HALL-MCP-NORTH-STAR.oct.md

§2::CURRENT_STATE

PHASE::B0[WORKSPACE_SETUP]
STATUS::COMPLETE
NEXT_PHASE::B1[FOUNDATION]

ARTIFACTS_CREATED::[
  pyproject.toml,
  .gitignore,
  .github/workflows/ci.yml,
  src/debate_hall_mcp/__init__.py,
  src/debate_hall_mcp/tools/__init__.py,
  tests/conftest.py,
  tests/unit/test___init__.py,
  tests/unit/test_tools_init.py
]

§3::IMMUTABLES_SUMMARY

I1::COGNITIVE_STATE_ISOLATION[agents_shared_nothing]
I2::UNIVERSAL_OCTAVE_BINDING[strict_protocol]
I3::FINITE_DIALECTIC_CLOSURE[hard_limits]
I4::VERIFIABLE_EVENT_LEDGER[append_only_hash_chain]
I5::SOVEREIGN_SAFETY_OVERRIDE[kill_switch_authority]

§4::BUILD_PLAN

B1::FOUNDATION[PENDING][
  state.py::DebateRoom_model+persistence,
  engine.py::turn_logic+modes+limits,
  server.py::MCP_scaffold
]

B2::FEATURES[PENDING][
  tools/init.py,
  tools/turn.py,
  tools/next.py,
  tools/status.py,
  tools/close.py,
  tools/pick.py,
  tools/admin.py
]

B3::INTEGRATION[PENDING]
B4::DOCUMENTATION[PENDING]
B5::RELEASE[PENDING]

§5::TECHNOLOGY_STACK

LANGUAGE::Python_3.11+
MCP_SDK::mcp>=1.0.0
VALIDATION::pydantic>=2.0.0
TEST::pytest+pytest-asyncio+pytest-cov
LINT::ruff+black
TYPE::mypy[strict]

§6::QUALITY_REQUIREMENTS

COVERAGE::90%+
TYPE_SAFETY::strict_mypy
LINT::zero_violations
TDD::RED→GREEN→REFACTOR

===END_PROJECT_CONTEXT===
