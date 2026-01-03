===EXECUTION_TIERS===

META:
  TYPE::ARCHITECTURAL_SPECIFICATION
  VERSION::"1.0.0"
  STATUS::DRAFT
  PURPOSE::Define_two_tier_execution_model_for_debate_participation

---

§1::OVERVIEW

PRINCIPLE::"Debate Hall orchestrates roles, not agents"

TWO_TIERS::[
  GENERIC::"Quick synthesis via dynamically-informed generalists",
  BESPOKE::"Deep debate via domain-expert teams per aisle"
]

METAPHOR::[
  HALL::Parliament_chamber,
  WIND|WALL|DOOR::Aisles_not_individual_seats,
  AGENTS::Speakers_who_take_the_floor_from_their_aisle,
  TEAM::Multiple_experts_on_same_aisle
]

§2::TIER_1_GENERIC_MODE

PURPOSE::"Low-friction exploration for one-off topics"

CHARACTERISTICS::[
  SETUP::Minimal[topic_only],
  SPEAKERS::Generic_agents_with_cognition_overlay,
  EXPERTISE::Emergent[scout_provides_context],
  AUDIT::Anonymous[role_tracked_not_specialist_identity]
]

FLOW::[
  1::INIT[topic→scout_phase],
  2::SCOUT[
    research_topic→Context7|codebase|web,
    identify_constraints→opportunities|blockers|prior_art,
    load_context→DEBATE_CONTEXT_artifact,
    output→shared_context_for_all_speakers
  ],
  3::DEBATE[
    wind→@cognitions/wind-pathos.oct.md+DEBATE_CONTEXT+"You are an expert in {topic}",
    wall→@cognitions/wall-ethos.oct.md+DEBATE_CONTEXT+"You are an expert in {topic}",
    door→@cognitions/door-logos.oct.md+DEBATE_CONTEXT+"You are an expert in {topic}"
  ],
  4::SYNTHESIS[door_closes→actionable_decision]
]

SCOUT_AGENT::[
  ROLE::"Pre-debate intelligence gathering",
  COGNITION::None[purely_functional],
  OUTPUTS::[
    topic_brief::2-3_sentence_summary,
    key_constraints::immutable_realities,
    key_opportunities::unexplored_possibilities,
    prior_art::existing_solutions_or_patterns,
    relevant_context::codebase_files|docs|external_references
  ],
  TOOLS::[Context7,Grep,Glob,Read,WebSearch,WebFetch],
  CONSTRAINT::"Scout informs but does not participate in debate"
]

USE_WHEN::[
  "Exploring unfamiliar territory",
  "Quick brainstorm needing structured synthesis",
  "No specific domain experts required",
  "Time-constrained decision needed",
  "Topic doesn't warrant team assembly"
]

§3::TIER_2_BESPOKE_MODE

PURPOSE::"Consequential decisions via domain-expert teams"

CHARACTERISTICS::[
  SETUP::Curated[explicit_team_roster_per_aisle],
  SPEAKERS::Named_specialist_agents,
  EXPERTISE::Pre-bound[agents_bring_their_domain_authority],
  AUDIT::Full[agent_role+model+turn_attribution]
]

TEAM_STRUCTURE::[
  WIND_AISLE::[
    speakers::N_agents_bound_to_PATHOS,
    examples::[ideator-catalyst,edge-optimizer,research-analyst],
    constraint::"All Wind speakers must generate divergent options"
  ],
  WALL_AISLE::[
    speakers::N_agents_bound_to_ETHOS,
    examples::[security-specialist,supabase-expert,critical-engineer],
    constraint::"All Wall speakers must render evidence-based verdicts"
  ],
  DOOR_AISLE::[
    speakers::N_agents_bound_to_LOGOS,
    examples::[technical-architect,synthesizer,completion-architect],
    constraint::"All Door speakers must produce emergent synthesis"
  ]
]

FLOW::[
  1::ROSTER[
    define_topic→consequential_decision,
    assign_wind_team→list[agent_roles],
    assign_wall_team→list[agent_roles],
    assign_door_team→list[agent_roles]
  ],
  2::DEBATE[
    turn_n→agent_from_assigned_aisle_speaks,
    identity_tracked→agent_role+model+cognition_in_turn_metadata,
    mediated_mode_recommended→orchestrator_picks_which_expert_speaks
  ],
  3::SYNTHESIS[
    door_team_member_closes→final_synthesis,
    accountability→"Who advocated what" fully traceable
  ]
]

USE_WHEN::[
  "Architectural decisions with long-term impact",
  "Security-critical choices",
  "Cross-domain trade-offs requiring specialist knowledge",
  "Audit trail of expert input required",
  "Decisions affecting production systems"
]

§4::COMPARISON

DIMENSION|GENERIC|BESPOKE
---|---|---
Setup time|Seconds|Minutes
Expertise source|Scout-gathered context|Pre-existing agent specialization
Speaker count|1 per aisle|N per aisle
Identity tracking|Role only|Full agent metadata
Audit depth|What was said|Who said what and why they had authority
Best for|Exploration|Consequential decisions
Cognition binding|Same|Same

INVARIANT::"Both tiers use identical cognition overlays (PATHOS/ETHOS/LOGOS)"

§5::HYBRID_PATTERNS

SCOUT_PLUS_BESPOKE::[
  PATTERN::"Scout prepares context, then expert teams debate",
  USE_CASE::"Experts need shared factual foundation before disagreeing",
  FLOW::scout_phase→team_roster→bespoke_debate
]

ESCALATION::[
  PATTERN::"Start generic, escalate to bespoke if impasse",
  TRIGGER::stalemate_status|high_stakes_detected,
  FLOW::generic_debate→stalemate→assemble_expert_roster→bespoke_continuation
]

MIXED_AISLES::[
  PATTERN::"Some aisles generic, others expert",
  USE_CASE::"Domain expertise needed only on one side",
  EXAMPLE::[
    wind→generic[scout-informed],
    wall→bespoke[security-specialist+supabase-expert],
    door→generic[scout-informed]
  ]
]

§6::IMPLEMENTATION_STATUS

CURRENT::[
  SUPPORTED::Multiple_speakers_per_role[agent_role_field_in_Turn],
  SUPPORTED::Identity_tracking[agent_role+model+cognition],
  SUPPORTED::Cognition_overlays[/cognitions/*.oct.md],
  NOT_YET::Scout_agent[proposed],
  NOT_YET::Team_roster_tracking[proposed],
  NOT_YET::Execution_tier_field_in_DebateRoom[proposed]
]

NEXT_STEPS::[
  1::Add_execution_tier_enum[GENERIC|BESPOKE|HYBRID],
  2::Implement_scout_agent_pattern,
  3::Add_team_roster_field_per_aisle,
  4::Update_README_with_two-tier_model,
  5::Create_example_orchestration_scripts
]

===END===
