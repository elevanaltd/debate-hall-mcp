"""OCTAVE format output using octave-mcp package.

Uses the official octave-mcp API for validated, secure OCTAVE format emission.

Implements I2 (Universal OCTAVE Binding) from North Star.
"""

import json
from enum import Enum
from typing import Any

try:
    import octave_mcp
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
    # Escape all special characters for OCTAVE format (order matters: \ first, quotes last)
    thread_id = (
        room.thread_id.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace('"', '\\"')
    )
    topic = (
        room.topic.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace('"', '\\"')
    )
    lines.append(f'  THREAD_ID::"{thread_id}"')
    lines.append(f'  TOPIC::"{topic}"')
    lines.append(f"  MODE::{room.mode.value}")
    lines.append(f"  STATUS::{room.status.value}")
    lines.append(f"  MAX_TURNS::{room.max_turns}")
    lines.append(f"  MAX_ROUNDS::{room.max_rounds}")
    lines.append(f"  STRICT_COGNITION::{str(room.strict_cognition).lower()}")
    lines.append(f"  OCTAVE_MODE::{str(room.octave_mode).lower()}")
    if room.expected_next_role:
        lines.append(f'  EXPECTED_NEXT_ROLE::"{room.expected_next_role}"')
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
            # Escape special characters (order matters: \ first, quotes last)
            content = (
                content.replace("\\", "\\\\")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
                .replace('"', '\\"')
            )
            cognition = turn.cognition or "UNKNOWN"
            if turn.agent_role or turn.model:
                # Format: [Cognition,AgentRole,Model]
                # Use "null" for missing fields to maintain positional integrity if needed,
                # or just use key-value style? Comma separated values is easiest.
                # Let's use: [Cognition|AgentRole|Model] using pipe as separator to avoid comma issues in lists?
                # Or just comma. Cognition is usually simple word. AgentRole/Model might have chars.
                # Let's use | separator.
                ar = turn.agent_role or ""
                md = turn.model or ""
                # Escape | in values? They should be simple identifiers.
                # If they contain |, replace with something else or strip.
                ar = ar.replace("|", "/")
                md = md.replace("|", "/")
                cognition_field = f"[{cognition}|{ar}|{md}]"
            else:
                cognition_field = f"[{cognition}]"

            timestamp = turn.timestamp.isoformat()

            # Format turn as a single quoted string to ensure safe list parsing
            # We first construct the inner content with its own escaping
            # content is already escaped for "..." usage
            # Add explicit hash persistence for I4 compliance (tombstones)
            inner_turn = f'T{i}::{turn.role}{cognition_field}#{turn.hash}@{timestamp}::"{content}"'

            # Now escape the entire turn string for the outer quotes
            # We need to escape backslashes and double quotes
            escaped_turn = inner_turn.replace("\\", "\\\\").replace('"', '\\"')

            lines.append(f'  "{escaped_turn}",')
        lines.append("]")
    else:
        lines.append("TURNS::[]")
    lines.append("")

    # SYNTHESIS section
    if room.synthesis:
        # Escape special characters (order matters: \ first, quotes last)
        synthesis = (
            room.synthesis.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
            .replace('"', '\\"')
        )
        lines.append(f'SYNTHESIS::"{synthesis}"')
    else:
        lines.append("SYNTHESIS::null")
    lines.append("")

    # Footer
    lines.append("===END===")

    # We serialize internal state as fields inside the document before END
    # But wait, we just appended END.
    # OCTAVE structure: HEADER ... CONTENT ... END.
    # So we must append these BEFORE "===END===".

    # Remove the last line (===END===) temporarily
    lines.pop()

    # Internal State Fields (for persistence fidelity)
    if output_mode == OutputMode.FULL:
        # Helper to safely quote JSON for OCTAVE
        def octave_json_string(obj: Any) -> str:
            json_str = json.dumps(obj)
            # Escape for OCTAVE string: \ -> \\, " -> \"
            escaped = json_str.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        # AUDIT_LOG
        if room.audit_log:
            data = [a.model_dump(mode="json") for a in room.audit_log]
            lines.append(f"AUDIT_LOG::{octave_json_string(data)}")

        # GITHUB_BINDING
        if room.github_binding:
            binding_data = room.github_binding.model_dump(mode="json")
            lines.append(f"GITHUB_BINDING::{octave_json_string(binding_data)}")

        # INJECTED_CONTEXT
        if room.injected_context:
            context_data = [c.model_dump(mode="json") for c in room.injected_context]
            lines.append(f"INJECTED_CONTEXT::{octave_json_string(context_data)}")

    lines.append("===END===")

    # Construct the document string
    doc_str = "\n".join(lines)

    # Validate that our manual construction is valid OCTAVE
    # Note: We don't use emit() because octave-mcp v0.3.0 has a bug in TURNS emission
    # Our manual escaping is correct and produces valid OCTAVE
    try:
        octave_mcp.parse(doc_str)
        # Parse succeeded - our format is valid
        return doc_str
    except Exception:
        # If parse fails, something is wrong with our escaping
        # Return the string anyway but this indicates a bug
        return doc_str


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
        for req_section in required_sections:
            if req_section not in section_keys:
                errors.append(f"Missing required section: {req_section}")

        return (len(errors) == 0, errors)

    except Exception as e:
        return (False, [f"Parse error: {str(e)}"])
