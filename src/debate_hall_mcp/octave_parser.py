"""OCTAVE format parser.

Parses OCTAVE debate transcripts into Python dictionaries.
Uses json.loads() for unescaping (NO manual character processing).
"""

import json
import re
from typing import Any


def parse_meta_section(content: str) -> dict[str, Any]:
    """Parse META section from OCTAVE format.

    Args:
        content: META section content (including "META::" header)

    Returns:
        Dictionary of metadata fields with proper type conversion

    Example:
        >>> meta = '''META::
        ...   thread_id::"debate-001"
        ...   max_turns::12
        ...   octave_mode::true'''
        >>> parse_meta_section(meta)
        {'thread_id': 'debate-001', 'max_turns': 12, 'octave_mode': True}
    """
    result: dict[str, Any] = {}

    # Parse each field line
    for line in content.split("\n"):
        line = line.strip()
        if not line or line == "META::":
            continue

        # Match pattern: key::value or key::"value"
        match = re.match(r"(\w+)::(.*)", line)
        if not match:
            continue

        key, value = match.groups()
        value = value.strip()

        # Handle quoted strings
        if value.startswith('"') and value.endswith('"'):
            # Unescape using json.loads
            result[key] = json.loads(value)
        # Handle boolean values
        elif value == "true":
            result[key] = True
        elif value == "false":
            result[key] = False
        # Handle integer values
        elif value.isdigit():
            result[key] = int(value)
        # Handle unquoted strings
        else:
            result[key] = value

    return result


def parse_turn(turn_line: str) -> dict[str, Any]:
    """Parse a single turn line from OCTAVE format.

    Format: T{index}::Role[Cognition]#{hash}@{timestamp}::"{content}"

    Args:
        turn_line: Single turn line in OCTAVE format

    Returns:
        Dictionary with turn data (index, role, cognition, hash, timestamp, content)

    Example:
        >>> turn = 'T0::Wind[PATHOS]#abc123@2026-01-08T10:30:00Z::"Test content"'
        >>> parse_turn(turn)
        {'index': 0, 'role': 'Wind', 'cognition': 'PATHOS', ...}
    """
    # Pattern: T{index}::Role[Cognition]#{hash}@{timestamp}::"{content}"
    # Timestamp can have +00:00 or Z suffix, so we need to match until ::
    pattern = r'T(\d+)::(\w+)\[(\w+)\]#([a-f0-9]{64})@(.+?)::"(.*)"$'
    match = re.match(pattern, turn_line, re.DOTALL)

    if not match:
        raise ValueError(f"Invalid turn format: {turn_line[:50]}...")

    index, role, cognition, content_hash, timestamp, escaped_content = match.groups()

    # Unescape content using json.loads
    content = json.loads(f'"{escaped_content}"')

    return {
        "index": int(index),
        "role": role,
        "cognition": cognition,
        "content_hash": content_hash,
        "timestamp": timestamp,
        "content": content,
    }


def parse_turns_section(content: str) -> list[dict[str, Any]]:
    """Parse TURNS section from OCTAVE format.

    Format: TURNS::[
      T0::...
      T1::...
    ]

    Args:
        content: TURNS section content (including "TURNS::[" header and "]" footer)

    Returns:
        List of parsed turn dictionaries
    """
    # Extract content between TURNS::[ and final ]
    # Use greedy match and look for the last closing bracket
    match = re.search(r"TURNS::\[(.*)\]", content, re.DOTALL)
    if not match:
        # Empty turns section or no match
        return []

    turns_content = match.group(1).strip()
    if not turns_content:
        return []

    # Split into individual turn lines (each starts with T followed by digit)
    turn_lines = [
        line.strip() for line in turns_content.split("\n") if re.match(r"T\d+::", line.strip())
    ]

    return [parse_turn(line) for line in turn_lines]


def parse_synthesis_section(content: str) -> dict[str, Any]:
    """Parse SYNTHESIS section from OCTAVE format.

    Args:
        content: SYNTHESIS section content

    Returns:
        Dictionary with synthesis data
    """
    result: dict[str, Any] = {}

    # Parse each field line
    for line in content.split("\n"):
        line = line.strip()
        if not line or line == "SYNTHESIS::":
            continue

        # Match pattern: key::value or key::"value"
        match = re.match(r"(\w+)::(.*)", line)
        if not match:
            continue

        key, value = match.groups()
        value = value.strip()

        # Handle quoted strings
        if value.startswith('"') and value.endswith('"'):
            result[key] = json.loads(value)
        else:
            result[key] = value

    return result


def parse_octave(content: str) -> dict[str, Any]:
    """Parse complete OCTAVE debate transcript.

    Args:
        content: Full OCTAVE format content

    Returns:
        Dictionary with meta, turns, and synthesis sections
    """
    # Extract META section
    meta_match = re.search(r"(META::.*?)(?=\n\w+::|$)", content, re.DOTALL)
    meta = parse_meta_section(meta_match.group(1)) if meta_match else {}

    # Extract TURNS section (use greedy match for final ])
    turns_match = re.search(r"(TURNS::\[.*\])", content, re.DOTALL)
    turns = parse_turns_section(turns_match.group(1)) if turns_match else []

    # Extract SYNTHESIS section (optional)
    synthesis_match = re.search(r"(SYNTHESIS::.*?)(?=\n===|$)", content, re.DOTALL)
    synthesis = parse_synthesis_section(synthesis_match.group(1)) if synthesis_match else None

    return {
        "meta": meta,
        "turns": turns,
        "synthesis": synthesis,
    }
