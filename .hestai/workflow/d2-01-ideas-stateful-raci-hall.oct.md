===D2_01_IDEAS===

META:
  TYPE::IDEATION_DOCUMENT
  PHASE::D2_01[PATHOS]
  FEATURE::"Stateful RACI Hall"
  ISSUE::"#163"
  NORTH_STAR::"stateful-raci-hall-north-star.oct.md"
  COGNITION::PATHOS[Wind]
  ROLE::IDEATOR
  DATE::"2026-02-14"
  STATUS::DRAFT

===

[CONNECTIONS]

STIMULUS::The North Star (I6-I8) demands three new architectural primitives:
  1. Participant Identity Registry (I6) -- sovereign participants with prompt_source
  2. Holographic Context Compression (I7) -- ~4096 tokens of compressed shared reality
  3. Recursive Topology Closure (I8) -- nested debates with leaf-to-root closure

EXISTING_CODEBASE_PATTERNS_MAPPED::[
  TurnManifest_Compiler[raci.py:compile_raci_manifest] -> compile_raci_manifest takes RACIConfig and produces an immutable execution plan. This is a COMPILER pattern: declarative input -> deterministic execution schedule.
  VTP[orchestrator.py:_format_debate_state+_execute_role_turn] -> Virtual Tool Preload pre-fetches state and injects it into prompts. Agents receive context PASSIVELY. This IS the holographic injection mechanism.
  Consensus_Loop[orchestrator.py:_execute_consensus_loop] -> Multi-round approval with vote tracking and refinement. This is a COMMITTEE VOTE protocol.
  Event_Ledger[events.py:append_event+DebateEvent] -> ULID-ordered append-only JSONL. Events are the RAW TRUTH from which compression derives.
  Decision_Record[decision.py:extract_decision_record] -> Structured extraction of synthesis + rationale + provenance from closed debates. This IS a compression template.
  Prompt_Loader[prompts/loader.py:get_agent_prompt] -> Layered resolution: ./agents/{name}.oct.md -> .hestai-sys/library/agents/{name}.oct.md. Already resolves agent identities from file paths.
  CAS_Persistence[state.py:save_debate_state_with_retry] -> Compare-and-Swap with exponential backoff. Production-grade concurrent state management.
  DebateRoom_Model[state.py:DebateRoom] -> Pydantic model with thread_id, mode, status, turns, synthesis, turn_manifest, consensus_metadata. The ATOMIC UNIT of debate state.
]

CROSS_DOMAIN_PATTERNS::[
  COMPILER_PATTERN::raci.py's compile_raci_manifest IS the same pattern as a query planner in databases (declarative intent -> execution plan). This generalizes to a HALL WORKFLOW COMPILER.
  VTP_AS_PROJECTION::VTP in orchestrator.py IS the database materialized view pattern -- compute once, inject everywhere. The Hall compressed_log is just a larger materialized view.
  EVENT_SOURCING::events.py IS event sourcing (append-only ledger -> derived state). The Hall IS the read model projected from debate events.
  TREE_LOCKING::I8 recursive closure IS the same as database foreign key cascading -- children must resolve before parent can close. No orphans.
]

===

[POSSIBILITIES]

===PATH_1::OBVIOUS===

LABEL::"Container Wrapper"
RISK::LOW
INNOVATION::LOW
PATTERN::PATTERN_TRANSPLANT["Wrap existing primitives with new coordination layer"]

DESCRIPTION::[
  The Hall is a NEW model (HallState) that wraps existing DebateRoom instances. It adds:
  - A participant registry (dict mapping participant_id -> Participant model)
  - A list of active/completed debate thread_ids
  - A compressed_log string regenerated on debate close
  - Parent/child relationships via new fields on DebateRoom
]

ARCHITECTURE::[
  NEW_FILES::[
    src/debate_hall_mcp/hall.py[HallState model + HallEngine + persistence],
    src/debate_hall_mcp/participant.py[Participant model + ParticipantRegistry],
    src/debate_hall_mcp/compression.py[structured compression engine],
    src/debate_hall_mcp/tools/hall.py[hall_open + hall_status + hall_close + hall_register + hall_unregister + hall_debate + hall_consult]
  ],
  MODIFIED_FILES::[
    src/debate_hall_mcp/state.py[add parent_hall_id, parent_thread_id, children to DebateRoom],
    src/debate_hall_mcp/orchestrator.py[inject hall compressed_log via VTP when parent_hall_id is set],
    src/debate_hall_mcp/server.py[register 6 new MCP tools]
  ]
]

