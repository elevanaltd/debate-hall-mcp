"""Unit tests for OCTAVE storage adapter.

Tests cover:
- Save debate as .oct.md file (supplementary human-readable format)
- Load debate from .oct.md file
- Round-trip: Save → Load preserves dialectic data (core fields)

Note: OCTAVE format intentionally excludes operational metadata
(audit_log, github_binding, injected_context) to focus on debate structure.
JSON remains the primary storage format with complete data."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
)


class TestOctaveStorage:
    """Test OCTAVE storage adapter for debate persistence."""

    @pytest.fixture
    def sample_room(self) -> DebateRoom:
        """Create a sample debate room for testing."""
        turn1 = Turn(
            role="Wind",
            content="Initial proposal",
            timestamp=datetime(2026, 1, 8, 10, 0, 0, tzinfo=UTC),
            previous_hash=None,
            agent_role="idea-generator",
            model="claude-opus-4",
            cognition="PATHOS",
        )
        turn2 = Turn(
            role="Wall",
            content="Critical analysis",
            timestamp=datetime(2026, 1, 8, 10, 5, 0, tzinfo=UTC),
            previous_hash=turn1.hash,
            agent_role="critical-thinker",
            model="gpt-5",
            cognition="ETHOS",
        )
        turn3 = Turn(
            role="Door",
            content="Synthesis proposal",
            timestamp=datetime(2026, 1, 8, 10, 10, 0, tzinfo=UTC),
            previous_hash=turn2.hash,
            agent_role="synthesizer",
            model="gemini-pro",
            cognition="LOGOS",
        )

        return DebateRoom(
            thread_id="2026-01-08-test-debate",
            topic="Test OCTAVE storage",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            max_turns=12,
            max_rounds=4,
            strict_cognition=True,
            octave_mode=True,
            turns=[turn1, turn2, turn3],
        )

    @pytest.fixture
    def closed_room(self, sample_room: DebateRoom) -> DebateRoom:
        """Create a closed debate room with synthesis."""
        room = sample_room.model_copy()
        room.status = DebateStatus.SYNTHESIS
        room.synthesis = "Final synthesis: Test completed successfully"
        return room

    def test_save_creates_octave_file(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that save() creates .oct.md file."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)

        octave_file = tmp_path / f"{sample_room.thread_id}.oct.md"
        assert octave_file.exists()
        assert octave_file.is_file()

    def test_save_creates_valid_octave_format(
        self, sample_room: DebateRoom, tmp_path: Path
    ) -> None:
        """Test that saved file contains valid OCTAVE format."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)

        octave_file = tmp_path / f"{sample_room.thread_id}.oct.md"
        content = octave_file.read_text()

        # Verify essential OCTAVE sections
        assert "META::" in content
        assert "TURNS::[" in content
        assert "thread_id::" in content
        assert "T0::Wind[PATHOS]#" in content
        assert "T1::Wall[ETHOS]#" in content
        assert "T2::Door[LOGOS]#" in content

    def test_save_uses_atomic_write(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that save() uses atomic write pattern (temp → rename)."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)

        # Final file should exist
        octave_file = tmp_path / f"{sample_room.thread_id}.oct.md"
        assert octave_file.exists()

        # No temp files should remain
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_load_from_octave_file(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that load() successfully loads from .oct.md file."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)

        # Load the room back
        loaded_room = storage.load(sample_room.thread_id)

        # Verify basic fields
        assert loaded_room.thread_id == sample_room.thread_id
        assert loaded_room.topic == sample_room.topic
        assert loaded_room.mode == sample_room.mode
        assert loaded_room.status == sample_room.status
        assert loaded_room.max_turns == sample_room.max_turns
        assert loaded_room.max_rounds == sample_room.max_rounds
        assert loaded_room.strict_cognition == sample_room.strict_cognition
        assert loaded_room.octave_mode == sample_room.octave_mode

    def test_load_preserves_turns(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that load() preserves turn data."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)
        loaded_room = storage.load(sample_room.thread_id)

        # Verify turn count
        assert len(loaded_room.turns) == len(sample_room.turns)

        # Verify each turn's data
        for original, loaded in zip(sample_room.turns, loaded_room.turns, strict=True):
            assert loaded.role == original.role
            assert loaded.content == original.content
            assert loaded.timestamp == original.timestamp
            assert loaded.previous_hash == original.previous_hash
            assert loaded.hash == original.hash
            assert loaded.agent_role == original.agent_role
            assert loaded.model == original.model
            assert loaded.cognition == original.cognition

    def test_load_preserves_hash_chain(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that load() preserves hash chain integrity."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)
        loaded_room = storage.load(sample_room.thread_id)

        # First turn should have no previous_hash
        assert loaded_room.turns[0].previous_hash is None

        # Subsequent turns should link correctly
        for i in range(1, len(loaded_room.turns)):
            assert loaded_room.turns[i].previous_hash == loaded_room.turns[i - 1].hash

    def test_load_preserves_synthesis(self, closed_room: DebateRoom, tmp_path: Path) -> None:
        """Test that load() preserves synthesis data."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(closed_room)
        loaded_room = storage.load(closed_room.thread_id)

        assert loaded_room.synthesis == closed_room.synthesis
        assert loaded_room.status == DebateStatus.SYNTHESIS

    def test_round_trip_fidelity(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that save → load → save → load preserves all data."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)

        # First round-trip
        storage.save(sample_room)
        loaded_once = storage.load(sample_room.thread_id)

        # Second round-trip
        storage.save(loaded_once)
        loaded_twice = storage.load(sample_room.thread_id)

        # Should be identical
        assert loaded_twice.model_dump() == sample_room.model_dump()

    def test_exists_returns_true_when_file_exists(
        self, sample_room: DebateRoom, tmp_path: Path
    ) -> None:
        """Test that exists() returns True when .oct.md file exists."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)
        storage.save(sample_room)

        assert storage.exists(sample_room.thread_id) is True

    def test_exists_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        """Test that exists() returns False when .oct.md file missing."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)

        assert storage.exists("nonexistent-thread-id") is False

    def test_load_raises_error_when_file_missing(self, tmp_path: Path) -> None:
        """Test that load() raises FileNotFoundError when .oct.md missing."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)

        with pytest.raises(FileNotFoundError):
            storage.load("nonexistent-thread-id")

    def test_save_overwrites_existing_file(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that save() overwrites existing .oct.md file."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)

        # Save initial version
        storage.save(sample_room)
        octave_file = tmp_path / f"{sample_room.thread_id}.oct.md"
        initial_content = octave_file.read_text()

        # Modify room and save again
        sample_room.turns.append(
            Turn(
                role="Wind",
                content="Additional turn",
                timestamp=datetime.now(UTC),
                previous_hash=sample_room.turns[-1].hash,
            )
        )
        storage.save(sample_room)

        # Content should be different
        updated_content = octave_file.read_text()
        assert updated_content != initial_content
        assert "Additional turn" in updated_content

    def test_validates_thread_id_safety(self, sample_room: DebateRoom, tmp_path: Path) -> None:
        """Test that storage validates thread_id for filesystem safety."""
        from debate_hall_mcp.octave_storage import OctaveStorage

        storage = OctaveStorage(tmp_path)

        # Create room with unsafe thread_id
        unsafe_room = sample_room.model_copy()
        unsafe_room.thread_id = "../../../etc/passwd"

        # Should raise ValueError
        with pytest.raises(ValueError, match="path-unsafe"):
            storage.save(unsafe_room)
