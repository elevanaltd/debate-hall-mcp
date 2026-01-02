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
    assert "===END===" in result  # Canonical OCTAVE uses ===END===


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


def test_compress_content_truncates_long_text_in_summary_mode() -> None:
    """Test that long content is truncated with ellipsis in SUMMARY mode."""
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    long_text = "A" * 200  # 200 characters

    # Explicit SUMMARY mode truncates content
    result = _compress_content(long_text, max_length=80, mode=OutputMode.SUMMARY)

    assert len(result) == 80
    assert result.endswith("...")


def test_compress_content_preserves_short_text() -> None:
    """Test that short content is not modified."""
    from debate_hall_mcp.octave_formatter import _compress_content

    short_text = "Short message"

    result = _compress_content(short_text)

    assert result == short_text


def test_compress_content_normalizes_whitespace_in_summary_mode() -> None:
    """Test that multiple whitespace is collapsed in SUMMARY mode only."""
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    text_with_whitespace = "Word1   Word2\n\nWord3\t\tWord4"

    # SUMMARY mode normalizes whitespace
    result = _compress_content(text_with_whitespace, mode=OutputMode.SUMMARY)

    assert result == "Word1 Word2 Word3 Word4"


def test_compress_content_preserves_whitespace_in_full_mode() -> None:
    """Test that whitespace is preserved in FULL mode (default)."""
    from debate_hall_mcp.octave_formatter import _compress_content

    text_with_whitespace = "Word1   Word2\n\nWord3\t\tWord4"

    # FULL mode (default) preserves whitespace
    result = _compress_content(text_with_whitespace)

    assert result == text_with_whitespace


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


def test_escape_handles_tabs() -> None:
    """Test that tabs are escaped (aligned with octave-mcp/core/emitter.py)."""
    from debate_hall_mcp.octave_formatter import _escape_octave_string

    text_with_tab = "Column1\tColumn2"

    result = _escape_octave_string(text_with_tab)

    # Tab should be escaped as \\t
    assert result == '"Column1\\tColumn2"'
    assert "\t" not in result


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


def test_format_debate_with_multiline_turn_content_full_mode() -> None:
    """Test that multiline turn content is preserved and escaped in FULL mode (default)."""
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

    # In FULL mode (default), newlines are PRESERVED but ESCAPED
    # The output should contain escaped newlines (\\n), not spaces
    assert "Point 1\\nPoint 2\\nPoint 3" in result

    # Find the specific turn line and verify it's properly formatted
    turn_lines = [line for line in result.split("\n") if "T1::Wind" in line]
    assert len(turn_lines) == 1
    # The turn line should contain the escaped content in quotes
    assert '"Point 1\\nPoint 2\\nPoint 3"' in turn_lines[0]


