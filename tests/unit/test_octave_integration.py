"""Integration tests for OCTAVE storage with state.py.

Tests verify that OCTAVE storage integrates correctly with the existing
state persistence layer without breaking backward compatibility.
"""

from datetime import UTC, datetime
from pathlib import Path

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
    load_debate_state,
    save_debate_state,
)


class TestOctaveIntegration:
    """Test OCTAVE storage integration with state.py."""

    def test_save_creates_both_json_and_octave(self, tmp_path: Path) -> None:
        """Test that save creates both .json and .oct.md when octave_mode=True."""
        turn = Turn(
            role="Wind",
            content="Test proposal",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            previous_hash=None,
            cognition="PATHOS",
        )

        room = DebateRoom(
            thread_id="2026-01-08-integration-test",
            topic="Test integration",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            octave_mode=True,  # Enable OCTAVE
            turns=[turn],
        )

        save_debate_state(room, tmp_path)

        # Both files should exist
        json_file = tmp_path / "2026-01-08-integration-test.json"
        octave_file = tmp_path / "2026-01-08-integration-test.oct.md"

        assert json_file.exists()
        assert octave_file.exists()

    def test_save_octave_mode_false_creates_only_json(self, tmp_path: Path) -> None:
        """Test that save creates only .json when octave_mode=False."""
        turn = Turn(
            role="Wind",
            content="Test proposal",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            previous_hash=None,
            cognition="PATHOS",
        )

        room = DebateRoom(
            thread_id="2026-01-08-json-only",
            topic="JSON only test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            octave_mode=False,  # Disable OCTAVE
            turns=[turn],
        )

        save_debate_state(room, tmp_path)

        # Only JSON file should exist
        json_file = tmp_path / "2026-01-08-json-only.json"
        octave_file = tmp_path / "2026-01-08-json-only.oct.md"

        assert json_file.exists()
        assert not octave_file.exists()

    def test_load_always_uses_json(self, tmp_path: Path) -> None:
        """Test that load always reads from JSON (primary storage)."""
        turn = Turn(
            role="Wind",
            content="Test proposal",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            previous_hash=None,
            cognition="PATHOS",
        )

        room = DebateRoom(
            thread_id="2026-01-08-load-test",
            topic="Load test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            octave_mode=True,
            turns=[turn],
        )

        save_debate_state(room, tmp_path)

        # Load should read from JSON
        loaded = load_debate_state("2026-01-08-load-test", tmp_path)

        assert loaded.thread_id == room.thread_id
        assert loaded.topic == room.topic
        assert len(loaded.turns) == 1
        assert loaded.turns[0].content == "Test proposal"

    def test_octave_file_is_human_readable(self, tmp_path: Path) -> None:
        """Test that .oct.md file is human-readable."""
        turn = Turn(
            role="Wind",
            content="Should we use OCTAVE format?",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            previous_hash=None,
            cognition="PATHOS",
        )

        room = DebateRoom(
            thread_id="2026-01-08-readable",
            topic="OCTAVE readability",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            octave_mode=True,
            turns=[turn],
        )

        save_debate_state(room, tmp_path)

        # Read OCTAVE file
        octave_file = tmp_path / "2026-01-08-readable.oct.md"
        content = octave_file.read_text()

        # Verify human-readable format
        assert "META::" in content
        assert "thread_id::" in content
        assert "TURNS::[" in content
        assert "Wind[PATHOS]" in content
        assert "Should we use OCTAVE format?" in content

    def test_backward_compatibility_json_only(self, tmp_path: Path) -> None:
        """Test that existing JSON-only storage continues to work."""
        # Create room with octave_mode=False
        turn = Turn(
            role="Wind",
            content="Legacy test",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            previous_hash=None,
            cognition="PATHOS",
        )

        room = DebateRoom(
            thread_id="2026-01-08-legacy",
            topic="Legacy compatibility",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            octave_mode=False,  # Old behavior
            turns=[turn],
        )

        save_debate_state(room, tmp_path)
        loaded = load_debate_state("2026-01-08-legacy", tmp_path)

        # Should load successfully
        assert loaded.thread_id == room.thread_id
        assert loaded.octave_mode is False
        assert len(loaded.turns) == 1
