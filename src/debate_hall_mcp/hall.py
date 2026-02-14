"""Hall module for Stateful RACI Hall feature (#163).

This module implements:
- HallStatus, ParticipantKind, HallEventType enums
- Participant, RaciMatrix, HallEvent, HallState Pydantic models
- Event reducer (apply_hall_event)
- Event ledger persistence (append_hall_event, load_hall_events)
- Smart Loader (load_hall) and write path (save_hall)
- Custom exception taxonomy (S14)

Governing Principle: "Ledger is Truth; File is Checkpoint"
Pattern: Hydrated Snapshot (CQRS variant)

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): Hall state managed exclusively by server
- I3 (FINITE_DIALECTIC_CLOSURE): max_debates, max_depth bounded
- I4 (VERIFIABLE_EVENT_LEDGER): Append-only JSONL event ledger
- I5 (SOVEREIGN_SAFETY_OVERRIDE): FORCE_CLOSED status + admin kill switch
- I6 (Participant Identity Registry): Participant model with unique IDs
- I7 (Context Compression): compressed_log with token budget
- I8 (Recursive Topology Closure): max_depth enforcement
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Literal

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from ulid import ULID

from debate_hall_mcp.config import RoleConfig

logger = logging.getLogger(__name__)

# ── S1.1: HallStatus Enum ────────────────────────────────────────────


class HallStatus(StrEnum):
    """Status of a Hall lifecycle.

    Transitions:
    - OPEN -> ACTIVE (first debate spawned via hall_debate)
    - ACTIVE -> REVIEWING (all active debates closed, no active debates remain)
    - REVIEWING -> ARCHIVED (hall_close called)
    - OPEN|ACTIVE -> ARCHIVED (hall_close with force=True, I5 enforcement)
    - ANY -> FORCE_CLOSED (admin kill switch)
    """

    OPEN = "open"
    ACTIVE = "active"
    REVIEWING = "reviewing"
    ARCHIVED = "archived"
    FORCE_CLOSED = "force_closed"


# ── S1.2: ParticipantKind Enum ────────────────────────────────────────


class ParticipantKind(StrEnum):
    """Kind of participant in the Hall."""

    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


# ── S1.5: HallEventType Enum ─────────────────────────────────────────


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


# ── S14: Error Taxonomy ──────────────────────────────────────────────


class HallNotFoundError(FileNotFoundError):
    """Raised when a hall does not exist."""

    def __init__(self, hall_id: str) -> None:
        super().__init__(f"Hall '{hall_id}' not found")
        self.hall_id = hall_id


class HallStatusError(ValueError):
    """Raised when hall is in wrong status for the requested operation."""

    def __init__(self, hall_id: str, current_status: str, required: list[str]) -> None:
        super().__init__(
            f"Hall '{hall_id}' has status '{current_status}'; " f"required: {required}"
        )
        self.hall_id = hall_id
        self.current_status = current_status
        self.required = required


class ParticipantNotFoundError(ValueError):
    """Raised when a participant is not registered in the hall."""

    def __init__(self, hall_id: str, participant_id: str) -> None:
        super().__init__(f"Participant '{participant_id}' not registered in hall '{hall_id}'")
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


# ── S1.3: Participant Model ──────────────────────────────────────────


class Participant(BaseModel):
    """A registered participant in the Hall (I6: Participant Identity Registry).

    The Hall maintains the single authoritative registry of all participants.
    No actor speaks without a registered identity.
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


# ── S1.4: RaciMatrix Model ───────────────────────────────────────────


class RaciMatrix(BaseModel):
    """RACI role assignment matrix for a hall-managed debate.

    Invariants:
    - Exactly one responsible
    - Exactly one accountable
    - responsible != accountable
    - All IDs must reference registered participants
    - consulted max 5, informed max 3
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
    def validate_raci_matrix(self) -> RaciMatrix:
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


# ── S1.6: HallEvent Model ────────────────────────────────────────────


class HallEvent(BaseModel):
    """A hall-level event with ULID-based monotonic ordering.

    Reuses the same patterns as DebateEvent (events.py):
    - ULID for monotonic ordering
    - UTC timestamp
    - Flexible payload dict
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
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


