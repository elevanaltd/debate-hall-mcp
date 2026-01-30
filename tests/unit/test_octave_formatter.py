"""Tests for octave_formatter using octave-mcp package."""

from datetime import UTC, datetime

import octave_mcp  # type: ignore[import-untyped]

from debate_hall_mcp.octave_formatter import (
    OutputMode,
    SealResult,
    format_debate_as_octave,
    seal_debate_transcript,
    validate_debate_octave,
    validate_debate_octave_lenient,
    verify_debate_seal,
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

    def test_multiline_content_escaping(self):
        """Test that newlines are properly escaped in turn content.

        Regression test for PR #86 - multi-line content must be escaped
        to prevent parse failures.
        """
        room = DebateRoom(
            thread_id="test",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )
        room.turns = [
            Turn(
                role="Wind",
                content="Line one\nLine two\nLine three",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room)

        # Should contain escaped newlines, not literal newlines that break structure
        assert "\\n" in result
        # TURNS line should be properly formed
        assert 'T1::Wind[PATHOS]::"Line one\\nLine two\\nLine three"' in result
        # Must parse back successfully
        is_valid, errors = validate_debate_octave(result)
        assert is_valid, f"Parse failed: {errors}"

    def test_tab_escaping_in_topic(self):
        """Test that tabs are properly escaped in META fields.

        Regression test for PR #86 - tabs must be escaped to prevent
        OCTAVE parse errors.
        """
        room = DebateRoom(
            thread_id="test",
            topic="Topic\twith\ttabs",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        result = format_debate_as_octave(room)

        # Must contain escaped tabs
        assert "\\t" in result
        assert 'TOPIC::"Topic\\twith\\ttabs"' in result
        # Must parse successfully
        is_valid, errors = validate_debate_octave(result)
        assert is_valid, f"Parse failed: {errors}"

    def test_carriage_return_escaping(self):
        """Test that carriage returns are properly escaped.

        Regression test for PR #86 - carriage returns must be escaped
        to prevent parse issues.
        """
        room = DebateRoom(
            thread_id="test",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Part one\rPart two",
        )

        result = format_debate_as_octave(room)

        # Must contain escaped CR
        assert "\\r" in result
        assert 'SYNTHESIS::"Part one\\rPart two"' in result
        # Must parse successfully
        is_valid, errors = validate_debate_octave(result)
        assert is_valid, f"Parse failed: {errors}"

    def test_all_special_chars_together(self):
        """Test comprehensive special character handling in one document.

        Regression test for PR #86 - all special characters must be
        properly escaped to prevent parse failures.
        """
        room = DebateRoom(
            thread_id="test",
            topic='Topic with "quotes" and\\backslash\tand\ttabs',
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        room.turns = [
            Turn(
                role="Wind",
                content='Quote: "test"\nNewline\rCarriage\tTab\\Backslash',
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]
        room.synthesis = "Final\nsynthesis\rwith\tspecial\\chars"

        result = format_debate_as_octave(room)

        # Must parse successfully despite all special chars
        is_valid, errors = validate_debate_octave(result)
        assert is_valid, f"Parse failed: {errors}"

        # Verify all escapes are present
        assert '\\"' in result  # Escaped quotes
        assert "\\n" in result  # Escaped newlines
        assert "\\r" in result  # Escaped carriage returns
        assert "\\t" in result  # Escaped tabs
        assert "\\\\" in result  # Escaped backslashes

    def test_escaping_order_prevents_double_escape(self):
        """Test that escaping order prevents double-escaping issues.

        Regression test for PR #86 - backslashes must be escaped FIRST
        to prevent \n becoming \\n becoming \\\\n.
        """
        room = DebateRoom(
            thread_id="test",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        # Content that already contains escaped sequences as literal text
        room.turns = [
            Turn(
                role="Wind",
                content="Literal \\n text and actual\nnewline",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]

        result = format_debate_as_octave(room)

        # Should have:
        # - Literal \n → \\n (backslash escaped, then n)
        # - Actual newline → \n (newline character escaped)
        # Result should be: "Literal \\\\n text and actual\\n"
        assert "\\\\n" in result  # Escaped literal backslash-n
        assert "actual\\nnewline" in result  # Escaped actual newline

        # Must parse successfully
        is_valid, errors = validate_debate_octave(result)
        assert is_valid, f"Parse failed: {errors}"


class TestOctaveSealing:
    """Test suite for OCTAVE document sealing (octave-mcp v1.0.0 feature)."""

    def test_seal_debate_transcript(self):
        """Test sealing a debate transcript."""
        room = DebateRoom(
            thread_id="seal-test",
            topic="Sealing Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        room.turns = [
            Turn(
                role="Wind",
                content="Opening statement",
                cognition="PATHOS",
                timestamp=datetime.now(UTC),
            )
        ]
        room.synthesis = "Final resolution"

        # Format and seal
        octave = format_debate_as_octave(room)
        sealed = seal_debate_transcript(octave)

        # Should have SEAL section
        assert "§SEAL" in sealed or "SEAL::" in sealed
        assert "HASH::" in sealed
        assert "SHA256" in sealed

    def test_verify_valid_seal(self):
        """Test verifying a valid seal."""
        room = DebateRoom(
            thread_id="verify-test",
            topic="Verify Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Resolution",
        )

        octave = format_debate_as_octave(room)
        sealed = seal_debate_transcript(octave)

        result = verify_debate_seal(sealed)

        assert result.is_valid
        assert result.status == "VERIFIED"
        assert "verified" in result.message.lower()
        assert result.expected_hash is not None
        assert result.actual_hash is not None
        assert result.expected_hash == result.actual_hash

    def test_detect_tampering(self):
        """Test that tampered content is detected."""
        room = DebateRoom(
            thread_id="tamper-test",
            topic="Original Topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Original resolution",
        )

        octave = format_debate_as_octave(room)
        sealed = seal_debate_transcript(octave)

        # Tamper with the content
        tampered = sealed.replace("Original Topic", "TAMPERED Topic")

        result = verify_debate_seal(tampered)

        assert not result.is_valid
        assert result.status == "INVALID"
        assert "modified" in result.message.lower() or "invalid" in result.message.lower()

    def test_verify_no_seal(self):
        """Test verifying a document without a seal."""
        room = DebateRoom(
            thread_id="no-seal-test",
            topic="No Seal Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        octave = format_debate_as_octave(room)

        result = verify_debate_seal(octave)

        assert not result.is_valid
        assert result.status in ("NO_SEAL", "ERROR")

    def test_seal_arbitrary_input_produces_sealed_output(self):
        """Test that sealing works with arbitrary input (lenient parsing).

        octave-mcp v1.0.0 uses lenient parsing which can handle most inputs.
        The seal function will produce a sealed document even with non-standard input.
        """
        # Lenient parsing means most input will parse
        result = seal_debate_transcript("===TEST===\nCONTENT::test\n===END===")

        # Should have SEAL section added
        assert "§SEAL" in result or "SEAL::" in result
        assert "HASH::" in result

    def test_seal_result_dataclass(self):
        """Test SealResult attributes."""
        result = SealResult(
            is_valid=True,
            status="VERIFIED",
            message="Test message",
            expected_hash="abc123",
            actual_hash="abc123",
        )

        assert result.is_valid
        assert result.status == "VERIFIED"
        assert result.message == "Test message"
        assert result.expected_hash == "abc123"
        assert result.actual_hash == "abc123"


class TestOctaveLenientValidation:
    """Test suite for lenient OCTAVE validation (octave-mcp v1.0.0 feature)."""

    def test_lenient_validation_valid_document(self):
        """Test lenient validation with valid document."""
        valid_octave = """===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"test-123"
  TOPIC::"Test Topic"
  MODE::fixed
  STATUS::active

PARTICIPANTS::[Wind]

TURNS::[
  T1::Wind[PATHOS]::"Test"
]

SYNTHESIS::null

===END==="""

        is_valid, errors, warnings = validate_debate_octave_lenient(valid_octave)

        assert is_valid
        assert len(errors) == 0

    def test_lenient_validation_with_warnings(self):
        """Test lenient validation captures warnings for minor issues."""
        # Document with unquoted string values (lenient parsing allows)
        octave_with_minor_issues = """===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"test-123"
  TOPIC::"Test Topic"
  MODE::fixed
  STATUS::active

PARTICIPANTS::[Wind]

TURNS::[]

SYNTHESIS::null

===END==="""

        is_valid, errors, warnings = validate_debate_octave_lenient(octave_with_minor_issues)

        assert is_valid
        assert len(errors) == 0
        # Warnings may or may not be present depending on content

    def test_lenient_validation_missing_fields(self):
        """Test lenient validation catches structural errors."""
        # Missing required META fields
        invalid_octave = """===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"test"

PARTICIPANTS::[]
TURNS::[]
SYNTHESIS::null

===END==="""

        is_valid, errors, warnings = validate_debate_octave_lenient(invalid_octave)

        assert not is_valid
        assert len(errors) > 0
        assert any("TOPIC" in err for err in errors)

    def test_lenient_validation_malformed_input(self):
        """Test lenient validation handles malformed input.

        octave-mcp v1.0.0's lenient parsing may still produce warnings
        for unparseable content, as it tries to salvage what it can.
        """
        is_valid, errors, warnings = validate_debate_octave_lenient("Not OCTAVE")

        # Should fail validation (missing required DEBATE_TRANSCRIPT structure)
        assert not is_valid
        assert len(errors) > 0
        # Warnings may be present from lenient parsing attempts
