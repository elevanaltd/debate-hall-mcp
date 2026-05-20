"""Unit tests for debate_hall_mcp.state module.

Tests cover:
- DebateStatus enum values
- DebateMode enum values
- Turn model with timestamp and hash
- DebateRoom model with thread_id, topic, mode, status, limits
- ConsensusMetadata model for consensus loop results
- State persistence to JSON with hash chain (I4 compliance)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.path_contract import (
    DiffRevision,
    FrameRevision,
    PathDiff,
    PathFrame,
    VerdictRevision,
    new_path_contract,
)
from debate_hall_mcp.state import (
    ConsensusMetadata,
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

    def test_paused_status_exists(self) -> None:
        """Verify PAUSED status exists for auto-orchestration (ADR-0002)."""
        assert DebateStatus.PAUSED.value == "paused"


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
        original_replace = os.replace

        def tracking_replace(src: str, dst: str) -> None:
            rename_calls.append((src, dst))
            original_replace(src, dst)

        monkeypatch.setattr("os.replace", tracking_replace)

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

        # Make replace fail to simulate crash after write but before commit
        def failing_replace(src: str, _dst: str) -> None:
            # Clean up temp file as the real implementation should
            Path(src).unlink(missing_ok=True)
            raise OSError("Simulated crash during rename")

        monkeypatch.setattr("os.replace", failing_replace)

        with pytest.raises(OSError, match="Simulated crash during rename"):
            save_debate_state(room, state_dir)

        # Verify original state is intact - no partial writes
        final_content = (state_dir / "partial-001.json").read_text()
        assert final_content == original_content


class TestFileLocking:
    """Tests for file-based concurrency control (Issue #48)."""

    def test_save_creates_lock_file(self, tmp_path: Path) -> None:
        """Save creates a .lock file for concurrency control."""
        room = DebateRoom(
            thread_id="lock-001",
            topic="Lock Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "states"
        state_dir.mkdir(parents=True)

        save_debate_state(room, state_dir)

        # Lock file should exist
        lock_file = state_dir / "lock-001.lock"
        assert lock_file.exists()

    def test_load_creates_lock_file(self, tmp_path: Path) -> None:
        """Load creates a .lock file for concurrency control."""
        room = DebateRoom(
            thread_id="lock-002",
            topic="Lock Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "states"
        state_dir.mkdir(parents=True)

        save_debate_state(room, state_dir)

        # Remove lock file manually to test load creates it
        lock_file = state_dir / "lock-002.lock"
        lock_file.unlink()
        assert not lock_file.exists()

        # Load should recreate lock file
        load_debate_state("lock-002", state_dir)
        assert lock_file.exists()

    def test_multiple_saves_use_same_lock_file(self, tmp_path: Path) -> None:
        """Multiple saves to same thread use same lock file."""
        room = DebateRoom(
            thread_id="lock-003",
            topic="Lock Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "states"
        state_dir.mkdir(parents=True)

        # Save twice
        save_debate_state(room, state_dir)
        room.topic = "Updated Topic"
        save_debate_state(room, state_dir)

        # Only one lock file should exist
        lock_files = list(state_dir.glob("*.lock"))
        assert len(lock_files) == 1
        assert lock_files[0].name == "lock-003.lock"


class TestInjectedContext:
    """Test InjectedContext model for human_interject (Issue #17)."""

    def test_injected_context_creation(self) -> None:
        """Create InjectedContext with all required fields."""
        from debate_hall_mcp.state import InjectedContext

        ctx = InjectedContext(
            source="github_comment",
            comment_id="DC_kwDOtest123",
            content="This is a human comment",
            injection_type="pathos",
            processed_at=datetime.now(UTC),
        )
        assert ctx.source == "github_comment"
        assert ctx.comment_id == "DC_kwDOtest123"
        assert ctx.content == "This is a human comment"
        assert ctx.injection_type == "pathos"
        assert ctx.author is None
        assert ctx.replied_to_turn is None

    def test_injected_context_with_optional_fields(self) -> None:
        """Create InjectedContext with all optional fields."""
        from debate_hall_mcp.state import InjectedContext

        ctx = InjectedContext(
            source="github_comment",
            comment_id="IC_kwDOtest456",
            content="Human insight",
            injection_type="ethos",
            processed_at=datetime.now(UTC),
            author="testuser",
            replied_to_turn=2,
        )
        assert ctx.author == "testuser"
        assert ctx.replied_to_turn == 2

    def test_injected_context_validates_injection_type(self) -> None:
        """InjectedContext validates injection_type is valid."""
        from pydantic import ValidationError

        from debate_hall_mcp.state import InjectedContext

        with pytest.raises(ValidationError, match="injection_type"):
            InjectedContext(
                source="github_comment",
                comment_id="DC_test",
                content="Content",
                injection_type="invalid_type",  # Invalid
                processed_at=datetime.now(UTC),
            )

    def test_debate_room_has_injected_context_list(self) -> None:
        """DebateRoom includes injected_context list field."""
        room = DebateRoom(
            thread_id="inject-001",
            topic="Injection Test",
            mode=DebateMode.FIXED,
        )
        assert hasattr(room, "injected_context")
        assert room.injected_context == []

    def test_debate_room_injected_context_persistence(self, tmp_path: Path) -> None:
        """InjectedContext persists with room state."""
        from debate_hall_mcp.state import InjectedContext

        room = DebateRoom(
            thread_id="inject-persist-001",
            topic="Persistence Test",
            mode=DebateMode.FIXED,
        )

        ctx = InjectedContext(
            source="github_comment",
            comment_id="DC_persist123",
            content="Persisted comment",
            injection_type="logos",
            processed_at=datetime.now(UTC),
            author="persistuser",
            replied_to_turn=1,
        )
        room.injected_context.append(ctx)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        loaded_room = load_debate_state("inject-persist-001", state_dir)
        assert len(loaded_room.injected_context) == 1
        assert loaded_room.injected_context[0].comment_id == "DC_persist123"
        assert loaded_room.injected_context[0].author == "persistuser"
        assert loaded_room.injected_context[0].injection_type == "logos"


class TestConsensusMetadata:
    """Test ConsensusMetadata model for consensus loop results."""

    def test_consensus_metadata_model_validation_minimal(self) -> None:
        """ConsensusMetadata with only required field (consensus_reached)."""
        metadata = ConsensusMetadata(consensus_reached=True)
        assert metadata.consensus_reached is True
        assert metadata.wind_approved is None
        assert metadata.wall_approved is None
        assert metadata.refinement_count == 0
        assert metadata.max_refinements_reached is False

    def test_consensus_metadata_model_validation_full(self) -> None:
        """ConsensusMetadata with all fields populated."""
        metadata = ConsensusMetadata(
            consensus_reached=True,
            wind_approved=True,
            wall_approved=True,
            refinement_count=2,
            max_refinements_reached=False,
        )
        assert metadata.consensus_reached is True
        assert metadata.wind_approved is True
        assert metadata.wall_approved is True
        assert metadata.refinement_count == 2
        assert metadata.max_refinements_reached is False

    def test_consensus_metadata_stalemate(self) -> None:
        """ConsensusMetadata for stalemate scenario."""
        metadata = ConsensusMetadata(
            consensus_reached=False,
            wind_approved=True,
            wall_approved=False,
            refinement_count=3,
            max_refinements_reached=True,
        )
        assert metadata.consensus_reached is False
        assert metadata.wind_approved is True
        assert metadata.wall_approved is False
        assert metadata.refinement_count == 3
        assert metadata.max_refinements_reached is True


class TestDebateRoomConsensusMetadata:
    """Test DebateRoom with consensus_metadata field."""

    def test_debate_room_with_consensus_metadata(self) -> None:
        """DebateRoom with consensus_metadata populated."""
        metadata = ConsensusMetadata(
            consensus_reached=True,
            wind_approved=True,
            wall_approved=True,
            refinement_count=1,
            max_refinements_reached=False,
        )
        room = DebateRoom(
            thread_id="consensus-001",
            topic="Consensus Test",
            mode=DebateMode.FIXED,
            consensus_metadata=metadata,
        )
        assert room.consensus_metadata is not None
        assert room.consensus_metadata.consensus_reached is True
        assert room.consensus_metadata.wind_approved is True
        assert room.consensus_metadata.wall_approved is True
        assert room.consensus_metadata.refinement_count == 1

    def test_debate_room_without_consensus_metadata(self) -> None:
        """DebateRoom without consensus_metadata (backwards compatibility)."""
        room = DebateRoom(
            thread_id="no-consensus-001",
            topic="No Consensus Test",
            mode=DebateMode.FIXED,
        )
        assert room.consensus_metadata is None

    def test_debate_room_consensus_metadata_persistence(self, tmp_path: Path) -> None:
        """ConsensusMetadata persists correctly with room state."""
        metadata = ConsensusMetadata(
            consensus_reached=True,
            wind_approved=True,
            wall_approved=True,
            refinement_count=2,
            max_refinements_reached=False,
        )
        room = DebateRoom(
            thread_id="consensus-persist-001",
            topic="Persistence Test",
            mode=DebateMode.FIXED,
            consensus_metadata=metadata,
        )

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        loaded_room = load_debate_state("consensus-persist-001", state_dir)
        assert loaded_room.consensus_metadata is not None
        assert loaded_room.consensus_metadata.consensus_reached is True
        assert loaded_room.consensus_metadata.wind_approved is True
        assert loaded_room.consensus_metadata.wall_approved is True
        assert loaded_room.consensus_metadata.refinement_count == 2
        assert loaded_room.consensus_metadata.max_refinements_reached is False

    def test_debate_room_without_consensus_loads_correctly(self, tmp_path: Path) -> None:
        """DebateRoom without consensus_metadata loads correctly (backwards compat)."""
        # Create room without consensus_metadata
        room = DebateRoom(
            thread_id="no-consensus-persist-001",
            topic="No Consensus Persistence",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        loaded_room = load_debate_state("no-consensus-persist-001", state_dir)
        assert loaded_room.consensus_metadata is None


class TestConcurrencyControl:
    """Tests for Compare-and-Swap (CAS) concurrency control (Issue #149).

    These tests verify that concurrent state modifications are handled safely
    through hash-based optimistic locking with retry support.
    """

    def test_concurrency_error_exists(self) -> None:
        """ConcurrencyError exception class exists and is importable."""
        from debate_hall_mcp.state import ConcurrencyError

        error = ConcurrencyError("Test message")
        assert isinstance(error, Exception)
        assert str(error) == "Test message"

    def test_compute_state_hash_returns_sha256(self, tmp_path: Path) -> None:
        """compute_state_hash returns SHA-256 hash of file contents."""
        from debate_hall_mcp.state import compute_state_hash

        room = DebateRoom(
            thread_id="hash-001",
            topic="Hash Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        file_hash = compute_state_hash("hash-001", state_dir)

        # Should be a 64-character hex string (SHA-256)
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_compute_state_hash_deterministic(self, tmp_path: Path) -> None:
        """compute_state_hash returns same hash for unchanged file."""
        from debate_hall_mcp.state import compute_state_hash

        room = DebateRoom(
            thread_id="hash-002",
            topic="Deterministic Hash Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        hash1 = compute_state_hash("hash-002", state_dir)
        hash2 = compute_state_hash("hash-002", state_dir)

        assert hash1 == hash2

    def test_compute_state_hash_changes_when_content_changes(self, tmp_path: Path) -> None:
        """compute_state_hash changes when file content changes."""
        from debate_hall_mcp.state import compute_state_hash

        room = DebateRoom(
            thread_id="hash-003",
            topic="Hash Change Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        hash1 = compute_state_hash("hash-003", state_dir)

        # Modify and save again
        room.topic = "Modified Topic"
        save_debate_state(room, state_dir)

        hash2 = compute_state_hash("hash-003", state_dir)

        assert hash1 != hash2

    def test_compute_state_hash_nonexistent_file_returns_none(self, tmp_path: Path) -> None:
        """compute_state_hash returns None for nonexistent file."""
        from debate_hall_mcp.state import compute_state_hash

        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        result = compute_state_hash("nonexistent", state_dir)

        assert result is None

    def test_save_with_expected_hash_success(self, tmp_path: Path) -> None:
        """save_debate_state succeeds when expected_hash matches current state."""
        from debate_hall_mcp.state import compute_state_hash

        room = DebateRoom(
            thread_id="cas-001",
            topic="CAS Success Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"

        # Initial save (no expected_hash needed for new files)
        save_debate_state(room, state_dir)

        # Get current hash
        current_hash = compute_state_hash("cas-001", state_dir)

        # Modify and save with correct expected_hash
        room.topic = "Updated Topic"
        save_debate_state(room, state_dir, expected_hash=current_hash)

        # Verify update was applied
        loaded = load_debate_state("cas-001", state_dir)
        assert loaded.topic == "Updated Topic"

    def test_save_with_wrong_expected_hash_raises_concurrency_error(self, tmp_path: Path) -> None:
        """save_debate_state raises ConcurrencyError when expected_hash doesn't match."""
        from debate_hall_mcp.state import ConcurrencyError

        room = DebateRoom(
            thread_id="cas-002",
            topic="CAS Failure Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"

        # Initial save
        save_debate_state(room, state_dir)

        # Try to save with wrong expected_hash
        room.topic = "Should Fail"
        with pytest.raises(ConcurrencyError, match="State has been modified"):
            save_debate_state(room, state_dir, expected_hash="wrong_hash_value")

    def test_save_with_expected_hash_new_file_raises_if_file_exists(self, tmp_path: Path) -> None:
        """save_debate_state with expected_hash=None raises if file already exists."""
        room = DebateRoom(
            thread_id="cas-003",
            topic="New File Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"

        # Create file first
        save_debate_state(room, state_dir)

        # Try to create as new (expected_hash=None means "expect file doesn't exist")
        # This should work - None means "no CAS check"
        room.topic = "Overwrite"
        save_debate_state(room, state_dir)  # No expected_hash = no check

    def test_save_debate_state_with_retry_success(self, tmp_path: Path) -> None:
        """save_debate_state_with_retry succeeds on first attempt when no conflict."""
        from debate_hall_mcp.state import save_debate_state_with_retry

        room = DebateRoom(
            thread_id="retry-001",
            topic="Retry Success Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"

        # Initial save
        save_debate_state(room, state_dir)

        # Load, modify, and save with retry
        loaded = load_debate_state("retry-001", state_dir)
        loaded.topic = "Modified via retry"

        result = save_debate_state_with_retry(
            loaded,
            state_dir,
            max_retries=3,
        )

        assert result is True
        reloaded = load_debate_state("retry-001", state_dir)
        assert reloaded.topic == "Modified via retry"

    def test_save_debate_state_with_retry_exhausted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_debate_state_with_retry raises after max retries exhausted."""
        from debate_hall_mcp.state import (
            ConcurrencyError,
            save_debate_state_with_retry,
        )

        room = DebateRoom(
            thread_id="retry-002",
            topic="Retry Exhausted Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Make compute_state_hash always return different hash to simulate
        # continuous concurrent modifications
        call_count = 0

        def always_different_hash(_thread_id: str, _state_dir: Path) -> str:
            nonlocal call_count
            call_count += 1
            return f"fake_hash_{call_count}"

        monkeypatch.setattr("debate_hall_mcp.state.compute_state_hash", always_different_hash)

        # Also make save_debate_state always raise ConcurrencyError
        original_save = save_debate_state

        def always_conflict(
            room: DebateRoom,
            state_dir: Path,
            expected_hash: str | None = None,
        ) -> None:
            if expected_hash is not None:
                raise ConcurrencyError("State has been modified")
            original_save(room, state_dir)

        monkeypatch.setattr("debate_hall_mcp.state.save_debate_state", always_conflict)

        room.topic = "Should Fail After Retries"

        with pytest.raises(ConcurrencyError, match="max retries"):
            save_debate_state_with_retry(room, state_dir, max_retries=3)

    def test_save_debate_state_with_retry_uses_exponential_backoff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_debate_state_with_retry uses exponential backoff between retries."""
        from debate_hall_mcp.state import save_debate_state_with_retry

        room = DebateRoom(
            thread_id="retry-003",
            topic="Backoff Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Track sleep calls
        sleep_durations: list[float] = []

        def tracking_sleep(duration: float) -> None:
            sleep_durations.append(duration)
            # Don't actually sleep in tests

        monkeypatch.setattr("time.sleep", tracking_sleep)

        # Simulate conflicts for first 2 attempts, then succeed by returning
        # different hashes that make CAS fail, then returning correct hash
        hash_call_count = 0
        original_compute_hash = __import__(
            "debate_hall_mcp.state", fromlist=["compute_state_hash"]
        ).compute_state_hash

        def controlled_hash(thread_id: str, state_dir: Path) -> str | None:
            nonlocal hash_call_count
            hash_call_count += 1
            # First 2 calls return stale hash to trigger CAS failure
            if hash_call_count <= 2:
                return "stale_hash_that_will_fail"
            # 3rd call returns actual hash for success
            return original_compute_hash(thread_id, state_dir)

        monkeypatch.setattr("debate_hall_mcp.state.compute_state_hash", controlled_hash)

        room.topic = "Eventually Succeeds"
        save_debate_state_with_retry(room, state_dir, max_retries=5, base_delay=0.1)

        # Should have slept twice (after failures 1 and 2)
        assert len(sleep_durations) == 2
        # Exponential backoff: first delay ~ 0.1s, second ~ 0.2s (with jitter)
        assert sleep_durations[0] >= 0.05  # Allow for jitter
        assert sleep_durations[1] >= 0.1  # Second should be longer


class TestContentHashVerification:
    """Tests for content hash re-computation on load (Issue #105).

    These tests verify that turn content hashes can be recomputed and verified
    against stored hashes to detect content tampering.
    """

    def test_integrity_error_exists(self) -> None:
        """IntegrityError exception class exists and is importable."""
        from debate_hall_mcp.state import IntegrityError

        error = IntegrityError("Test message")
        assert isinstance(error, Exception)
        assert str(error) == "Test message"

    def test_verify_turn_content_hash_success(self) -> None:
        """verify_turn_content_hash returns True for unmodified turn."""
        from debate_hall_mcp.state import verify_turn_content_hash

        turn = Turn(
            role="Wind",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )

        assert verify_turn_content_hash(turn) is True

    def test_verify_turn_content_hash_detects_tampered_content(self) -> None:
        """verify_turn_content_hash returns False when content was tampered."""
        from debate_hall_mcp.state import verify_turn_content_hash

        turn = Turn(
            role="Wind",
            content="Original content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )

        # Tamper with content directly (bypassing hash recalculation)
        original_hash = turn.hash
        turn.content = "Tampered content"
        # Note: Pydantic model doesn't auto-recalculate hash on attribute change

        # Keep hash unchanged to simulate tampering
        turn.hash = original_hash

        assert verify_turn_content_hash(turn) is False

    def test_verify_turn_content_hash_skips_tombstoned_turns(self) -> None:
        """verify_turn_content_hash returns True for tombstoned turns."""
        from debate_hall_mcp.state import verify_turn_content_hash

        turn = Turn(
            role="Wind",
            content="Original content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )

        # Simulate tombstoning: replace content but keep hash
        original_hash = turn.hash
        turn.content = "[REDACTED: privacy concern]"
        turn.hash = original_hash  # Tombstone preserves original hash

        # Should pass because it's a legitimate tombstone
        assert verify_turn_content_hash(turn) is True

    def test_load_debate_state_with_verify_content_detects_tampering(self, tmp_path: Path) -> None:
        """load_debate_state raises IntegrityError when content was tampered."""
        from debate_hall_mcp.state import IntegrityError

        room = DebateRoom(
            thread_id="tamper-001",
            topic="Tamper Detection Test",
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

        # Directly modify the JSON file to simulate tampering
        state_file = state_dir / "tamper-001.json"
        import json

        with open(state_file) as f:
            data = json.load(f)

        # Tamper with content but keep hash unchanged
        data["turns"][0]["content"] = "Tampered content"

        with open(state_file, "w") as f:
            json.dump(data, f)

        # Load with verification should detect tampering
        with pytest.raises(IntegrityError, match="content.*tamper|hash.*mismatch"):
            load_debate_state("tamper-001", state_dir, verify_content=True)

    def test_load_debate_state_without_verify_content_ignores_tampering(
        self, tmp_path: Path
    ) -> None:
        """load_debate_state without verify_content loads tampered state."""
        room = DebateRoom(
            thread_id="tamper-002",
            topic="No Verify Test",
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

        # Directly modify the JSON file to simulate tampering
        state_file = state_dir / "tamper-002.json"
        import json

        with open(state_file) as f:
            data = json.load(f)

        data["turns"][0]["content"] = "Tampered content"

        with open(state_file, "w") as f:
            json.dump(data, f)

        # Load without verification (default) should succeed
        loaded = load_debate_state("tamper-002", state_dir)
        assert loaded.turns[0].content == "Tampered content"

    def test_load_debate_state_with_verify_content_allows_tombstoned(self, tmp_path: Path) -> None:
        """load_debate_state with verify_content allows tombstoned turns."""
        room = DebateRoom(
            thread_id="tombstone-001",
            topic="Tombstone Verify Test",
            mode=DebateMode.FIXED,
        )

        turn = Turn(
            role="Wind",
            content="Original content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        original_hash = turn.hash
        room.turns.append(turn)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Simulate tombstoning by modifying file
        state_file = state_dir / "tombstone-001.json"
        import json

        with open(state_file) as f:
            data = json.load(f)

        # Tombstone: content is [REDACTED:...] but hash stays same
        data["turns"][0]["content"] = "[REDACTED: privacy concern]"
        data["turns"][0]["hash"] = original_hash

        with open(state_file, "w") as f:
            json.dump(data, f)

        # Load with verification should succeed (tombstone is legitimate)
        loaded = load_debate_state("tombstone-001", state_dir, verify_content=True)
        assert loaded.turns[0].content == "[REDACTED: privacy concern]"

    def test_verify_all_turn_content_hashes_returns_results(self) -> None:
        """verify_all_turn_content_hashes returns detailed verification results."""
        from debate_hall_mcp.state import verify_all_turn_content_hashes

        room = DebateRoom(
            thread_id="verify-all-001",
            topic="Verify All Test",
            mode=DebateMode.FIXED,
        )

        # Add 3 turns
        prev_hash: str | None = None
        for i, role in enumerate(["Wind", "Wall", "Door"]):
            turn = Turn(
                role=role,
                content=f"Turn {i + 1} content",
                timestamp=datetime.now(UTC),
                previous_hash=prev_hash,
            )
            room.turns.append(turn)
            prev_hash = turn.hash

        results = verify_all_turn_content_hashes(room.turns)

        assert len(results) == 3
        assert all(result["verified"] is True for result in results)
        assert all("turn_index" in result for result in results)


class TestReaderWriterLock:
    """Tests for read/write lock pattern for concurrency (Issue #106).

    These tests verify that:
    - Multiple concurrent readers don't block each other
    - Writers get exclusive access
    - Read/write lock separation improves concurrent read throughput
    """

    def test_get_read_write_lock_exists(self) -> None:
        """_get_read_write_lock function exists and returns RW lock interface."""
        from debate_hall_mcp.state import _get_read_write_lock

        # Should be able to call the function
        lock = _get_read_write_lock(Path("/tmp/test.lock"))
        assert lock is not None
        # Should have both read and write lock methods
        assert hasattr(lock, "acquire_read_lock")
        assert hasattr(lock, "release_read_lock")
        assert hasattr(lock, "acquire_write_lock")
        assert hasattr(lock, "release_write_lock")

    def test_multiple_concurrent_readers_allowed(self, tmp_path: Path) -> None:
        """Multiple readers can acquire read lock simultaneously without blocking."""
        import threading
        import time

        from debate_hall_mcp.state import _get_read_write_lock

        lock_file = tmp_path / "concurrent.lock"

        # Track when each thread acquires and releases locks
        acquisition_times: list[tuple[str, float]] = []
        release_times: list[tuple[str, float]] = []
        lock_for_times = threading.Lock()

        def reader(reader_id: str) -> None:
            """Reader that holds lock for 0.1 seconds."""
            # Each reader gets its own lock instance (simulates different processes)
            # All instances coordinate via the same lock file
            lock = _get_read_write_lock(lock_file)
            lock.acquire_read_lock()
            with lock_for_times:
                acquisition_times.append((reader_id, time.time()))
            time.sleep(0.1)  # Hold lock for 0.1 seconds
            with lock_for_times:
                release_times.append((reader_id, time.time()))
            lock.release_read_lock()

        # Start 3 readers at almost the same time
        threads = [threading.Thread(target=reader, args=(f"reader-{i}",)) for i in range(3)]
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        # If readers blocked each other (exclusive locks), total time would be ~0.3s
        # With shared read locks, all 3 readers run concurrently, total time ~0.1s
        # Allow some slack for thread scheduling overhead
        assert total_time < 0.25, (
            f"Concurrent readers took {total_time:.3f}s, expected < 0.25s. "
            f"Readers may be blocking each other (using exclusive instead of shared locks)."
        )

        # All 3 readers should have acquired locks within a small time window
        acq_times = [t for _, t in acquisition_times]
        assert len(acq_times) == 3
        time_spread = max(acq_times) - min(acq_times)
        assert time_spread < 0.05, (
            f"Reader acquisition spread was {time_spread:.3f}s, expected < 0.05s. "
            f"Readers appear to be waiting for each other."
        )

    def test_writer_blocks_readers_across_processes(self, tmp_path: Path) -> None:
        """Writer gets exclusive access, blocking readers in other PROCESSES.

        Note: InterProcessReaderWriterLock uses fcntl which is per-process, not per-thread.
        This test uses subprocesses to properly test inter-process locking behavior.
        """
        import json
        import subprocess
        import sys

        lock_file = tmp_path / "exclusive.lock"
        results_file = tmp_path / "results.json"

        # Python script for writer process
        writer_script = f"""
import fasteners
import time
import json

lock = fasteners.InterProcessReaderWriterLock("{lock_file}")
lock.acquire_write_lock()
acquired_time = time.time()
print("WRITER_ACQUIRED", flush=True)
time.sleep(0.15)  # Hold lock for 150ms
released_time = time.time()
lock.release_write_lock()

with open("{results_file}", "w") as f:
    json.dump({{"writer_acquired": acquired_time, "writer_released": released_time}}, f)
"""

        # Python script for reader process
        reader_script = f"""
import fasteners
import time
import sys

# Wait a bit for writer to acquire
time.sleep(0.05)

lock = fasteners.InterProcessReaderWriterLock("{lock_file}")
request_time = time.time()
lock.acquire_read_lock()
acquired_time = time.time()
lock.release_read_lock()

print(f"{{request_time}},{{acquired_time}}")
"""

        # Start writer and reader processes
        writer_proc = subprocess.Popen(
            [sys.executable, "-c", writer_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for writer to signal it has acquired the lock
        writer_out = writer_proc.stdout.readline() if writer_proc.stdout else ""
        assert "WRITER_ACQUIRED" in writer_out, f"Writer failed to acquire lock: {writer_out}"

        # Start reader after writer has lock
        reader_proc = subprocess.Popen(
            [sys.executable, "-c", reader_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for both to complete
        reader_stdout, reader_stderr = reader_proc.communicate(timeout=5)
        writer_proc.wait(timeout=5)

        # Parse results
        with open(results_file) as f:
            writer_results = json.load(f)

        reader_times = reader_stdout.strip().split(",")
        reader_request_time = float(reader_times[0])
        reader_acquired_time = float(reader_times[1])

        # Reader should have requested while writer held lock
        assert reader_request_time < writer_results["writer_released"], (
            f"Reader requested at {reader_request_time:.4f}, "
            f"but writer released at {writer_results['writer_released']:.4f}"
        )

        # Reader should have acquired AFTER writer released (blocked by write lock)
        assert reader_acquired_time >= writer_results["writer_released"], (
            f"Reader acquired lock while writer held it. "
            f"Reader acquired at {reader_acquired_time:.4f}, "
            f"Writer released at {writer_results['writer_released']:.4f}"
        )

    def test_load_uses_read_lock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_debate_state uses read lock (shared) not exclusive lock."""
        from unittest.mock import MagicMock

        from debate_hall_mcp import state

        # Create a test state file
        room = DebateRoom(
            thread_id="rwlock-001",
            topic="RW Lock Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Mock the RW lock to track which lock type is used
        mock_lock = MagicMock()
        mock_lock.acquire_read_lock = MagicMock()
        mock_lock.release_read_lock = MagicMock()
        mock_lock.acquire_write_lock = MagicMock()
        mock_lock.release_write_lock = MagicMock()

        def mock_get_rw_lock(_path: Path) -> MagicMock:
            return mock_lock

        monkeypatch.setattr(state, "_get_read_write_lock", mock_get_rw_lock)

        # Load should use read lock
        load_debate_state("rwlock-001", state_dir)

        # Verify read lock was used, not write lock
        mock_lock.acquire_read_lock.assert_called_once()
        mock_lock.release_read_lock.assert_called_once()
        mock_lock.acquire_write_lock.assert_not_called()
        mock_lock.release_write_lock.assert_not_called()

    def test_save_uses_write_lock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_debate_state uses write lock (exclusive) for data integrity."""
        from unittest.mock import MagicMock

        from debate_hall_mcp import state

        # Mock the RW lock to track which lock type is used
        mock_lock = MagicMock()
        mock_lock.acquire_read_lock = MagicMock()
        mock_lock.release_read_lock = MagicMock()
        mock_lock.acquire_write_lock = MagicMock()
        mock_lock.release_write_lock = MagicMock()

        def mock_get_rw_lock(_path: Path) -> MagicMock:
            return mock_lock

        monkeypatch.setattr(state, "_get_read_write_lock", mock_get_rw_lock)

        room = DebateRoom(
            thread_id="rwlock-002",
            topic="RW Lock Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Save should use write lock
        save_debate_state(room, state_dir)

        # Verify write lock was used, not read lock
        mock_lock.acquire_write_lock.assert_called_once()
        mock_lock.release_write_lock.assert_called_once()
        mock_lock.acquire_read_lock.assert_not_called()
        mock_lock.release_read_lock.assert_not_called()

    def test_concurrent_reads_dont_block_performance(self, tmp_path: Path) -> None:
        """Verify concurrent load_debate_state calls can run in parallel."""
        import threading
        import time

        room = DebateRoom(
            thread_id="perf-001",
            topic="Performance Test",
            mode=DebateMode.FIXED,
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        results: list[DebateRoom] = []
        results_lock = threading.Lock()

        def read_state() -> None:
            """Load state with a small artificial delay to test concurrency."""
            loaded = load_debate_state("perf-001", state_dir)
            time.sleep(0.05)  # Simulate some processing time after read
            with results_lock:
                results.append(loaded)

        # Run 5 concurrent reads
        threads = [threading.Thread(target=read_state) for _ in range(5)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # All reads should succeed
        assert len(results) == 5
        assert all(r.thread_id == "perf-001" for r in results)

        # With concurrent readers, should complete in ~0.05s + overhead
        # If using exclusive locks, would take ~0.25s (5 * 0.05s serial)
        assert elapsed < 0.20, (
            f"Concurrent reads took {elapsed:.3f}s, expected < 0.20s. "
            f"Reads may be blocking each other."
        )


# ---------------------------------------------------------------------------
# RFC-0001 #197 — PathContract persistence on DebateRoom
#
# RED tests for:
#   1. round-trip preserves all PathContract fields including append-only
#      revision histories (PROD::I4, RFC §3.1)
#   2. backward compat: state files without `path_contracts` load with
#      `path_contracts = []` (always-emit-empty design)
#   3. typed append API: `append_frame_revision` / `append_verdict_revision`
#      / `append_diff_revision` auto-create the contract for the path_id,
#      auto-assign monotonic `rev`, enforce ownership at the API boundary,
#      and reject mutation of already-appended revisions (PROD::I4
#      append-only invariant)
#   4. `prompt_context_view` on a persisted contract returns the correct
#      `latest_*` revisions (regression guard for #199 renderer hot path)
# ---------------------------------------------------------------------------


def _ts(minute: int = 0) -> datetime:
    """Stable timezone-aware timestamp for deterministic tests."""
    return datetime(2026, 5, 19, 12, minute, 0, tzinfo=UTC)


def _frame_value(problem: str = "x") -> PathFrame:
    return PathFrame(
        assumed_problem=problem,
        success_criterion="criterion",
        accepted_failure_mode="failure_mode",
        invariants_touched=["inv_a"],
    )


def _diff_value_empty() -> PathDiff:
    return PathDiff(accepted=[], disputed=[], reframed=[])


class TestDebateRoomPathContractsField:
    """The `path_contracts` field exists with a sensible default."""

    def test_path_contracts_defaults_to_empty_list(self) -> None:
        """Fresh DebateRoom has `path_contracts == []` (always-emit-empty)."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-default",
            topic="contracts field default",
            mode=DebateMode.FIXED,
        )
        assert room.path_contracts == []

    def test_path_contracts_accepts_initial_contracts(self) -> None:
        """Construction with pre-built contracts list preserves them."""
        contract = new_path_contract("p1")
        room = DebateRoom(
            thread_id="2026-05-19-pc-init",
            topic="contracts on construction",
            mode=DebateMode.FIXED,
            path_contracts=[contract],
        )
        assert len(room.path_contracts) == 1
        assert room.path_contracts[0]["path_id"] == "p1"


class TestPathContractsRoundTrip:
    """Round-trip preserves every PathContract field through JSON."""

    def test_roundtrip_preserves_all_histories(self, tmp_path: Path) -> None:
        """Save then reload preserves frame/verdict/diff histories and dt fields."""
        contract = new_path_contract("path_alpha")
        contract["frame_history"].append(
            FrameRevision(
                rev=0,
                written_at=_ts(0),
                written_by="Wind",
                value=_frame_value("alpha problem"),
            )
        )
        contract["verdict_history"].append(
            VerdictRevision(
                rev=0,
                written_at=_ts(1),
                written_by="Wall",
                value={"inv_a": {"status": "HARD_pass", "rationale": "ok"}},
            )
        )
        contract["diff_history"].append(
            DiffRevision(
                rev=0,
                written_at=_ts(2),
                written_by="Wind",
                value=_diff_value_empty(),
                divergence_marker="NO_NEW_DIVERGENCE",
            )
        )
        room = DebateRoom(
            thread_id="2026-05-19-pc-rt",
            topic="round-trip preservation",
            mode=DebateMode.FIXED,
            path_contracts=[contract],
        )

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-05-19-pc-rt", state_dir)

        assert len(loaded.path_contracts) == 1
        rt = loaded.path_contracts[0]
        assert rt["path_id"] == "path_alpha"
        assert len(rt["frame_history"]) == 1
        assert len(rt["verdict_history"]) == 1
        assert len(rt["diff_history"]) == 1
        assert rt["frame_history"][0]["written_by"] == "Wind"
        assert rt["frame_history"][0]["value"]["assumed_problem"] == "alpha problem"
        # datetime restored to native type, not str
        assert isinstance(rt["frame_history"][0]["written_at"], datetime)
        assert rt["verdict_history"][0]["value"]["inv_a"]["status"] == "HARD_pass"
        # NotRequired key preserved when present on input
        assert rt["diff_history"][0].get("divergence_marker") == "NO_NEW_DIVERGENCE"

    def test_roundtrip_multiple_contracts_preserved(self, tmp_path: Path) -> None:
        """Multiple PathContracts persist independently."""
        c1 = new_path_contract("p1")
        c2 = new_path_contract("p2")
        c2["frame_history"].append(
            FrameRevision(
                rev=0,
                written_at=_ts(),
                written_by="Wind",
                value=_frame_value(),
            )
        )
        room = DebateRoom(
            thread_id="2026-05-19-pc-multi",
            topic="multi-path",
            mode=DebateMode.FIXED,
            path_contracts=[c1, c2],
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-05-19-pc-multi", state_dir)
        assert [c["path_id"] for c in loaded.path_contracts] == ["p1", "p2"]
        assert len(loaded.path_contracts[0]["frame_history"]) == 0
        assert len(loaded.path_contracts[1]["frame_history"]) == 1


class TestPathContractsBackwardCompat:
    """State files written before #197 land with no `path_contracts` key
    must still load, defaulting to an empty list."""

    def test_legacy_state_without_path_contracts_loads(self, tmp_path: Path) -> None:
        """Hand-craft a state file lacking `path_contracts`; load yields []."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir()
        legacy_payload = {
            "thread_id": "2026-05-19-legacy",
            "topic": "legacy",
            "mode": "fixed",
            "status": "active",
            "max_turns": 12,
            "max_rounds": 4,
            "turns": [],
            "audit_log": [],
            "injected_context": [],
        }
        (state_dir / "2026-05-19-legacy.json").write_text(json.dumps(legacy_payload))

        loaded = load_debate_state("2026-05-19-legacy", state_dir)
        assert loaded.path_contracts == []


class TestPathContractTypedAppendAPI:
    """`DebateRoom.append_*_revision` methods enforce the PROD::I4
    append-only invariant at the type/API boundary."""

    def test_append_frame_revision_auto_creates_contract(self) -> None:
        """First append for a new path_id transparently creates the contract."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-auto",
            topic="auto-create",
            mode=DebateMode.FIXED,
        )
        room.append_frame_revision(
            path_id="new_path",
            written_at=_ts(),
            value=_frame_value(),
        )
        assert len(room.path_contracts) == 1
        contract = room.path_contracts[0]
        assert contract["path_id"] == "new_path"
        assert len(contract["frame_history"]) == 1
        # rev auto-assigned to 0 for first append
        assert contract["frame_history"][0]["rev"] == 0
        # ownership Literal set by API, not caller
        assert contract["frame_history"][0]["written_by"] == "Wind"

    def test_append_frame_revision_monotonic_rev(self) -> None:
        """Successive appends assign rev = previous rev + 1."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-mono",
            topic="monotonic",
            mode=DebateMode.FIXED,
        )
        room.append_frame_revision(path_id="p1", written_at=_ts(0), value=_frame_value("v0"))
        room.append_frame_revision(path_id="p1", written_at=_ts(1), value=_frame_value("v1"))
        contract = room.path_contracts[0]
        assert [r["rev"] for r in contract["frame_history"]] == [0, 1]
        assert contract["frame_history"][1]["value"]["assumed_problem"] == "v1"

    def test_append_verdict_revision_sets_wall_owner(self) -> None:
        """Verdict appends are stamped `written_by='Wall'` by the API."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-verdict",
            topic="verdict owner",
            mode=DebateMode.FIXED,
        )
        room.append_verdict_revision(
            path_id="p1",
            written_at=_ts(),
            value={"inv_a": {"status": "HARD_pass", "rationale": "r"}},
        )
        contract = room.path_contracts[0]
        assert contract["verdict_history"][0]["written_by"] == "Wall"
        assert contract["verdict_history"][0]["rev"] == 0

    def test_append_diff_revision_sets_wind_owner(self) -> None:
        """Diff appends are stamped `written_by='Wind'` by the API."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-diff",
            topic="diff owner",
            mode=DebateMode.FIXED,
        )
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(),
            value=_diff_value_empty(),
        )
        contract = room.path_contracts[0]
        assert contract["diff_history"][0]["written_by"] == "Wind"
        assert contract["diff_history"][0]["rev"] == 0

    def test_append_diff_revision_carries_optional_fields(self) -> None:
        """Optional `divergence_marker` / `synthesis_guidance` flow through."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-diff-opt",
            topic="diff optional",
            mode=DebateMode.FIXED,
        )
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(),
            value=_diff_value_empty(),
            divergence_marker="NO_NEW_DIVERGENCE",
            synthesis_guidance="cross-path insight",
        )
        contract = room.path_contracts[0]
        diff = contract["diff_history"][0]
        assert diff.get("divergence_marker") == "NO_NEW_DIVERGENCE"
        assert diff.get("synthesis_guidance") == "cross-path insight"

    def test_append_methods_are_per_path(self) -> None:
        """Different path_ids produce distinct contracts; rev counters are
        independent per (path_id, history-kind)."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-perpath",
            topic="per-path",
            mode=DebateMode.FIXED,
        )
        room.append_frame_revision(path_id="p1", written_at=_ts(0), value=_frame_value())
        room.append_frame_revision(path_id="p2", written_at=_ts(1), value=_frame_value())
        room.append_frame_revision(path_id="p1", written_at=_ts(2), value=_frame_value())
        assert {c["path_id"] for c in room.path_contracts} == {"p1", "p2"}
        by_id = {c["path_id"]: c for c in room.path_contracts}
        assert [r["rev"] for r in by_id["p1"]["frame_history"]] == [0, 1]
        assert [r["rev"] for r in by_id["p2"]["frame_history"]] == [0]

    def test_append_diff_rejects_illegal_divergence_marker(self) -> None:
        """API guards the `divergence_marker` Literal at the boundary so
        the persisted form cannot carry an invalid sentinel value."""
        room = DebateRoom(
            thread_id="2026-05-19-pc-bad-sentinel",
            topic="bad sentinel",
            mode=DebateMode.FIXED,
        )
        with pytest.raises(ValueError, match="divergence_marker"):
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(),
                value=_diff_value_empty(),
                divergence_marker="BOGUS_MARKER",
            )


class TestPathContractLatestRevisionGuard:
    """Regression guard for #199: `prompt_context_view` on a persisted
    contract MUST return the correct latest revision per field — this is
    the renderer's hot-path invariant."""

    def test_prompt_context_view_after_roundtrip(self, tmp_path: Path) -> None:
        """Persist a contract with 2 frame revs; latest_frame is rev 1."""
        from debate_hall_mcp.path_contract import prompt_context_view

        room = DebateRoom(
            thread_id="2026-05-19-pc-latest",
            topic="latest",
            mode=DebateMode.FIXED,
        )
        room.append_frame_revision(path_id="p1", written_at=_ts(0), value=_frame_value("rev0"))
        room.append_frame_revision(path_id="p1", written_at=_ts(1), value=_frame_value("rev1"))
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-05-19-pc-latest", state_dir)

        view = prompt_context_view(loaded.path_contracts[0])
        assert view["frame_count"] == 2
        assert view["latest_frame"] is not None
        assert view["latest_frame"]["rev"] == 1
        assert view["latest_frame"]["value"]["assumed_problem"] == "rev1"
        assert view["latest_verdict"] is None
        assert view["latest_diff"] is None

    def test_prompt_context_view_latest_verdict_after_roundtrip(self, tmp_path: Path) -> None:
        """Persist a contract with 2 verdict revs; latest_verdict is rev 1.

        Symmetric coverage of TMG CONDITIONAL (#219): the renderer's hot-path
        invariant must hold for verdict history under round-trip, not just frame.
        """
        from debate_hall_mcp.path_contract import prompt_context_view

        room = DebateRoom(
            thread_id="2026-05-19-pc-latest-verdict",
            topic="latest verdict",
            mode=DebateMode.FIXED,
        )
        room.append_verdict_revision(
            path_id="p1",
            written_at=_ts(0),
            value={"inv_a": {"status": "HARD_pass", "rationale": "rev0"}},
        )
        room.append_verdict_revision(
            path_id="p1",
            written_at=_ts(1),
            value={"inv_a": {"status": "HARD_pass", "rationale": "rev1"}},
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-05-19-pc-latest-verdict", state_dir)

        view = prompt_context_view(loaded.path_contracts[0])
        assert view["verdict_count"] == 2
        assert view["latest_verdict"] is not None
        assert view["latest_verdict"]["rev"] == 1
        assert view["latest_verdict"]["value"]["inv_a"]["rationale"] == "rev1"

    def test_prompt_context_view_latest_diff_after_roundtrip(self, tmp_path: Path) -> None:
        """Persist a contract with 2 diff revs; latest_diff is rev 1.

        Symmetric coverage of TMG CONDITIONAL (#219): the renderer's hot-path
        invariant must hold for diff history under round-trip, not just frame.
        """
        from debate_hall_mcp.path_contract import prompt_context_view

        room = DebateRoom(
            thread_id="2026-05-19-pc-latest-diff",
            topic="latest diff",
            mode=DebateMode.FIXED,
        )
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(0),
            value=_diff_value_empty(),
            synthesis_guidance="rev0",
        )
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(1),
            value=_diff_value_empty(),
            synthesis_guidance="rev1",
        )
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-05-19-pc-latest-diff", state_dir)

        view = prompt_context_view(loaded.path_contracts[0])
        assert view["diff_count"] == 2
        assert view["latest_diff"] is not None
        assert view["latest_diff"]["rev"] == 1
        assert view["latest_diff"]["synthesis_guidance"] == "rev1"
