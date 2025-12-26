"""Tests for debate_get tool - unified read operation.

Consolidates test coverage from test_status.py and test_next.py.
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


class TestDebateGetBasic:
    """Basic get operations (status-like behavior)."""

    def test_debate_get_new_debate(self, tmp_path: Path) -> None:
        """Get returns state for new debate."""
        debate_init(
            thread_id="test-get-1",
            topic="Test topic",
            mode="fixed",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="test-get-1", state_dir=tmp_path)

        assert result["thread_id"] == "test-get-1"
        assert result["topic"] == "Test topic"
        assert result["mode"] == "fixed"
        assert result["status"] == "active"
        assert result["turn_count"] == 0
        assert result["next_role"] == "Wind"
        assert "transcript" not in result  # Not requested

    def test_debate_get_with_turns(self, tmp_path: Path) -> None:
        """Get reflects turn count after turns added."""
        debate_init(
            thread_id="test-get-2",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="test-get-2",
            role="Wind",
            content="Wind content",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="test-get-2", state_dir=tmp_path)

        assert result["turn_count"] == 1
        assert result["next_role"] == "Wall"

    def test_debate_get_closed_debate_includes_synthesis(self, tmp_path: Path) -> None:
        """Get includes synthesis for closed debates."""
        debate_init(
            thread_id="test-get-3",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_close(
            thread_id="test-get-3",
            synthesis="Final synthesis",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="test-get-3", state_dir=tmp_path)

        assert result["status"] == "synthesis"
        assert result["synthesis"] == "Final synthesis"
        assert result["next_role"] is None

    def test_debate_get_thread_not_found(self, tmp_path: Path) -> None:
        """Get raises FileNotFoundError for missing thread."""
        with pytest.raises(FileNotFoundError):
            debate_get(thread_id="nonexistent", state_dir=tmp_path)

    def test_debate_get_mediated_mode(self, tmp_path: Path) -> None:
        """Get returns None for next_role in mediated mode."""
        debate_init(
            thread_id="test-get-4",
            topic="Test",
            mode="mediated",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="test-get-4", state_dir=tmp_path)

        assert result["mode"] == "mediated"
        assert result["next_role"] is None


class TestDebateGetWithTranscript:
    """Transcript inclusion (next-like behavior)."""

    def test_debate_get_with_transcript(self, tmp_path: Path) -> None:
        """Get includes transcript when requested."""
        debate_init(
            thread_id="test-transcript-1",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="test-transcript-1",
            role="Wind",
            content="Wind says hello",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="test-transcript-1",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert "transcript" in result
        assert len(result["transcript"]) == 1
        assert result["transcript"][0]["role"] == "Wind"
        assert result["transcript"][0]["content"] == "Wind says hello"
        assert "timestamp" in result["transcript"][0]

    def test_debate_get_transcript_context_lines(self, tmp_path: Path) -> None:
        """context_lines limits transcript depth."""
        debate_init(
            thread_id="test-context-1",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        # Add 3 turns
        for role in ["Wind", "Wall", "Door"]:
            debate_turn(
                thread_id="test-context-1",
                role=role,
                content=f"{role} content",
                state_dir=tmp_path,
            )

        result = debate_get(
            thread_id="test-context-1",
            include_transcript=True,
            context_lines=2,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 2
        assert result["transcript"][0]["role"] == "Wall"
        assert result["transcript"][1]["role"] == "Door"

    def test_debate_get_empty_transcript(self, tmp_path: Path) -> None:
        """Transcript is empty list for new debate."""
        debate_init(
            thread_id="test-empty-1",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="test-empty-1",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert result["transcript"] == []

    def test_debate_get_includes_limits(self, tmp_path: Path) -> None:
        """Get always includes max_turns and max_rounds."""
        debate_init(
            thread_id="test-limits-1",
            topic="Test",
            max_turns=20,
            max_rounds=5,
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="test-limits-1", state_dir=tmp_path)

        assert result["max_turns"] == 20
        assert result["max_rounds"] == 5