HALL_LIFECYCLE::[
  hall_open -> creates HallState JSON at {state_dir}/halls/{hall_id}.json,
  hall_register -> adds participant to registry (resolves prompt_source via get_agent_prompt),
  hall_debate -> calls debate_init + compiles RACI manifest from registry + runs orchestration,
  close_debate (existing) -> triggers hall compression_engine to regenerate compressed_log,
  hall_close -> validates all children closed (I8) -> archives final compressed_log
]

COMPRESSION_APPROACH::[
  STRATEGY::STRUCTURED_EXTRACTION[per NR4],
  FORMAT::OCTAVE[
    DECISIONS::[{thread_id, topic, verdict, status}...],
    ACTIVE::[{thread_id, topic, turn_count, participants}...],
    PARTICIPANTS::[{id, name, status, raci_designation}...],
    UNRESOLVED::[explicit markers for open questions]
  ],
  TOKEN_BUDGET::Each decision ~100 tokens -> ~40 decisions in 4096 tokens,
  TRIGGER::On debate_close when parent_hall_id is set
]

PARTICIPANT_REGISTRY::[
  REGISTRATION::hall_register(hall_id, name, kind, prompt_source, provider_config, capabilities),
  RESOLUTION::prompt_source -> get_agent_prompt(name) (existing loader.py pattern),
  INJECTION::On turn request load prompt_source content and inject as system context,
  RACI_ASSIGNMENT::capabilities list enables tag-based matching for auto-RACI assignment
]

STRENGTHS::[
  "Zero risk to existing 864 tests -- purely additive",
  "Each component testable in isolation",
  "Clear separation of concerns: Hall manages lifecycle, DebateRoom manages debate",
  "Reuses ALL existing persistence patterns (JSON files, CAS, file locking)"
]

WEAKNESSES::[
  "New files increase surface area (~6 new files, ~2000 LOC estimated)",
  "Dual state management: HallState + DebateRoom must stay synchronized",
  "Compression regeneration on every debate_close could be expensive for large halls",
  "The 'wrapper' pattern adds indirection without simplifying the core model"
]

===

===PATH_2::ADJACENT===

LABEL::"Manifest Compiler Generalization"
RISK::MEDIUM
INNOVATION::MEDIUM
PATTERN::CONSTRAINT_INVERSION["The TurnManifest compiler pattern from RACI mode generalizes to a HALL WORKFLOW COMPILER"]

DESCRIPTION::[
  KEY_INSIGHT::The TurnManifest (raci.py:compile_raci_manifest) already compiles governance topology into execution plans. The Hall is ITSELF a manifest -- a multi-debate workflow plan. Instead of the Hall being a container with imperative lifecycle management, it becomes a COMPILED WORKFLOW that the orchestrator executes.

  The Hall Manifest Compiler takes:
    INPUT::HallConfig (participants, debate_schedule, RACI_assignments, depth_limits)
    OUTPUT::HallManifest (ordered list of DebateSpec + dependency graph + compression checkpoints)

  The orchestrator then executes the HallManifest as a sequence (same pattern as RACI turn execution in orchestrator.py:run_raci, lines 1543-1611).
]

ARCHITECTURE::[
  CORE_INSIGHT::"Reuse compile_raci_manifest pattern at a higher abstraction level",
  NEW_MODELS::[
    HallConfig::declarative_hall_specification[participants, debates, topology],
    HallManifest::compiled_execution_plan[debate_specs, dependency_graph, compression_checkpoints],
    DebateSpec::single_debate_specification[topic, raci_config, parent_thread_id, depth],
    Participant::registry_entry[name, kind, prompt_source, provider_config, capabilities]
  ],
  NEW_FILES::[
    src/debate_hall_mcp/hall_compiler.py[compile_hall_manifest from HallConfig],
    src/debate_hall_mcp/hall_state.py[HallState model + persistence],
    src/debate_hall_mcp/hall_orchestrator.py[execute HallManifest],
    src/debate_hall_mcp/compression.py[structured extraction engine],
    src/debate_hall_mcp/tools/hall.py[MCP tool surface]
  ]
]

