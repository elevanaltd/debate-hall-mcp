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
            thread_id="2025-01-01-test-get-1",
            topic="Test topic",
            mode="fixed",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-test-get-1", state_dir=tmp_path)

        assert result["thread_id"] == "2025-01-01-test-get-1"
        assert result["topic"] == "Test topic"
        assert result["mode"] == "fixed"
        assert result["status"] == "active"
        assert result["turn_count"] == 0
        assert result["next_role"] == "Wind"
        assert "transcript" not in result  # Not requested

    def test_debate_get_with_turns(self, tmp_path: Path) -> None:
        """Get reflects turn count after turns added."""
        debate_init(
            thread_id="2025-01-01-test-get-2",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-get-2",
            role="Wind",
            content="Wind content",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-test-get-2", state_dir=tmp_path)

        assert result["turn_count"] == 1
        assert result["next_role"] == "Wall"

    def test_debate_get_closed_debate_includes_synthesis(self, tmp_path: Path) -> None:
        """Get includes synthesis for closed debates."""
        debate_init(
            thread_id="2025-01-01-test-get-3",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_close(
            thread_id="2025-01-01-test-get-3",
            synthesis="Final synthesis",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-test-get-3", state_dir=tmp_path)

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
            thread_id="2025-01-01-test-get-4",
            topic="Test",
            mode="mediated",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-test-get-4", state_dir=tmp_path)

        assert result["mode"] == "mediated"
        assert result["next_role"] is None


class TestDebateGetWithTranscript:
    """Transcript inclusion (next-like behavior)."""

    def test_debate_get_with_transcript(self, tmp_path: Path) -> None:
        """Get includes transcript when requested."""
        debate_init(
            thread_id="2025-01-01-test-transcript-1",
            topic="Test",
            mode="fixed",
            octave_preamble=False,  # Disable to test core transcript
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-transcript-1",
            role="Wind",
            content="Wind says hello",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-transcript-1",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert "transcript" in result
        assert len(result["transcript"]) == 1
        assert result["transcript"][0]["role"] == "Wind"
        assert result["transcript"][0]["content"] == "Wind says hello"
        assert "timestamp" in result["transcript"][0]

    def test_debate_get_transcript_context_turns(self, tmp_path: Path) -> None:
        """context_turns limits transcript depth and adds omission indicator."""
        debate_init(
            thread_id="2025-01-01-test-context-1",
            topic="Test",
            mode="fixed",
            octave_preamble=False,  # Disable to test context_turns logic
            state_dir=tmp_path,
        )
        # Add 3 turns
        for role in ["Wind", "Wall", "Door"]:
            debate_turn(
                thread_id="2025-01-01-test-context-1",
                role=role,
                content=f"{role} content",
                state_dir=tmp_path,
            )

        result = debate_get(
            thread_id="2025-01-01-test-context-1",
            include_transcript=True,
            context_turns=2,
            state_dir=tmp_path,
        )

        # With context_turns=2, we get: System omission message + 2 turns
        assert len(result["transcript"]) == 3
        assert result["transcript"][0]["role"] == "System"
        assert "1 earlier turns omitted" in result["transcript"][0]["content"]
        assert result["transcript"][1]["role"] == "Wall"
        assert result["transcript"][2]["role"] == "Door"

    def test_debate_get_empty_transcript(self, tmp_path: Path) -> None:
        """Transcript is empty list for new debate (with preamble disabled)."""
        debate_init(
            thread_id="2025-01-01-test-empty-1",
            topic="Test",
            mode="fixed",
            octave_preamble=False,  # Disable to test empty state
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-empty-1",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert result["transcript"] == []

    def test_debate_get_includes_limits(self, tmp_path: Path) -> None:
        """Get always includes max_turns and max_rounds."""
        debate_init(
            thread_id="2025-01-01-test-limits-1",
            topic="Test",
            max_turns=20,
            max_rounds=5,
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-test-limits-1", state_dir=tmp_path)

        assert result["max_turns"] == 20
        assert result["max_rounds"] == 5


class TestDebateGetOctavePreamble:
    """Tests for OCTAVE preamble in transcript (view-layer only)."""

    def test_octave_preamble_prepended_when_enabled(self, tmp_path: Path) -> None:
        """Preamble is prepended to transcript when octave_preamble=True."""
        debate_init(
            thread_id="2025-01-01-test-preamble-1",
            topic="Test",
            mode="fixed",
            octave_preamble=True,  # Explicit (also default)
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-preamble-1",
            role="Wind",
            content="Test content",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-preamble-1",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 2
        assert result["transcript"][0]["role"] == "System"
        # Uses official octave-literacy-primer from octave-mcp v1.0.0
        content = result["transcript"][0]["content"]
        assert "===OCTAVE_LITERACY_PRIMER===" in content or "===PROTOCOL===" in content
        assert "===END===" in content
        assert result["transcript"][1]["role"] == "Wind"

    def test_octave_preamble_not_present_when_disabled(self, tmp_path: Path) -> None:
        """Preamble is NOT added when octave_preamble=False."""
        debate_init(
            thread_id="2025-01-01-test-preamble-2",
            topic="Test",
            mode="fixed",
            octave_preamble=False,
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-preamble-2",
            role="Wind",
            content="Test content",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-preamble-2",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 1
        assert result["transcript"][0]["role"] == "Wind"

    def test_octave_preamble_appears_for_empty_debate(self, tmp_path: Path) -> None:
        """Preamble appears even with no turns when enabled."""
        debate_init(
            thread_id="2025-01-01-test-preamble-3",
            topic="Test",
            mode="fixed",
            octave_preamble=True,
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-preamble-3",
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 1
        assert result["transcript"][0]["role"] == "System"

    def test_octave_preamble_not_included_without_transcript(self, tmp_path: Path) -> None:
        """Preamble is NOT added when include_transcript=False."""
        debate_init(
            thread_id="2025-01-01-test-preamble-4",
            topic="Test",
            mode="fixed",
            octave_preamble=True,
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-preamble-4",
            include_transcript=False,
            state_dir=tmp_path,
        )

        assert "transcript" not in result


class TestDebateGetWithMetadata:
    """Tests for speaker metadata in transcript (Issue #4)."""

    def test_transcript_includes_metadata_fields(self, tmp_path: Path) -> None:
        """Transcript entries include agent_role, model, cognition."""
        debate_init(
            thread_id="2025-01-01-test-metadata-1",
            topic="Test",
            mode="fixed",
            octave_preamble=False,
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-metadata-1",
            role="Wind",
            content="Wind content",
            agent_role="ideator",
            model="claude-opus-4-5-20251101",
            cognition="PATHOS",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-metadata-1",
            include_transcript=True,
            include_metadata=True,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 1
        turn_entry = result["transcript"][0]

        # Original fields preserved
        assert turn_entry["role"] == "Wind"
        assert turn_entry["content"] == "Wind content"
        assert "timestamp" in turn_entry

        # New metadata fields present
        assert turn_entry["agent_role"] == "ideator"
        assert turn_entry["model"] == "claude-opus-4-5-20251101"
        assert turn_entry["cognition"] == "PATHOS"

    def test_transcript_metadata_none_when_not_provided(self, tmp_path: Path) -> None:
        """Metadata fields are None when not provided (backward compatibility)."""
        debate_init(
            thread_id="2025-01-01-test-metadata-2",
            topic="Test",
            mode="mediated",
            octave_preamble=False,
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-metadata-2",
            role="Wall",
            content="Wall content",
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-metadata-2",
            include_transcript=True,
            include_metadata=True,
            state_dir=tmp_path,
        )

        turn_entry = result["transcript"][0]
        assert turn_entry["role"] == "Wall"
        assert turn_entry["agent_role"] is None
        assert turn_entry["model"] is None
        assert turn_entry["cognition"] is None

    def test_include_metadata_false_still_returns_cognition_and_token_output(
        self, tmp_path: Path
    ) -> None:
        """cognition and token_output are always included for VTP observability (#135).

        Regression test: include_metadata=False must still return cognition and
        token_output but NOT agent_role and model. This ensures the VTP
        injection pipeline always has access to token-counting data.
        """
        debate_init(
            thread_id="2025-01-01-test-vtp-metadata",
            topic="VTP observability test",
            mode="fixed",
            octave_preamble=False,
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2025-01-01-test-vtp-metadata",
            role="Wind",
            content="Wind observability content",
            agent_role="ideator",
            model="claude-opus-4-5-20251101",
            cognition="PATHOS",
            token_output=500,
            state_dir=tmp_path,
        )

        result = debate_get(
            thread_id="2025-01-01-test-vtp-metadata",
            include_transcript=True,
            include_metadata=False,
            state_dir=tmp_path,
        )

        assert len(result["transcript"]) == 1
        turn_entry = result["transcript"][0]

        # VTP fields always present (regardless of include_metadata)
        assert turn_entry["cognition"] == "PATHOS"
        assert turn_entry["token_output"] == 500

        # Identity metadata gated by include_metadata=False
        assert "agent_role" not in turn_entry
        assert "model" not in turn_entry

        # Standard fields always present
        assert turn_entry["role"] == "Wind"
        assert turn_entry["content"] == "Wind observability content"
        assert "timestamp" in turn_entry


class TestDebateGetContextTurns:
    """Tests for context_turns parameter."""

    def test_context_turns_limits_transcript_depth(self, tmp_path: Path) -> None:
        """context_turns limits transcript depth and adds omission indicator."""
        debate_init(
            thread_id="2025-01-01-test-turns-1",
            topic="Test",
            mode="fixed",
            octave_preamble=False,
            state_dir=tmp_path,
        )
        # Add 3 turns
        for role in ["Wind", "Wall", "Door"]:
            debate_turn(
                thread_id="2025-01-01-test-turns-1",
                role=role,
                content=f"{role} content",
                state_dir=tmp_path,
            )

        result = debate_get(
            thread_id="2025-01-01-test-turns-1",
            include_transcript=True,
            context_turns=2,
            state_dir=tmp_path,
        )

        # With context_turns=2, we get: System omission message + 2 turns
        assert len(result["transcript"]) == 3
        assert result["transcript"][0]["role"] == "System"
        assert "1 earlier turns omitted" in result["transcript"][0]["content"]
        assert result["transcript"][1]["role"] == "Wall"
        assert result["transcript"][2]["role"] == "Door"
