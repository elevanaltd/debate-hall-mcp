===D2_03_DESIGN===

META:
  TYPE::DESIGN_SPEC
  VERSION::"2.0"
  STATUS::APPROVED
  PARENT::"issue-163-stateful-raci-hall"
  AUTHOR::"HO Synthesis (Manual D2 + run_debate Wind/Wall/Door)"
  DATE::"2026-02-14"
  SOURCES::[
    MANUAL_D2::"Claude(Ideator)+Gemini(Synthesizer) via subagent delegation",
    AUTO_D2::"run_debate[thread:2026-02-14-stateful-raci-hall-d2-debate][Wind:Claude/PATHOS+Wall:GPT5.2/ETHOS+Door:Gemini3Pro/LOGOS]"
  ]

## APPROACH: Hydrated Snapshot Hall (Event-Sourced Container)

**Unified Concept:**
The Hall is a **Separated Model** (not a DebateRoom) that acts as a **Workflow Container** orchestrating child DebateRooms. Its persistence follows the **Hydrated Snapshot Pattern** (CQRS variant): the event ledger is the single source of truth, while `halls/{id}.json` is a cached checkpoint that self-heals on read.

This approach was synthesized from:
- **Manual D2**: Separated model, RaciMatrix, Dynamic Participant Injection, Decision Record Stacking compression, 5-phase implementation
- **run_debate synthesis**: Hydrated Snapshot Pattern, event-sourced reducer, `last_event_id` tracking, read-repair mechanism, self-healing persistence

The key architectural insight from run_debate: **"Ledger is Truth; File is Checkpoint."** This resolves the dual-write consistency problem the manual D2 did not address, while satisfying the North Star's requirement for persistent `halls/{id}.json` artifacts (H3).

## PERSISTENCE_ARCHITECTURE

**Organizing Principle:** The Event Ledger (`halls/{id}.events.jsonl`) is the authoritative source of truth. The state file (`halls/{id}.json`) is a Persistent Materialized View.

**Write Path:**
```
Acquire Lock -> Append Event to JSONL (Truth) -> Update In-Memory State -> Flush JSON (Checkpoint) -> Release Lock
```

**Read Path (Self-Healing):**
```
Acquire Lock -> Load JSON Snapshot -> Read Event Tail -> If Tail > Snapshot.last_event_id:
    Replay Delta Events via Reducer -> Flush Updated JSON -> Return Fresh State
Else: Return Snapshot
```

**Benefits:**
- Single source of truth (events) — no dual-write consistency bugs
- Crash recovery via read-repair (stale JSON auto-heals from ledger)
- Satisfies North Star H3 (artifacts exist) and I4 (ledger integrity)
- Reuses existing `events.py` infrastructure (FileLock, ULID ordering, append-only JSONL)

**Cross-Domain Evidence:** Git (reflog is truth, HEAD is pointer), Kafka (log is database), Redux (actions are truth, UI is derived), Banking (ledger entries are truth, balance is derived).

## DATA_MODEL

### HallState (New — Snapshot Model)
Persisted as checkpoint at `{state_dir}/halls/{hall_id}.json`. Derived from events.
```python
class HallState(BaseModel):
    hall_id: str                              # "hall-YYYY-MM-DD-topic"
    topic: str
    status: HallStatus = HallStatus.OPEN      # open|active|reviewing|archived
    participants: dict[str, Participant] = {}  # Registry (I6)
    raci_matrix: RaciMatrix | None = None     # Current RACI assignment
    active_debates: list[str] = []            # thread_ids of child debates
    completed_debates: list[str] = []
    compressed_log: str = ""                  # OCTAVE summary (I7)
    max_depth: int = 3                        # I8 enforcement
    max_context_tokens: int = 4096            # I7 budget
    context_files: list[str] = []             # Shared codebase context
    last_event_id: str = ""                   # ULID of last applied event (snapshot version)
    created_at: datetime
    updated_at: datetime
```

### Participant (New)
```python
class ParticipantKind(str, Enum):
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"

class Participant(BaseModel):
    id: str                              # Unique within hall
    name: str                            # Display name (e.g., "implementation-lead")
    kind: ParticipantKind
    status: Literal["on_call", "active", "completed"] = "on_call"
    prompt_source: str | None = None     # Agent file path for prompt loading (I6)
    provider_config: RoleConfig | None = None  # For AI agents
    capabilities: list[str] = []         # Tag-based capability matching
    raci_designation: str | None = None  # R|A|C|I when assigned
```

### RaciMatrix (New)
```python
class RaciMatrix(BaseModel):
    responsible: str                     # The Proposer
    accountable: str                     # The Decision Maker
    consulted: list[str] = []            # Advisors
    informed: list[str] = []             # Observers
```

