"""Context Compiler - Export decisions and render in-prompt context blocks.

This module hosts two related concerns:

1. **Decision export (issue #138)** — :func:`export_decision_to_context` writes
   a :class:`DecisionRecord` to ``.hestai/state/context/decisions/`` as a
   compiled OCTAVE file that future agents can read as binding context (≈98%
   token savings vs re-debating).

2. **In-prompt ``<PATH_CONTRACTS>`` rendering (RFC-0001 #199)** —
   :func:`render_path_contracts_block` projects the latest revision of each
   :class:`PathContract` field plus revision counts into a sub-block that the
   orchestrator injects inside ``<DEBATE_STATE>``. This satisfies RFC §6 item 1
   ("the ``<DEBATE_STATE>`` block in prompts includes a ``<PATH_CONTRACTS>``
   sub-block with the latest revision per field plus revision counts; full
   history available in storage but not pushed into prompts on every turn")
   while keeping the token-budget ceiling of RFC §8 Q3.

Compliance:

- I4 (Verifiable Event Ledger): Exported decisions preserve integrity via hashes;
  ``render_path_contracts_block`` projects history without mutating it.
- I2 (Universal OCTAVE Binding): All emitted blocks use OCTAVE structural form.
- I1 (Cognitive State Isolation): The renderer is a pure function over its
  inputs; it performs no disk reads (the orchestrator-side fix for Finding I).
"""

import json
import re
from pathlib import Path
from typing import Any

from debate_hall_mcp.decision import DecisionRecord
from debate_hall_mcp.path_contract import PathContract, prompt_context_view

# Maximum length for slugified topic in filename
MAX_SLUG_LENGTH = 60


def slugify_topic(topic: str) -> str:
    """Convert a topic string to a URL/filename-safe slug.

    Args:
        topic: Original topic string

    Returns:
        Lowercase, hyphenated slug suitable for filenames

    Examples:
        >>> slugify_topic("Should We Use TypeScript?")
        'should-we-use-typescript'
        >>> slugify_topic("")
        'untitled'
    """
    if not topic or not topic.strip():
        return "untitled"

    # Convert to lowercase
    slug = topic.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove any character that isn't alphanumeric or hyphen
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens into one
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to max length (at word boundary if possible)
    if len(slug) > MAX_SLUG_LENGTH:
        truncated = slug[:MAX_SLUG_LENGTH]
        # Try to truncate at a hyphen for cleaner slug
        last_hyphen = truncated.rfind("-")
        slug = truncated[:last_hyphen] if last_hyphen > MAX_SLUG_LENGTH // 2 else truncated

    return slug if slug else "untitled"


def _escape_octave_string(value: str) -> str:
    """Escape a string value for OCTAVE format.

    Args:
        value: String to escape

    Returns:
        Escaped string safe for OCTAVE
    """
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace('"', '\\"')
    )


