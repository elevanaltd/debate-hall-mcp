===D3_BLUEPRINT===

META:
  TYPE::TECHNICAL_BLUEPRINT
  VERSION::"1.0"
  STATUS::DRAFT
  FEATURE::"Stateful RACI Hall"
  ISSUE::"#163"
  PHASE::D3_DAEDALUS_CONSTRUCTION
  PARENT_DESIGN::"d2-03-design-stateful-raci-hall.oct.md[v2.0]"
  NORTH_STAR::"stateful-raci-hall-north-star.oct.md[v1.1]"
  AUTHOR::"design-architect[LOGOS]"
  DATE::"2026-02-14"
  AUTHORITY::ULTIMATE[Blueprint_creation+Specification_definition]

[BLUEPRINT_OVERVIEW]

This blueprint specifies the complete implementation of the Stateful RACI Hall feature
for debate-hall-mcp (Issue #163). It transforms the approved D2_03 design synthesis
(Hydrated Snapshot Hall with Event-Sourced Container) into implementation-ready
specifications that an implementation-lead can execute via TDD without ambiguity.

GOVERNING_PRINCIPLE::"Ledger is Truth; File is Checkpoint"
PATTERN::Hydrated_Snapshot[CQRS_variant]
SCOPE::7_new_MCP_tools + 3_new_modules + 4_modified_modules + I6-I8_enforcement

[DECISION_LOG]

DL1::[
  QUESTION::"Separate HallState model or extend DebateRoom?",
  OPTIONS::[
    A::"Separate HallState model (D2_03 recommended, Path 1)",
    B::"DebateRoom extension with HALL mode (Path 3 heretical)"
  ],
  CHOICE::A,
  RATIONALE::"Single Responsibility. DebateRoom manages debate state; HallState manages hall lifecycle. Avoids model bloat (DebateRoom already has 15+ fields). Path 3's turn-type proliferation creates conceptual overloading. D2_03 was ratified with this approach."
]

DL2::[
  QUESTION::"Hall event system: extend existing events.py or separate hall event module?",
  OPTIONS::[
    A::"Extend existing EventType enum in events.py",
    B::"Create separate HallEventType enum in hall.py"
  ],
  CHOICE::B,
  RATIONALE::"I4 tension resolution: Hall events and debate events are separate ledger domains. Separate enums prevent accidental cross-contamination. Hall events use their own JSONL file ({hall_id}.events.jsonl) with their own lock. Reuses the infrastructure patterns (ULID, FileLock, append-only JSONL) without coupling the enum surface."
]

DL3::[
  QUESTION::"Compression strategy: Decision Record Stacking vs Progressive Compression?",
  OPTIONS::[
    A::"Decision Record Stacking (D2_03 recommended)",
    B::"Progressive Compression (WAL compaction)",
    C::"Topic-Clustered Compression"
  ],
  CHOICE::A,
  RATIONALE::"NR4 prohibits LLM-based compression for V1. Decision Record Stacking is deterministic structured extraction using existing DecisionRecord infrastructure. Token budget math from D2_03: 10 decisions + 2 active + 5 participants = 975 tokens (24% of 4096 budget). Progressive compression adds compaction heuristics that risk losing critical details."
]

DL4::[
  QUESTION::"Lock discipline: coarse-grained hall lock or fine-grained per-field locks?",
  OPTIONS::[
    A::"Coarse-grained FileLock on halls/{id}.lock (D2_03 recommended)",
    B::"Fine-grained per-field locks (participant registry, debate list, etc.)"
  ],
  CHOICE::A,
  RATIONALE::"Hall operations are infrequent (register participant, spawn debate, close hall). Coarse-grained lock simplifies reasoning and eliminates deadlock risk. Fine-grained locks only justified under high-contention workloads (NR2: single Hall instance per server). Child debates have independent locks (existing CAS pattern)."
]

DL5::[
  QUESTION::"Sub-debate spawning: orchestrator-auto-detect or explicit MCP tool call?",
  OPTIONS::[
    A::"Orchestrator detects SPAWN markers in turn content",
    B::"Explicit hall_debate MCP tool call from external caller (D2_03 recommended)"
  ],
  CHOICE::B,
  RATIONALE::"No implicit behavior. Full control by the caller. Aligns with NR3 (no dynamic reassignment within a debate). The MCP client decides when to spawn sub-debates. Hall validates depth < max_depth (I8)."
]

DL6::[
  QUESTION::"Token counting mechanism: tiktoken, simple heuristic, or configurable?",
  OPTIONS::[
    A::"tiktoken library (exact GPT-family counts)",
    B::"Simple heuristic (chars / 4)",
    C::"Configurable with heuristic default"
  ],
  CHOICE::C,
  RATIONALE::"The compressed log is model-agnostic OCTAVE text. Exact token counts vary by model. A simple heuristic (len(text) // 4) is sufficient for budget enforcement with a safety margin. Allow override via optional token_counter callable in HallEngine for users who need precision. This resolves G2 (token budget empirical validation) by allowing measurement without hard dependency."
]

===

## S1::DATA_MODELS

All models live in `src/debate_hall_mcp/hall.py` unless otherwise noted.

### S1.1::HallStatus Enum

```python
class HallStatus(StrEnum):
    """Status of a Hall lifecycle.

    Transitions:
    - OPEN -> ACTIVE (first debate spawned via hall_debate)
    - ACTIVE -> REVIEWING (all active debates closed, no active debates remain)
    - REVIEWING -> ARCHIVED (hall_close called)
    - OPEN|ACTIVE -> ARCHIVED (hall_close with force=True, I5 enforcement)
    - ANY -> FORCE_CLOSED (admin kill switch)
    """

    OPEN = "open"           # Created, accepting participant registration
    ACTIVE = "active"       # At least one debate is running
    REVIEWING = "reviewing" # All debates closed, awaiting human review
    ARCHIVED = "archived"   # Finalized, read-only
    FORCE_CLOSED = "force_closed"  # Emergency shutdown (I5)
```

### S1.2::ParticipantKind Enum

```python
class ParticipantKind(StrEnum):
    """Kind of participant in the Hall."""

    AGENT = "agent"    # AI agent with provider_config
    HUMAN = "human"    # Human participant (async turn-based)
    SYSTEM = "system"  # System-generated entries (compression, etc.)
```

### S1.3::Participant Model

```python
class Participant(BaseModel):
    """A registered participant in the Hall (I6: Participant Identity Registry).

    The Hall maintains the single authoritative registry of all participants.
    No actor speaks without a registered identity.

    Fields:
    - id: Unique within hall. Generated as slugified name if not provided.
    - name: Display name (e.g., "implementation-lead", "Alice")
    - kind: ParticipantKind (agent|human|system)
    - status: Current participation status
    - prompt_source: Role name for prompt resolution via get_agent_prompt().
        Follows existing resolution: ./agents/{name}.oct.md -> .hestai-sys/library/agents/{name}.oct.md
    - provider_config: For AI agents, the RoleConfig for provider creation.
        When None, uses the hall's default tier_config.wind provider.
    - capabilities: Tag-based capability matching for RACI role assignment.
        Example: ["architecture", "security", "testing"]
    - raci_designation: Current RACI role in active debate (R|A|C|I|None).
        Set by hall_debate when assigning participants. Cleared on debate close.
    - registered_at: UTC timestamp of registration.
    """

    id: str = Field(..., description="Unique participant ID within hall")
    name: str = Field(..., min_length=1, max_length=128, description="Display name")
    kind: ParticipantKind = Field(..., description="Participant kind")
    status: Literal["on_call", "active", "completed", "offline"] = Field(
        default="on_call", description="Current participation status"
    )
    prompt_source: str | None = Field(
        default=None,
        description="Role name for prompt resolution via get_agent_prompt()",
    )
    provider_config: RoleConfig | None = Field(
        default=None,
        description="Provider config for AI agents (None = use hall default)",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Tag-based capability matching",
    )
    raci_designation: str | None = Field(
        default=None,
        description="Current RACI role: R|A|C|I (None when not in active debate)",
    )
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of registration",
    )

    @field_validator("id")
    @classmethod
    def validate_participant_id(cls, v: str) -> str:
        """Validate participant ID is filesystem-safe and non-empty."""
        if not v or not v.strip():
            raise ValueError("participant id must be non-empty")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                f"participant id '{v}' contains invalid characters: "
                "only alphanumeric, hyphens, and underscores allowed"
            )
        return v

    @field_validator("raci_designation")
    @classmethod
    def validate_raci_designation(cls, v: str | None) -> str | None:
        """Validate RACI designation is one of R, A, C, I, or None."""
        if v is not None and v not in ("R", "A", "C", "I"):
            raise ValueError(f"raci_designation must be R, A, C, I, or None; got '{v}'")
        return v
```

### S1.4::RaciMatrix Model

```python
class RaciMatrix(BaseModel):
    """RACI role assignment matrix for a hall-managed debate.

    Maps participant IDs to RACI roles. Used by hall_debate to configure
    the DebateOrchestrator with the correct participants.

    Invariants:
    - Exactly one responsible
    - Exactly one accountable
    - responsible != accountable
    - All IDs must reference registered participants
    - consulted max 5, informed max 3 (reuses RACIConfig limits)
    """

    responsible: str = Field(..., description="Participant ID for Responsible role")
    accountable: str = Field(..., description="Participant ID for Accountable role")
    consulted: list[str] = Field(
        default_factory=list,
        description="Participant IDs for Consulted roles (max 5)",
    )
    informed: list[str] = Field(
        default_factory=list,
        description="Participant IDs for Informed roles (max 3)",
    )

    @model_validator(mode="after")
    def validate_raci_matrix(self) -> "RaciMatrix":
        """Validate RACI constraints."""
        if self.responsible == self.accountable:
            raise ValueError("responsible and accountable must be different participants")
        if len(self.consulted) > 5:
            raise ValueError(f"consulted exceeds max 5: got {len(self.consulted)}")
        if len(self.informed) > 3:
            raise ValueError(f"informed exceeds max 3: got {len(self.informed)}")
        # Check for duplicates across all roles
        all_ids = [self.responsible, self.accountable] + self.consulted + self.informed
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("each participant must have exactly one RACI designation")
        return self
```

### S1.5::HallEventType Enum

```python
class HallEventType(StrEnum):
    """Types of hall-level events for the event ledger (I4 compliance).

    These are SEPARATE from debate-level EventType in events.py.
    Hall events track hall lifecycle; debate events track debate lifecycle.
    """

    HALL_OPENED = "hall_opened"
    PARTICIPANT_REGISTERED = "participant_registered"
    PARTICIPANT_UNREGISTERED = "participant_unregistered"
    RACI_ASSIGNED = "raci_assigned"
    DEBATE_SPAWNED = "debate_spawned"
    DEBATE_COMPLETED = "debate_completed"
    CONSULTATION_COMPLETED = "consultation_completed"
    CONTEXT_COMPRESSED = "context_compressed"
    HALL_CLOSED = "hall_closed"
    HALL_FORCE_CLOSED = "hall_force_closed"
```

### S1.6::HallEvent Model

```python
class HallEvent(BaseModel):
    """A hall-level event with ULID-based monotonic ordering.

    Reuses the same patterns as DebateEvent (events.py):
    - ULID for monotonic ordering
    - UTC timestamp
    - Flexible payload dict

    Fields:
    - event_id: ULID string (26 chars, Crockford Base32)
    - hall_id: Hall this event belongs to
    - event_type: Type of hall event (from HallEventType)
    - timestamp: UTC timestamp
    - data: Event-specific data (typed per event_type)
    """

    event_id: str = Field(..., description="ULID for monotonic ordering")
    hall_id: str = Field(..., description="Hall identifier")
    event_type: HallEventType = Field(..., description="Type of hall event")
    timestamp: datetime = Field(..., description="UTC timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v
```

### S1.7::HallState Model (Snapshot)

```python
class HallState(BaseModel):
    """Persistent state of a Hall (Hydrated Snapshot Pattern).

    This is the CHECKPOINT, not the source of truth. The source of truth is
    the event ledger at {state_dir}/halls/{hall_id}.events.jsonl.

    The snapshot is materialized from events via apply_hall_event() reducer
    and cached at {state_dir}/halls/{hall_id}.json for fast reads.

    Self-healing: On read, if last_event_id < latest event in ledger,
    the Smart Loader replays delta events to bring the snapshot current.

    Fields:
    - hall_id: Unique identifier in "hall-YYYY-MM-DD-topic" format
    - topic: Hall topic / purpose
    - status: Current lifecycle status (HallStatus)
    - participants: Registry mapping participant_id -> Participant (I6)
    - raci_matrix: Current RACI assignment (set by hall_debate, cleared on debate close)
    - active_debates: List of thread_ids for currently running child debates
    - completed_debates: List of thread_ids for finished child debates
    - compressed_log: OCTAVE-formatted summary of hall state (I7)
    - max_depth: Maximum nesting depth for sub-debates (I8, default 3)
    - max_context_tokens: Token budget for compressed_log (I7, default 4096)
    - max_debates: Maximum total debates allowed in this hall (I3 at hall level, default 20)
    - context_files: List of file paths for shared codebase context
    - tier_name: Tier configuration name for provider creation (default "standard")
    - last_event_id: ULID of last applied event (snapshot version marker)
    - created_at: UTC timestamp of hall creation
    - updated_at: UTC timestamp of last state change
    """

    hall_id: str = Field(..., description="Unique hall identifier")
    topic: str = Field(..., min_length=1, description="Hall topic / purpose")
    status: HallStatus = Field(default=HallStatus.OPEN, description="Lifecycle status")
    participants: dict[str, Participant] = Field(
        default_factory=dict,
        description="Participant registry (I6)",
    )
    raci_matrix: RaciMatrix | None = Field(
        default=None,
        description="Current RACI assignment for active debate",
    )
    active_debates: list[str] = Field(
        default_factory=list,
        description="Thread IDs of running child debates",
    )
    completed_debates: list[str] = Field(
        default_factory=list,
        description="Thread IDs of finished child debates",
    )
    compressed_log: str = Field(
        default="",
        description="OCTAVE-compressed hall context (I7)",
    )
    max_depth: int = Field(default=3, ge=1, le=10, description="Max nesting depth (I8)")
    max_context_tokens: int = Field(
        default=4096, ge=256, le=32768, description="Token budget for compressed_log (I7)"
    )
    max_debates: int = Field(
        default=20, ge=1, le=100, description="Max total debates in hall (I3 at hall level)"
    )
    context_files: list[str] = Field(
        default_factory=list,
        description="Shared codebase context file paths",
    )
    tier_name: str = Field(
        default="standard",
        description="Tier config name for provider creation",
    )
    last_event_id: str = Field(
        default="",
        description="ULID of last applied event (snapshot version)",
    )
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC last update timestamp")

    @field_validator("hall_id")
    @classmethod
    def validate_hall_id(cls, v: str) -> str:
        """Validate hall_id is filesystem-safe."""
        if not v or not v.strip():
            raise ValueError("hall_id must be non-empty")
        for pattern in ("..", "/", "\\"):
            if pattern in v:
                raise ValueError(f"hall_id '{v}' contains path-unsafe characters")
        return v
```

### S1.8::DebateRoom Extension

In `src/debate_hall_mcp/state.py`, add two optional fields to the existing `DebateRoom` model:

```python
class DebateRoom(BaseModel):
    # ... all existing fields unchanged ...

    # Hall integration (Issue #163 - Stateful RACI Hall)
    parent_hall_id: str | None = Field(
        default=None,
        description="ID of containing Hall (None for standalone debates)",
    )
    parent_thread_id: str | None = Field(
        default=None,
        description="Thread ID of parent debate (None for root-level debates, enables I8 nesting)",
    )
```

**Backward Compatibility Guarantee:** Both fields default to `None`. Existing JSON state files
will deserialize correctly (Pydantic assigns defaults for missing fields). Zero existing test
breakage. This resolves G3 (test blast radius): the extension is purely additive.

===

## S2::HYDRATED_SNAPSHOT_IMPLEMENTATION

### S2.1::File Layout

```
{state_dir}/
  halls/                              # New directory for hall state
    {hall_id}.json                     # Snapshot (checkpoint)
    {hall_id}.events.jsonl             # Event ledger (truth)
    {hall_id}.lock                     # FileLock for hall operations
  {thread_id}.json                    # Existing debate state (unchanged)
  {thread_id}.events.jsonl            # Existing debate events (unchanged)
  {thread_id}.lock                    # Existing debate lock (unchanged)
```

### S2.2::Event Ledger Functions

Located in `src/debate_hall_mcp/hall.py`:

```python
def _get_halls_dir(state_dir: Path) -> Path:
    """Get the halls subdirectory, creating if needed."""
    halls_dir = state_dir / "halls"
    halls_dir.mkdir(parents=True, exist_ok=True)
    return halls_dir


def _get_hall_lock(hall_id: str, state_dir: Path) -> FileLock:
    """Get FileLock for hall operations.

    Args:
        hall_id: Hall identifier
        state_dir: State directory

    Returns:
        FileLock instance for halls/{hall_id}.lock
    """
    halls_dir = _get_halls_dir(state_dir)
    lock_file = halls_dir / f"{hall_id}.lock"
    return FileLock(str(lock_file))


def _get_hall_events_file(hall_id: str, state_dir: Path) -> Path:
    """Get path to hall event ledger JSONL file."""
    return _get_halls_dir(state_dir) / f"{hall_id}.events.jsonl"


def _get_hall_state_file(hall_id: str, state_dir: Path) -> Path:
    """Get path to hall snapshot JSON file."""
    return _get_halls_dir(state_dir) / f"{hall_id}.json"


def append_hall_event(
    hall_id: str,
    event_type: HallEventType,
    data: dict[str, Any],
    state_dir: Path,
) -> HallEvent:
    """Append an event to the hall's event ledger.

    Thread-safe via FileLock on the events file.
    Reuses ULID generation from events.py for monotonic ordering.

    Args:
        hall_id: Hall identifier
        event_type: Type of hall event
        data: Event-specific data
        state_dir: State directory

    Returns:
        The created HallEvent

    Raises:
        ValueError: If hall_id contains path-unsafe characters
    """
    # Security: validate hall_id
    _validate_hall_id_for_filesystem(hall_id)

    event = HallEvent(
        event_id=str(ULID()),
        hall_id=hall_id,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        data=data,
    )

    events_file = _get_hall_events_file(hall_id, state_dir)
    lock = _get_hall_lock(hall_id, state_dir)

    with lock:
        with open(events_file, "a") as f:
            f.write(event.model_dump_json() + "\n")

    return event


def load_hall_events(
    hall_id: str,
    state_dir: Path,
    after: str | None = None,
) -> list[HallEvent]:
    """Load events from hall event ledger.

    Args:
        hall_id: Hall identifier
        state_dir: State directory
        after: Only return events with event_id > this ULID (for delta replay)

    Returns:
        List of HallEvent objects, ordered by ULID.
        Empty list if events file does not exist.
    """
    _validate_hall_id_for_filesystem(hall_id)
    events_file = _get_hall_events_file(hall_id, state_dir)

    if not events_file.exists():
        return []

    events: list[HallEvent] = []
    lock = _get_hall_lock(hall_id, state_dir)

    with lock:
        with open(events_file) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = HallEvent.model_validate_json(line)
                except ValidationError:
                    logger.warning(
                        "Skipping corrupt hall event line %d in %s",
                        line_num,
                        events_file.name,
                    )
                    continue

                if after is not None and event.event_id <= after:
                    continue

                events.append(event)

    return events


def _validate_hall_id_for_filesystem(hall_id: str) -> None:
    """Validate hall_id is safe for filesystem operations."""
    for pattern in ("..", "/", "\\"):
        if pattern in hall_id:
            raise ValueError(f"Invalid hall_id '{hall_id}': contains path-unsafe characters")
```

### S2.3::Event Reducer (Pure Function)

```python
def apply_hall_event(state: HallState, event: HallEvent) -> HallState:
    """Pure reducer: state(N) + event -> state(N+1).

    Applies a single event to the hall state, returning the mutated state.
    This function is the ONLY way hall state changes. All MCP tools
    append events, then the reducer derives the new state.

    Note: This function mutates `state` in place for efficiency during
    replay. Callers should NOT reuse the input state after calling this.

    Args:
        state: Current hall state (will be mutated)
        event: Event to apply

    Returns:
        The mutated state (same object as input)

    Raises:
        ValueError: If event data is malformed for the event type
    """
    match event.event_type:
        case HallEventType.HALL_OPENED:
            state.status = HallStatus.OPEN
            # hall_id, topic, max_depth, max_context_tokens set at creation time

        case HallEventType.PARTICIPANT_REGISTERED:
            participant = Participant(**event.data)
            state.participants[participant.id] = participant

        case HallEventType.PARTICIPANT_UNREGISTERED:
            pid = event.data["participant_id"]
            state.participants.pop(pid, None)

        case HallEventType.RACI_ASSIGNED:
            state.raci_matrix = RaciMatrix(**event.data["raci_matrix"])
            # Update participant RACI designations
            for pid, participant in state.participants.items():
                participant.raci_designation = None  # Reset all
            matrix = state.raci_matrix
            if matrix.responsible in state.participants:
                state.participants[matrix.responsible].raci_designation = "R"
            if matrix.accountable in state.participants:
                state.participants[matrix.accountable].raci_designation = "A"
            for pid in matrix.consulted:
                if pid in state.participants:
                    state.participants[pid].raci_designation = "C"
            for pid in matrix.informed:
                if pid in state.participants:
                    state.participants[pid].raci_designation = "I"

        case HallEventType.DEBATE_SPAWNED:
            thread_id = event.data["thread_id"]
            if thread_id not in state.active_debates:
                state.active_debates.append(thread_id)
            state.status = HallStatus.ACTIVE
            # Update participating agents to "active" status
            for pid in event.data.get("participant_ids", []):
                if pid in state.participants:
                    state.participants[pid].status = "active"

        case HallEventType.DEBATE_COMPLETED:
            thread_id = event.data["thread_id"]
            if thread_id in state.active_debates:
                state.active_debates.remove(thread_id)
            if thread_id not in state.completed_debates:
                state.completed_debates.append(thread_id)
            # Update compressed_log if provided
            if "compressed_log" in event.data:
                state.compressed_log = event.data["compressed_log"]
            # Reset participating agents to "on_call"
            for pid in event.data.get("participant_ids", []):
                if pid in state.participants:
                    state.participants[pid].status = "on_call"
                    state.participants[pid].raci_designation = None
            # Clear RACI matrix after debate completes
            state.raci_matrix = None
            # Auto-transition to REVIEWING if no active debates remain
            if not state.active_debates and state.status == HallStatus.ACTIVE:
                state.status = HallStatus.REVIEWING

        case HallEventType.CONSULTATION_COMPLETED:
            thread_id = event.data["thread_id"]
            if thread_id not in state.completed_debates:
                state.completed_debates.append(thread_id)
            if "compressed_log" in event.data:
                state.compressed_log = event.data["compressed_log"]

        case HallEventType.CONTEXT_COMPRESSED:
            state.compressed_log = event.data["compressed_log"]

        case HallEventType.HALL_CLOSED:
            state.status = HallStatus.ARCHIVED
            if "compressed_log" in event.data:
                state.compressed_log = event.data["compressed_log"]

        case HallEventType.HALL_FORCE_CLOSED:
            state.status = HallStatus.FORCE_CLOSED

    # Always update version marker and timestamp
    state.last_event_id = event.event_id
    state.updated_at = event.timestamp
    return state
```

### S2.4::Smart Loader (Read Path with Self-Healing)

```python
def load_hall(hall_id: str, state_dir: Path) -> HallState:
    """Load hall state with self-healing read-repair.

    Read Path (Hydrated Snapshot Pattern):
    1. Acquire hall lock
    2. Load JSON snapshot (if exists)
    3. Read event tail (events after snapshot.last_event_id)
    4. If tail is non-empty: replay delta events via reducer
    5. Flush updated snapshot to JSON
    6. Release lock and return fresh state

    If no snapshot exists but events exist, replays ALL events from a
    blank initial state (full reconstruction).

    If neither snapshot nor events exist, raises FileNotFoundError.

    Args:
        hall_id: Hall identifier
        state_dir: State directory

    Returns:
        Current HallState (up-to-date with event ledger)

    Raises:
        FileNotFoundError: If hall does not exist (no events and no snapshot)
        ValueError: If hall_id is path-unsafe
    """
    _validate_hall_id_for_filesystem(hall_id)

    state_file = _get_hall_state_file(hall_id, state_dir)
    events_file = _get_hall_events_file(hall_id, state_dir)
    lock = _get_hall_lock(hall_id, state_dir)

    with lock:
        state: HallState | None = None

        # Step 1: Try to load snapshot
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
            state = HallState.model_validate(data)

        # Step 2: Load delta events (after snapshot version)
        after = state.last_event_id if state else None
        delta_events = _load_hall_events_unlocked(hall_id, state_dir, after=after)

        # Step 3: If no snapshot and no events, hall doesn't exist
        if state is None and not delta_events:
            raise FileNotFoundError(f"Hall '{hall_id}' not found")

        # Step 4: If no snapshot but events exist, create initial state
        if state is None and delta_events:
            # Reconstruct from first event (must be HALL_OPENED)
            first = delta_events[0]
            state = HallState(
                hall_id=hall_id,
                topic=first.data.get("topic", ""),
                max_depth=first.data.get("max_depth", 3),
                max_context_tokens=first.data.get("max_context_tokens", 4096),
                max_debates=first.data.get("max_debates", 20),
                context_files=first.data.get("context_files", []),
                tier_name=first.data.get("tier_name", "standard"),
                created_at=first.timestamp,
                updated_at=first.timestamp,
            )

        # Step 5: Replay delta events through reducer
        if delta_events and state is not None:
            for event in delta_events:
                state = apply_hall_event(state, event)

            # Step 6: Flush updated snapshot (read-repair)
            _save_hall_snapshot_unlocked(state, state_dir)

        assert state is not None  # Guaranteed by steps 3-4
        return state


def _load_hall_events_unlocked(
    hall_id: str,
    state_dir: Path,
    after: str | None = None,
) -> list[HallEvent]:
    """Load hall events WITHOUT acquiring lock (caller holds lock).

    Internal function for use within load_hall where lock is already held.
    """
    events_file = _get_hall_events_file(hall_id, state_dir)
    if not events_file.exists():
        return []

    events: list[HallEvent] = []
    with open(events_file) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = HallEvent.model_validate_json(line)
            except ValidationError:
                logger.warning(
                    "Skipping corrupt hall event line %d for hall %s",
                    line_num,
                    hall_id,
                )
                continue
            if after is not None and event.event_id <= after:
                continue
            events.append(event)

    return events
```

### S2.5::Save Hall (Write Path)

```python
def save_hall(
    state: HallState,
    event_type: HallEventType,
    event_data: dict[str, Any],
    state_dir: Path,
) -> HallEvent:
    """Write path: append event first, then update snapshot.

    Write Path (Event-First):
    1. Acquire hall lock
    2. Append event to JSONL ledger (truth)
    3. Apply event to in-memory state via reducer
    4. Flush updated snapshot to JSON (checkpoint)
    5. Release lock

    This is the PRIMARY write function. All hall mutations go through here.

    Args:
        state: Current HallState (will be mutated by reducer)
        event_type: Type of event to append
        event_data: Event-specific data
        state_dir: State directory

    Returns:
        The appended HallEvent

    Raises:
        ValueError: If hall_id is path-unsafe
    """
    _validate_hall_id_for_filesystem(state.hall_id)
    lock = _get_hall_lock(state.hall_id, state_dir)

    with lock:
        # Step 1: Create and append event
        event = HallEvent(
            event_id=str(ULID()),
            hall_id=state.hall_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            data=event_data,
        )

        events_file = _get_hall_events_file(state.hall_id, state_dir)
        with open(events_file, "a") as f:
            f.write(event.model_dump_json() + "\n")

        # Step 2: Apply event to in-memory state
        apply_hall_event(state, event)

        # Step 3: Flush snapshot
        _save_hall_snapshot_unlocked(state, state_dir)

    return event


def _save_hall_snapshot_unlocked(state: HallState, state_dir: Path) -> None:
    """Flush hall state snapshot to JSON (caller holds lock).

    Uses atomic write pattern (temp file + rename) matching state.py.
    """
    state_file = _get_hall_state_file(state.hall_id, state_dir)

    fd, tmp_path = tempfile.mkstemp(
        dir=_get_halls_dir(state_dir),
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(state.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(state_file))
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
```

### S2.6::Lock Discipline Summary

| Operation | Lock Acquired | Lock Scope |
|-----------|--------------|------------|
| `load_hall` | `halls/{hall_id}.lock` | Full read-hydrate-flush cycle |
| `save_hall` | `halls/{hall_id}.lock` | Event append + reducer + snapshot flush |
| `append_hall_event` | `halls/{hall_id}.lock` | Event append only (for standalone events) |
| Child debate operations | `{thread_id}.lock` | Existing CAS pattern (independent) |

**No nested locks.** Hall lock and debate lock are never held simultaneously.
The HallEngine releases the hall lock BEFORE spawning a child debate.
Child results are committed to the hall ledger AFTER the child debate completes.

===

## S3::MCP_TOOL_SPECIFICATIONS

All tool implementations live in `src/debate_hall_mcp/tools/hall.py`.
All tools are registered in `src/debate_hall_mcp/server.py`.

### S3.1::hall_open

```python
async def hall_open(
    topic: str,
    hall_id: str | None = None,
    max_depth: int = 3,
    max_context_tokens: int = 4096,
    max_debates: int = 20,
    context_files: list[str] | None = None,
    tier: str = "standard",
) -> dict[str, Any]:
    """Create a new Hall for multi-debate governance orchestration.

    Args:
        topic: Hall topic / purpose (required, min 1 char)
        hall_id: Optional custom hall ID. If None, generated as
            "hall-YYYY-MM-DD-{slugified-topic}-{ulid8}".
        max_depth: Maximum nesting depth for sub-debates (I8, 1-10, default 3)
        max_context_tokens: Token budget for compressed context (I7, 256-32768, default 4096)
        max_debates: Maximum total debates allowed (I3 at hall level, 1-100, default 20)
        context_files: Optional list of absolute file paths for shared codebase context
        tier: Tier configuration name for debate orchestration (default "standard")

    Returns:
        {
            "hall_id": str,
            "topic": str,
            "status": "open",
            "max_depth": int,
            "max_context_tokens": int,
            "max_debates": int,
            "created_at": str  # ISO format
        }

    Events emitted:
        HALL_OPENED with data: {topic, max_depth, max_context_tokens, max_debates, context_files, tier_name}

    Validation:
        - topic must be non-empty
        - max_depth in [1, 10]
        - max_context_tokens in [256, 32768]
        - max_debates in [1, 100]
        - context_files paths must be absolute if provided
        - hall_id must be filesystem-safe if provided

    Error cases:
        - ValueError if topic is empty
        - ValueError if limits are out of range
        - ValueError if hall_id contains path-unsafe characters
        - FileExistsError if hall_id already exists
    """
```

### S3.2::hall_status

```python
def hall_status(
    hall_id: str,
) -> dict[str, Any]:
    """View current Hall state including participants, debates, and compressed context.

    Loads hall via Smart Loader (read-repair if stale snapshot).

    Args:
        hall_id: Hall identifier

    Returns:
        {
            "hall_id": str,
            "topic": str,
            "status": str,  # "open"|"active"|"reviewing"|"archived"|"force_closed"
            "participants": {
                str: {  # participant_id -> participant data
                    "id": str,
                    "name": str,
                    "kind": str,
                    "status": str,
                    "prompt_source": str | None,
                    "capabilities": list[str],
                    "raci_designation": str | None,
                    "registered_at": str
                }
            },
            "active_debates": list[str],   # thread_ids
            "completed_debates": list[str], # thread_ids
            "compressed_log": str,          # OCTAVE context (I7)
            "max_depth": int,
            "max_context_tokens": int,
            "max_debates": int,
            "debate_count": int,  # len(active) + len(completed)
            "participant_count": int,
            "created_at": str,
            "updated_at": str
        }

    Events emitted:
        None (read-only operation; read-repair is internal)

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if hall_id is path-unsafe
    """
```

### S3.3::hall_close

```python
def hall_close(
    hall_id: str,
    summary: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Archive a Hall, generating final compressed context.

    Args:
        hall_id: Hall identifier
        summary: Optional human-provided summary to include in final compressed_log
        force: If True, force-close all active debates first (I5 enforcement).
            If False and active debates exist, returns error.

    Returns:
        {
            "hall_id": str,
            "status": "archived",
            "compressed_log": str,  # Final OCTAVE compressed context
            "total_debates": int,
            "total_participants": int,
            "closed_at": str
        }

    Events emitted:
        - If force=True and active debates exist: HALL_FORCE_CLOSED
        - Otherwise: HALL_CLOSED with data: {summary, compressed_log}

    Validation:
        - Hall must exist
        - If force=False: all active_debates must be empty (I8 enforcement)
        - Hall must not already be ARCHIVED or FORCE_CLOSED

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if active debates exist and force=False
        - ValueError if hall already archived/force_closed
    """
```

### S3.4::hall_register

```python
def hall_register(
    hall_id: str,
    name: str,
    kind: str = "agent",
    participant_id: str | None = None,
    prompt_source: str | None = None,
    provider_config: dict[str, Any] | None = None,
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Register a participant in the Hall's identity registry (I6).

    Args:
        hall_id: Hall identifier
        name: Display name (e.g., "implementation-lead", "Alice")
        kind: Participant kind: "agent"|"human"|"system" (default "agent")
        participant_id: Optional custom ID. If None, generated from slugified name.
        prompt_source: Role name for prompt resolution via get_agent_prompt().
            If provided, validates the prompt exists at registration time.
        provider_config: For AI agents, provider configuration dict matching RoleConfig schema.
            If None, hall's default tier provider is used for this participant.
        capabilities: Tag-based capability list for RACI role assignment.

    Returns:
        {
            "hall_id": str,
            "participant_id": str,
            "name": str,
            "kind": str,
            "status": "on_call",
            "prompt_source": str | None,
            "capabilities": list[str],
            "registered_at": str
        }

    Events emitted:
        PARTICIPANT_REGISTERED with data: {id, name, kind, status, prompt_source, capabilities, registered_at}
        (provider_config is NOT included in event data to avoid persisting secrets)

    Validation:
        - Hall must exist and not be ARCHIVED or FORCE_CLOSED
        - name must be non-empty (1-128 chars)
        - kind must be "agent"|"human"|"system"
        - participant_id must be unique within hall
        - participant_id must be filesystem-safe (alphanumeric + hyphens + underscores)
        - If prompt_source provided: get_agent_prompt(prompt_source) must return non-None
        - If provider_config provided: must validate as RoleConfig

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if hall is archived/force_closed
        - ValueError if participant_id already registered
        - ValueError if prompt_source not resolvable
        - ValidationError if provider_config is invalid RoleConfig
    """
```

### S3.5::hall_unregister

```python
def hall_unregister(
    hall_id: str,
    participant_id: str,
) -> dict[str, Any]:
    """Remove a participant from the Hall's identity registry.

    Args:
        hall_id: Hall identifier
        participant_id: ID of participant to remove

    Returns:
        {
            "hall_id": str,
            "participant_id": str,
            "status": "unregistered",
            "unregistered_at": str
        }

    Events emitted:
        PARTICIPANT_UNREGISTERED with data: {participant_id}

    Validation:
        - Hall must exist and not be ARCHIVED or FORCE_CLOSED
        - participant_id must be registered
        - Participant must NOT be in "active" status (i.e., not in an active debate)

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if hall is archived/force_closed
        - ValueError if participant_id not found
        - ValueError if participant is in active debate
    """
```

### S3.6::hall_debate

```python
async def hall_debate(
    hall_id: str,
    topic: str,
    mode: str = "raci",
    responsible: str | None = None,
    accountable: str | None = None,
    consulted: list[str] | None = None,
    informed: list[str] | None = None,
    parent_thread_id: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Spawn and run a debate within the Hall context.

    Creates a child DebateRoom linked to this Hall, auto-assigns participants
    from the registry, injects hall compressed_log as context, and runs the
    debate via DebateOrchestrator.

    Args:
        hall_id: Hall identifier
        topic: Debate topic
        mode: Debate mode: "raci"|"speed"|"standard" (default "raci")
        responsible: Participant ID for R role (required for raci mode)
        accountable: Participant ID for A role (required for raci mode)
        consulted: Participant IDs for C roles (optional, max 5)
        informed: Participant IDs for I roles (optional, max 3)
        parent_thread_id: For sub-debates, the parent debate's thread_id.
            Enables I8 recursive topology tracking.
        thread_id: Optional custom thread ID (auto-generated if None)

    Returns:
        {
            "hall_id": str,
            "thread_id": str,
            "topic": str,
            "status": str,           # Final debate status
            "turn_count": int,
            "synthesis": str | None,
            "mode": str,
            "depth": int,            # Nesting depth (0 = root, 1 = child, etc.)
            "parent_thread_id": str | None
        }

    Events emitted (in order):
        1. RACI_ASSIGNED with data: {raci_matrix: {responsible, accountable, consulted, informed}}
        2. DEBATE_SPAWNED with data: {thread_id, topic, mode, parent_thread_id, depth, participant_ids}
        3. (debate runs via DebateOrchestrator — emits its own debate-level events)
        4. DEBATE_COMPLETED with data: {thread_id, status, synthesis_preview, compressed_log, participant_ids}

    Validation:
        - Hall must exist and be OPEN or ACTIVE
        - All participant IDs must be registered in hall
        - For raci mode: responsible and accountable are required
        - Nesting depth must be < max_depth (I8)
        - Total debates (active + completed) must be < max_debates (I3 at hall level)
        - If parent_thread_id provided: must be in active_debates

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if hall is not OPEN or ACTIVE
        - ValueError if participant not registered
        - ValueError if depth >= max_depth (I8 violation)
        - ValueError if max_debates exceeded (I3 at hall level)
        - ValueError if raci mode but R/A not specified
        - RuntimeError if debate orchestration fails

    Side effects:
        - Creates DebateRoom with parent_hall_id and parent_thread_id set
        - Updates participant statuses to "active" during debate
        - Regenerates compressed_log on debate completion
        - Updates hall status to ACTIVE on first debate
        - Resets participant statuses to "on_call" on completion
    """
```

**Depth Calculation Logic:**

```python
def _calculate_depth(
    hall_state: HallState,
    parent_thread_id: str | None,
    state_dir: Path,
) -> int:
    """Calculate nesting depth for a new debate.

    - Root debate (no parent): depth = 0
    - Child of root: depth = 1
    - Grandchild: depth = 2
    - etc.

    Walks parent_thread_id chain to count depth.
    """
    if parent_thread_id is None:
        return 0

    depth = 0
    current_parent = parent_thread_id
    while current_parent is not None:
        depth += 1
        # Load parent debate to check its parent
        try:
            parent_room = load_debate_state(current_parent, state_dir)
            current_parent = parent_room.parent_thread_id
        except FileNotFoundError:
            break

    return depth
```

### S3.7::hall_consult

```python
async def hall_consult(
    hall_id: str,
    question: str,
    consultant_id: str,
) -> dict[str, Any]:
    """Lightweight 2-turn consultation within the Hall.

    Runs a minimal Speed-mode debate (max_turns=2):
    - Turn 1: System poses question with hall compressed_log as context
    - Turn 2: Consultant responds

    The consultation is recorded as a completed sub-debate linked to the hall.

    Args:
        hall_id: Hall identifier
        question: The question to pose to the consultant
        consultant_id: Participant ID of the consultant to invoke

    Returns:
        {
            "hall_id": str,
            "thread_id": str,       # Consultation debate thread_id
            "question": str,
            "consultant_id": str,
            "response": str,        # Consultant's response content
            "token_count": int | None  # Response token count if available
        }

    Events emitted:
        CONSULTATION_COMPLETED with data: {thread_id, consultant_id, question_preview, compressed_log}

    Validation:
        - Hall must exist and be OPEN or ACTIVE
        - consultant_id must be registered and kind="agent"
        - question must be non-empty

    Error cases:
        - FileNotFoundError if hall does not exist
        - ValueError if hall is not OPEN or ACTIVE
        - ValueError if consultant not registered
        - ValueError if consultant is not kind="agent"
        - ValueError if question is empty
        - RuntimeError if consultation fails

    Side effects:
        - Creates Speed-mode DebateRoom linked to hall (parent_hall_id set)
        - Regenerates compressed_log to include consultation result
    """
```

===

## S4::ORCHESTRATOR_REFACTOR

### S4.1::Changes to DebateOrchestrator.__init__

**Current signature:**
```python
def __init__(
    self,
    tier_config: TierConfig,
    state_dir: Path,
    provider_factory: ProviderFactory | None = None,
    context_block: str | None = None,
) -> None:
```

**New signature (backward-compatible):**
```python
def __init__(
    self,
    tier_config: TierConfig,
    state_dir: Path,
    provider_factory: ProviderFactory | None = None,
    context_block: str | None = None,
    hall_context: str | None = None,
    participant_providers: dict[str, ModelProvider] | None = None,
) -> None:
    """Initialize orchestrator with tier configuration.

    Args:
        tier_config: Configuration for Wind/Wall/Door providers
        state_dir: Directory for debate state persistence
        provider_factory: Optional factory for creating providers
        context_block: Optional pre-formatted codebase context block
        hall_context: Optional OCTAVE-formatted hall context (I7 injection).
            When provided, prepended BEFORE <DEBATE_STATE> in every
            agent prompt as <HALL_CONTEXT>...</HALL_CONTEXT>.
        participant_providers: Optional mapping of participant_id -> ModelProvider.
            When provided, _execute_raci_role_turn uses this mapping instead
            of creating providers from tier_config. Enables dynamic participant
            injection from hall registry.
    """
    self.tier_config = tier_config
    self.state_dir = state_dir
    self._provider_factory = provider_factory or create_provider
    self._context_block = context_block
    self._hall_context = hall_context
    self._participant_providers = participant_providers or {}
```

### S4.2::Changes to _execute_role_turn

Add hall context injection in the VTP prompt assembly:

```python
# In _execute_role_turn, after state_block construction:

# VTP: Build enhanced prompt with primers, compression, context, hall context, state
enhanced_prompt = ""
if primer_content:
    enhanced_prompt += f"{primer_content}\n\n"
if compression_directive:
    enhanced_prompt += (
        f"<COMPRESSION_DIRECTIVE>\n{compression_directive}\n</COMPRESSION_DIRECTIVE>\n\n"
    )
if self._context_block:
    enhanced_prompt += f"{self._context_block}\n\n"
# NEW: Hall context injection (I7: Holographic Context Compression)
if self._hall_context:
    enhanced_prompt += f"<HALL_CONTEXT>\n{self._hall_context}\n</HALL_CONTEXT>\n\n"
enhanced_prompt += f"{state_block}\n\n{user_prompt}"
```

The same change applies to `_execute_speed_role_turn` and `_execute_raci_role_turn`.

### S4.3::Changes to run_raci for Participant Providers

In `run_raci`, when `self._participant_providers` is non-empty, use participant-specific providers:

```python
# In run_raci, replace:
#   provider = self._provider_factory(self.tier_config.wind)
# With:

if self._participant_providers:
    # Hall-managed debate: use participant-specific providers
    def _get_participant_provider(role_name: str) -> ModelProvider:
        if role_name in self._participant_providers:
            return self._participant_providers[role_name]
        # Fallback to default wind provider
        return self._provider_factory(self.tier_config.wind)

    # Then in the manifest execution loop, replace `provider` with:
    provider = _get_participant_provider(spec.role)
else:
    # Standalone RACI: use single wind provider (existing behavior)
    provider = self._provider_factory(self.tier_config.wind)
```

### S4.4::Backward Compatibility Guarantees

1. `hall_context=None` (default): No `<HALL_CONTEXT>` tag injected. Zero change to existing prompts.
2. `participant_providers={}` (default): Provider creation uses existing tier_config logic. Zero change.
3. All existing method signatures preserved. New parameters are keyword-only with defaults.
4. All 864+ existing tests continue to pass without modification.

===

## S5::COMPRESSION_ENGINE

Located in `src/debate_hall_mcp/compression.py`.

### S5.1::Function Signature

```python
def generate_compressed_log(
    hall_state: HallState,
    state_dir: Path,
    token_counter: Callable[[str], int] | None = None,
) -> str:
    """Generate OCTAVE-compressed hall context for participant injection (I7).

    Produces a structured OCTAVE summary of the hall's current state including:
    - Completed debate decisions (from DecisionRecord extraction)
    - Active debate summaries
    - Participant registry summary
    - Unresolved questions

    The output must fit within hall_state.max_context_tokens.

    Args:
        hall_state: Current HallState with completed/active debates
        state_dir: State directory for loading child debate rooms
        token_counter: Optional token counting function.
            Default: len(text) // 4 (heuristic, ~4 chars per token).
            Override for precise model-specific counting.

    Returns:
        OCTAVE-formatted compressed log string

    Raises:
        ContextBudgetExceeded: If compression cannot fit within token budget
            even after FIFO eviction of oldest decisions.

    Token Budget Enforcement:
        RESERVED_BUFFER = 200 tokens (for runtime overhead)
        effective_budget = max_context_tokens - RESERVED_BUFFER
        If compressed log exceeds effective_budget:
        1. Apply FIFO eviction: remove oldest completed decisions
        2. If still exceeds after evicting all but 3 most recent: raise ContextBudgetExceeded
    """
```

### S5.2::OCTAVE Template

```python
HALL_CONTEXT_TEMPLATE = """\
===HALL_CONTEXT===
HALL::{hall_id}
TOPIC::{topic}
STATUS::{status}
DECISIONS::{decision_count}
PARTICIPANTS::{participant_count}

{decisions_section}

{active_section}

{participants_section}

{unresolved_section}
===END==="""

DECISION_TEMPLATE = "D{index}::[topic::{topic}, verdict::{verdict}, constraint::{constraint}, thread::{thread_id}]"

ACTIVE_DEBATE_TEMPLATE = "  {thread_id}::[topic::{topic}, turn::{turn_count}/{max_turns}, participants::{participant_names}]"

PARTICIPANT_TEMPLATE = "  {name}::[kind::{kind}, status::{status}, raci::{raci}]"
```

### S5.3::Implementation Logic

```python
class ContextBudgetExceeded(Exception):
    """Raised when compressed log cannot fit within token budget."""
    pass


# Default token counter: heuristic ~4 chars per token
DEFAULT_TOKEN_COUNTER: Callable[[str], int] = lambda text: len(text) // 4

# Reserved buffer for runtime overhead
RESERVED_BUFFER_TOKENS = 200


def generate_compressed_log(
    hall_state: HallState,
    state_dir: Path,
    token_counter: Callable[[str], int] | None = None,
) -> str:
    count_tokens = token_counter or DEFAULT_TOKEN_COUNTER
    effective_budget = hall_state.max_context_tokens - RESERVED_BUFFER_TOKENS

    # 1. Extract decisions from completed debates
    decisions: list[dict[str, str]] = []
    for thread_id in hall_state.completed_debates:
        try:
            room = load_debate_state(thread_id, state_dir)
            record = extract_decision_record(room)
            # Extract verdict from synthesis (first 100 chars)
            verdict = _extract_verdict(record.synthesis)
            # Extract key constraint from wall_constraints (first item, truncated)
            constraint = (
                record.wall_constraints[0][:80] if record.wall_constraints else "none"
            )
            decisions.append({
                "topic": record.topic[:60],
                "verdict": verdict,
                "constraint": constraint,
                "thread_id": thread_id,
            })
        except (FileNotFoundError, ValueError):
            # Skip debates that can't be loaded
            continue

    # 2. Build active debate summaries
    active_lines: list[str] = []
    for thread_id in hall_state.active_debates:
        try:
            room = load_debate_state(thread_id, state_dir)
            participant_names = ", ".join(t.role for t in room.turns[-3:]) if room.turns else "none"
            active_lines.append(
                ACTIVE_DEBATE_TEMPLATE.format(
                    thread_id=thread_id,
                    topic=room.topic[:50],
                    turn_count=len(room.turns),
                    max_turns=room.max_turns,
                    participant_names=participant_names,
                )
            )
        except FileNotFoundError:
            continue

    # 3. Build participant summary
    participant_lines: list[str] = []
    for pid, p in hall_state.participants.items():
        participant_lines.append(
            PARTICIPANT_TEMPLATE.format(
                name=p.name,
                kind=p.kind.value,
                status=p.status,
                raci=p.raci_designation or "none",
            )
        )

    # 4. Build with FIFO eviction for budget enforcement
    while True:
        decisions_section = "COMPLETED_DECISIONS::[\n" + "\n".join(
            DECISION_TEMPLATE.format(
                index=i + 1,
                topic=d["topic"],
                verdict=d["verdict"],
                constraint=d["constraint"],
                thread_id=d["thread_id"],
            )
            for i, d in enumerate(decisions)
        ) + "\n]" if decisions else "COMPLETED_DECISIONS::[]"

        active_section = "ACTIVE_DEBATES::[\n" + "\n".join(active_lines) + "\n]" if active_lines else "ACTIVE_DEBATES::[]"

        participants_section = "PARTICIPANTS::[\n" + "\n".join(participant_lines) + "\n]" if participant_lines else "PARTICIPANTS::[]"

        unresolved_section = "UNRESOLVED::[]"  # V1: no explicit unresolved tracking

        compressed = HALL_CONTEXT_TEMPLATE.format(
            hall_id=hall_state.hall_id,
            topic=hall_state.topic[:80],
            status=hall_state.status.value,
            decision_count=len(decisions),
            participant_count=len(hall_state.participants),
            decisions_section=decisions_section,
            active_section=active_section,
            participants_section=participants_section,
            unresolved_section=unresolved_section,
        )

        token_count = count_tokens(compressed)
        if token_count <= effective_budget:
            return compressed

        # FIFO eviction: remove oldest decision
        if len(decisions) > 3:
            decisions.pop(0)  # Remove oldest
            continue

        # Cannot fit even with minimum decisions
        raise ContextBudgetExceeded(
            f"Hall context ({token_count} tokens) exceeds budget "
            f"({effective_budget} tokens) even after FIFO eviction. "
            f"Consider increasing max_context_tokens."
        )


def _extract_verdict(synthesis: str) -> str:
    """Extract verdict label from synthesis text.

    Looks for GO, NO-GO, CONDITIONAL, APPROVED, REJECTED patterns.
    Falls back to first 20 chars of synthesis.
    """
    synthesis_upper = synthesis.upper()
    if "NO-GO" in synthesis_upper or "REJECTED" in synthesis_upper:
        return "NO-GO"
    if "CONDITIONAL" in synthesis_upper:
        return "CONDITIONAL"
    if "GO" in synthesis_upper or "APPROVED" in synthesis_upper:
        return "GO"
    return synthesis[:20].replace("\n", " ")
```

### S5.4::Token Budget Math

| Component | Tokens (approx) | Formula |
|-----------|-----------------|---------|
| Header | ~25 | Fixed template overhead |
| Per decision | ~80 | topic(15) + verdict(3) + constraint(20) + thread_id(10) + markup(32) |
| Per active debate | ~40 | thread_id(10) + topic(12) + counts(5) + names(8) + markup(5) |
| Per participant | ~15 | name(5) + kind(2) + status(3) + raci(2) + markup(3) |
| Footer | ~10 | UNRESOLVED + END markers |

**Example workloads:**
- Small: 3 decisions + 1 active + 3 participants = 25 + 240 + 40 + 45 + 10 = 360 tokens (9% of 4096)
- Medium: 10 decisions + 2 active + 5 participants = 25 + 800 + 80 + 75 + 10 = 990 tokens (24%)
- Large: 40 decisions + 3 active + 10 participants = 25 + 3200 + 120 + 150 + 10 = 3505 tokens (86%)
- At 86%, FIFO eviction begins trimming oldest decisions

This resolves G2 (token budget empirical validation): the math shows 4096 comfortably handles
10+ decisions. The FIFO eviction mechanism handles the edge case of very active halls.

===

## S6::MODULE_STRUCTURE

### S6.1::New Files

| File | Purpose | Approx LOC |
|------|---------|------------|
| `src/debate_hall_mcp/hall.py` | HallState, HallEvent, HallEventType, Participant, ParticipantKind, RaciMatrix, HallStatus, apply_hall_event reducer, load_hall, save_hall, persistence functions | ~500 |
| `src/debate_hall_mcp/tools/hall.py` | MCP tool implementations: hall_open, hall_status, hall_close, hall_register, hall_unregister, hall_debate, hall_consult | ~400 |
| `src/debate_hall_mcp/compression.py` | generate_compressed_log, ContextBudgetExceeded, OCTAVE templates, token counting, FIFO eviction | ~200 |

### S6.2::Modified Files

| File | Changes | Impact |
|------|---------|--------|
| `src/debate_hall_mcp/state.py` | Add `parent_hall_id: str \| None = None` and `parent_thread_id: str \| None = None` to DebateRoom | 2 lines added. Zero existing test breakage. |
| `src/debate_hall_mcp/orchestrator.py` | Add `hall_context` and `participant_providers` params to `__init__`. Add `<HALL_CONTEXT>` injection in `_execute_role_turn`, `_execute_speed_role_turn`, `_execute_raci_role_turn`. | ~30 lines added. All new params have defaults. Zero existing test breakage. |
| `src/debate_hall_mcp/server.py` | Register 7 new MCP tools (hall_open, hall_status, hall_close, hall_register, hall_unregister, hall_debate, hall_consult). Update tool count in docstring. | ~100 lines added. No existing tool changes. |
| `src/debate_hall_mcp/events.py` | No changes needed. Hall events use their own infrastructure in hall.py. | 0 lines changed. |

### S6.3::Unchanged Files

| File | Reason |
|------|--------|
| `src/debate_hall_mcp/engine.py` | Turn logic is debate-level. Hall operates above this layer. |
| `src/debate_hall_mcp/raci.py` | RACIConfig and compile_raci_manifest are reused as-is by hall_debate. |
| `src/debate_hall_mcp/config.py` | TierConfig and RoleConfig are reused as-is. |
| `src/debate_hall_mcp/decision.py` | DecisionRecord and extract_decision_record are reused as-is by compression engine. |
| `src/debate_hall_mcp/prompts/` | Prompt infrastructure reused as-is. get_agent_prompt() used for participant prompt resolution. |
| `src/debate_hall_mcp/providers/` | Provider infrastructure reused as-is. create_provider() used for participant providers. |

===

## S7::TEST_STRATEGY

### S7.1::Unit Tests for hall.py

**File:** `tests/unit/test_hall.py`

| Test Scenario | Category | Description |
|--------------|----------|-------------|
| `test_hall_state_creation` | Happy path | Create HallState with valid fields, verify defaults |
| `test_hall_state_validation_bad_hall_id` | Error | hall_id with path traversal characters rejected |
| `test_participant_creation` | Happy path | Create Participant with all fields |
| `test_participant_id_validation` | Error | Invalid chars in participant_id rejected |
| `test_raci_designation_validation` | Error | Invalid RACI designation rejected |
| `test_raci_matrix_validation` | Happy path | Valid RACI matrix with R, A, C, I |
| `test_raci_matrix_same_ra` | Error | responsible == accountable rejected |
| `test_raci_matrix_duplicate_roles` | Error | Same participant in multiple roles rejected |
| `test_raci_matrix_consulted_limit` | Error | >5 consulted rejected |
| `test_hall_event_type_values` | Happy path | All enum values serializable |
| `test_apply_hall_event_opened` | Reducer | HALL_OPENED sets status |
| `test_apply_hall_event_participant_registered` | Reducer | Adds participant to registry |
| `test_apply_hall_event_participant_unregistered` | Reducer | Removes participant |
| `test_apply_hall_event_raci_assigned` | Reducer | Sets RACI designations |
| `test_apply_hall_event_debate_spawned` | Reducer | Adds to active_debates, sets ACTIVE |
| `test_apply_hall_event_debate_completed` | Reducer | Moves to completed, updates compressed_log |
| `test_apply_hall_event_debate_completed_auto_reviewing` | Reducer | Auto-transitions to REVIEWING when no active debates |
| `test_apply_hall_event_hall_closed` | Reducer | Sets ARCHIVED |
| `test_apply_hall_event_force_closed` | Reducer | Sets FORCE_CLOSED |
| `test_apply_hall_event_updates_version` | Reducer | last_event_id and updated_at always updated |
| `test_load_hall_from_events_only` | Smart Loader | No snapshot, full replay from events |
| `test_load_hall_from_snapshot_only` | Smart Loader | Snapshot is current, no replay needed |
| `test_load_hall_stale_snapshot` | Smart Loader | Snapshot behind events, delta replay |
| `test_load_hall_not_found` | Error | No snapshot and no events raises FileNotFoundError |
| `test_save_hall_event_first` | Write path | Event appended before snapshot updated |
| `test_save_hall_atomic_write` | Write path | Snapshot uses temp-file-rename pattern |
| `test_append_hall_event_thread_safety` | Concurrency | FileLock prevents concurrent corruption |
| `test_load_hall_events_after_filter` | Ledger | `after` parameter filters correctly |
| `test_load_hall_events_corrupt_line` | Error | Corrupt JSONL line skipped with warning |
| `test_hall_id_filesystem_safety` | Security | Path traversal in hall_id rejected |

**Estimated test count: ~28 tests**

### S7.2::Unit Tests for compression.py

**File:** `tests/unit/test_compression.py`

| Test Scenario | Category | Description |
|--------------|----------|-------------|
| `test_generate_compressed_log_empty_hall` | Happy path | No debates, produces minimal output |
| `test_generate_compressed_log_with_decisions` | Happy path | Completed debates produce decision entries |
| `test_generate_compressed_log_with_active_debates` | Happy path | Active debates listed with turn counts |
| `test_generate_compressed_log_with_participants` | Happy path | Participants listed with RACI designations |
| `test_generate_compressed_log_token_budget_within` | Happy path | Output fits within max_context_tokens |
| `test_generate_compressed_log_fifo_eviction` | Edge case | Oldest decisions evicted when budget exceeded |
| `test_generate_compressed_log_budget_exceeded` | Error | ContextBudgetExceeded when even min decisions exceed budget |
| `test_generate_compressed_log_custom_token_counter` | Happy path | Custom counter function used |
| `test_extract_verdict_go` | Unit | "GO" detected in synthesis |
| `test_extract_verdict_no_go` | Unit | "NO-GO" detected in synthesis |
| `test_extract_verdict_conditional` | Unit | "CONDITIONAL" detected |
| `test_extract_verdict_fallback` | Unit | Unknown verdict falls back to first 20 chars |
| `test_compressed_log_octave_format` | Format | Output is valid OCTAVE with ===HALL_CONTEXT=== markers |
| `test_compressed_log_missing_debate_skipped` | Error | FileNotFoundError for debate gracefully skipped |

**Estimated test count: ~14 tests**

### S7.3::Unit Tests for tools/hall.py

**File:** `tests/unit/tools/test_hall_tools.py`

| Test Scenario | Category | Description |
|--------------|----------|-------------|
| `test_hall_open_basic` | Happy path | Create hall with defaults |
| `test_hall_open_custom_id` | Happy path | Custom hall_id accepted |
| `test_hall_open_validation_empty_topic` | Error | Empty topic rejected |
| `test_hall_open_validation_bad_limits` | Error | Out-of-range limits rejected |
| `test_hall_open_duplicate_id` | Error | Existing hall_id rejected |
| `test_hall_status_basic` | Happy path | Returns full state |
| `test_hall_status_not_found` | Error | Non-existent hall raises FileNotFoundError |
| `test_hall_close_basic` | Happy path | Archives hall with final compressed_log |
| `test_hall_close_active_debates_blocked` | Error (I8) | Close blocked when active debates exist |
| `test_hall_close_force` | Happy path (I5) | Force-close with active debates |
| `test_hall_close_already_archived` | Error | Already archived hall rejected |
| `test_hall_register_basic` | Happy path | Register agent with defaults |
| `test_hall_register_with_prompt_source` | Happy path | Prompt source resolved |
| `test_hall_register_bad_prompt_source` | Error | Unresolvable prompt_source rejected |
| `test_hall_register_duplicate_id` | Error | Duplicate participant_id rejected |
| `test_hall_register_archived_hall` | Error | Registration on archived hall rejected |
| `test_hall_unregister_basic` | Happy path | Remove participant |
| `test_hall_unregister_active_participant` | Error | Active participant removal blocked |
| `test_hall_unregister_not_found` | Error | Non-existent participant rejected |
| `test_hall_debate_raci_mode` | Happy path | Full RACI debate within hall |
| `test_hall_debate_speed_mode` | Happy path | Speed debate within hall |
| `test_hall_debate_depth_limit` | Error (I8) | Depth >= max_depth rejected |
| `test_hall_debate_max_debates` | Error (I3) | Exceeding max_debates rejected |
| `test_hall_debate_unregistered_participant` | Error | Unregistered participant rejected |
| `test_hall_debate_context_injection` | I7 | Compressed log injected into debate context |
| `test_hall_consult_basic` | Happy path | 2-turn consultation returns response |
| `test_hall_consult_human_rejected` | Error | Human consultant rejected |
| `test_hall_consult_not_found` | Error | Non-existent consultant rejected |

**Estimated test count: ~28 tests**

### S7.4::Integration Tests

**File:** `tests/integration/test_hall_integration.py`

| Test Scenario | Description |
|--------------|-------------|
| `test_full_hall_lifecycle` | Open -> Register 3 agents -> Debate (RACI) -> Close |
| `test_nested_debate_topology` | Root debate -> Child -> Grandchild (depth=2), verify I8 closure |
| `test_crash_recovery_read_repair` | Corrupt snapshot JSON -> load_hall repairs from events |
| `test_hall_with_real_providers` | End-to-end with VirtualProvider (from existing test infrastructure) |
| `test_compressed_log_injection` | Verify hall_context appears in agent prompt during debate |
| `test_multiple_sequential_debates` | Register -> Debate1 -> Debate2 -> verify compressed_log accumulates |
| `test_consultation_within_active_hall` | Open -> Register -> Consult -> verify consultation recorded |

**Estimated test count: ~7 tests**

### S7.5::Golden Tests (Backward Compatibility)

**File:** `tests/golden/test_no_regression.py`

| Test Scenario | Description |
|--------------|-------------|
| `test_existing_debate_init_unchanged` | debate_init with no hall params produces identical output |
| `test_existing_debate_turn_unchanged` | debate_turn output format unchanged |
| `test_existing_debate_get_unchanged` | debate_get output includes parent_hall_id=None, parent_thread_id=None |
| `test_existing_debate_close_unchanged` | debate_close output format unchanged |
| `test_existing_orchestrator_unchanged` | DebateOrchestrator with no hall params produces identical behavior |
| `test_existing_raci_mode_unchanged` | run_raci without hall context produces identical behavior |
| `test_existing_state_deserialization` | Old JSON state files (without hall fields) load correctly |

**Estimated test count: ~7 tests**

### S7.6::Total Test Estimate

| Module | Tests |
|--------|-------|
| test_hall.py | ~28 |
| test_compression.py | ~14 |
| test_hall_tools.py | ~28 |
| test_hall_integration.py | ~7 |
| test_no_regression.py | ~7 |
| **Total new tests** | **~84** |
| **Existing tests** | **864+** |
| **Total after implementation** | **~948+** |

===

## S8::I_COMPLIANCE_VERIFICATION

### I1::COGNITIVE_STATE_ISOLATION

| Mechanism | How Tested |
|-----------|-----------|
| Participant registry is Hall-side state. Agents never query it directly. | `test_hall_debate_context_injection` verifies agents only see compressed_log via VTP. |
| Agents receive hall context per-turn via `<HALL_CONTEXT>` tag injection (VTP extension). | `test_compressed_log_injection` verifies `<HALL_CONTEXT>` appears in prompt. |
| No agent-side persistence. Compressed_log is read-only context injection. | Architectural: agents call MCP tools (stateless). Hall manages all state. |
| Concurrent debate participants see same compressed_log (holographic). | `test_hall_debate_context_injection` verifies consistent injection. |
| **Tension T3 resolved:** Hall context is injected as read-only structured text. No side-channel between concurrent participants. Each debate's VTP includes the same frozen compressed_log from the point of debate spawn. |

### I2::UNIVERSAL_OCTAVE_BINDING

| Mechanism | How Tested |
|-----------|-----------|
| compressed_log is structured OCTAVE (`===HALL_CONTEXT===` / `===END===`). | `test_compressed_log_octave_format` validates OCTAVE markers. |
| All hall_* tools return structured dicts (JSON via MCP, OCTAVE via compressed_log). | Tool return type assertions in test_hall_tools.py. |

### I3::FINITE_DIALECTIC_CLOSURE

| Mechanism | How Tested |
|-----------|-----------|
| Each child debate independently enforces max_turns/max_rounds (existing engine.py). | Existing test_limits_enforcement.py covers per-debate I3. |
| Hall enforces max_debates (total cap, default 20). | `test_hall_debate_max_debates` verifies rejection at limit. |
| Hall enforces max_depth (nesting cap, default 3, I8). | `test_hall_debate_depth_limit` verifies rejection at depth. |
| **Tension T2 resolved:** Hall-level I3 closure guaranteed by max_debates and max_depth. Per-debate I3 remains unchanged. Total resource consumption bounded by max_debates * max_turns_per_debate. |

### I4::VERIFIABLE_EVENT_LEDGER

| Mechanism | How Tested |
|-----------|-----------|
| Hall events in separate append-only JSONL (`{hall_id}.events.jsonl`). | `test_save_hall_event_first` verifies event-first write. |
| ULID ordering for monotonic event IDs. | `test_load_hall_events_after_filter` verifies ULID ordering. |
| FileLock on `{hall_id}.lock` prevents concurrent corruption. | `test_append_hall_event_thread_safety`. |
| Snapshot derived from ledger (Hydrated Snapshot Pattern). | `test_load_hall_stale_snapshot` verifies read-repair. |
| Debate events remain in separate `{thread_id}.events.jsonl` (no contamination). | Architectural: hall and debate events use different file paths. |
| **Tension T1 resolved:** Hall events and debate events are isolated in separate JSONL files with separate locks. No cross-contamination of hash chains. |

### I5::SOVEREIGN_SAFETY_OVERRIDE

| Mechanism | How Tested |
|-----------|-----------|
| `hall_close(force=True)` cascades force_close to all active child debates. | `test_hall_close_force`. |
| HALL_FORCE_CLOSED event emitted for audit trail. | Event assertion in test_hall_close_force. |
| Existing `force_close_debate` tool still works for individual debates. | Existing test_admin_functions.py unchanged. |

### I6::PARTICIPANT_IDENTITY_REGISTRY

| Mechanism | How Tested |
|-----------|-----------|
| `hall_register` adds participant to Hall-managed registry. | `test_hall_register_basic`. |
| `prompt_source` validated at registration via `get_agent_prompt()`. | `test_hall_register_with_prompt_source`, `test_hall_register_bad_prompt_source`. |
| No anonymous/unregistered actors can participate in hall debates. | `test_hall_debate_unregistered_participant` verifies rejection. |
| Identity injected per-turn via prompt_source content + RACI instruction. | Architectural: orchestrator uses `_get_raci_prompt(turn_type, role_name)` existing pattern. |

### I7::HOLOGRAPHIC_CONTEXT_COMPRESSION

| Mechanism | How Tested |
|-----------|-----------|
| `generate_compressed_log` produces OCTAVE summary within max_context_tokens. | `test_generate_compressed_log_token_budget_within`. |
| FIFO eviction trims oldest decisions when budget exceeded. | `test_generate_compressed_log_fifo_eviction`. |
| Compressed log regenerated on each DEBATE_COMPLETED event. | Reducer test: `test_apply_hall_event_debate_completed`. |
| Injected into debate context via `<HALL_CONTEXT>` tag. | `test_compressed_log_injection`. |
| Custom token counter injectable for model-specific precision. | `test_generate_compressed_log_custom_token_counter`. |

### I8::RECURSIVE_TOPOLOGY_CLOSURE

| Mechanism | How Tested |
|-----------|-----------|
| `max_depth` enforced on spawn in `hall_debate`. | `test_hall_debate_depth_limit`. |
| `hall_close(force=False)` rejects if active debates exist. | `test_hall_close_active_debates_blocked`. |
| `parent_thread_id` on DebateRoom enables nesting tracking. | `test_nested_debate_topology` (integration). |
| Depth calculated by walking parent_thread_id chain. | Unit test for `_calculate_depth`. |
| Leaf-to-root pruning: children must close before parent. | `test_nested_debate_topology` verifies closure order. |

===

## S9::MIGRATION_AND_BACKWARD_COMPATIBILITY

### S9.1::DebateRoom Extension Migration

**Change:** Add two optional fields to DebateRoom with `None` defaults.

**Impact:** Zero. Pydantic's `BaseModel` assigns default values for missing fields during
deserialization. Existing JSON files without `parent_hall_id` and `parent_thread_id` will
load correctly with both fields as `None`.

**Verification:** `test_existing_state_deserialization` in golden tests loads a pre-existing
JSON state file and verifies `parent_hall_id is None` and `parent_thread_id is None`.

### S9.2::Orchestrator Extension Migration

**Change:** Add two optional keyword arguments to `DebateOrchestrator.__init__`.

**Impact:** Zero. Both parameters have default values (`None` and `{}`). All existing
code that creates `DebateOrchestrator` instances continues to work unchanged.

**Verification:** `test_existing_orchestrator_unchanged` and `test_existing_raci_mode_unchanged`
in golden tests verify identical behavior when new params are not provided.

### S9.3::Server Extension Migration

**Change:** Register 7 new MCP tools in `create_server()`.

**Impact:** Additive only. No existing tool signatures or behaviors change. MCP clients
that don't use the new tools are unaffected.

### S9.4::Directory Structure Migration

**Change:** New `{state_dir}/halls/` directory created on first `hall_open` call.

**Impact:** Zero. The directory is created lazily. Existing `{state_dir}/` structure
with `{thread_id}.json` files is completely unchanged.

===

## S10::EVIDENCE_GAPS_RESOLUTION

### G1::Replay Latency for 50+ Hall Events

**Resolution strategy:** Empirical benchmark during Phase 1.

**Measurement approach:**
1. Create a test that generates 50, 100, and 200 hall events
2. Measure `load_hall` time for:
   a. Full replay (no snapshot): cold start performance
   b. Delta replay (stale snapshot): incremental catch-up performance
   c. No replay (current snapshot): hot read performance
3. Target: full replay of 200 events < 200ms (per North Star quality criteria)

**Mitigation if target missed:**
- Increase snapshot flush frequency (currently every write; could batch)
- Add snapshot compaction (rewrite snapshot from all events periodically)
- These are performance optimizations, not design changes

**Implementation note:** Add `@pytest.mark.benchmark` markers on latency tests.
Include in Phase 1 PR for early visibility.

### G2::Token Budget Empirical Validation

**Resolved in S5.4 (Token Budget Math).** The analysis shows:
- 10 decisions + 2 active + 5 participants = 990 tokens (24% of budget)
- FIFO eviction kicks in only after ~40+ decisions
- Custom `token_counter` callable allows precise model-specific validation

**Additional Phase 1 validation:**
1. Generate compressed_log for test halls with 5, 10, 20, 40 decisions
2. Measure actual token count with tiktoken (GPT-4 tokenizer) as baseline
3. Verify heuristic (len/4) is within 20% of actual count
4. Record in test assertions for regression detection

### G3::Test Blast Radius from DebateRoom Extension

**Resolved by design.** The DebateRoom extension adds two `None`-default fields.
Pydantic assigns defaults for missing fields. Zero existing test breakage.

**Verification:** `test_existing_state_deserialization` golden test explicitly loads
old-format JSON and verifies the new fields are `None`. This catches any accidental
required-field changes.

**Quantified blast radius:** 0 tests affected. Both fields are `Optional[str]` with
`default=None`. No existing code reads these fields. No existing serialization changes.

===

## S11::IMPLEMENTATION_SEQUENCE

### Phase 1: Core Models and Event Infrastructure (TDD)

**Files to create:**
- `src/debate_hall_mcp/hall.py` (models, enums, reducer, persistence)
- `tests/unit/test_hall.py` (~28 tests)

**Files to modify:**
- `src/debate_hall_mcp/state.py` (add parent_hall_id, parent_thread_id to DebateRoom)
- `tests/golden/test_no_regression.py` (add state deserialization golden test)

**TDD sequence:**
1. RED: Write tests for HallState, Participant, HallEventType, HallEvent models
2. GREEN: Implement models with all validators
3. RED: Write tests for apply_hall_event reducer (all event types)
4. GREEN: Implement reducer
5. RED: Write tests for load_hall (smart loader with read-repair)
6. GREEN: Implement load_hall and persistence functions
7. RED: Write tests for save_hall (event-first write path)
8. GREEN: Implement save_hall
9. RED: Write G1 benchmark test (50+ events replay latency)
10. GREEN: Verify < 200ms target
11. REFACTOR: Clean up, add docstrings, run ruff+black+mypy

**Exit criteria:** All hall.py tests pass. G1 benchmark within target. mypy clean. ruff clean.

### Phase 2: Orchestrator Refactor (TDD)

**Files to modify:**
- `src/debate_hall_mcp/orchestrator.py` (add hall_context, participant_providers)
- `tests/golden/test_no_regression.py` (add orchestrator unchanged golden test)

**TDD sequence:**
1. RED: Write golden tests verifying existing orchestrator behavior unchanged
2. GREEN: Verify they pass (no code changes yet)
3. RED: Write test for hall_context injection in _execute_role_turn
4. GREEN: Add hall_context param and injection logic
5. RED: Write test for participant_providers in run_raci
6. GREEN: Add participant_providers param and lookup logic
7. REFACTOR: Verify all 864+ existing tests still pass

**Exit criteria:** All existing tests pass. New golden tests pass. mypy clean.

### Phase 3: Hall Tools - Lifecycle and Participant Management (TDD)

**Files to create:**
- `src/debate_hall_mcp/tools/hall.py` (hall_open, hall_status, hall_close, hall_register, hall_unregister)
- `tests/unit/tools/test_hall_tools.py` (lifecycle and participant tests, ~18 of ~28)

**Files to modify:**
- `src/debate_hall_mcp/server.py` (register 5 tools)

**TDD sequence:**
1. RED: Write tests for hall_open (happy path, validation, errors)
2. GREEN: Implement hall_open
3. RED: Write tests for hall_register and hall_unregister
4. GREEN: Implement registration tools
5. RED: Write tests for hall_status
6. GREEN: Implement hall_status
7. RED: Write tests for hall_close (including I8 enforcement, I5 force)
8. GREEN: Implement hall_close
9. Register 5 tools in server.py
10. REFACTOR: Run full test suite

**Exit criteria:** 5 hall tools operational. All tests pass.

### Phase 4: Compression Engine and Debate Integration (TDD)

**Files to create:**
- `src/debate_hall_mcp/compression.py` (generate_compressed_log, templates)
- `tests/unit/test_compression.py` (~14 tests)

**Files to modify:**
- `src/debate_hall_mcp/tools/hall.py` (add hall_debate, hall_consult)
- `src/debate_hall_mcp/server.py` (register 2 more tools)
- `tests/unit/tools/test_hall_tools.py` (add ~10 debate/consult tests)

**TDD sequence:**
1. RED: Write tests for generate_compressed_log (all scenarios)
2. GREEN: Implement compression engine
3. RED: Write G2 validation test (token count vs tiktoken baseline)
4. GREEN: Verify heuristic accuracy
5. RED: Write tests for hall_debate (RACI mode, depth limit, max_debates)
6. GREEN: Implement hall_debate (integrates orchestrator + compression)
7. RED: Write tests for hall_consult
8. GREEN: Implement hall_consult
9. Register 2 tools in server.py
10. REFACTOR: Run full test suite

**Exit criteria:** All 7 tools operational. Compression within budget. All tests pass.

### Phase 5: E2E Verification and Hardening (TDD)

**Files to create:**
- `tests/integration/test_hall_integration.py` (~7 tests)
- `tests/golden/test_no_regression.py` (remaining golden tests, ~7 total)

**TDD sequence:**
1. RED: Write full lifecycle integration test
2. GREEN: Verify end-to-end flow
3. RED: Write nested debate topology test (I8)
4. GREEN: Verify depth enforcement and leaf-to-root closure
5. RED: Write crash recovery test (corrupt JSON -> read-repair)
6. GREEN: Verify self-healing
7. RED: Write all remaining golden tests
8. GREEN: Verify zero regression
9. Run full test suite: all ~948+ tests
10. Run quality gates: ruff check, black check, mypy
11. REFACTOR: Final cleanup

**Exit criteria:** All ~948+ tests pass. Quality gates clean. G1, G2, G3 resolved with evidence.

===

## S12::IMPORTS_AND_DEPENDENCIES

### New Dependencies (None Required)

The implementation reuses all existing dependencies:
- `pydantic` (models, validators)
- `filelock` (FileLock for hall operations)
- `ulid-py` (ULID generation for event IDs)
- `fasteners` (not needed for hall; hall uses filelock directly)

No new pip packages required.

### Key Imports for hall.py

```python
import contextlib
import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from ulid import ULID

from debate_hall_mcp.config import RoleConfig
from debate_hall_mcp.state import (
    DebateRoom,
    _validate_thread_id_for_filesystem,
    load_debate_state,
)
```

### Key Imports for compression.py

```python
from collections.abc import Callable
from pathlib import Path

from debate_hall_mcp.decision import extract_decision_record
from debate_hall_mcp.hall import HallState
from debate_hall_mcp.state import load_debate_state
```

### Key Imports for tools/hall.py

```python
from typing import Any

from debate_hall_mcp.compression import generate_compressed_log
from debate_hall_mcp.config import RoleConfig, load_tier_config
from debate_hall_mcp.hall import (
    HallEventType,
    HallState,
    HallStatus,
    Participant,
    ParticipantKind,
    RaciMatrix,
    load_hall,
    save_hall,
)
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.prompts.loader import get_agent_prompt
from debate_hall_mcp.providers import create_provider
from debate_hall_mcp.state import get_state_dir
```

===

## S13::HALL_DEBATE_IMPLEMENTATION_DETAIL

This section provides the detailed implementation specification for `hall_debate`,
the most complex tool, to eliminate implementation ambiguity.

```python
async def _hall_debate_impl(
    hall_id: str,
    topic: str,
    mode: str,
    responsible: str | None,
    accountable: str | None,
    consulted: list[str] | None,
    informed: list[str] | None,
    parent_thread_id: str | None,
    thread_id: str | None,
) -> dict[str, Any]:
    """Implementation for hall_debate MCP tool.

    Sequence:
    1. Load hall state
    2. Validate hall status, participant registration, depth, debate count
    3. Build RACI config from participant IDs
    4. Emit RACI_ASSIGNED event
    5. Create participant-specific providers from registry
    6. Build orchestrator with hall_context and participant_providers
    7. Emit DEBATE_SPAWNED event
    8. Release hall lock
    9. Run debate via orchestrator (debate has its own lock)
    10. Re-acquire hall lock
    11. Generate updated compressed_log
    12. Emit DEBATE_COMPLETED event
    13. Return result
    """
    state_dir = get_state_dir()
    hall = load_hall(hall_id, state_dir)

    # Validate hall status
    if hall.status not in (HallStatus.OPEN, HallStatus.ACTIVE):
        raise ValueError(
            f"Cannot spawn debate in hall with status '{hall.status.value}': "
            "hall must be OPEN or ACTIVE"
        )

    # Validate debate count (I3 at hall level)
    total_debates = len(hall.active_debates) + len(hall.completed_debates)
    if total_debates >= hall.max_debates:
        raise ValueError(
            f"Hall has reached max_debates limit ({hall.max_debates}). "
            f"Current: {total_debates} debates."
        )

    # Validate depth (I8)
    depth = _calculate_depth(hall, parent_thread_id, state_dir)
    if depth >= hall.max_depth:
        raise ValueError(
            f"Nesting depth {depth} would exceed max_depth {hall.max_depth} (I8). "
            "Close existing sub-debates before spawning deeper ones."
        )

    # Validate all participants are registered
    consulted = consulted or []
    informed = informed or []
    all_participant_ids = []
    if mode == "raci":
        if not responsible or not accountable:
            raise ValueError("responsible and accountable required for RACI mode")
        all_participant_ids = [responsible, accountable] + consulted + informed
    for pid in all_participant_ids:
        if pid not in hall.participants:
            raise ValueError(f"Participant '{pid}' not registered in hall '{hall_id}'")

    # Build RACI config
    raci_config = None
    if mode == "raci":
        # Map participant IDs to names for RACIConfig (role names)
        raci_config = {
            "responsible": hall.participants[responsible].name,
            "accountable": hall.participants[accountable].name,
            "consulted": [hall.participants[pid].name for pid in consulted],
            "informed": [hall.participants[pid].name for pid in informed],
        }

    # Build RACI matrix for event
    raci_matrix_data = None
    if mode == "raci":
        raci_matrix_data = {
            "responsible": responsible,
            "accountable": accountable,
            "consulted": consulted,
            "informed": informed,
        }

    # Emit RACI_ASSIGNED event
    if raci_matrix_data:
        save_hall(
            hall,
            HallEventType.RACI_ASSIGNED,
            {"raci_matrix": raci_matrix_data},
            state_dir,
        )

    # Create participant-specific providers
    participant_providers = {}
    tier_config = load_tier_config(hall.tier_name)
    for pid in all_participant_ids:
        participant = hall.participants[pid]
        if participant.kind == ParticipantKind.AGENT:
            role_config = participant.provider_config or tier_config.wind
            participant_providers[participant.name] = create_provider(role_config)

    # Build context block from hall context_files
    context_block = None
    if hall.context_files:
        context_parts = []
        for fpath in hall.context_files:
            try:
                content = Path(fpath).read_text(encoding="utf-8")
                context_parts.append(f"<FILE path=\"{fpath}\">\n{content}\n</FILE>")
            except (FileNotFoundError, PermissionError):
                continue
        if context_parts:
            context_block = "\n\n".join(context_parts)

    # Generate thread_id if not provided
    if thread_id is None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        safe_topic = topic.lower().replace(" ", "-")
        safe_topic = "".join(c for c in safe_topic if c.isalnum() or c == "-")[:30]
        ulid_suffix = str(ULID())[:8].lower()
        thread_id = f"{today}-{safe_topic}-{ulid_suffix}"

    # Emit DEBATE_SPAWNED event
    save_hall(
        hall,
        HallEventType.DEBATE_SPAWNED,
        {
            "thread_id": thread_id,
            "topic": topic,
            "mode": mode,
            "parent_thread_id": parent_thread_id,
            "depth": depth,
            "participant_ids": all_participant_ids,
        },
        state_dir,
    )

    # Create orchestrator with hall context and participant providers
    orchestrator = DebateOrchestrator(
        tier_config=tier_config,
        state_dir=state_dir,
        hall_context=hall.compressed_log if hall.compressed_log else None,
        participant_providers=participant_providers if participant_providers else None,
        context_block=context_block,
    )

    # Run debate (orchestrator manages its own debate-level locks)
    try:
        if mode == "raci" and raci_config:
            result = await orchestrator.run_raci(
                topic=topic,
                raci_config=raci_config,
                thread_id=thread_id,
            )
        elif mode == "speed":
            result = await orchestrator.run_speed(
                topic=topic,
                thread_id=thread_id,
            )
        else:
            result = await orchestrator.run(
                topic=topic,
                thread_id=thread_id,
            )

        # Set parent_hall_id and parent_thread_id on the debate room
        room = load_debate_state(thread_id, state_dir)
        room.parent_hall_id = hall_id
        room.parent_thread_id = parent_thread_id
        from debate_hall_mcp.state import save_debate_state
        save_debate_state(room, state_dir)

    except Exception:
        # On failure, still emit DEBATE_COMPLETED with error status
        # Re-load hall state (may have been modified by other events)
        hall = load_hall(hall_id, state_dir)
        save_hall(
            hall,
            HallEventType.DEBATE_COMPLETED,
            {
                "thread_id": thread_id,
                "status": "paused",
                "synthesis_preview": "",
                "compressed_log": hall.compressed_log,
                "participant_ids": all_participant_ids,
            },
            state_dir,
        )
        raise

    # Generate updated compressed_log
    hall = load_hall(hall_id, state_dir)
    new_compressed_log = generate_compressed_log(hall, state_dir)

    # Emit DEBATE_COMPLETED event
    save_hall(
        hall,
        HallEventType.DEBATE_COMPLETED,
        {
            "thread_id": thread_id,
            "status": result.status,
            "synthesis_preview": (result.synthesis or "")[:100],
            "compressed_log": new_compressed_log,
            "participant_ids": all_participant_ids,
        },
        state_dir,
    )

    return {
        "hall_id": hall_id,
        "thread_id": thread_id,
        "topic": topic,
        "status": result.status,
        "turn_count": result.turn_count,
        "synthesis": result.synthesis,
        "mode": mode,
        "depth": depth,
        "parent_thread_id": parent_thread_id,
    }
```

===

## S14::ERROR_TAXONOMY

All custom exceptions for the hall module:

```python
# In src/debate_hall_mcp/hall.py
class HallNotFoundError(FileNotFoundError):
    """Raised when a hall does not exist."""
    def __init__(self, hall_id: str) -> None:
        super().__init__(f"Hall '{hall_id}' not found")
        self.hall_id = hall_id

class HallStatusError(ValueError):
    """Raised when hall is in wrong status for the requested operation."""
    def __init__(self, hall_id: str, current_status: str, required: list[str]) -> None:
        super().__init__(
            f"Hall '{hall_id}' has status '{current_status}'; "
            f"required: {required}"
        )
        self.hall_id = hall_id
        self.current_status = current_status
        self.required = required

class ParticipantNotFoundError(ValueError):
    """Raised when a participant is not registered in the hall."""
    def __init__(self, hall_id: str, participant_id: str) -> None:
        super().__init__(
            f"Participant '{participant_id}' not registered in hall '{hall_id}'"
        )
        self.hall_id = hall_id
        self.participant_id = participant_id

class ParticipantActiveError(ValueError):
    """Raised when trying to unregister an active participant."""
    def __init__(self, hall_id: str, participant_id: str) -> None:
        super().__init__(
            f"Participant '{participant_id}' is active in hall '{hall_id}': "
            "cannot unregister during active debate"
        )

class DepthLimitExceeded(ValueError):
    """Raised when sub-debate would exceed max_depth (I8)."""
    def __init__(self, hall_id: str, current_depth: int, max_depth: int) -> None:
        super().__init__(
            f"Nesting depth {current_depth} would exceed max_depth {max_depth} "
            f"in hall '{hall_id}' (I8: Recursive Topology Closure)"
        )

class DebateLimitExceeded(ValueError):
    """Raised when hall has reached max_debates (I3 at hall level)."""
    def __init__(self, hall_id: str, current: int, maximum: int) -> None:
        super().__init__(
            f"Hall '{hall_id}' has reached max_debates limit: "
            f"{current}/{maximum} (I3: Finite Dialectic Closure)"
        )

class ActiveDebatesExistError(ValueError):
    """Raised when trying to close hall with active debates (I8)."""
    def __init__(self, hall_id: str, active_debates: list[str]) -> None:
        super().__init__(
            f"Cannot close hall '{hall_id}': {len(active_debates)} active debate(s) "
            f"must close first (I8): {active_debates}"
        )

# In src/debate_hall_mcp/compression.py
class ContextBudgetExceeded(ValueError):
    """Raised when compressed log cannot fit within token budget (I7)."""
    pass
```

===

===END===