def test_format_debate_with_multiline_turn_content_summary_mode() -> None:
    """Test that multiline turn content is normalized in SUMMARY mode."""
    from debate_hall_mcp.octave_formatter import OutputMode, format_debate_as_octave

    room = DebateRoom(
        thread_id="2025-01-01-test-multiline-turn-summary",
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

    result = format_debate_as_octave(room, output_mode=OutputMode.SUMMARY)

    # In SUMMARY mode, newlines are NORMALIZED to spaces
    assert "Point 1 Point 2 Point 3" in result

    # Find the specific turn line and verify it's properly formatted
    turn_lines = [line for line in result.split("\n") if "T1::Wind" in line]
    assert len(turn_lines) == 1
    # The turn line should contain the space-separated content in quotes
    assert '"Point 1 Point 2 Point 3"' in turn_lines[0]


# =============================================================================
# Test: FULL mode preserves formatting (Issue #26 CE BLOCKING fix)
# =============================================================================


def test_full_mode_preserves_newlines_and_tabs() -> None:
    """Test that FULL mode preserves newlines and tabs verbatim.

    CE BLOCKING: FULL mode was destroying formatting by unconditionally
    normalizing whitespace (joining with single space).

    Expected: FULL mode should NOT normalize whitespace.
    """
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    # Content with newlines and tabs that should be preserved
    content_with_formatting = "Line 1\nLine 2\n\tIndented line\nLine 4"

    result = _compress_content(content_with_formatting, mode=OutputMode.FULL)

    # In FULL mode, newlines and tabs should be PRESERVED
    assert "\n" in result, "FULL mode must preserve newlines"
    assert "\t" in result, "FULL mode must preserve tabs"
    assert result == content_with_formatting, "FULL mode must return content verbatim"


def test_full_mode_preserves_code_block_indentation() -> None:
    """Test that FULL mode preserves code block indentation.

    CE BLOCKING: Code snippets, Markdown lists were flattened into single line.
    """
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    code_block = """def hello():
    print("Hello")
    return True"""

    result = _compress_content(code_block, mode=OutputMode.FULL)

    # Code block formatting must be preserved
    assert result == code_block
    assert "    print" in result  # Indentation preserved
    assert "\n" in result  # Newlines preserved


def test_summary_mode_still_normalizes_whitespace() -> None:
    """Test that SUMMARY mode continues to normalize whitespace.

    Backward compatibility: SUMMARY mode should collapse whitespace.
    """
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    text_with_whitespace = "Word1   Word2\n\nWord3\t\tWord4"

    result = _compress_content(text_with_whitespace, mode=OutputMode.SUMMARY)

    # SUMMARY mode should normalize whitespace
    assert result == "Word1 Word2 Word3 Word4"
    assert "\n" not in result
    assert "\t" not in result


def test_full_mode_content_escapes_properly_in_octave_output() -> None:
    """Test that preserved newlines in FULL mode are escaped in final OCTAVE output.

    Content flow: FULL mode preserves newlines -> _escape_octave_string escapes them
    The escaped newlines should appear as \\n in the final OCTAVE string.
    """
    from datetime import UTC, datetime

    from debate_hall_mcp.octave_formatter import (
        OutputMode,
        format_debate_as_octave,
    )
    from debate_hall_mcp.state import DebateMode, DebateRoom, Turn

    # Turn content with newlines that should be preserved then escaped
    multiline_content = "Point 1\nPoint 2\nPoint 3"
    room = DebateRoom(
        thread_id="2025-01-01-test-full-escape",
        topic="Test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content=multiline_content,
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
        ],
    )

    result = format_debate_as_octave(room, output_mode=OutputMode.FULL)

    # In FULL mode, newlines should be PRESERVED (not normalized to spaces)
    # But they should be ESCAPED as \\n in the final output
    # So we should see "Point 1\\nPoint 2\\nPoint 3" not "Point 1 Point 2 Point 3"
    assert (
        "Point 1\\nPoint 2\\nPoint 3" in result
    ), "Newlines should be escaped, not normalized to spaces"
    # Should NOT have the space-normalized version
    assert (
        "Point 1 Point 2 Point 3" not in result
    ), "FULL mode should NOT normalize newlines to spaces"


# =============================================================================
# Test: OutputMode enum and content preservation (Issue #26)
# =============================================================================


def test_output_mode_enum_exists() -> None:
    """Test that OutputMode enum is available with FULL and SUMMARY values.

    RED: This test should fail until OutputMode is implemented.
    """
    from debate_hall_mcp.octave_formatter import OutputMode

    # Verify enum values exist
    assert OutputMode.FULL is not None
    assert OutputMode.SUMMARY is not None
    # Verify they are distinct
    assert OutputMode.FULL != OutputMode.SUMMARY


def test_full_mode_preserves_complete_content() -> None:
    """Test that FULL mode preserves content verbatim (no truncation).

    RED: This test should fail until OutputMode and _compress_content changes are implemented.
    Agent-produced OCTAVE content should be preserved completely.
    """
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    # Content longer than 80 chars - should NOT be truncated in FULL mode
    long_content = "A" * 200

    result = _compress_content(long_content, mode=OutputMode.FULL)

    # In FULL mode, content should be preserved completely (only whitespace normalized)
    assert len(result) == 200
    assert result == long_content
    assert not result.endswith("...")


def test_summary_mode_truncates_content() -> None:
    """Test that SUMMARY mode truncates content to 80 chars with ellipsis.

    Provides backward compatibility for dashboard/summary use cases.
    """
    from debate_hall_mcp.octave_formatter import OutputMode, _compress_content

    long_content = "A" * 200

    result = _compress_content(long_content, mode=OutputMode.SUMMARY)

    # SUMMARY mode should truncate to 80 chars
    assert len(result) == 80
    assert result.endswith("...")


def test_compress_content_default_mode_is_full() -> None:
    """Test that default mode is FULL (preserves content).

    RED: This will fail until default is changed from current truncation behavior.
    """
    from debate_hall_mcp.octave_formatter import _compress_content

    long_content = "A" * 200

    # Call without mode parameter - should use FULL (preserve content)
    result = _compress_content(long_content)

    # Default should be FULL mode - no truncation
    assert len(result) == 200
    assert not result.endswith("...")