def format_decision_as_octave(record: DecisionRecord) -> str:
    """Format a DecisionRecord as an OCTAVE document.

    Produces a COMPILED_DECISION document with the following structure:
    - META: Document metadata and identity
    - OUTCOME: Synthesis, hash, and status
    - RATIONALE: Extracted perspectives by role
    - VALIDATION: Consensus and refinement info
    - PROVENANCE: Source and extraction metadata

    Args:
        record: DecisionRecord to format

    Returns:
        OCTAVE-formatted string
    """
    lines = []

    # Header
    lines.append("===COMPILED_DECISION===")
    lines.append("")

    # META section
    lines.append("META:")
    lines.append("  TYPE::COMPILED_DECISION")
    lines.append('  VERSION::"1.0"')
    lines.append(f'  THREAD_ID::"{_escape_octave_string(record.thread_id)}"')
    lines.append(f'  TOPIC::"{_escape_octave_string(record.topic)}"')
    lines.append(f'  DECIDED_AT::"{record.decided_at.isoformat()}"')
    lines.append("")

    # OUTCOME section
    lines.append("OUTCOME:")
    lines.append(f'  SYNTHESIS::"{_escape_octave_string(record.synthesis)}"')
    lines.append(f'  DECISION_HASH::"{record.decision_hash}"')
    lines.append(f"  STATUS::{record.status}")
    lines.append("")

    # RATIONALE section
    lines.append("RATIONALE:")
    if record.wind_perspectives:
        lines.append("  WIND_PERSPECTIVES::[")
        for perspective in record.wind_perspectives:
            lines.append(f'    "{_escape_octave_string(perspective)}",')
        lines.append("  ]")
    else:
        lines.append("  WIND_PERSPECTIVES::[]")

    if record.wall_constraints:
        lines.append("  WALL_CONSTRAINTS::[")
        for constraint in record.wall_constraints:
            lines.append(f'    "{_escape_octave_string(constraint)}",')
        lines.append("  ]")
    else:
        lines.append("  WALL_CONSTRAINTS::[]")

    if record.door_refinements:
        lines.append("  DOOR_REFINEMENTS::[")
        for refinement in record.door_refinements:
            lines.append(f'    "{_escape_octave_string(refinement)}",')
        lines.append("  ]")
    else:
        lines.append("  DOOR_REFINEMENTS::[]")
    lines.append("")

    # VALIDATION section
    lines.append("VALIDATION:")
    consensus_str = "true" if record.consensus_reached else "false"
    lines.append(f"  CONSENSUS_REACHED::{consensus_str}")
    if record.consensus_votes:
        wind_vote = record.consensus_votes.get("wind")
        wall_vote = record.consensus_votes.get("wall")
        wind_str = str(wind_vote).lower() if wind_vote is not None else "null"
        wall_str = str(wall_vote).lower() if wall_vote is not None else "null"
        lines.append(f"  VOTES::{{wind:{wind_str},wall:{wall_str}}}")
    else:
        lines.append("  VOTES::{}")
    lines.append(f"  REFINEMENT_COUNT::{record.refinement_count}")
    lines.append(f"  TURN_COUNT::{record.turn_count}")
    lines.append("")

    # PROVENANCE section
    lines.append("PROVENANCE:")
    lines.append(f'  EXTRACTED_AT::"{record.extracted_at.isoformat()}"')
    lines.append(f'  SOURCE_HASH::"{record.source_hash}"')
    lines.append("")

    # Footer
    lines.append("===END===")

    return "\n".join(lines)


def _extract_short_id(thread_id: str) -> str:
    """Extract a short identifier from thread_id for filename uniqueness.

    Takes the last hyphen-separated segment of the thread_id, or
    the first 8 characters if no hyphen is found.

    Defense-in-depth: although thread_id is validated upstream at debate
    creation, this helper revalidates because a DecisionRecord could reach
    it from another caller (import, external tool). Inputs containing path
    separators ('/', '\\'), parent traversal ('..'), or control characters
    are rejected with ValueError to ensure the resulting filename suffix
    cannot escape the decisions/ directory.

    Args:
        thread_id: Full thread identifier

    Returns:
        Short identifier suitable for filename suffix

    Raises:
        ValueError: If thread_id is empty, or contains '/', '\\', '..',
            or any control character (\\x00–\\x1f, \\x7f).

    Examples:
        >>> _extract_short_id("2026-01-30-api-design-morning")
        'morning'
        >>> _extract_short_id("abc123def456")
        'abc123de'
    """
    if not thread_id:
        raise ValueError("invalid thread_id: must be non-empty")
    if "/" in thread_id or "\\" in thread_id:
        raise ValueError("invalid thread_id: path separators ('/', '\\\\') are not allowed")
    if ".." in thread_id:
        raise ValueError("invalid thread_id: parent traversal ('..') is not allowed")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in thread_id):
        raise ValueError("invalid thread_id: control characters are not allowed")

    if "-" in thread_id:
        return thread_id.split("-")[-1]
    return thread_id[:8]