VTP_AS_HOLOGRAPHIC_INJECTOR::[
  EXISTING::orchestrator.py:_format_debate_state builds <DEBATE_STATE> XML tags and injects into prompts,
  EXTENSION::Add <HALL_CONTEXT> tag injection alongside <DEBATE_STATE>,
  MECHANISM::[
    1. On each turn request within a hall-managed debate,
    2. Load hall compressed_log from HallState,
    3. Prepend as <HALL_CONTEXT>...compressed OCTAVE...</HALL_CONTEXT>,
    4. Existing VTP machinery (<DEBATE_STATE>) remains unchanged,
    5. Agent sees: <HALL_CONTEXT> + <DEBATE_STATE> + user_prompt
  ],
  PATTERN_NAME::HOLOGRAPHIC_VTP[
    "The VTP already pre-fetches and injects debate state.",
    "Extending it to inject hall context is a natural generalization.",
    "The 'holographic' property: every agent sees the same compressed reality."
  ]
]

CONSENSUS_AS_COMMITTEE_VOTE::[
  EXISTING::orchestrator.py:_execute_consensus_loop implements Wind+Wall approval voting,
  EXTENSION::"What if we generalize consensus to N-participant committee votes?",
  MECHANISM::[
    Within a Hall a debate synthesis could require approval from K of N registered participants,
    This is the consensus_loop pattern generalized from 2 voters (Wind+Wall) to K-of-N,
    The committee vote becomes a sub-debate spawned by the Hall,
    Approval threshold is configurable on the Hall
  ],
  CAUTION::"This adds complexity. The North Star NR3 says no dynamic reassignment within a debate. Committee votes would need to be a SEPARATE debate instance, not in-debate consensus."
]

EVENT_SOURCING_FOR_COMPRESSION::[
  EXISTING::events.py stores DEBATE_STARTED, TURN_ADDED, CONSENSUS_VOTE, DEBATE_CLOSED events,
  EXTENSION::Add HALL-level events (HALL_OPENED, PARTICIPANT_REGISTERED, DEBATE_SPAWNED, HALL_CLOSED),
  COMPRESSION_SOURCE::"The compressed_log is a PROJECTION of the event ledger",
  MECHANISM::[
    1. Hall events form their own JSONL ledger ({state_dir}/halls/{hall_id}.events.jsonl),
    2. Compression engine reads event stream + completed debate syntheses,
    3. Produces structured OCTAVE summary within token budget,
    4. This IS event sourcing: events = source of truth, compressed_log = read model
  ]
]

STRENGTHS::[
  "Compiler pattern is ALREADY proven in raci.py -- transplanting it to Hall level",
  "VTP extension is minimal -- add one more tag to existing injection point",
  "Event-sourced compression aligns with I4 (events ARE the source of truth)",
  "Declarative HallConfig enables future features: hall templates, replay, dry-run"
]

WEAKNESSES::[
  "The manifest compiler adds design complexity upfront",
  "Pre-compiled workflows are less flexible for dynamic scenarios (ad-hoc sub-debates)",
  "Dependency graph execution is more complex than simple sequential orchestration"
]

===

===PATH_3::HERETICAL===

LABEL::"Hall AS DebateRoom"
RISK::HIGH
INNOVATION::HIGH
PATTERN::SUBTRACTION_INNOVATION["What if we REMOVED the container and made the Hall a special DebateRoom mode?"]

DESCRIPTION::[
  PROVOCATION::What if there is no HallState model at all?

  The existing DebateRoom already has:
  - thread_id (identity)
  - mode enum (FIXED, MEDIATED, SPEED, RACI -- add HALL)
  - status enum (ACTIVE, PAUSED, SYNTHESIS, etc.)
  - turns list (state history)
  - turn_manifest (compiled execution plan)
  - consensus_metadata (vote tracking)
  - injected_context (human participation)
  - GitHub binding (external sync)

  What if DebateMode.HALL is a new mode where:
  - turns can contain BOTH debate content AND hall management events,
  - turn_manifest becomes a HallManifest (list of DebateSpec),
  - the "synthesis" field becomes the compressed_log,
  - sub-debates are DebateRooms with parent_thread_id pointing back to the Hall Room,
  - participant registration is a special turn type (like TurnType.REGISTRATION),
  - the existing engine, persistence, hash chain, events ALL apply unchanged

  The Hall IS a DebateRoom with extended lifecycle.
]

