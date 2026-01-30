"""Unit tests for debate_hall_mcp.events module.

Tests cover (ADR-0002 Foundation):
- EventType enum values
- DebateEvent model with ULID, timestamp, payload
- Event validation
- Event persistence (append/load) with JSONL storage
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


class TestEventType:
    """Test EventType enum for debate events."""

    def test_debate_started_event_type(self) -> None:
        """Verify DEBATE_STARTED event type exists."""
        from debate_hall_mcp.events import EventType

        assert EventType.DEBATE_STARTED.value == "debate_started"

    def test_turn_added_event_type(self) -> None:
        """Verify TURN_ADDED event type exists."""
        from debate_hall_mcp.events import EventType

        assert EventType.TURN_ADDED.value == "turn_added"

    def test_consensus_vote_event_type(self) -> None:
        """Verify CONSENSUS_VOTE event type exists."""
        from debate_hall_mcp.events import EventType

        assert EventType.CONSENSUS_VOTE.value == "consensus_vote"

    def test_error_event_type(self) -> None:
        """Verify ERROR event type exists."""
        from debate_hall_mcp.events import EventType

        assert EventType.ERROR.value == "error"

    def test_debate_closed_event_type(self) -> None:
        """Verify DEBATE_CLOSED event type exists."""
        from debate_hall_mcp.events import EventType

        assert EventType.DEBATE_CLOSED.value == "debate_closed"


class TestDebateEvent:
    """Test DebateEvent model for event representation."""

    def test_event_creation_with_required_fields(self) -> None:
        """Create DebateEvent with all required fields."""
        from debate_hall_mcp.events import DebateEvent, EventType

        event = DebateEvent(
            id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Example ULID
            thread_id="test-thread-001",
            event_type=EventType.DEBATE_STARTED,
            timestamp=datetime.now(UTC),
            payload={"topic": "Test Topic"},
        )
        assert event.id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert event.thread_id == "test-thread-001"
        assert event.event_type == EventType.DEBATE_STARTED
        assert event.payload == {"topic": "Test Topic"}

    def test_event_id_is_ulid_format(self) -> None:
        """Event ID must be a valid ULID (26 chars, Crockford Base32)."""
        from debate_hall_mcp.events import DebateEvent, EventType
        from ulid import ULID

        # Generate a proper ULID
        ulid_str = str(ULID())
        event = DebateEvent(
            id=ulid_str,
            thread_id="test-thread",
            event_type=EventType.TURN_ADDED,
            timestamp=datetime.now(UTC),
            payload={},
        )
        assert len(event.id) == 26  # ULID is always 26 chars

    def test_event_requires_thread_id(self) -> None:
        """DebateEvent requires thread_id."""
        from pydantic import ValidationError

        from debate_hall_mcp.events import DebateEvent, EventType

        with pytest.raises(ValidationError, match="thread_id"):
            DebateEvent(
                id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type=EventType.DEBATE_STARTED,
                timestamp=datetime.now(UTC),
                payload={},
            )

    def test_event_requires_event_type(self) -> None:
        """DebateEvent requires event_type."""
        from pydantic import ValidationError

        from debate_hall_mcp.events import DebateEvent

        with pytest.raises(ValidationError, match="event_type"):
            DebateEvent(
                id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                thread_id="test-thread",
                timestamp=datetime.now(UTC),
                payload={},
            )

    def test_event_requires_payload(self) -> None:
        """DebateEvent requires payload dict."""
        from pydantic import ValidationError

        from debate_hall_mcp.events import DebateEvent, EventType

        with pytest.raises(ValidationError, match="payload"):
            DebateEvent(
                id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                thread_id="test-thread",
                event_type=EventType.DEBATE_STARTED,
                timestamp=datetime.now(UTC),
            )

    def test_event_timestamp_is_utc(self) -> None:
        """Event timestamp is timezone-aware (UTC)."""
        from debate_hall_mcp.events import DebateEvent, EventType

        timestamp = datetime.now(UTC)
        event = DebateEvent(
            id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            thread_id="test-thread",
            event_type=EventType.ERROR,
            timestamp=timestamp,
            payload={"error": "test"},
        )
        assert event.timestamp.tzinfo is not None

    def test_event_serialization_to_json(self) -> None:
        """DebateEvent serializes to JSON correctly."""
        from debate_hall_mcp.events import DebateEvent, EventType

        event = DebateEvent(
            id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            thread_id="test-thread",
            event_type=EventType.CONSENSUS_VOTE,
            timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            payload={"vote": "agree", "role": "Wind"},
        )
        json_str = event.model_dump_json()
        assert "01ARZ3NDEKTSV4RRFFQ69G5FAV" in json_str
        assert "consensus_vote" in json_str
        assert "test-thread" in json_str

    def test_event_deserialization_from_json(self) -> None:
        """DebateEvent deserializes from JSON correctly."""
        import json

        from debate_hall_mcp.events import DebateEvent, EventType

        event = DebateEvent(
            id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            thread_id="test-thread",
            event_type=EventType.DEBATE_CLOSED,
            timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            payload={"synthesis": "resolved"},
        )
        json_str = event.model_dump_json()
        loaded = DebateEvent.model_validate(json.loads(json_str))
        assert loaded.id == event.id
        assert loaded.event_type == EventType.DEBATE_CLOSED
        assert loaded.payload == {"synthesis": "resolved"}


class TestEventPersistence:
    """Test event persistence layer (append/load) with JSONL storage."""

    def test_append_event_creates_file(self, tmp_path: Path) -> None:
        """append_event creates JSONL file if it doesn't exist."""
        from debate_hall_mcp.events import EventType, append_event

        state_dir = tmp_path / "events"
        event = append_event(
            thread_id="persist-001",
            event_type=EventType.DEBATE_STARTED,
            payload={"topic": "Test"},
            state_dir=state_dir,
        )

        events_file = state_dir / "persist-001.events.jsonl"
        assert events_file.exists()
        assert event.thread_id == "persist-001"
        assert event.event_type == EventType.DEBATE_STARTED

    def test_append_event_returns_event_with_ulid(self, tmp_path: Path) -> None:
        """append_event returns DebateEvent with generated ULID."""
        from debate_hall_mcp.events import EventType, append_event

        state_dir = tmp_path / "events"
        event = append_event(
            thread_id="ulid-001",
            event_type=EventType.TURN_ADDED,
            payload={"role": "Wind", "content": "test"},
            state_dir=state_dir,
        )

        assert len(event.id) == 26  # ULID is 26 chars
        assert event.timestamp.tzinfo is not None

    def test_append_event_appends_to_existing_file(self, tmp_path: Path) -> None:
        """append_event appends to existing JSONL file (append-only)."""
        from debate_hall_mcp.events import EventType, append_event

        state_dir = tmp_path / "events"

        # Append first event
        event1 = append_event(
            thread_id="append-001",
            event_type=EventType.DEBATE_STARTED,
            payload={"topic": "Test"},
            state_dir=state_dir,
        )

        # Append second event
        event2 = append_event(
            thread_id="append-001",
            event_type=EventType.TURN_ADDED,
            payload={"role": "Wind"},
            state_dir=state_dir,
        )

        # Verify file has two lines
        events_file = state_dir / "append-001.events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 2

        # Verify events are in order
        first_event = json.loads(lines[0])
        second_event = json.loads(lines[1])
        assert first_event["id"] == event1.id
        assert second_event["id"] == event2.id

    def test_append_event_rejects_path_traversal(self, tmp_path: Path) -> None:
        """append_event rejects thread_id with path traversal."""
        from debate_hall_mcp.events import EventType, append_event

        state_dir = tmp_path / "events"

        with pytest.raises(ValueError, match="Invalid thread_id"):
            append_event(
                thread_id="../sensitive",
                event_type=EventType.DEBATE_STARTED,
                payload={},
                state_dir=state_dir,
            )

    def test_load_events_returns_all_events(self, tmp_path: Path) -> None:
        """load_events returns all events from JSONL file."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Create 3 events
        append_event("load-001", EventType.DEBATE_STARTED, {"topic": "Test"}, state_dir)
        append_event("load-001", EventType.TURN_ADDED, {"role": "Wind"}, state_dir)
        append_event("load-001", EventType.TURN_ADDED, {"role": "Wall"}, state_dir)

        # Load events
        events = load_events("load-001", state_dir)
        assert len(events) == 3
        assert events[0].event_type == EventType.DEBATE_STARTED
        assert events[1].event_type == EventType.TURN_ADDED
        assert events[2].event_type == EventType.TURN_ADDED

    def test_load_events_with_after_filter(self, tmp_path: Path) -> None:
        """load_events filters events after specified ULID."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Create 3 events
        event1 = append_event("filter-001", EventType.DEBATE_STARTED, {}, state_dir)
        event2 = append_event("filter-001", EventType.TURN_ADDED, {}, state_dir)
        event3 = append_event("filter-001", EventType.TURN_ADDED, {}, state_dir)

        # Load events after first event
        events = load_events("filter-001", state_dir, after=event1.id)
        assert len(events) == 2
        assert events[0].id == event2.id
        assert events[1].id == event3.id

    def test_load_events_with_limit(self, tmp_path: Path) -> None:
        """load_events respects limit parameter."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Create 5 events
        for i in range(5):
            append_event("limit-001", EventType.TURN_ADDED, {"turn": i}, state_dir)

        # Load with limit
        events = load_events("limit-001", state_dir, limit=2)
        assert len(events) == 2

    def test_load_events_file_not_found(self, tmp_path: Path) -> None:
        """load_events raises FileNotFoundError for missing file."""
        from debate_hall_mcp.events import load_events

        state_dir = tmp_path / "events"
        state_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="No events file found"):
            load_events("nonexistent", state_dir)

    def test_load_events_rejects_path_traversal(self, tmp_path: Path) -> None:
        """load_events rejects thread_id with path traversal."""
        from debate_hall_mcp.events import load_events

        state_dir = tmp_path / "events"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="Invalid thread_id"):
            load_events("../sensitive", state_dir)

    def test_append_load_cycle_preserves_data(self, tmp_path: Path) -> None:
        """Full append/load cycle preserves all event data."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Create event with complex payload
        original = append_event(
            thread_id="cycle-001",
            event_type=EventType.CONSENSUS_VOTE,
            payload={
                "role": "Door",
                "vote": "agree",
                "reasoning": "Tests pass",
                "nested": {"key": "value"},
            },
            state_dir=state_dir,
        )

        # Load and verify
        events = load_events("cycle-001", state_dir)
        assert len(events) == 1
        loaded = events[0]

        assert loaded.id == original.id
        assert loaded.thread_id == original.thread_id
        assert loaded.event_type == original.event_type
        assert loaded.payload == original.payload
        assert loaded.timestamp == original.timestamp

    def test_events_are_ulid_ordered(self, tmp_path: Path) -> None:
        """Events are ordered by ULID (lexicographically sortable)."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Create events
        events_created = []
        for i in range(3):
            event = append_event("order-001", EventType.TURN_ADDED, {"i": i}, state_dir)
            events_created.append(event)

        # Load and verify order
        events = load_events("order-001", state_dir)
        assert len(events) == 3

        # ULIDs should be monotonically increasing
        for i in range(len(events) - 1):
            assert events[i].id < events[i + 1].id