def export_decision_to_context(
    record: DecisionRecord,
    context_dir: Path,
) -> Path:
    """Export a DecisionRecord to the context decisions directory.

    Creates an OCTAVE file at:
    {context_dir}/decisions/{YYYY-MM-DD}-{topic-slug}-{short_id}.oct.md

    The short_id suffix is extracted from the thread_id to ensure
    filename uniqueness when multiple debates on the same topic
    occur on the same day.

    Args:
        record: DecisionRecord to export
        context_dir: Base context directory (.hestai/state/context)

    Returns:
        Absolute path to the created file
    """
    # Create decisions directory if it doesn't exist
    decisions_dir = context_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from decided_at date, topic slug, and short_id
    date_str = record.decided_at.strftime("%Y-%m-%d")
    topic_slug = slugify_topic(record.topic)
    short_id = _extract_short_id(record.thread_id)
    filename = f"{date_str}-{topic_slug}-{short_id}.oct.md"

    # Full path to output file
    output_path = decisions_dir / filename

    # Format as OCTAVE and write
    octave_content = format_decision_as_octave(record)
    output_path.write_text(octave_content)

    return output_path.resolve()


def list_decisions(context_dir: Path) -> list[Path]:
    """List all exported decision files in the context directory.

    Args:
        context_dir: Base context directory (.hestai/state/context)

    Returns:
        List of paths to decision files, sorted by name (most recent first)
    """
    decisions_dir = context_dir / "decisions"

    # Create directory if it doesn't exist
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Find all .oct.md files
    decision_files = sorted(
        decisions_dir.glob("*.oct.md"),
        key=lambda p: p.name,
        reverse=True,  # Most recent first (dates sort correctly)
    )

    return decision_files


def get_context_dir() -> Path:
    """Get the context directory for decision exports.

    Resolution order:
    1. Environment variable DEBATE_HALL_CONTEXT_DIR
    2. Project root / ".hestai" / "state" / "context" (auto-detected, Tier 3)
    3. Current working directory / ".hestai" / "state" / "context" (fallback)

    Returns:
        Path to context directory
    """
    import os

    from debate_hall_mcp.state import find_project_root

    # Priority 1: Environment variable
    env_value = os.environ.get("DEBATE_HALL_CONTEXT_DIR", "")
    if env_value:
        return Path(env_value)

    # Priority 2: Project-relative detection
    # Uses Tier 3 path (.hestai/state/context) per three-tier architecture:
    # - Tier 1: .hestai-sys/ (MCP-managed, gitignored)
    # - Tier 2: .hestai/ (project governance, committed)
    # - Tier 3: .hestai/state/ (working state, gitignored)
    try:
        project_root = find_project_root()
        return project_root / ".hestai" / "state" / "context"
    except Exception:
        pass

    # Priority 3: Current working directory fallback
    return Path.cwd() / ".hestai" / "state" / "context"


# ---------------------------------------------------------------------------
# RFC-0001 #199 — <PATH_CONTRACTS> sub-block renderer
#
# Pure projection of a list of PathContract objects into the in-prompt
# <PATH_CONTRACTS> sub-block. Consumed by Orchestrator._format_debate_state.
#
# Design choices:
#
# * Latest-revision-only per field, plus revision counts (RFC §6 item 1).
#   Earlier revisions stay in storage (I4 append-only) and are never rendered.
#
# * Empty input list ⇒ empty string output. The caller is responsible for
#   suppressing the surrounding envelope structure. This preserves byte-identity
#   with the legacy envelope when the feature is off or no contracts exist.
#
# * Frame/verdict/diff values are emitted as compact one-line JSON. OCTAVE
#   tolerates JSON-as-value, and per-line JSON keeps the projection trivially
#   diff-able. Token budget tests (see test_context_compiler_path_contracts.py)
#   gate the worst case against RFC §8 Q3.
#
# * datetime objects are ISO-8601-stringified (re-using the storage helper's
#   convention) so the rendered block is JSON-safe and stable across runs.
# ---------------------------------------------------------------------------


def _isoformat_datetimes(obj: Any) -> Any:
    """Recursively convert datetime values to ISO-8601 strings for JSON safety."""
    from datetime import datetime

    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _isoformat_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_isoformat_datetimes(item) for item in obj]
    return obj