ARCHITECTURE::[
  MODIFIED_ONLY::[
    src/debate_hall_mcp/state.py[
      ADD::DebateMode.HALL,
      ADD::TurnType.REGISTRATION|COMPRESSION|SPAWN,
      ADD::parent_thread_id and children fields to DebateRoom,
      ADD::participant_registry dict to DebateRoom,
      ADD::compressed_log field to DebateRoom
    ],
    src/debate_hall_mcp/engine.py[
      EXTEND::add_turn to handle REGISTRATION/COMPRESSION/SPAWN turn types,
      EXTEND::close_debate to check children closure (I8)
    ],
    src/debate_hall_mcp/orchestrator.py[
      ADD::run_hall method (parallel to run_raci and run_speed),
      EXTEND::_format_debate_state to include hall context for child debates,
      ADD::_execute_hall_lifecycle method
    ],
    src/debate_hall_mcp/tools/hall.py[
      NEW::MCP tool wrappers that delegate to engine/orchestrator
    ]
  ],
  ZERO_NEW_MODELS::"No new state models. DebateRoom IS the Hall.",
  PERSISTENCE::"Unchanged. Hall IS a DebateRoom JSON file."
]

TURN_TYPE_EXTENSION::[
  EXISTING::[PROPOSAL, ADVICE, REBUTTAL, VERDICT, OBSERVATION],
  NEW::[
    REGISTRATION::"Participant joins the hall. Content is structured participant info.",
    COMPRESSION::"System-generated compressed_log turn. Appears after debate close.",
    SPAWN::"System-generated turn recording sub-debate creation.",
    CONSULTATION::"Lightweight 2-turn advisory exchange."
  ],
  INSIGHT::"Every hall action becomes a turn in the hash chain (I4). Registration, compression, spawning -- all are auditable events in the same ledger."
]

LIFECYCLE_AS_TURNS::[
  hall_open -> Creates DebateRoom with mode=HALL,
  hall_register -> add_turn(role=SYSTEM, turn_type=REGISTRATION, content=participant_OCTAVE),
  hall_debate -> add_turn(role=SYSTEM, turn_type=SPAWN, content=child_thread_id) + debate_init(parent_thread_id),
  debate_close (child) -> triggers add_turn(role=SYSTEM, turn_type=COMPRESSION, content=updated_compressed_log) on parent,
  hall_close -> close_debate on the Hall room (checks all children closed via I8)
]

SUBTRACTION_ANALYSIS::[
  REMOVED::HallState model (DebateRoom is the state),
  REMOVED::Separate persistence layer (reuses DebateRoom persistence),
  REMOVED::Separate event system (hall events ARE debate turns in the hash chain),
  REMOVED::Separate locking strategy (DebateRoom CAS handles it),
  PRESERVED::ALL existing tests (DebateRoom model is backward compatible),
  PRESERVED::ALL immutables (I1-I5 apply to DebateRooms, which IS the Hall)
]

STRENGTHS::[
  "Maximum reuse -- zero new state models, zero new persistence code",
  "Every hall action is a turn in the hash chain -- automatic I4 compliance",
  "The existing get_debate tool gives you hall status for free",
  "Speed mode, RACI mode, HALL mode -- consistent abstraction level",
  "Compression turns are themselves verifiable and auditable",
  "Testing: existing DebateRoom test infrastructure covers hall state"
]

WEAKNESSES::[
  "Conceptual overloading: DebateRoom becomes a 'do everything' model",
  "Turn types proliferate (REGISTRATION, COMPRESSION, SPAWN, CONSULTATION)",
  "Hall-specific fields (participant_registry, compressed_log) bloat DebateRoom",
  "The 'turns' list mixes debate content with administrative events",
  "Compression turn content is system-generated, not agent-generated -- conceptual purity issue",
  "Harder to query: 'show me all halls' requires filtering DebateRooms by mode"
]

