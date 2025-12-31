"""Tests for OCTAVE formatter module (Issue #29).

TDD Discipline: RED -> GREEN -> REFACTOR
Immutables: I2 (Universal OCTAVE Binding)

Unit tests for the octave_formatter module that generates
compressed OCTAVE representation of debate state.
"""

from datetime import UTC, datetime

from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn

# =============================================================================
# Test: format_debate_as_octave basic output
# =============================================================================


def test_format_debate_as_octave_returns_string() -> None:
    """Test that formatter returns a string."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-001",
        topic="Test topic",
        mode=DebateMode.FIXED,
        status=DebateStatus.SYNTHESIS,
        synthesis="Final synthesis.",
    )

    result = format_debate_as_octave(room)

    assert isinstance(result, str)
    assert len(result) > 0


def test_format_debate_as_octave_contains_header_footer() -> None:
    """Test that output contains DEBATE_TRANSCRIPT markers."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-002",
        topic="Test topic",
        mode=DebateMode.FIXED,
    )

    result = format_debate_as_octave(room)

    assert "===DEBATE_TRANSCRIPT===" in result
    assert "===END_DEBATE_TRANSCRIPT===" in result


def test_format_debate_as_octave_contains_meta_fields() -> None:
    """Test that output contains all META fields."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-003",
        topic="Important debate topic",
        mode=DebateMode.MEDIATED,
        status=DebateStatus.ACTIVE,
    )

    result = format_debate_as_octave(room)

    assert "META:" in result
    assert 'THREAD_ID::"2025-01-01-test-003"' in result
    assert 'TOPIC::"Important debate topic"' in result
    assert "MODE::mediated" in result
    assert "STATUS::active" in result


def test_format_debate_as_octave_contains_participants() -> None:
    """Test that output lists participating roles."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-004",
        topic="Test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content="First turn",
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
            Turn(
                role="Wall",
                content="Second turn",
                timestamp=datetime.now(UTC),
                cognition="ETHOS",
            ),
        ],
    )

    result = format_debate_as_octave(room)

    assert "PARTICIPANTS::" in result
    assert "Wall" in result
    assert "Wind" in result


def test_format_debate_as_octave_contains_turns() -> None:
    """Test that output includes turn entries with role and cognition."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-005",
        topic="Test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content="Creative exploration",
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
            Turn(
                role="Door",
                content="Synthesis approach",
                timestamp=datetime.now(UTC),
                cognition="LOGOS",
            ),
        ],
    )

    result = format_debate_as_octave(room)

    assert "TURNS::" in result
    assert "Wind[PATHOS]" in result
    assert "Door[LOGOS]" in result


def test_format_debate_as_octave_contains_synthesis() -> None:
    """Test that output includes synthesis content."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    synthesis_text = "Final resolution with clear outcome."
    room = DebateRoom(
        thread_id="2025-01-01-test-006",
        topic="Test",
        mode=DebateMode.FIXED,
        status=DebateStatus.SYNTHESIS,
        synthesis=synthesis_text,
    )

    result = format_debate_as_octave(room)

    assert "SYNTHESIS::" in result
    assert synthesis_text in result


# =============================================================================
# Test: Content compression
# =============================================================================


def test_compress_content_truncates_long_text() -> None:
    """Test that long content is truncated with ellipsis."""
    from debate_hall_mcp.octave_formatter import _compress_content

    long_text = "A" * 200  # 200 characters

    result = _compress_content(long_text, max_length=80)

    assert len(result) == 80
    assert result.endswith("...")


def test_compress_content_preserves_short_text() -> None:
    """Test that short content is not modified."""
    from debate_hall_mcp.octave_formatter import _compress_content

    short_text = "Short message"

    result = _compress_content(short_text)

    assert result == short_text


def test_compress_content_normalizes_whitespace() -> None:
    """Test that multiple whitespace is collapsed."""
    from debate_hall_mcp.octave_formatter import _compress_content

    text_with_whitespace = "Word1   Word2\n\nWord3\t\tWord4"

    result = _compress_content(text_with_whitespace)

    assert result == "Word1 Word2 Word3 Word4"


# =============================================================================
# Test: Edge cases
# =============================================================================


def test_format_debate_as_octave_empty_turns() -> None:
    """Test formatting with no turns."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-007",
        topic="Empty debate",
        mode=DebateMode.FIXED,
    )

    result = format_debate_as_octave(room)

    assert "PARTICIPANTS::[]" in result
    assert "TURNS::[]" in result


def test_format_debate_as_octave_no_synthesis() -> None:
    """Test formatting with null synthesis."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-008",
        topic="No synthesis",
        mode=DebateMode.FIXED,
    )

    result = format_debate_as_octave(room)

    assert "SYNTHESIS::null" in result