def render_path_contracts_block(contracts: list[PathContract]) -> str:
    """Render the in-prompt ``<PATH_CONTRACTS>`` sub-block (RFC-0001 #199).

    Per RFC §6 item 1, only the latest revision of each field is rendered,
    accompanied by revision counts. Full revision history stays in storage
    (RFC §3.1, I4 append-only ledger) and is never blasted into prompts.

    Args:
        contracts: Per-path append-only contracts. ``[]`` yields ``""`` so the
            caller can omit the surrounding envelope structure entirely (the
            feature-off byte-identity guarantee).

    Returns:
        OCTAVE sub-block bracketed by ``<PATH_CONTRACTS>`` / ``</PATH_CONTRACTS>``
        when ``contracts`` is non-empty; the empty string otherwise.
    """
    if not contracts:
        return ""

    lines: list[str] = ["<PATH_CONTRACTS>"]
    for contract in contracts:
        view = prompt_context_view(contract)
        lines.append(f"  PATH::{view['path_id']}")
        lines.append(f"    frame_rev_count::{view['frame_count']}")
        if view["latest_frame"] is not None:
            frame_value = _isoformat_datetimes(view["latest_frame"]["value"])
            lines.append(f"    FRAME::{json.dumps(frame_value, separators=(',', ':'))}")
        lines.append(f"    verdict_rev_count::{view['verdict_count']}")
        if view["latest_verdict"] is not None:
            verdict_value = _isoformat_datetimes(view["latest_verdict"]["value"])
            lines.append(f"    VERDICT::{json.dumps(verdict_value, separators=(',', ':'))}")
        lines.append(f"    diff_rev_count::{view['diff_count']}")
        if view["latest_diff"] is not None:
            diff_payload: dict[str, Any] = {"value": view["latest_diff"]["value"]}
            # Carry optional fields when present so downstream consumers
            # (Door's citation rule, validator) can see them without a second lookup.
            if "divergence_marker" in view["latest_diff"]:
                diff_payload["divergence_marker"] = view["latest_diff"]["divergence_marker"]
            if "synthesis_guidance" in view["latest_diff"]:
                diff_payload["synthesis_guidance"] = view["latest_diff"]["synthesis_guidance"]
            diff_payload = _isoformat_datetimes(diff_payload)
            lines.append(f"    DIFF::{json.dumps(diff_payload, separators=(',', ':'))}")
    lines.append("</PATH_CONTRACTS>")
    return "\n".join(lines)


def derive_synthesis_status(*, synthesis: str | None, turn_count: int) -> str:
    """Derive the ``<SYNTHESIS_STATUS>`` value for the envelope (Finding F).

    Three values disambiguate the APPROVE/REJECT-vs-no-synthesis conflation
    reported in RFC-0001 §3.3 Finding F:

    * ``PRESENT`` — Door has produced (or refined) a synthesis that is
      currently the active candidate; ``synthesis`` is set.
    * ``PENDING_INITIAL`` — No synthesis exists yet for the current round and
      Door has not run; fewer than 3 turns have completed.
    * ``PENDING_REFINEMENT`` — A prior synthesis was withdrawn (e.g. rejected)
      and a Door refinement turn is expected; ``synthesis`` is unset but at
      least 3 turns have completed (Wind/Wall/Door have all spoken).

    The orchestrator emits this value as ``SYNTHESIS_STATUS::<value>`` inside
    ``<DEBATE_STATE>``. Wind's #198 prompt branches on it deterministically so
    APPROVE/REJECT can never be conflated with "there is nothing to vote on".

    Args:
        synthesis: ``debate_state["synthesis"]`` (may be ``None`` or empty).
        turn_count: ``debate_state["turn_count"]``.

    Returns:
        One of ``"PRESENT"``, ``"PENDING_INITIAL"``, or ``"PENDING_REFINEMENT"``.
    """
    if synthesis:
        return "PRESENT"
    if turn_count < 3:
        return "PENDING_INITIAL"
    return "PENDING_REFINEMENT"