===

===CHALLENGE_1::COMPRESSION_ALGORITHM===

QUESTION::"How do you compress an entire multi-debate lifecycle into ~4096 tokens of OCTAVE?"

[CONNECTIONS]
  EVIDENCE_1::DecisionRecord (decision.py:extract_decision_record) already extracts thread_id, topic, synthesis, status, consensus info, and provenance from closed debates. This IS a compression template.
  EVIDENCE_2::The existing _format_debate_state (orchestrator.py:204-246) compresses a debate into ~200 tokens of structured text.
  EVIDENCE_3::The North Star A4 says "Start with structured extraction rather than LLM summarization" and NR4 says "No LLM-based compression for V1."

[POSSIBILITIES]

APPROACH_A::DECISION_RECORD_STACKING[
  PATTERN::PATTERN_TRANSPLANT["extract_decision_record applied to each closed debate, stacked into compressed_log"],
  MECHANISM::[
    1. When a debate closes within a Hall, call extract_decision_record(),
    2. Compress the DecisionRecord into a fixed-token OCTAVE block (~80-120 tokens),
    3. Stack all decision blocks + active debate summaries + participant table,
    4. If total exceeds max_context_tokens, apply FIFO eviction on oldest decisions
  ],
  FORMAT::[
    ===HALL_CONTEXT===
    HALL::{hall_id}
    DECISIONS_MADE::{count}

    D1::[topic::{topic}, verdict::{GO|NO-GO|CONDITIONAL}, key_constraint::{wall_summary}, thread::{thread_id}]
    D2::[topic::{...}]
    ...

    ACTIVE::[
      {thread_id}::[topic::{topic}, turn::{n}/{max}, participants::{names}]
    ]

    PARTICIPANTS::[
      {name}::[kind::{agent|human}, status::{active|on_call}, raci::{R|A|C|I|none}]
    ]

    UNRESOLVED::[
      "Explicit markers for questions still open"
    ]
    ===END===
  ],
  TOKEN_BUDGET::[
    HEADER::~20 tokens,
    PER_DECISION::~80 tokens (topic + verdict + key constraint),
    PER_ACTIVE::~40 tokens,
    PER_PARTICIPANT::~15 tokens,
    EXAMPLE::20 + (10 * 80) + (2 * 40) + (5 * 15) = 975 tokens for 10 decisions + 2 active + 5 participants,
    HEADROOM::4096 - 975 = 3121 tokens remaining for more decisions or detail
  ]
]

APPROACH_B::PROGRESSIVE_COMPRESSION[
  PATTERN::DOMAIN_COLLISION["Database WAL compaction applied to debate history"],
  MECHANISM::[
    1. Maintain a running compressed_log (starts empty),
    2. On each debate close, APPEND new decision summary,
    3. When compressed_log exceeds 80% of max_context_tokens, COMPACT:
       - Merge old decisions into category summaries (e.g., "3 architecture decisions: all GO"),
       - Preserve most recent N decisions in full detail,
       - Preserve ALL active debate summaries (never compacted),
    4. This mimics WAL (Write-Ahead Log) compaction in databases
  ],
  ADVANTAGE::"Never reprocesses the full history -- incremental compression",
  RISK::"Compaction heuristics could lose critical details"
]

APPROACH_C::TOPIC_CLUSTERED_COMPRESSION[
  PATTERN::PERSPECTIVE_SHIFT["What if compression is not temporal but topical?"],
  MECHANISM::[
    1. Cluster decisions by topic similarity (keyword overlap),
    2. Compress each cluster into a topic summary,
    3. Active topics get full detail; archived topics get one-line summaries,
    4. This preserves thematic coherence over temporal ordering
  ],
  ADVANTAGE::"Agents see related decisions grouped, improving context utilization",
  RISK::"Clustering algorithm adds complexity; NR4 says no LLM summarization"
]

===

===CHALLENGE_2::PARTICIPANT_PROMPT_LOADING===

QUESTION::"How to wire participant registry -> prompt resolution elegantly?"