def test_format_debate_as_octave_handles_quotes_in_topic() -> None:
    """Test that quotes in content are properly escaped."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-009",
        topic='Topic with "quotes" inside',
        mode=DebateMode.FIXED,
    )

    result = format_debate_as_octave(room)

    # Quotes should be escaped
    assert 'TOPIC::"Topic with \\"quotes\\" inside"' in result


# =============================================================================
# Test: Newline and special character escaping (Issue #29 - CRS BLOCKING fix)
# =============================================================================


def test_escape_handles_newlines() -> None:
    """Test that newlines are escaped to prevent line breaks in OCTAVE output.

    CRS BLOCKING: Raw newlines inside string values break line-structured format.
    """
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    text_with_newline = "Line one\nLine two"

    result = _escape_octave_string(text_with_newline)

    # Newline should be escaped as \\n (literal backslash-n in output)
    assert result == '"Line one\\nLine two"'
    # Must NOT contain actual newline character
    assert "\n" not in result


def test_escape_handles_carriage_returns() -> None:
    """Test that carriage returns are escaped."""
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    text_with_cr = "Line one\rLine two"

    result = _escape_octave_string(text_with_cr)

    # CR should be escaped as \\r
    assert result == '"Line one\\rLine two"'
    assert "\r" not in result


def test_escape_handles_backslashes() -> None:
    """Test that backslashes are escaped first to prevent double-escaping issues."""
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    text_with_backslash = "Path\\to\\file"

    result = _escape_octave_string(text_with_backslash)

    # Backslash should be escaped as \\
    assert result == '"Path\\\\to\\\\file"'


def test_escape_handles_multiline_synthesis() -> None:
    """Test multiline synthesis content is properly escaped.

    CRS BLOCKING: This is the primary failure case from Issue #29.
    Synthesis like "1. Step one\n2. Step two" must remain on single line.
    """
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    multiline_synthesis = "1. Step one\n2. Step two\n3. Step three"

    result = _escape_octave_string(multiline_synthesis)

    # Must be a single line with escaped newlines
    assert "\n" not in result
    assert result == '"1. Step one\\n2. Step two\\n3. Step three"'


def test_escape_handles_combined_special_chars() -> None:
    """Test escaping when multiple special characters are combined."""
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    # Combine backslash, newline, quote, and carriage return
    complex_text = 'Say "hello"\nPath: C:\\Users\r\n'

    result = _escape_octave_string(complex_text)

    # Verify no raw special characters remain
    assert "\n" not in result
    assert "\r" not in result
    # Backslashes should be doubled
    assert "\\\\Users" in result
    # Quotes should be escaped
    assert '\\"hello\\"' in result


def test_octave_output_is_single_line_per_field() -> None:
    """Test that each OCTAVE field outputs on exactly one line.

    CRS BLOCKING: OCTAVE format requires each field on its own line.
    Multiline content must be escaped to prevent format corruption.
    """
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    # Create room with multiline synthesis
    multiline_synthesis = "Step 1: Analysis\nStep 2: Decision\nStep 3: Action"
    room = DebateRoom(
        thread_id="2025-01-01-test-newline",
        topic="Multiline test",
        mode=DebateMode.FIXED,
        status=DebateStatus.SYNTHESIS,
        synthesis=multiline_synthesis,
    )

    result = format_debate_as_octave(room)

    # Find the SYNTHESIS line
    lines = result.split("\n")
    synthesis_lines = [line for line in lines if line.startswith("SYNTHESIS::")]

    # There should be exactly ONE synthesis line
    assert len(synthesis_lines) == 1

    # The synthesis line should contain escaped newlines, not raw newlines
    synthesis_line = synthesis_lines[0]
    assert "Step 1: Analysis\\nStep 2: Decision\\nStep 3: Action" in synthesis_line


def test_format_debate_with_multiline_turn_content() -> None:
    """Test that multiline turn content is handled via compression and escaping."""
    from debate_hall_mcp.octave_formatter import format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-multiline-turn",
        topic="Test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content="Point 1\nPoint 2\nPoint 3",
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
        ],
    )

    result = format_debate_as_octave(room)

    # Turn content with newlines should be compressed (newlines become spaces)
    # and the output should be valid line-structured OCTAVE format
    assert "Point 1 Point 2 Point 3" in result

    # Find the specific turn line and verify it's properly formatted
    turn_lines = [line for line in result.split("\n") if "T1::Wind" in line]
    assert len(turn_lines) == 1
    # The turn line should contain the compressed content in quotes
    assert '"Point 1 Point 2 Point 3"' in turn_lines[0]
