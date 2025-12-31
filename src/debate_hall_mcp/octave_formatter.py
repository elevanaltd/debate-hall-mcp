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

from debate_hall_mcp.state import DebateRoom


def _compress_content(content: str, max_length: int = 80) -> str:
    """Compress content for OCTAVE output.

    Semantic compression: Remove redundancy while preserving meaning.
    - Truncate to max_length with ellipsis
    - Replace newlines with spaces
    - Collapse multiple spaces

    Args:
        content: Original content string
        max_length: Maximum length before truncation

    Returns:
        Compressed content string
    """
    # Normalize whitespace
    compressed = " ".join(content.split())

    # Truncate if needed
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


def format_debate_as_octave(room: DebateRoom) -> str:
    """Generate OCTAVE format transcript from debate room.

    Args:
        room: DebateRoom instance with debate state

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
            compressed = _compress_content(turn.content)
            lines.append(f"  T{i}::{turn.role}[{cognition}]::{_escape_octave_string(compressed)},")
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
