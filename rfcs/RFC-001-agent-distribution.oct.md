===RFC===

META:
  TYPE::REQUEST_FOR_COMMENTS
  ID::"RFC-001"
  VERSION::"0.1.0"
  STATUS::DRAFT
  DATE::"2025-12-26"
  AUTHOR::Human[with_claude_assistance]
  DEBATE_REQUESTED::true

---

§1::TITLE

"GitHub Copilot Agent Distribution Strategy for debate-hall-mcp"

§2::SUMMARY

How should Wind/Wall/Door agent definitions be distributed from debate-hall-mcp
(canonical source) to consuming repositories that need them in `.github/agents/`?

§3::CONTEXT

DISCOVERY::[
  GitHub_Copilot_Custom_Agents::"`.github/agents/*.agent.md` enables role-specific AI behavior",
  Assign_to_Issue::"Built-in workflow triggers agent with issue context",
  MCP_Integration::"Copilot can connect to MCP servers (like debate-hall-mcp)"
]

CONSTRAINT::[
  NO_SYMLINKS::"GitHub requires actual files, not symlinks across repos",
  MUST_EXIST_IN_TARGET::"`.github/agents/` must contain real files in each consuming repo",
  VERSION_DRIFT::"Manual copies create drift risk between source and consumers"
]

RELATIONSHIP::[
  COGNITIONS::"/cognitions/*.oct.md"[Canonical_behavioral_contracts],
  AGENTS::"/agents/*.agent.md"[GitHub_Copilot_format_derived_from_cognitions],
  CONSUMERS::"Any repo wanting to use Wind/Wall/Door via Copilot"
]

§4::PROBLEM_STATEMENT

debate-hall-mcp has canonical cognition definitions that should be the source
of truth for Wind/Wall/Door behavioral contracts. However, GitHub Copilot
requires `.github/agents/*.agent.md` files to exist IN EACH REPOSITORY
that wants to use them.

QUESTIONS::[
  Q1::"Where should master agent definitions live?",
  Q2::"How do consuming repos receive and keep them in sync?",
  Q3::"What happens when cognitions evolve?",
  Q4::"Should agents be generated from cognitions or authored separately?"
]

§5::OPTIONS_IDENTIFIED

OPTION_A::MANUAL_COPY[
  MECHANISM::"User manually copies agent files",
  PROS::[explicit,simple,no_tooling_required],
  CONS::[drift_risk,manual_effort,no_versioning],
  EFFORT::LOW
]

OPTION_B::CLI_INSTALL[
  MECHANISM::"`debate-hall install-agents --target /path/to/repo`",
  PROS::[automated,versioned,single_command],
  CONS::[requires_CLI_installation,user_must_run],
  EFFORT::MEDIUM
]

OPTION_C::GITHUB_ACTION_SYNC[
  MECHANISM::"Scheduled workflow syncs from debate-hall-mcp",
  PROS::[automated,always_current,no_manual_intervention],
  CONS::[complexity,needs_PAT,cross_repo_permissions],
  EFFORT::HIGH
]

OPTION_D::NPM_PACKAGE[
  MECHANISM::"`npm install debate-hall-agents` + postinstall copy",
  PROS::[standard_tooling,versioned,dependency_managed],
  CONS::[overhead_for_non_JS_repos,indirect],
  EFFORT::MEDIUM
]

OPTION_E::TEMPLATE_REPO[
  MECHANISM::"Fork/template includes agents, updated manually",
  PROS::[one_time_setup,familiar_pattern],
  CONS::[no_updates_after_fork,version_frozen],
  EFFORT::LOW
]

OPTION_F::GENERATE_FROM_COGNITIONS[
  MECHANISM::"`scripts/generate-agents.py` transforms cognitions → GitHub agents",
  PROS::[single_source_of_truth,enforces_fidelity,auditable_transformation],
  CONS::[build_step_required,format_coupling],
  EFFORT::MEDIUM
]

§6::PROPOSED_ARCHITECTURE

Based on initial analysis, recommend combination:

MASTER_SOURCE::debate-hall-mcp/agents/[
  DERIVED_FROM::"/cognitions/*.oct.md"_via_generate-agents.py,
  AUTHORITATIVE::true,
  VERSIONED::git_tags
]

DISTRIBUTION_MECHANISM::CLI_INSTALL[
  COMMAND::"`debate-hall install-agents`",
  ALTERNATIVE::"`uvx debate-hall-mcp install-agents`",
  OUTPUT::[
    ".github/agents/wind.agent.md",
    ".github/agents/wall.agent.md",
    ".github/agents/door.agent.md",
    ".github/agents/README.md"[with_source_version_header]
  ]
]

SYNC_INDICATOR::[
  HEADER_IN_COPIED_FILES::"# Source: debate-hall-mcp v{version} @ {commit_sha}",
  ENABLES::"Consumers can check if they're out of date"
]

§7::QUESTIONS_FOR_DEBATE

FOR_WIND::[
  "What edges have we not explored?",
  "Is there a more elegant distribution pattern?",
  "What emergent capabilities could this enable?"
]

FOR_WALL::[
  "What constraints make certain options non-viable?",
  "What will break in practice?",
  "What's the maintenance burden of each option?"
]

FOR_DOOR::[
  "Can options be combined for best of all worlds?",
  "What's the minimum viable distribution mechanism?",
  "How does this integrate with Issue #60 Agoral Forge?"
]

§8::RELATION_TO_EXECUTION_TIERS

TIER_1_GENERIC::Uses_agents_as_is[
  SCENARIO::"Quick debate, generic Wind/Wall/Door",
  AGENT_REQUIREMENT::"Standard agents from debate-hall-mcp suffice"
]

TIER_2_BESPOKE::May_customize_agents[
  SCENARIO::"Expert team debate with specialized instructions",
  AGENT_REQUIREMENT::"Might want project-specific Wind/Wall/Door variants",
  QUESTION::"Should CLI support merging custom instructions?"
]

§9::DECISION_REQUESTED

After debate, produce ADR answering:
1. Master source location (debate-hall-mcp/agents/ confirmed?)
2. Primary distribution mechanism (CLI install, npm, GH Action, other?)
3. Generation from cognitions (automated or authored separately?)
4. Consumer sync strategy (manual check vs automated alerts)

===END_RFC===
