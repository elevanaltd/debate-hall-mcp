===NORTH_STAR===

META:
  TYPE::FEATURE_NORTH_STAR
  FEATURE::"Stateful RACI Hall"
  ISSUE::"#163"
  VERSION::"1.1"
  STATUS::RATIFIED
  PARENT::"000-DEBATE-HALL-MCP-NORTH-STAR.oct.md"
  VALIDATED_BY::"requirements-architect[Gemini]+requirements-steward[Claude]"
  VALIDATED_AT::"2026-02-14"

§1::IDENTITY

NAME::Stateful_RACI_Hall
PURPOSE::"To elevate the Debate Hall from a transient interaction room into a persistent, stateful governance container where identity, context, and recursive dialectic topology persist across individual debate sessions."

WHAT_IT_IS::[
  DEFINITION::"A persistent container model (The Hall) that manages a registry of sovereign participants (Agents/Humans) and orchestrates multiple, potentially nested, debate threads (Rooms) sharing a unified compressed context.",
  METAPHOR::"A physical debate hall where members enter, sit, listen (shared context), and are called to the podium (active debate) or break out into caucus rooms (sub-debates).",
  SCOPE::"Super-structure managing Life (Participants), Time (Persistence), and Space (Topology) for debates."
]

WHAT_IT_IS_NOT::[
  NOT::"A chat room (strict turn-taking and structural governance remain)",
  NOT::"A replacement for DebateRoom (it wraps and orchestrates DebateRooms)",
  NOT::"A distributed system (single logical Hall instance)",
  NOT::"An agent runtime (participants are invoked externally, Hall manages state only)"
]

§2::IMMUTABLES

// EXTENDS I1-I5 from Product North Star (000-DEBATE-HALL-MCP-NORTH-STAR.oct.md)
// ADDS I6-I8 for Stateful Hall

I6::PARTICIPANT_IDENTITY_REGISTRY[
  DEFINITION::"The Hall maintains the single authoritative registry of all participants. No actor speaks without a registered identity and assigned status. Each participant MAY declare a prompt_source (file path, agent definition, or inline config) that the Hall loads and injects as system context on turn request.",
  CONSTRAINT::"Identity > Participation. Anonymous or ephemeral agents cannot hold governance roles (R/A). Prompt loading is Hall-side state injection, NOT agent-side memory.",
  I1_COMPLIANCE::"The registry is Hall-managed state. Agents receive identity context per-turn via context injection, never by querying the registry directly. No agent-side persistence.",
  ENFORCEMENT::"hall_register_tool + active_participant_check_before_turn + prompt_injection_on_context_build"
]

I7::HOLOGRAPHIC_CONTEXT_COMPRESSION[
  DEFINITION::"Every participant has access to an ultra-compressed, verifiable log of the Hall's global state, ensuring shared reality without context window exhaustion.",
  CONSTRAINT::"Context <= max_context_tokens (configurable, default 4096). The Hall must provide a compressed state summary that fits within this bound.",
  VERIFICATION::"The compressed log is derived FROM the I4-compliant event ledger, not a replacement for it. Raw events remain the source of truth.",
  ENFORCEMENT::"auto_compression_on_debate_close + context_injection_on_turn_request + token_count_validation"
]

I8::RECURSIVE_TOPOLOGY_CLOSURE[
  DEFINITION::"Debates can spawn sub-debates (nested topology), but a parent debate cannot close until all its child debates have resolved (atomic closure).",
  CONSTRAINT::"No orphaned threads. The tree must prune from leaves to root.",
  DEPTH_LIMIT::"max_depth (configurable, default 3) is a property of the Hall. No sub-debate may spawn beyond this depth.",
  I3_COMPLIANCE::"Each individual debate within the tree independently enforces I3 limits (max_turns, max_rounds). Total tree resource consumption = sum of individual room limits, bounded by max_depth.",
  ENFORCEMENT::"close_gate_check_children + recursive_status_propagation + depth_check_on_spawn"
]

§3::ARCHITECTURE

MODEL_HIERARCHY::[
  HALL::[
    ID::"hall_id (YYYY-MM-DD-subject format, consistent with thread_id)",
    REGISTRY::"Map[participant_id, Participant]",
    ACTIVE_DEBATES::"List[thread_id]",
    COMPLETED_DEBATES::"List[thread_id]",
    COMPRESSED_LOG::"str (OCTAVE-compressed state summary, regenerated on debate close)",
    STATUS::"HallStatus (open|active|reviewing|archived)",
    MAX_DEPTH::"int (default 3, I8 enforcement)",
    MAX_CONTEXT_TOKENS::"int (default 4096, I7 enforcement)",
    CREATED_AT::"datetime (UTC)",
    UPDATED_AT::"datetime (UTC)"
  ],
  PARTICIPANT::[
    ID::"participant_id (unique within hall)",
    NAME::"str (display name, e.g. 'implementation-lead')",
    KIND::"ParticipantKind (agent|human|system)",
    STATUS::"ParticipantStatus (on_call|active|completed|offline)",
    PROMPT_SOURCE::"str|None (agent file path, prompt name, or inline)",
    PROVIDER_CONFIG::"RoleConfig|None (for AI agents: provider, model, cli)",
    CAPABILITIES::"list[str] (tag-based capability matching for RACI role assignment)",
    RACI_DESIGNATION::"str|None (R|A|C|I when assigned to active debate)"
  ],
  DEBATE_ROOM::[
    EXTENSION::"Add parent_hall_id: str|None and parent_thread_id: str|None to existing DebateRoom model",
    CHILDREN::"List[thread_id] (sub-debates spawned from this room)",
    CONTEXT::"Hall compressed log injected into debate context on turn request"
  ]
]