[CONNECTIONS]
  EVIDENCE_1::get_agent_prompt (prompts/loader.py:85-135) already resolves agent files by name with layered discovery: ./agents/ -> .hestai-sys/library/agents/
  EVIDENCE_2::orchestrator.py:_get_raci_prompt (line 1340) already combines agent file content with RACI turn instructions
  EVIDENCE_3::The VTP pattern (orchestrator.py:_execute_role_turn) already injects system prompts into provider calls

[POSSIBILITIES]

APPROACH_A::DIRECT_WIRE[
  MECHANISM::[
    1. Participant.prompt_source holds the role name (e.g., "implementation-lead"),
    2. On hall_register, call get_agent_prompt(prompt_source) to validate the file exists,
    3. On turn request, call get_agent_prompt(prompt_source) to load fresh content,
    4. Combine with RACI turn instruction (existing _get_raci_turn_instruction pattern),
    5. Pass combined prompt as system_prompt to provider
  ],
  CODE_CHANGE::Minimal -- participant_registry stores name, loader resolves at turn time,
  ALIGNMENT::Exactly mirrors orchestrator.py:_get_raci_prompt (line 1340-1376)
]

APPROACH_B::PROMPT_CACHE_WITH_INVALIDATION[
  MECHANISM::[
    1. On hall_register, resolve and CACHE the prompt content in participant record,
    2. On turn request, use cached prompt (no file I/O),
    3. On hall_register with force=True, invalidate and re-resolve,
    4. Advantage: single file read at registration time, not per-turn
  ],
  RISK::"Cached prompts go stale if agent files are edited mid-hall",
  MITIGATION::"Add prompt_hash to detect changes; re-resolve on hash mismatch"
]

APPROACH_C::COMPOSITE_PROMPT_BUILDER[
  PATTERN::DOMAIN_COLLISION["Component composition from UI frameworks applied to prompts"],
  MECHANISM::[
    1. Decompose prompt into layers: IDENTITY + CAPABILITIES + GOVERNANCE_ROLE + HALL_CONTEXT,
    2. Identity layer: loaded from get_agent_prompt(name),
    3. Capabilities layer: extracted from agent file CAPABILITIES section,
    4. Governance layer: _get_raci_turn_instruction(turn_type) (existing),
    5. Hall context layer: compressed_log injection (new),
    6. Compose: IDENTITY + GOVERNANCE + HALL_CONTEXT + DEBATE_STATE + USER_PROMPT
  ],
  INSIGHT::"This is what _execute_role_turn already does informally. Making it explicit enables reuse."
]

===

===CHALLENGE_3::ON_DEMAND_CONSULTATION===

QUESTION::"An agent mid-work calls into the hall for advice. How does this work with MCP's request/response model?"

[CONNECTIONS]
  EVIDENCE_1::MCP is strict request/response (no WebSocket, per NR1)
  EVIDENCE_2::The existing human_interject tool (state.py:InjectedContext) allows injecting external context into active debates
  EVIDENCE_3::resolve_question (tools/decision.py) already runs a complete debate as a single MCP tool call

[POSSIBILITIES]

APPROACH_A::HALL_CONSULT_TOOL[
  PATTERN::PATTERN_TRANSPLANT["resolve_question pattern applied to hall consultation"],
  MECHANISM::[
    1. New MCP tool: hall_consult(hall_id, question, consultant_id) -> response,
    2. Internally: creates a LIGHTWEIGHT 2-turn exchange:
       - Turn 1: System poses question with hall compressed_log as context,
       - Turn 2: Consultant (from registry) responds,
    3. The exchange is recorded as a sub-debate (mode=SPEED, max_turns=2),
    4. Response returned synchronously to caller,
    5. Compressed_log updated with consultation result
  ],
  MCP_COMPATIBILITY::"Single request -> orchestrate mini-debate -> single response. Same pattern as run_debate and resolve_question.",
  TOOL_SURFACE::[
    hall_consult(hall_id:str, question:str, consultant_id:str) -> {response:str, thread_id:str}
  ],
  TOKEN_COST::"~500-1000 tokens (similar to Speed mode validated at 550 tokens)"
]

