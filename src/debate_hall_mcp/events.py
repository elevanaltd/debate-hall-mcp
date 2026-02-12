"""Event management for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements:
- EventType enum for debate lifecycle events
- DebateEvent model with ULID-based ordering
- Event persistence layer (append-only JSONL)

Event-Driven Architecture:
Events provide an append-only log of debate state transitions,
enabling async orchestration and replay capabilities.

Concurrency Control:
Uses filelock for cross-platform file locking to prevent
concurrent write corruption (Issue #111 - CE Review).

ULID Ordering Limitation:
Event IDs use standard ULID() generation which provides millisecond
precision timestamps. Under high-frequency concurrent writes within
the same millisecond, lexicographic ordering may not reflect exact
write order. For typical debate orchestration (seconds between turns),
this is not a practical concern. If strict total ordering is required,
use the event file line position as a secondary sort key.
"""

import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError, field_validator
from ulid import ULID

from debate_hall_mcp.state import _validate_thread_id_for_filesystem

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    """Types of debate events for auto-orchestration (ADR-0002).

    Event lifecycle:
    - DEBATE_STARTED: Debate initialized with topic and config
    - TURN_ADDED: New turn added by Wind/Wall/Door
    - CONSENSUS_VOTE: Agent voted on consensus
    - ERROR: Error occurred during processing
    - DEBATE_CLOSED: Debate concluded (synthesis, exhaustion, etc.)
    """

    DEBATE_STARTED = "debate_started"
    TURN_ADDED = "turn_added"
    CONSENSUS_VOTE = "consensus_vote"
    ERROR = "error"
    DEBATE_CLOSED = "debate_closed"


class DebateEvent(BaseModel):
    """A debate event with ULID-based monotonic ordering.

    ULIDs provide:
    - Monotonic ordering (lexicographically sortable)
    - Timestamp embedded in ID (first 48 bits)
    - Collision resistance (80 bits of randomness)

    Fields:
    - id: ULID string (26 chars, Crockford Base32)
    - thread_id: Debate thread this event belongs to
    - event_type: Type of event (from EventType enum)
    - timestamp: When the event occurred (UTC)
    - payload: Event-specific data (flexible dict)
    """

    id: str = Field(..., description="ULID for monotonic ordering")
    thread_id: str = Field(..., description="Debate thread identifier")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="UTC timestamp of event")
    payload: dict[str, Any] = Field(..., description="Event-specific data")

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if isinstance(v, str):
            # Parse ISO format string
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=UTC)
        return v


# Maximum excerpt length for turn_added event payloads (Issue #147)
TURN_EXCERPT_MAX_LENGTH = 200


def build_turn_added_payload(
    role: str,
    model: str | None,
    content: str,
    content_hash: str,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build enriched payload for TURN_ADDED events (Issue #147).

    Enriches the audit log with turn content metadata without storing
    full content (for size reasons). The content_hash links the event
    to the full turn in the state file for forensic correlation.

    Args:
        role: Agent role (Wind, Wall, Door)
        model: AI model identifier (may be None)
        content: Full turn content (used to compute excerpt and length)
        content_hash: SHA-256 hash of the turn (from Turn model)
        tokens_in: Optional input token count
        tokens_out: Optional output token count
        **extra: Additional payload fields (e.g., mode for Speed)

    Returns:
        Dictionary suitable for use as append_event payload
    """
    # 1. Build base payload with identity fields
    payload: dict[str, Any] = {
        "role": role,
        "model": model,
    }

    # 2. Merge extra fields first (e.g., mode="speed")
    payload.update(extra)

    # 3. Set forensic fields AFTER extra merge to prevent override.
    # These are computed server-side and must never be caller-controlled.
    payload["content_length"] = len(content)
    payload["excerpt"] = content[:TURN_EXCERPT_MAX_LENGTH]
    payload["content_hash"] = content_hash

    # Include token counts when available (gracefully handle None)
    # Set after extra merge to prevent override of server-computed values.
    if tokens_in is not None:
        payload["tokens_in"] = tokens_in
    if tokens_out is not None:
        payload["tokens_out"] = tokens_out

    return payload


def generate_event_id() -> str:
    """Generate a new ULID for an event.

    Returns:
        26-character ULID string
    """
    return str(ULID())


def _get_event_file_lock(event_file: Path) -> FileLock:
    """Get a cross-platform file lock for event file operations.

    Uses filelock library for cross-platform file locking (Issue #111).
    Works on POSIX (Linux, macOS) and Windows.

    Args:
        event_file: Path to the event JSONL file

    Returns:
        FileLock instance that can be used as context manager

    Note:
        Uses exclusive locks. For our use case this is appropriate
        since both reads and writes need consistency and contention
        is expected to be low.
    """
    lock_file = event_file.with_suffix(".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_file))


def append_event(
    thread_id: str,
    event_type: EventType,
    payload: dict[str, Any],
    state_dir: Path,
) -> DebateEvent:
    """Append an event to the thread's event log.

    Creates a new DebateEvent with auto-generated ULID and current timestamp,
    then appends it to the JSONL file for the thread.

    Args:
        thread_id: Debate thread identifier
        event_type: Type of event
        payload: Event-specific data
        state_dir: Directory for event storage

    Returns:
        The created DebateEvent

    Raises:
        ValueError: If thread_id contains path-unsafe characters
    """
    # Security: Validate thread_id before using in file path
    _validate_thread_id_for_filesystem(thread_id)

    # Create event with current timestamp and generated ULID
    event = DebateEvent(
        id=generate_event_id(),
        thread_id=thread_id,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        payload=payload,
    )

    # Ensure state directory exists
    state_dir.mkdir(parents=True, exist_ok=True)

    # Append to JSONL file with file locking for concurrency safety (Issue #111)
    events_file = state_dir / f"{thread_id}.events.jsonl"
    with _get_event_file_lock(events_file), open(events_file, "a") as f:
        f.write(event.model_dump_json() + "\n")

    return event


def load_events(
    thread_id: str,
    state_dir: Path,
    after: str | None = None,
    limit: int = 50,
) -> list[DebateEvent]:
    """Load events from the thread's event log.

    Reads events from the JSONL file, optionally filtering by ULID
    and limiting the number of results.

    Args:
        thread_id: Debate thread identifier
        state_dir: Directory for event storage
        after: Only return events with ID greater than this ULID
        limit: Maximum number of events to return (default 50)

    Returns:
        List of DebateEvent objects, ordered by ULID

    Raises:
        ValueError: If thread_id contains path-unsafe characters
        FileNotFoundError: If events file doesn't exist
    """
    # Security: Validate thread_id before using in file path
    _validate_thread_id_for_filesystem(thread_id)

    events_file = state_dir / f"{thread_id}.events.jsonl"
    if not events_file.exists():
        raise FileNotFoundError(f"No events file found for thread {thread_id}")

    events: list[DebateEvent] = []

    # Use file locking for read consistency (Issue #111 - CE Review)
    with _get_event_file_lock(events_file), open(events_file) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            # Graceful handling of corrupt lines (Issue #111 - CE Review)
            # Risk: Torn write during crash can corrupt a line
            # Fix: Skip corrupt lines with warning, don't crash
            try:
                event = DebateEvent.model_validate_json(line)
            except ValidationError as e:
                logger.warning(
                    "Skipping corrupt event line %d in %s: %s",
                    line_num,
                    events_file.name,
                    str(e),
                )
                continue

            # Filter by 'after' if specified (ULID comparison is lexicographic)
            if after is not None and event.id <= after:
                continue

            events.append(event)

            # Apply limit
            if len(events) >= limit:
                break

    return events
