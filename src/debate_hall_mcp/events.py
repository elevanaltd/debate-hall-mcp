"""Event management for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements:
- EventType enum for debate lifecycle events
- DebateEvent model with ULID-based ordering
- Event persistence layer (append-only JSONL)

Event-Driven Architecture:
Events provide an append-only log of debate state transitions,
enabling async orchestration and replay capabilities.
"""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from ulid import ULID

from debate_hall_mcp.state import _validate_thread_id_for_filesystem


class EventType(str, Enum):
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


def generate_event_id() -> str:
    """Generate a new ULID for an event.

    Returns:
        26-character ULID string
    """
    return str(ULID())


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

    # Append to JSONL file
    events_file = state_dir / f"{thread_id}.events.jsonl"
    with open(events_file, "a") as f:
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
    with open(events_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = DebateEvent.model_validate_json(line)

            # Filter by 'after' if specified (ULID comparison is lexicographic)
            if after is not None and event.id <= after:
                continue

            events.append(event)

            # Apply limit
            if len(events) >= limit:
                break

    return events