def test_format_debate_accepts_output_mode_parameter() -> None:
    """Test that format_debate_as_octave accepts optional output_mode parameter."""
    from debate_hall_mcp.octave_formatter import (
        OutputMode,
        format_debate_as_octave,
    )

    long_turn_content = "A" * 200
    room = DebateRoom(
        thread_id="2025-01-01-test-mode",
        topic="Test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content=long_turn_content,
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
        ],
    )

    # FULL mode should preserve complete content
    result_full = format_debate_as_octave(room, output_mode=OutputMode.FULL)
    assert ("A" * 200) in result_full

    # SUMMARY mode should truncate
    result_summary = format_debate_as_octave(room, output_mode=OutputMode.SUMMARY)
    assert ("A" * 77 + "...") in result_summary  # 80 total: 77 + 3 for ellipsis


# =============================================================================
# Test: Security - Envelope injection prevention (Issue #26)
# =============================================================================


def test_sanitize_value_exists() -> None:
    """Test that _sanitize_value function exists for security sanitization."""
    from debate_hall_mcp.octave_formatter import _sanitize_value

    # Basic test that function exists and returns string
    result = _sanitize_value("normal text")
    assert isinstance(result, str)


def test_sanitize_value_escapes_envelope_markers() -> None:
    """Test that envelope markers are escaped to prevent OCTAVE structure injection.

    Security: Malicious content like ===END=== could corrupt document structure.
    Pattern from octave-mcp/mcp/debate_convert.py.
    """
    from debate_hall_mcp.octave_formatter import _sanitize_value

    # Content containing envelope marker that could inject structure
    malicious_content = "Some text ===END=== more text"

    result = _sanitize_value(malicious_content)

    # Envelope marker should be escaped
    assert "===END===" not in result
    assert "ESCAPED_ENVELOPE_END" in result


def test_sanitize_value_escapes_multiple_envelope_markers() -> None:
    """Test that multiple envelope markers are all escaped."""
    from debate_hall_mcp.octave_formatter import _sanitize_value

    content = "===META=== injection ===DEBATE_TRANSCRIPT=== attack"

    result = _sanitize_value(content)

    assert "===META===" not in result
    assert "===DEBATE_TRANSCRIPT===" not in result
    assert "ESCAPED_ENVELOPE_META" in result
    assert "ESCAPED_ENVELOPE_DEBATE_TRANSCRIPT" in result


def test_sanitize_value_passes_through_newlines() -> None:
    """Test that _sanitize_value preserves newlines (escaping is done by _escape_octave_string).

    Note: Newline escaping was moved to _escape_octave_string to avoid double-escaping.
    _sanitize_value now focuses only on structural injection prevention (envelope markers).
    """
    from debate_hall_mcp.octave_formatter import _sanitize_value

    content = "Line 1\nLine 2\r\nLine 3"

    result = _sanitize_value(content)

    # Newlines should be PRESERVED by _sanitize_value
    # (escaping happens later in _escape_octave_string)
    assert "\n" in result
    assert "\r" in result
    assert result == content


def test_sanitize_value_handles_non_strings() -> None:
    """Test that _sanitize_value converts non-strings to strings."""
    from debate_hall_mcp.octave_formatter import _sanitize_value

    assert _sanitize_value(123) == "123"
    assert _sanitize_value(None) == "None"
    assert _sanitize_value(True) == "True"


def test_turn_content_is_sanitized_in_full_mode() -> None:
    """Test that turn content is sanitized for security even in FULL mode."""
    from debate_hall_mcp.octave_formatter import (
        OutputMode,
        format_debate_as_octave,
    )

    # Turn content with malicious envelope marker
    malicious_content = "My argument is ===END=== and more"
    room = DebateRoom(
        thread_id="2025-01-01-test-security",
        topic="Security test",
        mode=DebateMode.FIXED,
        turns=[
            Turn(
                role="Wind",
                content=malicious_content,
                timestamp=datetime.now(UTC),
                cognition="PATHOS",
            ),
        ],
    )

    result = format_debate_as_octave(room, output_mode=OutputMode.FULL)

    # The malicious envelope marker should be escaped
    assert "===END===" not in result.split("TURNS")[1].split("SYNTHESIS")[0]
    # The escaped version should be present
    assert "ESCAPED_ENVELOPE_END" in result
