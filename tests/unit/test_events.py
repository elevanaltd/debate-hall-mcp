"""Unit tests for debate_hall_mcp.events module.

Tests cover (ADR-0002 Foundation):
- EventType enum values
- DebateEvent model with ULID, timestamp, payload
- Event validation
- Event persistence (append/load) with JSONL storage
- Enriched turn_added payloads (Issue #147)
"""

import json
import time
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
        from ulid import ULID

        from debate_hall_mcp.events import DebateEvent, EventType

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

        # Create 3 events with small delays to ensure distinct ULID timestamps
        # across Python versions (ULID monotonicity not guaranteed within same ms)
        event1 = append_event("filter-001", EventType.DEBATE_STARTED, {}, state_dir)
        time.sleep(0.002)
        event2 = append_event("filter-001", EventType.TURN_ADDED, {}, state_dir)
        time.sleep(0.002)
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


class TestEventConcurrency:
    """Test concurrency safety for event persistence (CE review fixes)."""

    def test_concurrent_append_does_not_corrupt_file(self, tmp_path: Path) -> None:
        """Concurrent appends should not corrupt the JSONL file.

        CE Review Issue #1: Event persistence has no locking.
        Risk: Concurrent writers can interleave/corrupt JSONL lines.
        Fix: Add file locking using filelock.
        """
        import concurrent.futures
        import threading

        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"
        thread_id = "concurrent-001"
        num_writers = 10
        events_per_writer = 20
        barrier = threading.Barrier(num_writers)

        def write_events(writer_id: int) -> list[str]:
            """Write events and return list of event IDs."""
            barrier.wait()  # Synchronize start
            event_ids = []
            for i in range(events_per_writer):
                event = append_event(
                    thread_id=thread_id,
                    event_type=EventType.TURN_ADDED,
                    payload={"writer": writer_id, "seq": i},
                    state_dir=state_dir,
                )
                event_ids.append(event.id)
            return event_ids

        # Run concurrent writers
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers) as executor:
            futures = [executor.submit(write_events, i) for i in range(num_writers)]
            all_written_ids = []
            for future in concurrent.futures.as_completed(futures):
                all_written_ids.extend(future.result())

        # Verify all events are readable (no corruption)
        events = load_events(thread_id, state_dir, limit=1000)

        # All events must be present and valid
        assert len(events) == num_writers * events_per_writer
        loaded_ids = {e.id for e in events}
        assert loaded_ids == set(all_written_ids)

    def test_append_uses_file_lock(self, tmp_path: Path) -> None:
        """Verify append_event uses file locking for thread safety.

        CE Review Issue #1: append_event should use FileLock.
        """
        from unittest.mock import MagicMock, patch

        from debate_hall_mcp.events import EventType, append_event

        state_dir = tmp_path / "events"

        # Mock FileLock to verify it's called
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=None)

        with patch("debate_hall_mcp.events.FileLock", return_value=mock_lock) as mock_cls:
            append_event(
                thread_id="lock-test-001",
                event_type=EventType.DEBATE_STARTED,
                payload={},
                state_dir=state_dir,
            )

            # FileLock should be instantiated with a lock file path
            mock_cls.assert_called_once()
            lock_path = mock_cls.call_args[0][0]
            assert "lock-test-001" in lock_path
            assert ".lock" in lock_path or "lock" in lock_path.lower()

            # Lock context manager should be used
            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()


