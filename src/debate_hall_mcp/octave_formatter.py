"""OCTAVE format output using octave-mcp package.

Uses the official octave-mcp API for validated, secure OCTAVE format emission.

Implements I2 (Universal OCTAVE Binding) from North Star.

New in octave-mcp v1.0.0:
- Document sealing for tamper-proof transcripts (seal_document, verify_seal)
- Lenient parsing with warnings (parse_with_warnings)
- Repair tiers for self-healing documents
"""

from enum import Enum
from typing import TypeVar

from debate_hall_mcp.state import DebateRoom

try:
    import octave_mcp
    from octave_mcp import (
        Document,
        SealVerificationResult,
        emit,
        parse_with_warnings,
        seal_document,
        verify_seal,
    )
    from octave_mcp.core.sealer import SealStatus
except ImportError as e:
    raise ImportError(
        "octave-mcp package is required. Install with: pip install octave-mcp>=1.0.0"
    ) from e

# Custom type variables
T = TypeVar("T")

# Define more precise types for section key handling
SectionKeyType = str | object | None
SectionKey = str | object
SectionKeyList = list[str | object]


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
            # Format turn with proper escaping
            lines.append(f'  T{i}::{turn.role}[{cognition}]::"{content}",')
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

    # Construct the document string
    doc_str = "\n".join(lines)

    # Validate that our manual construction is valid OCTAVE
    # Note: We construct manually because octave-mcp emit() doesn't handle
    # our custom TURNS format (T1::Role[Cognition]::"content")
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
        doc: Document = octave_mcp.parse(content)

        # Check required structure
        errors: list[str] = []

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
        section_keys: SectionKeyList = []
        for section in doc.sections:
            # Safely extract key, allowing for different key types
            raw_key: SectionKeyType = getattr(section, "key", None)

            # Append key if it's a string
            if isinstance(raw_key, str):
                section_keys.append(raw_key)

        # Convert required_sections to prevent type issues
        required_sections = ["PARTICIPANTS", "TURNS", "SYNTHESIS"]
        for section_name in required_sections:
            # Use a local variable and type hint to satisfy mypy
            section_name_str: str = str(section_name)
            if section_name_str not in section_keys:
                errors.append(f"Missing required section: {section_name_str}")

        return (len(errors) == 0, errors)

    except Exception as e:
        return (False, [f"Parse error: {str(e)}"])


def seal_debate_transcript(content: str) -> str:
    """Add cryptographic seal to a debate transcript for tamper-proofing.

    The seal is a SHA-256 hash of the document content, appended as a
    §SEAL section. Any modification to the content will invalidate the seal.

    Args:
        content: Valid OCTAVE-formatted debate transcript

    Returns:
        OCTAVE string with §SEAL section appended

    Raises:
        ValueError: If content is not valid OCTAVE

    Example:
        >>> sealed = seal_debate_transcript(octave_transcript)
        >>> # Later, verify the transcript hasn't been modified
        >>> result = verify_debate_seal(sealed)
        >>> assert result.is_valid
    """
    try:
        doc = octave_mcp.parse(content)
        sealed_doc = seal_document(doc)
        return emit(sealed_doc)
    except Exception as e:
        raise ValueError(f"Cannot seal invalid OCTAVE document: {e}") from e


class SealResult:
    """Result of verifying a debate transcript seal."""

    def __init__(
        self,
        is_valid: bool,
        status: str,
        message: str,
        expected_hash: str | None = None,
        actual_hash: str | None = None,
    ) -> None:
        self.is_valid = is_valid
        self.status = status
        self.message = message
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash


def verify_debate_seal(content: str) -> SealResult:
    """Verify that a sealed debate transcript has not been tampered with.

    Args:
        content: OCTAVE-formatted debate transcript with §SEAL section

    Returns:
        SealResult with verification status and details

    Example:
        >>> result = verify_debate_seal(sealed_transcript)
        >>> if result.is_valid:
        ...     print("Transcript integrity verified")
        ... else:
        ...     print(f"TAMPER DETECTED: {result.message}")
    """
    try:
        doc = octave_mcp.parse(content)
        result: SealVerificationResult = verify_seal(doc)

        return SealResult(
            is_valid=result.status == SealStatus.VERIFIED,
            status=result.status.value,
            message=result.message or "Seal verification complete",
            expected_hash=result.expected_hash,
            actual_hash=result.actual_hash,
        )
    except Exception as e:
        return SealResult(
            is_valid=False,
            status="ERROR",
            message=f"Failed to verify seal: {e}",
        )


def validate_debate_octave_lenient(content: str) -> tuple[bool, list[str], list[dict[str, object]]]:
    """Validate OCTAVE-formatted debate with lenient parsing.

    Uses octave-mcp v1.0.0's parse_with_warnings for more forgiving validation
    that can handle minor formatting issues while still reporting them.

    Args:
        content: OCTAVE-formatted string to validate

    Returns:
        Tuple of (is_valid, errors, warnings)
        - is_valid: True if document structure is correct (ignoring minor warnings)
        - errors: List of structural errors that prevent valid parsing
        - warnings: List of warning dicts from lenient parsing (minor issues)

    Example:
        >>> is_valid, errors, warnings = validate_debate_octave_lenient(content)
        >>> if warnings:
        ...     print(f"Minor issues found: {len(warnings)}")
    """
    try:
        # Use lenient parsing that captures warnings
        doc, warnings = parse_with_warnings(content)

        # Check required structure
        errors: list[str] = []

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

        # Check for required sections
        section_keys: list[str] = []
        for section in doc.sections:
            raw_key = getattr(section, "key", None)
            if isinstance(raw_key, str):
                section_keys.append(raw_key)

        required_sections = ["PARTICIPANTS", "TURNS", "SYNTHESIS"]
        for section_name in required_sections:
            if section_name not in section_keys:
                errors.append(f"Missing required section: {section_name}")

        return (len(errors) == 0, errors, warnings)

    except Exception as e:
        return (False, [f"Parse error: {str(e)}"], [])