PERSISTENCE_STRATEGY::[
  HALL_STATE::"JSON file at {state_dir}/halls/{hall_id}.json",
  HALL_EVENTS::"Append-only JSONL at {state_dir}/halls/{hall_id}.events.jsonl",
  DEBATE_STATE::"Existing DebateRoom JSON persistence (unchanged)",
  INTEGRITY::"Hall events extend I4 hash chain pattern from debate events",
  CONCURRENCY::"Reuse existing CAS + file locking patterns from state.py"
]

COMPRESSION_ENGINE::[
  INPUT::"Completed debate syntheses + active debate summaries",
  TRIGGER::"Regenerated on each debate close within the hall",
  OUTPUT::"OCTAVE-compressed state summary (decisions made, active topics, participant status)",
  BUDGET::"Must fit within max_context_tokens (I7 enforcement)"
]

§4::MCP_TOOLS

// NEW TOOLS (extending existing tool surface)

HALL_LIFECYCLE::[
  hall_open::[create_hall → hall_id + topic + max_depth + max_context_tokens],
  hall_status::[view_hall → participants + active_debates + compressed_log + status],
  hall_close::[archive_hall → final_compressed_log + cascade_close_active_debates]
]

PARTICIPANT_MANAGEMENT::[
  hall_register::[add_participant → participant_id + name + kind + prompt_source + provider_config],
  hall_unregister::[remove_participant → validates_not_in_active_debate]
]

HALL_DEBATE_CONTROL::[
  hall_debate::[spawn_debate_in_hall → thread_id + auto_assign_participants_from_registry],
  hall_consult::[lightweight_2_turn_exchange → question + participant_id → response]
]

EXISTING_TOOL_MODIFICATIONS::[
  add_turn::"Inject hall compressed_log into debate context when parent_hall_id is set",
  close_debate::"Trigger hall compressed_log regeneration when parent_hall_id is set",
  get_debate::"Include hall context summary when parent_hall_id is set"
]

§5::ASSUMPTION_REGISTER

A1::[
  ASSUMPTION::"Agents can effectively utilize the compressed OCTAVE context without hallucinating details.",
  CONFIDENCE::"Medium",
  MITIGATION::"Include explicit 'unresolved' and 'active' markers in summary. Empirical testing required."
]

A2::[
  ASSUMPTION::"Recursive locking for nested debates won't introduce prohibitive latency or deadlocks.",
  CONFIDENCE::"Medium",
  MITIGATION::"Optimistic locking with fine-grained state updates. Separate lock paths per debate. Deadlock detection at spawn time."
]

A3::[
  ASSUMPTION::"Human participants will tolerate async turn-based governance of the Hall.",
  CONFIDENCE::"Low",
  MITIGATION::"Allow 'Observer' role with async comment injection (already supported via human_interject)."
]

A4::[
  ASSUMPTION::"The compression algorithm can achieve sufficient ratio while preserving decision-critical information within max_context_tokens budget.",
  CONFIDENCE::"Low",
  MITIGATION::"Start with structured extraction (decisions + active topics) rather than LLM summarization. Measure empirically."
]

A5::[
  ASSUMPTION::"Recursive debate topology does not create lock dependency cycles in the file-based persistence layer.",
  CONFIDENCE::"Medium",
  MITIGATION::"Each debate has independent lock files. Hall lock is separate from debate locks. No cross-lock dependencies by design."
]

§6::EXPLICIT_NON_REQUIREMENTS

NR1::"Real-time streaming (WebSocket) - strict MCP Request/Response for V1."
NR2::"Multi-Hall Federation - one Hall instance per server process for V1."
NR3::"Dynamic R/A reassignment within a single debate instance - RACI roles are fixed per debate. Participants CAN be added/removed from the Hall between debates."
NR4::"LLM-based compression - V1 uses structured extraction, not LLM summarization."
NR5::"Hall-to-Hall communication - Halls are independent containers."

§7::SUCCESS_CRITERIA

FUNCTIONAL::[
  CAN::"Register 3 distinct agents (with different provider configs) and 1 human in a Hall",
  CAN::"Run a root debate that spawns a sub-debate, with participants auto-assigned from registry",
  CAN::"Block root closure until sub-debate finishes (I8 enforcement)",
  CAN::"Persist Hall state across server restarts",
  CAN::"Inject compressed OCTAVE log into debate context for each participant turn",
  CAN::"Load agent prompts from prompt_source on participant registration"
]

QUALITY::[
  METRIC::"Compressed log fits within max_context_tokens budget (default 4096 tokens)",
  METRIC::"Hall state operations < 200ms latency",
  METRIC::"Zero regression on existing 1,239 tests"
]

ADOPTION::[
  METRIC::"Used to orchestrate at least one real multi-agent workflow end-to-end"
]

===END_NORTH_STAR===
