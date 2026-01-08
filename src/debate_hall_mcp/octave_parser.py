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