APPROACH_B::CONTEXT_INJECTION_ONLY[
  PATTERN::SUBTRACTION_INNOVATION["What if consultation is just reading the compressed_log?"],
  MECHANISM::[
    1. No new tool needed,
    2. Agent calls hall_status(hall_id) to get compressed_log,
    3. The compressed_log already contains all decisions and active state,
    4. Agent uses this context to answer their own question,
    5. If the context is insufficient, agent initiates a full hall_debate
  ],
  ADVANTAGE::"Zero new tools. Zero token cost beyond the compressed_log read.",
  RISK::"Compressed_log may not have the specific answer needed. Agent must self-assess."
]

APPROACH_C::ASYNC_CONSULTATION_WITH_CALLBACK[
  PATTERN::PERSPECTIVE_SHIFT["What if consultation is async and the hall notifies when ready?"],
  MECHANISM::[
    1. Agent calls hall_consult_async(hall_id, question) -> consultation_id,
    2. Hall schedules the consultation as a pending debate,
    3. Agent continues work (does not block),
    4. Agent polls hall_consult_status(consultation_id) for result,
    5. When consultant responds, result is available
  ],
  ADVANTAGE::"Non-blocking for the calling agent",
  RISK::"MCP has no push notifications. Polling is wasteful. This violates NR1 spirit."
]

===

===CHALLENGE_4::SUB_DEBATE_SPAWNING===

QUESTION::"When a debate reveals a deeper question, how does it spawn a child? Who decides? What triggers it?"

[CONNECTIONS]
  EVIDENCE_1::I8 (Recursive Topology Closure) requires parent-child tracking with leaf-to-root closure
  EVIDENCE_2::The existing debate_init function creates independent DebateRooms -- no parent relationship exists
  EVIDENCE_3::orchestrator.py:run_raci already creates debates from compiled manifests

[POSSIBILITIES]

APPROACH_A::ORCHESTRATOR_DECIDES[
  MECHANISM::[
    1. During a hall-managed debate, the orchestrator monitors turn content,
    2. If Door's synthesis contains an explicit SPAWN marker (e.g., "[REQUIRES_DEBATE: topic]"),
    3. Orchestrator pauses current debate (status=PAUSED),
    4. Spawns child debate with parent_thread_id set,
    5. Runs child to completion,
    6. Injects child synthesis into parent's compressed_log,
    7. Resumes parent debate
  ],
  TRIGGER::"Explicit SPAWN marker in turn content (agent signals intent)",
  DECISION_MAKER::"Door role (LOGOS) identifies when synthesis requires deeper exploration",
  I8_COMPLIANCE::"Parent stays PAUSED until child completes. Children tracked in parent.children list."
]

APPROACH_B::HALL_DEBATE_EXPLICIT[
  MECHANISM::[
    1. Sub-debates are NEVER spawned automatically by the orchestrator,
    2. The external caller (MCP client) decides when to spawn sub-debates,
    3. Caller calls hall_debate(hall_id, topic, parent_thread_id=current_debate),
    4. Hall validates depth < max_depth (I8),
    5. Hall creates child DebateRoom with parent linkage,
    6. Caller orchestrates child, then resumes parent
  ],
  TRIGGER::"Explicit MCP tool call from external agent/client",
  DECISION_MAKER::"External caller (human or orchestrating agent)",
  ADVANTAGE::"No implicit behavior. Full control by the caller.",
  I8_COMPLIANCE::"Hall tracks parent-child relationship. close_debate on parent validates all children closed."
]

APPROACH_C::MANIFEST_PRE_PLANNED[
  PATTERN::CONSTRAINT_INVERSION["What if sub-debates are planned at Hall open, not discovered at runtime?"],
  MECHANISM::[
    1. HallManifest (from PATH_2) includes a dependency graph of planned debates,
    2. Sub-debates are pre-declared with trigger conditions (e.g., "if verdict=CONDITIONAL, spawn review debate"),
    3. Hall orchestrator follows the dependency graph,
    4. Dynamic spawning is limited to pre-declared patterns
  ],
  ADVANTAGE::"Deterministic topology. No surprise depth explosions.",
  RISK::"Cannot handle truly emergent sub-topics discovered during debate"
]

===

===CHALLENGE_5::HALL_LIFECYCLE_MANAGEMENT===

QUESTION::"When does a hall end? Who closes it? Can it auto-archive?"