### DebateRoom (Extension)
```python
class DebateRoom(BaseModel):
    # ... existing fields unchanged ...
    parent_hall_id: str | None = None         # Links to containing Hall
    parent_thread_id: str | None = None       # Links to parent debate (for nesting)
```

## EVENT_REDUCER

Pure function that derives state from events. Lives in new `src/debate_hall_mcp/hall.py`.

```python
def apply_hall_event(state: HallState, event: HallEvent) -> HallState:
    """Pure reducer: state(N) + event -> state(N+1)"""
    match event.event_type:
        case HallEventType.HALL_OPENED:
            state.status = HallStatus.OPEN
        case HallEventType.PARTICIPANT_REGISTERED:
            state.participants[event.data["id"]] = Participant(**event.data)
        case HallEventType.PARTICIPANT_UNREGISTERED:
            del state.participants[event.data["id"]]
        case HallEventType.DEBATE_SPAWNED:
            state.active_debates.append(event.data["thread_id"])
            state.status = HallStatus.ACTIVE
        case HallEventType.DEBATE_CLOSED:
            thread_id = event.data["thread_id"]
            state.active_debates.remove(thread_id)
            state.completed_debates.append(thread_id)
            state.compressed_log = generate_compressed_log(state, event.data)
        case HallEventType.HALL_CLOSED:
            state.status = HallStatus.ARCHIVED
    state.last_event_id = event.event_id
    state.updated_at = event.timestamp
    return state
```

## MCP_TOOLS

### Hall Lifecycle (3 tools)
1. **`hall_open(topic, max_depth?, max_context_tokens?, context_files?) -> hall_id`**
   - Creates HallState. Appends HALL_OPENED event.
   - Returns hall_id.

2. **`hall_status(hall_id) -> HallState`**
   - Loads hall via Smart Loader (read-repair if needed).
   - Returns full state including compressed_log, participants, debates.

3. **`hall_close(hall_id, summary?) -> archived HallState`**
   - Validates all active debates closed (I8 enforcement).
   - If active debates remain, returns error with list of open threads.
   - Appends HALL_CLOSED event. Generates final compressed_log.
   - Status -> ARCHIVED.

### Participant Management (2 tools)
4. **`hall_register(hall_id, name, kind, prompt_source?, provider_config?, capabilities?) -> participant_id`**
   - Adds participant to registry. Validates prompt_source exists via get_agent_prompt().
   - Appends PARTICIPANT_REGISTERED event.

5. **`hall_unregister(hall_id, participant_id) -> success`**
   - Validates participant not in active debate.
   - Appends PARTICIPANT_UNREGISTERED event.

### Debate Control (2 tools)
6. **`hall_debate(hall_id, topic, mode?, participants_override?, parent_thread_id?) -> thread_id`**
   - Validates depth < max_depth (I8).
   - Creates child DebateRoom with parent_hall_id set.
   - Auto-assigns participants from registry based on RACI matrix.
   - Appends DEBATE_SPAWNED event.
   - Runs debate via DebateOrchestrator with dynamic participant injection.

7. **`hall_consult(hall_id, question, consultant_id) -> response`**
   - Lightweight 2-turn exchange (speed mode, max_turns=2).
   - Injects compressed_log as context for consultant.
   - Appends CONSULTATION event to hall ledger.
   - Returns response synchronously.

**Total new tools: 7** (extending existing 14+6 RACI = 27 total)

## ORCHESTRATOR_REFACTOR

**Problem:** `DebateOrchestrator.run_turn` hardcodes `[Wind, Wall, Door]`.
**Solution:** Dynamic Participant Injection.

1. **Abstract `Participant`** wrapping role, prompt_path, capabilities.
2. **Refactor `DebateOrchestrator.__init__`** to accept optional `participants: list[Participant]`. Default loads standard Wind/Wall/Door tier.
3. **HallManager as Meta-Orchestrator**: Steps through the RACI manifest, configures `DebateOrchestrator` with specific participants per step.
4. **Backward compatibility**: Zero changes when `participants=None` (existing behavior preserved).

## COMPRESSION_STRATEGY (I7)

**Strategy:** Decision Record Stacking with Token Budgeting.

**Format:** Structured OCTAVE (per NR4: no LLM summarization).
```octave
===HALL_CONTEXT===
HALL::{hall_id}
STATUS::{status}
DECISIONS::{count}

D1::[topic::{topic}, verdict::{GO|NO-GO|CONDITIONAL}, constraint::{wall_summary}, thread::{thread_id}]
D2::[...]

ACTIVE::[
  {thread_id}::[topic::{topic}, turn::{n}/{max}, participants::{names}]
]

PARTICIPANTS::[
  {name}::[kind::{kind}, status::{status}, raci::{designation}]
]

UNRESOLVED::[explicit_open_questions]
===END===
```

**Token Budget:**
- Header: ~20 tokens
- Per decision: ~80 tokens
- Per active debate: ~40 tokens
- Per participant: ~15 tokens
- Example: 10 decisions + 2 active + 5 participants = 975 tokens (24% of 4096 budget)

