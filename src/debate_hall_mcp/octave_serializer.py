"""OCTAVE format serializer.

Serializes Python dictionaries to OCTAVE debate transcript format.
Uses json.dumps() for escaping (NO manual character processing).
"""

import json
from datetime import datetime
from typing import Any


def serialize_meta_section(meta: dict[str, Any]) -> str:
    """Serialize META section to OCTAVE format.

    Args:
        meta: Dictionary of metadata fields

    Returns:
        OCTAVE formatted META section

    Example:
        >>> meta = {'thread_id': 'debate-001', 'max_turns': 12}
        >>> serialize_meta_section(meta)
        'META::\\n  thread_id::"debate-001"\\n  max_turns::12'
    """
    lines = ["META::"]

    for key, value in meta.items():
        # Handle different value types
        if isinstance(value, str):
            # Use json.dumps for escaping, strip outer quotes
            escaped = json.dumps(value)
            lines.append(f"  {key}::{escaped}")
        elif isinstance(value, bool):
            # Lowercase boolean
            lines.append(f"  {key}::{str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"  {key}::{value}")
        else:
            # For other types, convert to string and escape
            escaped = json.dumps(str(value))
            lines.append(f"  {key}::{escaped}")

    return "\n".join(lines)


def serialize_turn(turn: dict[str, Any], index: int) -> str:
    """Serialize a single turn to OCTAVE format.

    Format: T{index}::Role[Cognition]#{hash}@{timestamp}::"{content}"

    Args:
        turn: Turn dictionary with role, cognition, content, etc.
        index: Zero-based turn index

    Returns:
        OCTAVE formatted turn line
    """
    # Extract fields
    role = turn.get("role", "Unknown")
    cognition = turn.get("cognition", "UNKNOWN")
    content_hash = turn.get("content_hash", "0" * 64)
    timestamp = turn.get("timestamp", "")
    content = turn.get("content", "")

    # Convert datetime to ISO format string if needed
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()

    # Escape content using json.dumps, strip outer quotes
    escaped_content = json.dumps(content)[1:-1]

    return f'T{index}::{role}[{cognition}]#{content_hash}@{timestamp}::"{escaped_content}"'


def serialize_turns_section(turns: list[dict[str, Any]]) -> str:
    """Serialize TURNS section to OCTAVE format.

    Args:
        turns: List of turn dictionaries

    Returns:
        OCTAVE formatted TURNS section
    """
    if not turns:
        return "TURNS::[]"

    lines = ["TURNS::["]
    for i, turn in enumerate(turns):
        lines.append(f"  {serialize_turn(turn, i)}")
    lines.append("]")

    return "\n".join(lines)


def serialize_synthesis_section(synthesis: dict[str, Any] | None) -> str:
    """Serialize SYNTHESIS section to OCTAVE format.

    Args:
        synthesis: Synthesis dictionary or None

    Returns:
        OCTAVE formatted SYNTHESIS section
    """
    if not synthesis:
        return ""

    lines = ["SYNTHESIS::"]

    for key, value in synthesis.items():
        if isinstance(value, str):
            escaped = json.dumps(value)
            lines.append(f"  {key}::{escaped}")
        else:
            lines.append(f"  {key}::{value}")

    return "\n".join(lines)


def serialize_octave(data: dict[str, Any]) -> str:
    """Serialize complete debate to OCTAVE format.

    Args:
        data: Dictionary with meta, turns, and synthesis sections

    Returns:
        Complete OCTAVE formatted document
    """
    sections = []

    # META section
    if "meta" in data and data["meta"]:
        sections.append(serialize_meta_section(data["meta"]))

    # TURNS section
    if "turns" in data:
        sections.append(serialize_turns_section(data["turns"]))

    # SYNTHESIS section (optional)
    if "synthesis" in data and data["synthesis"]:
        sections.append(serialize_synthesis_section(data["synthesis"]))

    return "\n\n".join(sections)