[CONNECTIONS]
  EVIDENCE_1::DebateRoom has clear termination: SYNTHESIS, STALEMATE, EXHAUSTION, FORCE_CLOSED
  EVIDENCE_2::I8 requires all children resolved before parent closes
  EVIDENCE_3::The North Star defines HallStatus as open|active|reviewing|archived

[POSSIBILITIES]

APPROACH_A::EXPLICIT_HUMAN_CLOSE[
  MECHANISM::[
    1. Hall has NO auto-close behavior,
    2. Human calls hall_close(hall_id) when satisfied,
    3. hall_close validates all active debates are closed (I8),
    4. If active debates remain, hall_close returns error with list of open debates,
    5. Hall moves to 'archived' status,
    6. Final compressed_log is generated as the Hall's "synthesis"
  ],
  STATUS_TRANSITIONS::[
    open -> active (first debate spawned),
    active -> reviewing (all debates closed, awaiting human review),
    reviewing -> archived (human calls hall_close),
    ANY -> force_closed (admin kill switch, I5)
  ],
  ADVANTAGE::"Humans retain ultimate authority over Hall lifecycle. Aligns with North Star 'NOT replacement for human decision'."
]

APPROACH_B::AUTO_ARCHIVE_ON_INACTIVITY[
  MECHANISM::[
    1. Hall tracks last_activity_at timestamp (updated on every debate close, turn, registration),
    2. Configure inactivity_timeout on Hall (e.g., 24 hours),
    3. When polled (via hall_status), check if inactive for > timeout,
    4. If inactive and all debates closed, auto-transition to archived,
    5. Emit HALL_AUTO_ARCHIVED event
  ],
  ADVANTAGE::"Prevents zombie halls that are forgotten",
  RISK::"MCP has no background processes. Auto-archive only triggers on next hall_status call (lazy evaluation)."
]

APPROACH_C::GOAL_DRIVEN_CLOSURE[
  PATTERN::PERSPECTIVE_SHIFT["What if the Hall closes when its PURPOSE is achieved?"],
  MECHANISM::[
    1. Hall is opened with a goal statement and success_criteria,
    2. After each debate close, compare compressed_log against success_criteria,
    3. If criteria met, auto-transition to 'reviewing',
    4. Human confirms or extends
  ],
  ADVANTAGE::"Purpose-driven lifecycle. The Hall exists to resolve a question.",
  RISK::"Success criteria evaluation requires either LLM (violates NR4) or structured matching (limited)"
]

===

===SYNTHESIS_OF_PATHS===

OBSERVATION::Three paths represent a gradient:
  PATH_1 (Obvious) adds a new layer. ~6 new files, ~2000 LOC. Safe but verbose.
  PATH_2 (Adjacent) generalizes existing compiler pattern. ~5 new files. Elegant but requires upfront design.
  PATH_3 (Heretical) subtracts a layer. ~0 new models. Radical but risks overloading DebateRoom.

EMERGENCE_PATTERN::The strongest ideas combine PATH_2 and PATH_3:
  - Use PATH_3's insight that Hall lifecycle events can be turns (I4 compliance for free),
  - Use PATH_2's manifest compiler for deterministic workflow planning,
  - Use PATH_1's separate HallState model to avoid overloading DebateRoom,
  - Use PATH_2's VTP extension for holographic context injection

QUESTIONS_FOR_VALIDATOR::[
  Q1::"Does overloading DebateRoom with Hall fields (PATH_3) violate Single Responsibility?",
  Q2::"Can the TurnManifest compiler pattern handle dependency graphs (PATH_2)?",
  Q3::"Is 4096 tokens sufficient for ~40 decision summaries? What is the empirical limit?",
  Q4::"Should hall_consult be synchronous (PATH_A) or just a context read (PATH_B)?",
  Q5::"Is pre-planned topology (CHALLENGE_4 PATH_C) too rigid for real workflows?",
  Q6::"What is the testing strategy for recursive topology closure (I8)?",
  Q7::"Should HallState reuse CAS persistence from state.py or introduce a new persistence pattern?"
]

HANDOFF::Validator(feasibility) -> assess PATH alignment with I6-I8 constraints and existing test infrastructure

===END===
