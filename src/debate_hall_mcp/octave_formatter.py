"""OCTAVE format output for debate transcripts (Issue #29).

Implements I2 (Universal OCTAVE Binding) from North Star.
Generates compressed OCTAVE representation of debate state.

Aligned with octave-mcp canonical format (see octave-mcp/core/emitter.py):
- Envelope: ===NAME=== ... ===END===
- Operator: :: (no whitespace)
- String escaping: \\ \" \\n \\t \\r

Format:
===DEBATE_TRANSCRIPT===
META:
  THREAD_ID::"..."
  TOPIC::"..."
  MODE::fixed|mediated
  STATUS::active|synthesis|...

PARTICIPANTS::[Wind,Wall,Door]

TURNS::[
  T1::Wind[PATHOS]::"...",
  T2::Wall[ETHOS]::"..."
]

SYNTHESIS::"..."
===END===
"""

import re
from enum import Enum
from typing import Any

from debate_hall_mcp.state import DebateRoom


class OutputMode(Enum):
    """Output mode for OCTAVE content formatting.

    FULL: Preserve complete content (default). Use for archival.
    SUMMARY: Truncate to 80 chars with ellipsis. Use for dashboards.
    """

    FULL = "full"
    SUMMARY = "summary"


def _sanitize_value(value: Any) -> str:
    """Sanitize untrusted strings to prevent OCTAVE structure injection.

    Prevents injection attacks where malicious input could:
    - Inject envelope markers (===XXX===) to create fake sections

    Note: Newline/CR escaping is handled by _escape_octave_string to avoid
    double-escaping. This function focuses only on structural injection prevention.

    Pattern adapted from octave-mcp/mcp/debate_convert.py.

    Args:
        value: Untrusted value from user input (will be converted to string if needed)

    Returns:
        Sanitized string safe for OCTAVE output

    Examples:
        >>> _sanitize_value("normal text")
        'normal text'
        >>> _sanitize_value("has===END===marker")
        'hasESCAPED_ENVELOPE_ENDmarker'
    """
    if not isinstance(value, str):
        return str(value)

    # Escape envelope markers (===XXX===) to prevent structure injection
    # Replace with visually similar but safe representation
    sanitized = re.sub(
        r"===([A-Z_]+)===",
        r"ESCAPED_ENVELOPE_\1",
        value,
    )

    return sanitized


def _compress_content(
    content: str,
    max_length: int = 80,
    mode: OutputMode = OutputMode.FULL,
) -> str:
    """Compress content for OCTAVE output.

    Semantic compression behavior depends on mode:
    - FULL mode (default): Preserve content verbatim (no whitespace normalization)
    - SUMMARY mode: Normalize whitespace and truncate to max_length with ellipsis

    Args:
        content: Original content string
        max_length: Maximum length before truncation (only applies in SUMMARY mode)
        mode: OutputMode.FULL (preserve content) or OutputMode.SUMMARY (truncate)

    Returns:
        Processed content string
    """
    # FULL mode: preserve content verbatim (no whitespace normalization)
    if mode == OutputMode.FULL:
        return content

    # SUMMARY mode: normalize whitespace and truncate
    compressed = " ".join(content.split())

    if len(compressed) > max_length:
        compressed = compressed[: max_length - 3] + "..."

    return compressed


def _escape_octave_string(value: str) -> str:
    """Escape a string value for OCTAVE format.

    Handles quotes and special characters. Order matters:
    1. Backslashes first (to avoid double-escaping)
    2. Newlines and carriage returns (to preserve line structure)
    3. Double quotes (for string boundaries)

    Args:
        value: The string to escape

    Returns:
        Quoted string with all special characters escaped
    """
    # Order matters: escape backslashes FIRST to avoid double-escaping
    # Aligned with octave-mcp/core/emitter.py:85
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\t", "\\t")
    escaped = escaped.replace("\r", "\\r")
    return f'"{escaped}"'


def format_debate_as_octave(
    room: DebateRoom,
    output_mode: OutputMode = OutputMode.FULL,
) -> str:
    """Generate OCTAVE format transcript from debate room.

    Args:
        room: DebateRoom instance with debate state
        output_mode: OutputMode.FULL (preserve content, default) or
                     OutputMode.SUMMARY (truncate to 80 chars)

    Returns:
        OCTAVE-formatted string representation
    """
    lines: list[str] = []

    # Header
    lines.append("===DEBATE_TRANSCRIPT===")
    lines.append("")

    # META section
    lines.append("META:")
    lines.append(f"  THREAD_ID::{_escape_octave_string(room.thread_id)}")
    lines.append(f"  TOPIC::{_escape_octave_string(room.topic)}")
    lines.append(f"  MODE::{room.mode.value}")
    lines.append(f"  STATUS::{room.status.value}")
    lines.append("")

    # PARTICIPANTS section - unique roles that participated
    participants = sorted({turn.role for turn in room.turns})
    if participants:
        lines.append(f"PARTICIPANTS::[{','.join(participants)}]")
    else:
        lines.append("PARTICIPANTS::[]")
    lines.append("")

    # TURNS section
    if room.turns:
        lines.append("TURNS::[")
        for i, turn in enumerate(room.turns, 1):
            cognition = turn.cognition or "UNKNOWN"
            # Compress (based on mode) then sanitize for security
            compressed = _compress_content(turn.content, mode=output_mode)
            sanitized = _sanitize_value(compressed)
            lines.append(f"  T{i}::{turn.role}[{cognition}]::{_escape_octave_string(sanitized)},")
        lines.append("]")
    else:
        lines.append("TURNS::[]")
    lines.append("")

    # SYNTHESIS section
    if room.synthesis:
        lines.append(f"SYNTHESIS::{_escape_octave_string(room.synthesis)}")
    else:
        lines.append("SYNTHESIS::null")
    lines.append("")

    # Footer - canonical OCTAVE uses ===END=== not ===END_NAME===
    lines.append("===END===")

    return "\n".join(lines)
