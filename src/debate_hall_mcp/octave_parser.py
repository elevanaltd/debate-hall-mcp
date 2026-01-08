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
