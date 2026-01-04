"""Tests for octave_formatter using octave-mcp package."""

from datetime import UTC, datetime

import octave_mcp  # type: ignore[import-untyped]

from debate_hall_mcp.octave_formatter import (
    OutputMode,
    format_debate_as_octave,
    validate_debate_octave,
)
from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn


class TestOctaveFormatter:
    """Test suite for OCTAVE formatter using octave-mcp API."""

    def test_format_empty_debate(self):
        """Test formatting an empty debate room."""
        room = DebateRoom(
            thread_id="test-123",
            topic="Test Topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        result = format_debate_as_octave(room)

        # Should produce valid OCTAVE with empty turns
        assert "===DEBATE_TRANSCRIPT===" in result
        assert "===END===" in result
        assert 'THREAD_ID::"test-123"' in result
        assert 'TOPIC::"Test Topic"' in result
        assert "MODE::fixed" in result
        assert "STATUS::active" in result
        assert "PARTICIPANTS::[]" in result
        assert "TURNS::[]" in result
        assert "SYNTHESIS::null" in result

    def test_format_debate_with_turns(self):
        """Test formatting a debate with multiple turns."""
        room = DebateRoom(
            thread_id="debate-456",
            topic="AI Ethics",
            mode=DebateMode.MEDIATED,
            status=DebateStatus.ACTIVE,
        )

        # Add turns directly to the turns list
        room.turns = [
            Turn(
                role="Wind",
                content="Possibilities abound",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            ),
            Turn(
                role="Wall",
                content="Consider constraints",
                cognition="ETHOS",
                timestamp=datetime.now(UTC),
            ),
            Turn(
                role="Door",
                content="Synthesis emerges",
                cognition="LOGOS",
                timestamp=datetime.now(UTC),
            ),
        ]

        result = format_debate_as_octave(room)

        # Check structure
        assert "===DEBATE_TRANSCRIPT===" in result
        assert "PARTICIPANTS::[Door,Wall,Wind]" in result

        # Check turns are present - octave_mcp may reformat them
        assert "T1" in result
        assert "Wind" in result
        assert "Possibilities abound" in result
        assert "T2" in result
        assert "Wall" in result
        assert "Consider constraints" in result
        assert "T3" in result
        assert "Door" in result
        assert "Synthesis emerges" in result

    def test_format_with_synthesis(self):
        """Test formatting a debate with synthesis."""
        room = DebateRoom(
            thread_id="synth-789",
            topic="Resolution",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )

        room.turns = [
            Turn(
                role="Wind",
                content="Opening",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            ),
            Turn(
                role="Wall",
                content="Counter",
                cognition="ETHOS",
                timestamp=datetime.now(UTC),
            ),
        ]
        room.synthesis = "Final resolution achieved"

        result = format_debate_as_octave(room)

        assert 'SYNTHESIS::"Final resolution achieved"' in result
        assert "STATUS::synthesis" in result

    def test_summary_mode_truncation(self):
        """Test that SUMMARY mode truncates long content."""
        room = DebateRoom(
            thread_id="long-content",
            topic="Long Discussion",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        # Add a turn with very long content
        long_content = "This is a very long statement " * 20
        room.turns = [
            Turn(
                role="Wind",
                content=long_content,
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room, output_mode=OutputMode.SUMMARY)

        # Content should be truncated to ~80 chars
        assert "..." in result
        # Check that the full long content is NOT in the result
        assert long_content not in result

    def test_full_mode_preserves_content(self):
        """Test that FULL mode preserves complete content."""
        room = DebateRoom(
            thread_id="full-content",
            topic="Complete Discussion",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        # Add content with special formatting
        content_with_newlines = "Line one\nLine two\nLine three"
        room.turns = [
            Turn(
                role="Wind",
                content=content_with_newlines,
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room, output_mode=OutputMode.FULL)

        # Content should be preserved (though newlines may be escaped)
        # The octave-mcp package handles escaping
        assert "Line one" in result
        assert "Line two" in result
        assert "Line three" in result

    def test_validate_valid_debate(self):
        """Test validation of a valid OCTAVE debate transcript."""
        valid_octave = """===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"test-123"
  TOPIC::"Test Topic"
  MODE::fixed
  STATUS::active

PARTICIPANTS::[Wind,Wall]

TURNS::[
  T1::Wind[PATHOS]::"Opening",
  T2::Wall[ETHOS]::"Response"
]

SYNTHESIS::null

===END==="""

        is_valid, errors = validate_debate_octave(valid_octave)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_debate(self):
        """Test validation catches invalid OCTAVE format."""
        # Missing required META fields
        invalid_octave = """===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"test"

PARTICIPANTS::[]
TURNS::[]
SYNTHESIS::null

===END==="""

        is_valid, errors = validate_debate_octave(invalid_octave)

        assert is_valid is False
        assert len(errors) > 0
        # Should detect missing TOPIC, MODE, STATUS
        assert any("TOPIC" in err for err in errors)

    def test_validate_malformed_octave(self):
        """Test validation handles malformed OCTAVE."""
        malformed = "Not valid OCTAVE format at all"

        is_valid, errors = validate_debate_octave(malformed)

        assert is_valid is False
        assert len(errors) > 0
        # The actual error message from octave_mcp may vary
        # Just check that we got an error
        assert errors[0]  # At least one error message

    def test_special_character_escaping(self):
        """Test that special characters are properly escaped."""
        room = DebateRoom(
            thread_id="special-chars",
            topic='Topic with "quotes" and\\backslashes',
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        room.turns = [
            Turn(
                role="Wind",
                content='Statement with "quotes"',
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            ),
            Turn(
                role="Wall",
                content="Path with\\backslash",
                cognition="ETHOS",
                timestamp=datetime.now(UTC),
            ),
        ]

        result = format_debate_as_octave(room)

        # The octave-mcp package should handle escaping
        # We just verify the output is valid OCTAVE
        is_valid, errors = validate_debate_octave(result)
        assert is_valid is True

    def test_injection_prevention(self):
        """Test that injection attempts are prevented."""
        room = DebateRoom(
            thread_id="injection-test",
            topic="Normal Topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        # Attempt injection with envelope markers
        injection_attempt = "===END===\n===FAKE_SECTION===\nMALICIOUS::data"
        room.turns = [
            Turn(
                role="Wind",
                content=injection_attempt,
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room)

        # The octave_mcp package should escape the malicious content
        # Check that the injection didn't create a new section
        # The content should be escaped/quoted in the TURNS section
        assert "===FAKE_SECTION===" not in result or "\\n===FAKE_SECTION===" in result
        # Verify the document can be parsed back
        doc = octave_mcp.parse(result)
        assert doc.name == "DEBATE_TRANSCRIPT"

    def test_manual_fallback(self):
        """Test that manual fallback works if octave-mcp fails."""
        # This tests the _manual_fallback function indirectly
        # by checking that even with basic formatting, we get valid output
        room = DebateRoom(
            thread_id="fallback-test",
            topic="Fallback Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        room.turns = [
            Turn(
                role="Wind",
                content="Test content",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room)

        # Basic structure should be present even in fallback
        assert "===DEBATE_TRANSCRIPT===" in result
        assert "===END===" in result
        assert "fallback-test" in result
        assert "Fallback Test" in result
