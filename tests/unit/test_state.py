"""Unit tests for debate_hall_mcp.state module.

Tests cover:
- DebateStatus enum values
- DebateMode enum values
- Turn model with timestamp and hash
- DebateRoom model with thread_id, topic, mode, status, limits
- State persistence to JSON with hash chain (I4 compliance)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
    calculate_turn_hash,
    load_debate_state,
    save_debate_state,
)


class TestDebateStatus:
    """Test DebateStatus enum."""

    def test_status_values(self) -> None:
        """Verify all required status values exist."""
        assert DebateStatus.ACTIVE.value == "active"
        assert DebateStatus.SYNTHESIS.value == "synthesis"
        assert DebateStatus.STALEMATE.value == "stalemate"
        assert DebateStatus.EXHAUSTION.value == "exhaustion"
        assert DebateStatus.FORCE_CLOSED.value == "force_closed"


class TestDebateMode:
    """Test DebateMode enum."""

    def test_mode_values(self) -> None:
        """Verify all required mode values exist."""
        assert DebateMode.FIXED.value == "fixed"
        assert DebateMode.MEDIATED.value == "mediated"


class TestTurn:
    """Test Turn model with hash chain support."""

    def test_turn_creation(self) -> None:
        """Create turn with role, content, timestamp."""
        turn = Turn(
            role="Wind",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        assert turn.role == "Wind"
        assert turn.content == "Test content"
        assert turn.previous_hash is None
        assert turn.hash is not None

    def test_turn_hash_calculated(self) -> None:
        """Turn hash is automatically calculated from content."""
        turn = Turn(
            role="Wall",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        # Hash should be deterministic based on role, content, timestamp, previous_hash
        expected_hash = calculate_turn_hash(
            turn.role, turn.content, turn.timestamp, turn.previous_hash
        )
        assert turn.hash == expected_hash

    def test_turn_hash_chain(self) -> None:
        """Each turn links to previous turn via hash (I4 compliance)."""
        turn1 = Turn(
            role="Wind",
            content="First",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        turn2 = Turn(
            role="Wall",
            content="Second",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        assert turn2.previous_hash == turn1.hash
        assert turn2.hash != turn1.hash


class TestDebateRoom:
    """Test DebateRoom model."""

    def test_room_creation_defaults(self) -> None:
        """Create debate room with required fields and defaults."""
        room = DebateRoom(
            thread_id="test-thread-001",
            topic="Test Topic",
            mode=DebateMode.FIXED,
        )
        assert room.thread_id == "test-thread-001"
        assert room.topic == "Test Topic"
        assert room.mode == DebateMode.FIXED
        assert room.status == DebateStatus.ACTIVE
        assert room.max_turns == 12
        assert room.max_rounds == 4
        assert room.turns == []
        assert room.synthesis is None

    def test_room_creation_custom_limits(self) -> None:
        """Create debate room with custom limits."""
        room = DebateRoom(
            thread_id="test-002",
            topic="Custom Limits",
            mode=DebateMode.MEDIATED,
            max_turns=6,
            max_rounds=2,
        )
        assert room.max_turns == 6
        assert room.max_rounds == 2

    def test_room_add_turn(self) -> None:
        """Add turn to debate room maintains hash chain."""
        room = DebateRoom(
            thread_id="test-003",
            topic="Hash Chain Test",
            mode=DebateMode.FIXED,
        )

        turn1 = Turn(
            role="Wind",
            content="First turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second turn",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        assert len(room.turns) == 2
        assert room.turns[1].previous_hash == room.turns[0].hash

    def test_room_turn_count(self) -> None:
        """Room tracks current turn count."""
        room = DebateRoom(
            thread_id="test-004",
            topic="Turn Count",
            mode=DebateMode.FIXED,
        )

        assert len(room.turns) == 0

        room.turns.append(
            Turn(
                role="Wind",
                content="Turn 1",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )

        assert len(room.turns) == 1


class TestStatePersistence:
    """Test JSON persistence with hash chain integrity."""

    def test_save_debate_state(self, tmp_path: Path) -> None:
        """Save debate room state to JSON file."""
        room = DebateRoom(
            thread_id="persist-001",
            topic="Persistence Test",
            mode=DebateMode.FIXED,
        )

        turn = Turn(
            role="Wind",
            content="Test turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Verify file was created
        state_file = state_dir / f"{room.thread_id}.json"
        assert state_file.exists()

        # Verify JSON structure
        with open(state_file) as f:
            data = json.load(f)

        assert data["thread_id"] == "persist-001"
        assert data["topic"] == "Persistence Test"
        assert data["mode"] == "fixed"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["role"] == "Wind"
        assert data["turns"][0]["hash"] is not None

    def test_load_debate_state(self, tmp_path: Path) -> None:
        """Load debate room state from JSON file."""
        # Create and save a room
        room = DebateRoom(
            thread_id="load-001",
            topic="Load Test",
            mode=DebateMode.MEDIATED,
            max_turns=8,
        )

        turn = Turn(
            role="Wall",
            content="Loaded turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Load the room
        loaded_room = load_debate_state("load-001", state_dir)

        assert loaded_room.thread_id == "load-001"
        assert loaded_room.topic == "Load Test"
        assert loaded_room.mode == DebateMode.MEDIATED
        assert loaded_room.max_turns == 8
        assert len(loaded_room.turns) == 1
        assert loaded_room.turns[0].role == "Wall"
        assert loaded_room.turns[0].hash == turn.hash

    def test_load_nonexistent_state(self, tmp_path: Path) -> None:
        """Loading nonexistent state raises FileNotFoundError."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            load_debate_state("nonexistent-thread", state_dir)

    def test_hash_chain_integrity_preserved(self, tmp_path: Path) -> None:
        """Hash chain integrity is preserved across save/load (I4 compliance)."""
        room = DebateRoom(
            thread_id="integrity-001",
            topic="Hash Chain Integrity",
            mode=DebateMode.FIXED,
        )

        # Create chain of 3 turns
        turn1 = Turn(
            role="Wind",
            content="First",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        turn3 = Turn(
            role="Door",
            content="Third",
            timestamp=datetime.now(UTC),
            previous_hash=turn2.hash,
        )
        room.turns.append(turn3)

        # Save and reload
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded_room = load_debate_state("integrity-001", state_dir)

        # Verify hash chain integrity
        assert loaded_room.turns[0].previous_hash is None
        assert loaded_room.turns[1].previous_hash == loaded_room.turns[0].hash
        assert loaded_room.turns[2].previous_hash == loaded_room.turns[1].hash


class TestCalculateTurnHash:
    """Test hash calculation function."""

    def test_hash_deterministic(self) -> None:
        """Hash is deterministic for same inputs."""
        timestamp = datetime.now(UTC)
        hash1 = calculate_turn_hash("Wind", "Content", timestamp, None)
        hash2 = calculate_turn_hash("Wind", "Content", timestamp, None)
        assert hash1 == hash2

    def test_hash_different_content(self) -> None:
        """Hash changes with different content."""
        timestamp = datetime.now(UTC)
        hash1 = calculate_turn_hash("Wind", "Content1", timestamp, None)
        hash2 = calculate_turn_hash("Wind", "Content2", timestamp, None)
        assert hash1 != hash2

    def test_hash_includes_previous(self) -> None:
        """Hash changes when previous_hash is different."""
        timestamp = datetime.now(UTC)
        hash1 = calculate_turn_hash("Wind", "Content", timestamp, None)
        hash2 = calculate_turn_hash("Wind", "Content", timestamp, "previous-hash")
        assert hash1 != hash2
