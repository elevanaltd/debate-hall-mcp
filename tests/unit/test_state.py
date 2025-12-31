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


class TestStateSecurityValidation:
    """Security tests for state persistence (path traversal prevention)."""

    def test_load_rejects_path_traversal_dotdot(self, tmp_path: Path) -> None:
        """Test that load_debate_state rejects path traversal with .."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="Invalid thread_id"):
            load_debate_state("../sensitive", state_dir)

    def test_load_rejects_forward_slash(self, tmp_path: Path) -> None:
        """Test that load_debate_state rejects forward slash."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="Invalid thread_id"):
            load_debate_state("foo/bar", state_dir)

    def test_load_rejects_backslash(self, tmp_path: Path) -> None:
        """Test that load_debate_state rejects backslash."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="Invalid thread_id"):
            load_debate_state("foo\\bar", state_dir)

    def test_save_rejects_path_traversal_in_thread_id(self, tmp_path: Path) -> None:
        """Test that save_debate_state rejects path traversal in thread_id."""
        # Create room with malicious thread_id (bypassing init validation)
        room = DebateRoom(
            thread_id="../sensitive",
            topic="Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        with pytest.raises(ValueError, match="Invalid thread_id"):
            save_debate_state(room, state_dir)

    def test_save_rejects_forward_slash_in_thread_id(self, tmp_path: Path) -> None:
        """Test that save_debate_state rejects forward slash in thread_id."""
        room = DebateRoom(
            thread_id="foo/bar",
            topic="Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        with pytest.raises(ValueError, match="Invalid thread_id"):
            save_debate_state(room, state_dir)


class TestAtomicPersistence:
    """Test atomic persistence for crash recovery (Issue #39).

    Verifies that state writes use atomic file operations to prevent
    data corruption from interrupted writes.
    """

    def test_save_uses_temp_file_then_rename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save creates temp file and atomically renames to final location."""
        import os

        room = DebateRoom(
            thread_id="atomic-001",
            topic="Atomic Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Track calls to os.rename
        rename_calls: list[tuple[str, str]] = []
        original_rename = os.rename

        def tracking_rename(src: str, dst: str) -> None:
            rename_calls.append((src, dst))
            original_rename(src, dst)

        monkeypatch.setattr("os.rename", tracking_rename)

        save_debate_state(room, state_dir)

        # Verify atomic rename was used
        assert len(rename_calls) == 1
        src, dst = rename_calls[0]
        # Source should be a temp file in the same directory
        assert tmp_path.as_posix() in src
        assert src.endswith(".tmp")
        # Destination should be the final state file
        assert dst == str(state_dir / "atomic-001.json")

    def test_save_calls_fsync_for_durability(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save calls fsync before rename to ensure durability."""
        import os

        room = DebateRoom(
            thread_id="fsync-001",
            topic="Fsync Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Track fsync calls
        fsync_calls: list[int] = []
        original_fsync = os.fsync

        def tracking_fsync(fd: int) -> None:
            fsync_calls.append(fd)
            original_fsync(fd)

        monkeypatch.setattr("os.fsync", tracking_fsync)

        save_debate_state(room, state_dir)

        # Verify fsync was called at least once
        assert len(fsync_calls) >= 1

    def test_save_cleans_up_temp_file_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Temp file is cleaned up if write fails."""
        import tempfile as tempfile_module

        room = DebateRoom(
            thread_id="cleanup-001",
            topic="Cleanup Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Track temp files created
        created_temps: list[str] = []
        original_mkstemp = tempfile_module.mkstemp

        def tracking_mkstemp(**kwargs: object) -> tuple[int, str]:
            fd, path = original_mkstemp(**kwargs)
            created_temps.append(path)
            return fd, path

        monkeypatch.setattr("tempfile.mkstemp", tracking_mkstemp)

        # Make model_dump_json raise an error to simulate write failure
        def failing_model_dump(_self: object, **_kwargs: object) -> str:
            raise RuntimeError("Simulated write failure")

        monkeypatch.setattr(DebateRoom, "model_dump_json", failing_model_dump)

        with pytest.raises(RuntimeError, match="Simulated write failure"):
            save_debate_state(room, state_dir)

        # Verify temp file was cleaned up
        assert len(created_temps) == 1
        temp_path = created_temps[0]
        assert not Path(temp_path).exists(), f"Temp file {temp_path} should have been cleaned up"

    def test_save_preserves_existing_state_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Existing state file is preserved if new write fails."""
        # Create initial state
        room = DebateRoom(
            thread_id="preserve-001",
            topic="Initial State",
            mode=DebateMode.FIXED,
        )
        turn = Turn(
            role="Wind",
            content="Original content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Record original file content
        state_file = state_dir / "preserve-001.json"
        original_content = state_file.read_text()

        # Create updated room that will fail to save
        updated_room = DebateRoom(
            thread_id="preserve-001",
            topic="Updated State",
            mode=DebateMode.FIXED,
        )

        # Make serialization fail after file operations begin
        def failing_dump(_self: object, **_kwargs: object) -> str:
            raise RuntimeError("Simulated serialization failure")

        monkeypatch.setattr(DebateRoom, "model_dump_json", failing_dump)

        with pytest.raises(RuntimeError, match="Simulated serialization failure"):
            save_debate_state(updated_room, state_dir)

        # Verify original state is preserved
        assert state_file.read_text() == original_content

    def test_save_no_temp_files_left_on_success(self, tmp_path: Path) -> None:
        """No temp files remain after successful save."""
        room = DebateRoom(
            thread_id="notmp-001",
            topic="No Temp Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        save_debate_state(room, state_dir)

        # Check for any .tmp files in the directory
        tmp_files = list(state_dir.glob("*.tmp"))
        assert tmp_files == [], f"Found leftover temp files: {tmp_files}"

    def test_atomic_write_prevents_partial_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Interrupted writes don't leave partial JSON files.

        Simulates a crash during write by having the write succeed but
        rename fail, verifying no partial content is written to final path.
        """
        room = DebateRoom(
            thread_id="partial-001",
            topic="Partial Write Test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Create existing valid state first
        existing_room = DebateRoom(
            thread_id="partial-001",
            topic="Existing Valid State",
            mode=DebateMode.FIXED,
        )
        save_debate_state(existing_room, state_dir)
        original_content = (state_dir / "partial-001.json").read_text()

        # Make rename fail to simulate crash after write but before commit
        def failing_rename(src: str, _dst: str) -> None:
            # Clean up temp file as the real implementation should
            Path(src).unlink(missing_ok=True)
            raise OSError("Simulated crash during rename")

        monkeypatch.setattr("os.rename", failing_rename)

        with pytest.raises(OSError, match="Simulated crash during rename"):
            save_debate_state(room, state_dir)

        # Verify original state is intact - no partial writes
        final_content = (state_dir / "partial-001.json").read_text()
        assert final_content == original_content
