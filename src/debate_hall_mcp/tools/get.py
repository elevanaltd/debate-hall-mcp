"""debate_get tool - Unified read operation for debate state.

Consolidates get_status + get_next_prompt into single tool.
Difference: include_transcript parameter controls transcript inclusion.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits visible

Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import get_next_speaker
from debate_hall_mcp.state import DebateStatus, get_state_dir, load_debate_state
from debate_hall_mcp.utils.primers import get_literacy_primer

# View-layer only: never stored in DB, never affects hash chain
# Use the official octave-literacy-primer from octave-mcp v1.0.0 (~40 tokens)
# Falls back to inline version if primer loading fails
_FALLBACK_OCTAVE_PREAMBLE = """===PROTOCOL===
FORMAT::OCTAVE[recommended]
SYNTAX::[KEY::value, LIST::[a,b], FLOW::A->B->C]
OPERATORS::[::=assignment, []=list, ->=flow, +=synthesis]
NOTE::"Using OCTAVE format improves token efficiency. Optional but recommended."
===END==="""


def _get_octave_preamble() -> str:
    """Get the OCTAVE preamble for agent context.

    Uses the official octave-literacy-primer from octave-mcp v1.0.0.
    Falls back to inline version if primer loading fails.
    """
    try:
        return get_literacy_primer()
    except (ImportError, FileNotFoundError):
        return _FALLBACK_OCTAVE_PREAMBLE


# Cached preamble content - loaded once at module import
OCTAVE_PREAMBLE_CONTENT = _get_octave_preamble()


def debate_get(
    thread_id: str,
    include_transcript: bool = False,
    include_metadata: bool = False,
    context_turns: int | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Get debate state, optionally with transcript.

    Args:
        thread_id: Thread identifier
        include_transcript: If True, include turn history
        include_metadata: If True, include agent_role and model for each turn.
            Note: cognition and token_output are always included in transcript
            entries for VTP observability (#135), regardless of this flag.
        context_turns: Limit transcript to N recent turns (None = all)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate state (always):
        - thread_id, topic, mode, status, turn_count, max_turns, max_rounds, next_role
        - synthesis (if present)
        - transcript (if include_transcript=True)
          Each transcript entry always contains: role, cognition, token_output,
          content, timestamp.
          When include_metadata=True, also contains: agent_role, model.

    Raises:
        FileNotFoundError: If thread doesn't exist
    """
    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

    room = load_debate_state(thread_id, state_dir)

    next_role = None
    if room.status == DebateStatus.ACTIVE:
        next_role = get_next_speaker(room)

    result: dict[str, Any] = {
        "thread_id": room.thread_id,
        "topic": room.topic,
        "mode": room.mode.value,
        "status": room.status.value,
        "turn_count": len(room.turns),
        "max_turns": room.max_turns,
        "max_rounds": room.max_rounds,
        "next_role": next_role,
        "octave_mode": room.octave_mode,
    }

    if room.synthesis is not None:
        result["synthesis"] = room.synthesis

    if include_transcript:
        turns_to_include = room.turns
        omitted_count = 0

        if context_turns is not None and context_turns > 0:
            omitted_count = max(0, len(room.turns) - context_turns)
            turns_to_include = room.turns[-context_turns:]

        transcript: list[dict[str, Any]] = []

        # Prepend OCTAVE preamble if enabled (view-layer only)
        if room.octave_preamble:
            transcript.append(
                {
                    "role": "System",
                    "content": OCTAVE_PREAMBLE_CONTENT,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        # Add window indicator if turns were omitted
        if omitted_count > 0:
            transcript.append(
                {
                    "role": "System",
                    "content": f"[... {omitted_count} earlier turns omitted for context window optimization ...]",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        # Add actual turns
        # token_output and cognition are always included for VTP observability (#135).
        # Identity metadata (agent_role, model) remains gated by include_metadata.
        transcript.extend(
            {
                "role": turn.role,
                "cognition": turn.cognition,
                "token_output": turn.token_output,
                **(
                    {
                        "agent_role": turn.agent_role,
                        "model": turn.model,
                    }
                    if include_metadata
                    else {}
                ),
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in turns_to_include
        )

        result["transcript"] = transcript

    return result
