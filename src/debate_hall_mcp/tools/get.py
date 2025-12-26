"""debate_get tool - Unified read operation for debate state.

Consolidates get_status + get_next_prompt into single tool.
Difference: include_transcript parameter controls transcript inclusion.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits visible
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import get_next_speaker
from debate_hall_mcp.state import DebateStatus, load_debate_state


def debate_get(
    thread_id: str,
    include_transcript: bool = False,
    context_lines: int | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Get debate state, optionally with transcript.

    Args:
        thread_id: Thread identifier
        include_transcript: If True, include turn history
        context_lines: Limit transcript to N recent turns (None = all)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate state (always):
        - thread_id, topic, mode, status, turn_count, max_turns, max_rounds, next_role
        - synthesis (if present)
        - transcript (if include_transcript=True)

    Raises:
        FileNotFoundError: If thread doesn't exist
    """
    if state_dir is None:
        state_dir = Path("./debates")

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
    }

    if room.synthesis is not None:
        result["synthesis"] = room.synthesis

    if include_transcript:
        turns_to_include = room.turns
        if context_lines is not None and context_lines > 0:
            turns_to_include = room.turns[-context_lines:]

        result["transcript"] = [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in turns_to_include
        ]

    return result
