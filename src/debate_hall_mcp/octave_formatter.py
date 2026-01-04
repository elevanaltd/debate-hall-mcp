"""OCTAVE format output using octave-mcp package.

Uses the official octave-mcp API for validated, secure OCTAVE format emission.

Implements I2 (Universal OCTAVE Binding) from North Star.
"""

from enum import Enum

try:
    import octave_mcp  # type: ignore[import-not-found]
except ImportError as e:
    raise ImportError(
        "octave-mcp package is required. Install with: pip install octave-mcp>=0.3.0"
    ) from e

from debate_hall_mcp.state import DebateRoom


class OutputMode(Enum):
    """Output mode for OCTAVE content formatting.

    FULL: Preserve complete content (default). Use for archival.
    SUMMARY: Truncate to 80 chars with ellipsis. Use for dashboards.
    """

    FULL = "full"
    SUMMARY = "summary"


def _compress_content(
    content: str,
    max_length: int = 80,
    mode: OutputMode = OutputMode.FULL,
) -> str:
    """Compress content for OCTAVE output.

    Args:
        content: Original content string
        max_length: Maximum length before truncation (only applies in SUMMARY mode)
        mode: OutputMode.FULL or OutputMode.SUMMARY

    Returns:
        Processed content string
    """
    if mode == OutputMode.FULL:
        return content

    # SUMMARY mode: normalize whitespace and truncate
    compressed = " ".join(content.split())
    if len(compressed) > max_length:
        compressed = compressed[: max_length - 3] + "..."

    return compressed


def format_debate_as_octave(
    room: DebateRoom,
    output_mode: OutputMode = OutputMode.FULL,
) -> str:
    """Generate OCTAVE format transcript from debate room using octave-mcp API.

    Args:
        room: DebateRoom instance with debate state
        output_mode: OutputMode.FULL or OutputMode.SUMMARY

    Returns:
        OCTAVE-formatted string representation
    """
    # Build the OCTAVE document manually as a string, then parse it
    lines = []

    # Header
    lines.append("===DEBATE_TRANSCRIPT===")
    lines.append("")

    # META section - escape special characters
    lines.append("META:")
    # Escape quotes and backslashes for OCTAVE format
    thread_id = room.thread_id.replace("\\", "\\\\").replace('"', '\\"')
    topic = room.topic.replace("\\", "\\\\").replace('"', '\\"')
    lines.append(f'  THREAD_ID::"{thread_id}"')
    lines.append(f'  TOPIC::"{topic}"')
    lines.append(f"  MODE::{room.mode.value}")
    lines.append(f"  STATUS::{room.status.value}")
    lines.append("")

    # PARTICIPANTS section
    if room.turns:
        participants = sorted({turn.role for turn in room.turns})
        lines.append(f"PARTICIPANTS::[{','.join(participants)}]")
    else:
        lines.append("PARTICIPANTS::[]")
    lines.append("")

    # TURNS section
    if room.turns:
        lines.append("TURNS::[")
        for i, turn in enumerate(room.turns, 1):
            # Compress content based on mode
            content = _compress_content(turn.content, mode=output_mode)
            # Escape special characters
            content = content.replace("\\", "\\\\").replace('"', '\\"')
            cognition = turn.cognition or "UNKNOWN"
            # Format turn with proper escaping
            lines.append(f'  T{i}::{turn.role}[{cognition}]::"{content}",')
        lines.append("]")
    else:
        lines.append("TURNS::[]")
    lines.append("")

    # SYNTHESIS section
    if room.synthesis:
        synthesis = room.synthesis.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'SYNTHESIS::"{synthesis}"')
    else:
        lines.append("SYNTHESIS::null")
    lines.append("")

    # Footer
    lines.append("===END===")

    # Construct the document string
    doc_str = "\n".join(lines)

    # Parse and re-emit to get canonical form with proper escaping
    doc = octave_mcp.parse(doc_str)
    return str(octave_mcp.emit(doc))


def validate_debate_octave(content: str) -> tuple[bool, list[str]]:
    """Validate OCTAVE-formatted debate transcript.

    Args:
        content: OCTAVE-formatted string to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        # Parse the document
        doc = octave_mcp.parse(content)

        # Check required structure
        errors = []

        if doc.name != "DEBATE_TRANSCRIPT":
            errors.append(f"Invalid document type: {doc.name}")

        # Check META fields
        if doc.meta:
            required_meta = ["THREAD_ID", "TOPIC", "MODE", "STATUS"]
            for field in required_meta:
                if field not in doc.meta:
                    errors.append(f"Missing META field: {field}")
        else:
            errors.append("Missing META section")

        # Check for required sections in assignments
        section_keys = []
        for section in doc.sections:
            if hasattr(section, "key"):
                section_keys.append(section.key)

        required_sections = ["PARTICIPANTS", "TURNS", "SYNTHESIS"]
        for section in required_sections:
            if section not in section_keys:
                errors.append(f"Missing required section: {section}")

        return (len(errors) == 0, errors)

    except Exception as e:
        return (False, [f"Parse error: {str(e)}"])