class TestEventCorruptionRecovery:
    """Test graceful handling of corrupt event lines (CE review fixes)."""

    def test_load_events_skips_corrupt_lines(self, tmp_path: Path) -> None:
        """load_events should skip corrupt lines gracefully.

        CE Review Issue #2: No recovery for partial/corrupt lines.
        Risk: Torn write during crash will break all future loads.
        Fix: Skip corrupt lines with warning, don't crash.
        """
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"
        thread_id = "corrupt-001"

        # Create valid event
        event1 = append_event(thread_id, EventType.DEBATE_STARTED, {"n": 1}, state_dir)

        # Manually inject corrupt lines (simulating torn write)
        events_file = state_dir / f"{thread_id}.events.jsonl"
        with open(events_file, "a") as f:
            f.write('{"id": "broken", "invalid": json\n')  # Corrupt JSON
            f.write("just a partial line\n")  # Another corrupt line

        # Add another valid event
        event3 = append_event(thread_id, EventType.TURN_ADDED, {"n": 3}, state_dir)

        # load_events should recover valid events, skip corrupt ones
        events = load_events(thread_id, state_dir, limit=100)

        # Should have both valid events, corrupt lines skipped
        assert len(events) == 2
        assert events[0].id == event1.id
        assert events[1].id == event3.id

    def test_load_events_handles_empty_lines(self, tmp_path: Path) -> None:
        """load_events handles empty lines gracefully."""
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"
        thread_id = "empty-lines-001"

        # Create valid event
        event1 = append_event(thread_id, EventType.DEBATE_STARTED, {}, state_dir)

        # Inject empty lines
        events_file = state_dir / f"{thread_id}.events.jsonl"
        with open(events_file, "a") as f:
            f.write("\n\n\n")  # Multiple empty lines

        # Add another valid event
        event2 = append_event(thread_id, EventType.TURN_ADDED, {}, state_dir)

        # Should handle empty lines without error
        events = load_events(thread_id, state_dir, limit=100)
        assert len(events) == 2
        assert events[0].id == event1.id
        assert events[1].id == event2.id

    def test_load_events_logs_warning_for_corrupt_lines(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load_events should log warning when skipping corrupt lines."""
        import logging

        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"
        thread_id = "warn-001"

        # Create valid event
        append_event(thread_id, EventType.DEBATE_STARTED, {}, state_dir)

        # Inject corrupt line
        events_file = state_dir / f"{thread_id}.events.jsonl"
        with open(events_file, "a") as f:
            f.write("this is not valid json\n")

        # Load with logging capture
        with caplog.at_level(logging.WARNING):
            load_events(thread_id, state_dir)

        # Should have logged a warning about the corrupt line
        assert any(
            "corrupt" in record.message.lower() or "skip" in record.message.lower()
            for record in caplog.records
        )

    def test_load_events_uses_file_lock(self, tmp_path: Path) -> None:
        """Verify load_events uses file locking for read consistency.

        CE Review: Use lock for consistent reads.
        """
        from unittest.mock import MagicMock, patch

        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"
        thread_id = "read-lock-001"

        # First create an event file
        append_event(thread_id, EventType.DEBATE_STARTED, {}, state_dir)

        # Now patch FileLock and verify load_events uses it
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=None)

        with patch("debate_hall_mcp.events.FileLock", return_value=mock_lock) as mock_cls:
            load_events(thread_id, state_dir)

            # FileLock should be instantiated
            assert mock_cls.called
            lock_path = mock_cls.call_args[0][0]
            assert thread_id in lock_path

            # Lock context manager should be used
            mock_lock.__enter__.assert_called()
            mock_lock.__exit__.assert_called()


class TestBuildTurnAddedPayload:
    """Test enriched turn_added payload construction (Issue #147).

    Verifies that build_turn_added_payload produces correct metadata
    for audit log enrichment including content_length, excerpt,
    content_hash, and optional token counts.
    """

    def test_payload_contains_required_fields(self) -> None:
        """Enriched payload must contain content_length, excerpt, content_hash."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content="This is a test turn content",
            content_hash="abc123def456",
        )

        assert payload["role"] == "Wind"
        assert payload["model"] == "claude-opus-4-5"
        assert payload["content_length"] == len("This is a test turn content")
        assert payload["excerpt"] == "This is a test turn content"
        assert payload["content_hash"] == "abc123def456"

    def test_excerpt_truncated_to_200_chars(self) -> None:
        """Excerpt is properly truncated to 200 characters."""
        from debate_hall_mcp.events import TURN_EXCERPT_MAX_LENGTH, build_turn_added_payload

        long_content = "A" * 500
        payload = build_turn_added_payload(
            role="Wall",
            model="gpt-4o",
            content=long_content,
            content_hash="hash123",
        )

        assert TURN_EXCERPT_MAX_LENGTH == 200
        assert len(payload["excerpt"]) == 200
        assert payload["excerpt"] == "A" * 200
        assert payload["content_length"] == 500

    def test_excerpt_short_content_not_padded(self) -> None:
        """Short content is kept as-is (not padded to 200)."""
        from debate_hall_mcp.events import build_turn_added_payload

        short_content = "Brief turn"
        payload = build_turn_added_payload(
            role="Door",
            model="gemini-2.0",
            content=short_content,
            content_hash="hash456",
        )

        assert payload["excerpt"] == "Brief turn"
        assert payload["content_length"] == len("Brief turn")

    def test_tokens_in_included_when_available(self) -> None:
        """tokens_in is included in payload when provided."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content="Test content",
            content_hash="hash789",
            tokens_in=1500,
        )

        assert payload["tokens_in"] == 1500

    def test_tokens_out_included_when_available(self) -> None:
        """tokens_out is included in payload when provided."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wall",
            model="gpt-4o",
            content="Test content",
            content_hash="hash101",
            tokens_out=800,
        )

        assert payload["tokens_out"] == 800

    def test_tokens_both_included_when_available(self) -> None:
        """Both tokens_in and tokens_out are included when provided."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Door",
            model="gemini-2.0",
            content="Test content",
            content_hash="hash202",
            tokens_in=2000,
            tokens_out=1000,
        )

        assert payload["tokens_in"] == 2000
        assert payload["tokens_out"] == 1000

    def test_tokens_in_gracefully_handles_none(self) -> None:
        """tokens_in is omitted from payload when None."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content="Test content",
            content_hash="hash303",
            tokens_in=None,
        )

        assert "tokens_in" not in payload

    def test_tokens_out_gracefully_handles_none(self) -> None:
        """tokens_out is omitted from payload when None."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wall",
            model="gpt-4o",
            content="Test content",
            content_hash="hash404",
            tokens_out=None,
        )

        assert "tokens_out" not in payload

    def test_tokens_both_none_omitted(self) -> None:
        """Both token fields omitted when None (default behavior)."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Door",
            model="gemini-2.0",
            content="Test content",
            content_hash="hash505",
        )

        assert "tokens_in" not in payload
        assert "tokens_out" not in payload

    def test_extra_kwargs_merged_into_payload(self) -> None:
        """Extra keyword arguments (e.g., mode) are merged into payload."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content="Test content",
            content_hash="hash606",
            mode="raci",
        )

        assert payload["mode"] == "raci"
        # Standard fields still present
        assert payload["role"] == "Wind"
        assert payload["content_hash"] == "hash606"

    def test_model_none_is_preserved(self) -> None:
        """Model can be None (preserved in payload)."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model=None,
            content="Test content",
            content_hash="hash707",
        )

        assert payload["model"] is None

    def test_empty_content_produces_zero_length(self) -> None:
        """Empty content produces content_length=0 and empty excerpt."""
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Door",
            model="test-model",
            content="",
            content_hash="hash808",
        )

        assert payload["content_length"] == 0
        assert payload["excerpt"] == ""

    def test_payload_persists_through_append_load_cycle(self, tmp_path: Path) -> None:
        """Enriched payload survives append/load cycle via JSONL."""
        from debate_hall_mcp.events import (
            EventType,
            append_event,
            build_turn_added_payload,
            load_events,
        )

        state_dir = tmp_path / "events"
        content = "A" * 300

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content=content,
            content_hash="persist-hash-123",
            tokens_in=1500,
            tokens_out=800,
        )

        append_event(
            thread_id="enrich-persist-001",
            event_type=EventType.TURN_ADDED,
            payload=payload,
            state_dir=state_dir,
        )

        events = load_events("enrich-persist-001", state_dir)
        assert len(events) == 1
        loaded_payload = events[0].payload

        assert loaded_payload["role"] == "Wind"
        assert loaded_payload["model"] == "claude-opus-4-5"
        assert loaded_payload["content_length"] == 300
        assert loaded_payload["excerpt"] == "A" * 200  # Truncated
        assert loaded_payload["content_hash"] == "persist-hash-123"
        assert loaded_payload["tokens_in"] == 1500
        assert loaded_payload["tokens_out"] == 800

    def test_extra_kwargs_cannot_override_forensic_fields(self) -> None:
        """Extra kwargs must NOT override forensic fields (CE advisory).

        Forensic fields (content_hash, content_length, excerpt, role) are
        computed server-side. A malicious or buggy caller passing colliding
        keys in **extra must not be able to override them.
        """
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wind",
            model="claude-opus-4-5",
            content="Authentic content",
            content_hash="real_hash_abc123",
            tokens_in=100,
            tokens_out=50,
            # Attempt to override forensic fields via extra kwargs
            content_length=999999,
            excerpt="INJECTED EXCERPT",
            content_hash_fake="should_be_ignored",  # non-colliding, fine
        )

        # Forensic fields must reflect server-computed values, not caller overrides
        assert payload["content_length"] == len("Authentic content")
        assert payload["excerpt"] == "Authentic content"
        assert payload["content_hash"] == "real_hash_abc123"
        assert payload["role"] == "Wind"
        assert payload["tokens_in"] == 100
        assert payload["tokens_out"] == 50
        # Non-colliding extra key is still present
        assert payload["content_hash_fake"] == "should_be_ignored"

    def test_extra_kwargs_cannot_override_token_counts(self) -> None:
        """Extra kwargs must NOT override token counts when provided.

        Token counts are server-computed and must not be overridable.
        """
        from debate_hall_mcp.events import build_turn_added_payload

        payload = build_turn_added_payload(
            role="Wall",
            model="gpt-4o",
            content="Test content",
            content_hash="hash_xyz",
            tokens_in=200,
            tokens_out=100,
            # Attempt to override token counts via extra
            tokens_in_override=9999,  # non-colliding, fine
        )

        assert payload["tokens_in"] == 200
        assert payload["tokens_out"] == 100

    def test_backward_compatibility_old_payload_still_loads(self, tmp_path: Path) -> None:
        """Old-style turn_added events (without enrichment) still load correctly.

        Ensures backward compatibility: existing event consumers that read
        events without the new fields don't break.
        """
        from debate_hall_mcp.events import EventType, append_event, load_events

        state_dir = tmp_path / "events"

        # Simulate old-style payload (pre-Issue #147)
        old_payload = {"role": "Wind", "model": "claude-opus-4-5"}
        append_event(
            thread_id="compat-001",
            event_type=EventType.TURN_ADDED,
            payload=old_payload,
            state_dir=state_dir,
        )

        events = load_events("compat-001", state_dir)
        assert len(events) == 1
        loaded = events[0]
        assert loaded.payload["role"] == "Wind"
        assert loaded.payload["model"] == "claude-opus-4-5"
        # New fields absent but event still loads fine
        assert "content_length" not in loaded.payload
        assert "excerpt" not in loaded.payload
        assert "content_hash" not in loaded.payload