# ── S1.7: HallState Model ────────────────────────────────────────────


class HallState(BaseModel):
    """Persistent state of a Hall (Hydrated Snapshot Pattern).

    This is the CHECKPOINT, not the source of truth. The source of truth is
    the event ledger at {state_dir}/halls/{hall_id}.events.jsonl.

    The snapshot is materialized from events via apply_hall_event() reducer
    and cached at {state_dir}/halls/{hall_id}.json for fast reads.
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
        description="Shared codebase context file paths (validated for path safety)",
    )
    # H-001 AMENDMENT: Maximum file count and size limits for context_files
    MAX_CONTEXT_FILES: ClassVar[int] = 10
    MAX_CONTEXT_FILE_SIZE: ClassVar[int] = 65536  # 64KB per file

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
        """Validate hall_id is filesystem-safe (M-001)."""
        if not v or not v.strip():
            raise ValueError("hall_id must be non-empty")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                f"hall_id '{v}' contains invalid characters: "
                "only alphanumeric, hyphens, and underscores allowed"
            )
        return v

    @field_validator("context_files")
    @classmethod
    def validate_context_files(cls, v: list[str]) -> list[str]:
        """Validate context_files paths for safety (H-001 AMENDMENT).

        Security controls:
        1. Maximum file count (10) to prevent prompt injection volume
        2. All paths must be absolute (no relative paths)
        3. All paths must resolve without '..' traversal after resolution
        4. Paths must not point to sensitive directories
        """
        if len(v) > 10:
            raise ValueError(f"context_files exceeds maximum of 10 files: got {len(v)}")

        sensitive_prefixes = (
            "/etc/",
            "/root/",
            "/proc/",
            "/sys/",
            "/dev/",
        )
        sensitive_home_dirs = (
            ".ssh",
            ".gnupg",
            ".config/secrets",
            ".env",
            ".aws",
            ".docker",
            ".kube",
        )

        for fpath in v:
            # Must be absolute
            if not os.path.isabs(fpath):
                raise ValueError(f"context_files path must be absolute: '{fpath}'")

            # Resolve and check for traversal
            resolved = os.path.realpath(fpath)
            if ".." in fpath:
                raise ValueError(f"context_files path contains traversal: '{fpath}'")

            # Block sensitive directories (check both original and resolved
            # to handle symlinks like /etc -> /private/etc on macOS)
            for prefix in sensitive_prefixes:
                if fpath.startswith(prefix) or resolved.startswith(prefix):
                    raise ValueError(
                        f"context_files path '{fpath}' points to " f"restricted directory: {prefix}"
                    )

            # Block sensitive home subdirectories
            home_dir = os.path.expanduser("~")
            for sensitive_dir in sensitive_home_dirs:
                sensitive_path = os.path.join(home_dir, sensitive_dir)
                if resolved.startswith(sensitive_path):
                    raise ValueError(
                        f"context_files path '{fpath}' points to "
                        f"sensitive home directory: ~/{sensitive_dir}"
                    )

        return v


# ── S2.3: Event Reducer ──────────────────────────────────────────────


def apply_hall_event(state: HallState, event: HallEvent) -> HallState:
    """Pure reducer: state(N) + event -> state(N+1).

    Applies a single event to the hall state, returning the mutated state.
    This function is the ONLY way hall state changes. All MCP tools
    append events, then the reducer derives the new state.

    W-CE-3: Wraps model construction and dict access in try/except to
    handle malformed event data gracefully during replay.

    Args:
        state: Current hall state (will be mutated)
        event: Event to apply

    Returns:
        The mutated state (same object as input)
    """
    try:
        match event.event_type:
            case HallEventType.HALL_OPENED:
                state.status = HallStatus.OPEN

            case HallEventType.PARTICIPANT_REGISTERED:
                participant = Participant(**event.data)
                state.participants[participant.id] = participant

            case HallEventType.PARTICIPANT_UNREGISTERED:
                pid = event.data["participant_id"]
                state.participants.pop(pid, None)

            case HallEventType.RACI_ASSIGNED:
                state.raci_matrix = RaciMatrix(**event.data["raci_matrix"])
                # Reset all participant RACI designations first
                for _pid, participant in state.participants.items():
                    participant.raci_designation = None
                # Set new designations from matrix
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
                for pid in event.data.get("participant_ids", []):
                    if pid in state.participants:
                        state.participants[pid].status = "active"

            case HallEventType.DEBATE_COMPLETED:
                thread_id = event.data["thread_id"]
                if thread_id in state.active_debates:
                    state.active_debates.remove(thread_id)
                if thread_id not in state.completed_debates:
                    state.completed_debates.append(thread_id)
                if "compressed_log" in event.data:
                    state.compressed_log = event.data["compressed_log"]
                for pid in event.data.get("participant_ids", []):
                    if pid in state.participants:
                        state.participants[pid].status = "on_call"
                        state.participants[pid].raci_designation = None
                state.raci_matrix = None
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

    except (KeyError, TypeError, ValueError) as exc:
        # W-CE-3: Log warning and skip malformed event data
        logger.warning(
            "Skipping malformed hall event %s (type=%s): %s",
            event.event_id,
            event.event_type,
            exc,
        )

    # Always update version marker and timestamp
    state.last_event_id = event.event_id
    state.updated_at = event.timestamp
    return state


# ── S2.1/S2.2: Event Ledger Functions ────────────────────────────────


def _get_halls_dir(state_dir: Path) -> Path:
    """Get the halls subdirectory, creating if needed."""
    halls_dir = state_dir / "halls"
    halls_dir.mkdir(parents=True, exist_ok=True)
    return halls_dir


def _get_hall_lock(hall_id: str, state_dir: Path) -> FileLock:
    """Get FileLock for hall operations."""
    halls_dir = _get_halls_dir(state_dir)
    lock_file = halls_dir / f"{hall_id}.lock"
    return FileLock(str(lock_file))


def _get_hall_events_file(hall_id: str, state_dir: Path) -> Path:
    """Get path to hall event ledger JSONL file."""
    return _get_halls_dir(state_dir) / f"{hall_id}.events.jsonl"


def _get_hall_state_file(hall_id: str, state_dir: Path) -> Path:
    """Get path to hall snapshot JSON file."""
    return _get_halls_dir(state_dir) / f"{hall_id}.json"


def _validate_hall_id_for_filesystem(hall_id: str) -> None:
    """Validate hall_id is safe for filesystem operations (M-001)."""
    if not hall_id or not re.match(r"^[a-zA-Z0-9_-]+$", hall_id):
        raise ValueError(
            f"Invalid hall_id '{hall_id}': only alphanumeric, hyphens, " "and underscores allowed"
        )


def append_hall_event(
    hall_id: str,
    event_type: HallEventType,
    data: dict[str, Any],
    state_dir: Path,
) -> HallEvent:
    """Append an event to the hall's event ledger.

    Thread-safe via FileLock. W-CE-2: f.flush() + os.fsync() after write.

    Args:
        hall_id: Hall identifier
        event_type: Type of hall event
        data: Event-specific data
        state_dir: State directory

    Returns:
        The created HallEvent
    """
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

    with lock, open(events_file, "a") as f:
        f.write(event.model_dump_json() + "\n")
        # W-CE-2: Ensure data reaches disk
        f.flush()
        os.fsync(f.fileno())

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

    with lock, open(events_file) as f:
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


def _load_hall_events_unlocked(
    hall_id: str,
    state_dir: Path,
    after: str | None = None,
) -> list[HallEvent]:
    """Load hall events WITHOUT acquiring lock (caller holds lock)."""
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