**Pre-flight Check:**
```python
if count_tokens(compressed_log) > max_context_tokens - RESERVED_BUFFER:
    raise ContextLimitExceeded("Hall context budget exceeded")
```

**Trigger:** Compression regenerated on each DEBATE_CLOSED event via the reducer.

## LOCK_DISCIPLINE

**Rule:** Coarse-grained FileLock on `halls/{id}.lock`.

1. **Lock scope:** Protects the full read-hydrate-write cycle.
2. **Mechanism:** `filelock.FileLock` (matching `events.py` pattern).
3. **Child isolation:** Each child DebateRoom has independent lock (existing CAS). No cross-lock dependencies.
4. **Unidirectional flow:** Child receives hall context as read-only injection. Child writes only to own state. HallManager commits child results to hall ledger.
5. **No deadlock risk:** Hall lock and debate lock never nested — HallManager releases hall lock before running child debate.

## PARTICIPANT_TO_ROLE_MAPPING

**Resolution chain:** `prompt_source` field on Participant -> `get_agent_prompt(name)` (existing loader.py).

**Discovery order:** `./agents/{name}.oct.md` -> `.hestai-sys/library/agents/{name}.oct.md` (existing pattern).

**Fallback:** Generic consultant prompt with role name injected as variable.

**Injection:** On turn request, load prompt_source content and inject as system context alongside compressed_log (VTP pattern extension).

## IMPLEMENTATION_SEQUENCE

### Phase 1: Core Models & Event Infrastructure
- Define `HallState`, `Participant`, `ParticipantKind`, `RaciMatrix`, `HallStatus` models
- Define `HallEventType` enum and extend event infrastructure for hall-level events
- Implement `apply_hall_event` reducer (pure function)
- Implement Smart Loader with read-repair (Hydrated Snapshot)
- Persistence: `{state_dir}/halls/` directory, JSON + JSONL files
- Add `parent_hall_id` and `parent_thread_id` to DebateRoom (backward-compatible defaults)

### Phase 2: Orchestrator Refactor
- Refactor `DebateOrchestrator` for dynamic participant injection
- Ensure backward compatibility (zero existing test breakage)
- Extract participant resolution from tier config

### Phase 3: Hall Manager & Basic Tools
- Implement `HallManager` (CRUD via event appending + snapshot flushing)
- Implement `hall_open`, `hall_status`, `hall_close` MCP tools
- Implement `hall_register`, `hall_unregister` MCP tools
- I8 enforcement: close_hall validates all children closed

### Phase 4: Debate Integration & Compression
- Implement `hall_debate` (spawns child DebateRoom within hall context)
- Implement `hall_consult` (speed mode within hall)
- Implement compression engine (Decision Record Stacking)
- Token budgeting and pre-flight checks
- Context injection via VTP extension (<HALL_CONTEXT> tag)

### Phase 5: E2E Verification & Hardening
- Full RACI flow test: Open -> Register -> Consult -> Debate -> Close
- Nested debate test: Parent -> Child -> Grandchild (depth limit)
- Crash recovery test: Corrupt JSON -> read-repair from events
- Golden tests: all existing tools return identical responses
- Soak tests: large halls (50+ events), deep nesting

## I_COMPLIANCE_MATRIX

| Immutable | Mechanism |
|-----------|-----------|
| I1 (Cognitive State Isolation) | Agents receive context per-turn via VTP injection. Registry is Hall-side state. |
| I2 (Universal OCTAVE Binding) | Compressed log is structured OCTAVE. All hall tools return OCTAVE-formatted responses. |
| I3 (Finite Dialectic Closure) | Each child debate independently enforces max_turns/max_rounds. Hall enforces max_depth (I8). |
| I4 (Verifiable Event Ledger) | Hall events in append-only JSONL with ULID ordering and FileLock. Snapshot derived from ledger. |
| I5 (Sovereign Safety Override) | hall_close cascades force_close to all active child debates. Admin kill switch preserved. |
| I6 (Participant Identity Registry) | Hall maintains authoritative registry. prompt_source loaded on registration. Identity injected per-turn. |
| I7 (Holographic Context Compression) | Decision Record Stacking within max_context_tokens budget. Regenerated on debate close. |
| I8 (Recursive Topology Closure) | max_depth enforced on spawn. Parent cannot close until all children resolved. Leaf-to-root pruning. |

## EVIDENCE_GAPS_TO_RESOLVE (from run_debate Wall)

- **G1:** Replay latency for event-sourcing with 50+ hall events — needs empirical benchmark
- **G2:** 4096-token budget empirical validation against real compressed log schema
- **G3:** Test blast radius quantification — exact count of existing tests affected by DebateRoom extension

These gaps should be addressed during Phase 1 implementation with measurement, not assumed.

===END===
