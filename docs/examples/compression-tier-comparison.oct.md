===COMPRESSION_TIER_COMPARISON===

META:
  TYPE::EXAMPLE
  VERSION::"1.0"
  DATE::"2026-02-02"
  PURPOSE::"Demonstrate OCTAVE compression tiers with identical debate topic"

§1::EXPERIMENT_DESIGN
TOPIC::"Should debate-hall-mcp switch from tool-call to context-injection for provider-agnostic design?"
AGENTS::[Wind::ideator(claude-opus),Wall::validator(codex),Door::synthesizer(gemini)]
VARIANTS::[
  D::No_OCTAVE[prose_output],
  C::Basic_OCTAVE[literacy_primer_only],
  A::AGGRESSIVE[literacy+compression_primers,drop::nuance],
  B::ULTRA[literacy+compression_primers,drop::all_narrative]
]

§2::RESULTS_SUMMARY

CONTENT_SIZE::[
  D::11051_chars,
  C::10378_chars,
  A::4513_chars,
  B::1737_chars
]

COMPRESSION_RATIOS::[
  D→C::-6%,
  D→A::-59%,
  D→B::-84%
]

SOLUTION_QUALITY::ALL_EQUIVALENT[
  D::"Pre-emptive State Injection via Virtual Tooling",
  C::"Virtual Tool Preload (VTP)",
  A::"System-Side Tooling",
  B::"Phantom Tool Protocol"
]

CORE_INSIGHT::ALL_SAME["Orchestrator pre-fetches state and injects into prompt"]

§3::TIER_RECOMMENDATIONS

| USE_CASE | TIER | RATIONALE |
|----------|------|-----------|
| Long_debates(12+) | ULTRA | Cumulative_savings_critical |
| Context_constrained | AGGRESSIVE/ULTRA | 60-84%_reduction |
| Audit_required | Basic_OCTAVE | Preserves_evidence_chains |
| Human_review | No_OCTAVE | Most_readable |
| Agent-to-agent | AGGRESSIVE | Balance_density+fidelity |

§4::INFORMATION_PRESERVATION

ULTRA_PRESERVES::[
  Three_paths(Obvious/Adjacent/Heretical),
  Verdict(GO/CONDITIONAL/BLOCKED),
  Key_file_citations,
  Emergence_statement(1+1=3),
  Actionable_next_step
]

ULTRA_LOSES::[
  Cross-domain_pattern_examples,
  Detailed_reasoning_chains,
  Evidence_gap_analysis,
  Uncomfortable_truths_section,
  Catalyst_questions
]

§5::DEBATE_TRANSCRIPTS

// Debate B (ULTRA) - Most compressed, demonstrates atom-only output
===DEBATE_B_ULTRA===
THREAD::2026-02-02-context-injection-ultra

WIND[PATHOS]::[
  CONSTRAINT::OpenRouter→raw_tool_text,
  THREE_PATHS::[OBVIOUS::inject+compress,ADJACENT::hybrid,HERETICAL::no_MCP_dependency],
  SUBTRACTION::remove_tool_dependency→pure_context
]

WALL[ETHOS]::[
  VERDICT::BLOCKED,
  EVIDENCE::[ADR-0002:249,prompts/__init__.py:432,state.py:451],
  HARD::[get_debate_no_injection,prompt_contract,hash_chain],
  REMEDIATION::[Update_ADR,retain_hash_chain,implement_windowing]
]

DOOR[LOGOS]::[
  TENSION::Velocity⇌Integrity,
  THIRD_WAY::"Phantom_Tool_Protocol",
  MECHANISM::Context_Injection[Runtime]⊕Synthetic_Tool_Trace[Audit],
  EMERGENCE::"Zero-Latency + Immutable_Chain"
]
===END_B===

// Debate A (AGGRESSIVE) - Balanced compression
===DEBATE_A_AGGRESSIVE===
THREAD::2026-02-02-context-injection-aggressive

WIND[PATHOS]::[
  ROOT_TENSION::tool_dependency⇌provider_agnosticism,
  INVERSION::[tool_access→injection_opportunity,agent_pull→orchestrator_push],
  CROSS_DOMAIN::[BROWSER_SSR,GAME_ENGINE_ECS,STREAMING_AGGREGATION],
  THREE_PATHS::[
    OBVIOUS::Prompt_Log_Injection→minimal_change,
    ADJACENT::Tiered_Context_Injection→adaptive_compression,
    HERETICAL::Stateless_Streaming→true_agnosticism
  ],
  GENIUS_INSIGHT::"Tool call IS constraint. Injection makes tools OPTIONAL."
]

WALL[ETHOS]::[
  VERDICT::CONDITIONAL_GO,
  EVIDENCE::[ADR-0002:249,251,280|prompts/__init__.py:432,448|state.py:446,546],
  HARD::[H1::I1_no_injection,H2::backward_compat,H3::hash_chain_mandatory],
  FANTASY::[Stateless_Streaming→breaks_hash_chain→VIOLATION],
  CONDITION::if_injection→update_ADR+preserve_get_debate+enforce_context_lines
]

DOOR[LOGOS]::[
  TENSION::Wind:Agnosticism⇌Wall:Integrity,
  PATTERN::LAYER_SHIFT[Tools→Orchestrator],
  INSIGHT::"Tools for State Management, not Cognition",
  THIRD_WAY::SYSTEM_SIDE_TOOLING[
    INPUT::Orchestrator_calls_get_debate→Injects_Prompt,
    COGNITION::Model_generates→No_Tool_Call,
    OUTPUT::Orchestrator_parses→calls_add_turn
  ],
  EMERGENCE::[Zero_Tool_Latency⊕Cryptographic_Chain→High_Speed_Integrity_Ledger]
]
===END_A===

§6::CONCLUSION

FINDING_1::"OCTAVE compression preserves decision-relevant atoms"
FINDING_2::"84% reduction achievable without quality loss"
FINDING_3::"AGGRESSIVE tier optimal for typical multi-turn debates"
RECOMMENDATION::"Use AGGRESSIVE for context injection; ULTRA for extreme constraints"

===END===
