"""Tests for octave_mode feature (Issue #26).

TDD Discipline: RED phase - these tests should FAIL until implementation.

octave_mode enables OCTAVE-mode debates where:
- Skills-based compression is expected
- Output defaults to OCTAVE format on close

Feature flow:
1. init_debate(octave_mode=True) creates room with flag set
2. get_debate returns octave_mode in response
3. close_debate uses "octave" output default when octave_mode=True
4. Explicit output_format overrides octave_mode default
"""

import json
from pathlib import Path

from debate_hall_mcp.state import DebateMode, DebateRoom


class TestDebateRoomOctaveMode:
    """Test octave_mode field on DebateRoom model."""

    def test_debate_room_octave_mode_defaults_to_true(self) -> None:
        """octave_mode should default to True for OCTAVE-first output."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
        )
        assert room.octave_mode is True

    def test_debate_room_octave_mode_can_be_set_true(self) -> None:
        """octave_mode can be explicitly set to True."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
            octave_mode=True,
        )
        assert room.octave_mode is True

    def test_debate_room_octave_mode_serializes_correctly(self) -> None:
        """octave_mode should be included in JSON serialization."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
            octave_mode=True,
        )
        data = json.loads(room.model_dump_json())
        assert "octave_mode" in data
        assert data["octave_mode"] is True

    def test_debate_room_octave_mode_deserializes_correctly(self) -> None:
        """octave_mode should be parsed from JSON correctly."""
        data = {
            "thread_id": "2025-01-01-test",
            "topic": "Test topic",
            "mode": "fixed",
            "octave_mode": True,
        }
        room = DebateRoom.model_validate(data)
        assert room.octave_mode is True

    def test_debate_room_backward_compatible_without_octave_mode(self) -> None:
        """Existing debates without octave_mode should deserialize with default True."""
        data = {
            "thread_id": "2025-01-01-test",
            "topic": "Test topic",
            "mode": "fixed",
            # No octave_mode field - simulating old debate data
        }
        room = DebateRoom.model_validate(data)
        assert room.octave_mode is True


class TestInitDebateOctaveMode:
    """Test octave_mode parameter in init_debate."""

    def test_init_debate_octave_mode_defaults_to_true(self, tmp_path: Path) -> None:
        """init_debate without octave_mode should default to True."""
        from debate_hall_mcp.tools.init import debate_init

        result = debate_init(
            thread_id="2025-01-01-test-octave-1",
            topic="Test topic",
            state_dir=tmp_path,
        )

        assert "octave_mode" in result
        assert result["octave_mode"] is True

        # Verify in state file
        state_file = tmp_path / "2025-01-01-test-octave-1.json"
        with open(state_file) as f:
            state_data = json.load(f)
        assert state_data["octave_mode"] is True

    def test_init_debate_octave_mode_can_be_set_true(self, tmp_path: Path) -> None:
        """init_debate with octave_mode=True should set the flag."""
        from debate_hall_mcp.tools.init import debate_init

        result = debate_init(
            thread_id="2025-01-01-test-octave-2",
            topic="Test topic",
            octave_mode=True,
            state_dir=tmp_path,
        )

        assert result["octave_mode"] is True

        # Verify in state file
        state_file = tmp_path / "2025-01-01-test-octave-2.json"
        with open(state_file) as f:
            state_data = json.load(f)
        assert state_data["octave_mode"] is True


class TestGetDebateOctaveMode:
    """Test octave_mode in get_debate response."""

    def test_get_debate_returns_octave_mode_false(self, tmp_path: Path) -> None:
        """get_debate should return octave_mode=False for non-octave debates."""
        from debate_hall_mcp.tools.get import debate_get
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-get-octave-1",
            topic="Test",
            octave_mode=False,
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-get-octave-1",
            state_dir=tmp_path,
        )

        assert "octave_mode" in result
        assert result["octave_mode"] is False

    def test_get_debate_returns_octave_mode_true(self, tmp_path: Path) -> None:
        """get_debate should return octave_mode=True for octave debates."""
        from debate_hall_mcp.tools.get import debate_get
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-get-octave-2",
            topic="Test",
            octave_mode=True,
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-get-octave-2",
            state_dir=tmp_path,
        )

        assert "octave_mode" in result
        assert result["octave_mode"] is True


class TestCloseDebateOctaveMode:
    """Test octave_mode affects close_debate output format default."""

    def test_close_debate_octave_mode_false_defaults_to_json(self, tmp_path: Path) -> None:
        """When octave_mode=False, close_debate defaults to JSON output."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-close-octave-1",
            topic="Test",
            octave_mode=False,
            state_dir=tmp_path,
        )

        result = debate_close(
            thread_id="2025-01-01-test-close-octave-1",
            synthesis="Final synthesis",
            state_dir=tmp_path,
            # output_format not specified - should default based on octave_mode
        )

        # Should return dict (JSON format)
        assert isinstance(result, dict)
        assert result["status"] == "synthesis"

    def test_close_debate_octave_mode_true_defaults_to_octave(self, tmp_path: Path) -> None:
        """When octave_mode=True, close_debate defaults to OCTAVE output."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-close-octave-2",
            topic="Test",
            octave_mode=True,
            state_dir=tmp_path,
        )

        result = debate_close(
            thread_id="2025-01-01-test-close-octave-2",
            synthesis="Final synthesis",
            state_dir=tmp_path,
            # output_format not specified - should default to "octave" because octave_mode=True
        )

        # Should return string (OCTAVE format)
        assert isinstance(result, str)
        assert "===DEBATE_TRANSCRIPT===" in result or "META::" in result

    def test_close_debate_explicit_json_overrides_octave_mode(self, tmp_path: Path) -> None:
        """Explicit output_format='json' overrides octave_mode=True."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-close-octave-3",
            topic="Test",
            octave_mode=True,
            state_dir=tmp_path,
        )

        result = debate_close(
            thread_id="2025-01-01-test-close-octave-3",
            synthesis="Final synthesis",
            state_dir=tmp_path,
            output_format="json",  # Explicit override
        )

        # Should return dict despite octave_mode=True
        assert isinstance(result, dict)
        assert result["status"] == "synthesis"

    def test_close_debate_explicit_octave_works_without_octave_mode(self, tmp_path: Path) -> None:
        """Explicit output_format='octave' works even with octave_mode=False."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-close-octave-4",
            topic="Test",
            octave_mode=False,
            state_dir=tmp_path,
        )

        result = debate_close(
            thread_id="2025-01-01-test-close-octave-4",
            synthesis="Final synthesis",
            state_dir=tmp_path,
            output_format="octave",  # Explicit octave
        )

        # Should return string (OCTAVE format)
        assert isinstance(result, str)

    def test_close_debate_explicit_both_overrides_octave_mode(self, tmp_path: Path) -> None:
        """Explicit output_format='both' overrides octave_mode default."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-test-close-octave-5",
            topic="Test",
            octave_mode=True,
            state_dir=tmp_path,
        )

        result = debate_close(
            thread_id="2025-01-01-test-close-octave-5",
            synthesis="Final synthesis",
            state_dir=tmp_path,
            output_format="both",  # Explicit override
        )

        # Should return dict with both formats
        assert isinstance(result, dict)
        assert "json" in result
        assert "octave" in result
