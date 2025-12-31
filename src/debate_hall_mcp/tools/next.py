"""debate_next tool - Get prompt for next speaker (T3).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server

TDD: Implements minimal functionality to pass tests.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import get_next_speaker
from debate_hall_mcp.state import DebateStatus, load_debate_state

# Holographic Preamble: OCTAVE format guidance for agents
# This is VIEW-LAYER ONLY - never stored in DB, never affects hash chain
OCTAVE_PREAMBLE_CONTENT = """===PROTOCOL===
FORMAT::OCTAVE[recommended]
SYNTAX::[KEY::value, LIST::[a,b], FLOW::A->B->C]
OPERATORS::[::=assignment, []=list, ->=flow, +=synthesis]
NOTE::"Using OCTAVE format improves token efficiency. Optional but recommended."
===END==="""


def debate_next(
    thread_id: str,
    context_lines: int | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Get prompt information for next speaker.

    Args:
        thread_id: Thread identifier
        context_lines: Number of recent turns to include (None = all)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with prompt information:
        - thread_id: Thread identifier
        - topic: Debate topic
        - mode: Orchestration mode
        - status: Current status
        - turn_count: Total turns so far
        - max_turns: Turn limit
        - max_rounds: Round limit
        - next_role: Expected next role (None for mediated mode or closed debates)
        - transcript: List of recent turns (limited by context_lines)

    Raises:
        FileNotFoundError: If thread doesn't exist
    """
    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Determine next role
    next_role = None
    if room.status == DebateStatus.ACTIVE:
        next_role = get_next_speaker(room)

    # Build transcript (limited by context_lines)
    transcript: list[dict[str, str]] = []

    # Prepend holographic preamble if enabled (view-layer only)
    if room.octave_preamble:
        transcript.append(
            {
                "role": "System",
                "content": OCTAVE_PREAMBLE_CONTENT,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    # Add real turns (limited by context_lines)
    turns_to_include = room.turns
    if context_lines is not None and context_lines > 0:
        turns_to_include = room.turns[-context_lines:]

    for turn in turns_to_include:
        transcript.append(
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
            }
        )

    # Return prompt information
    return {
        "thread_id": room.thread_id,
        "topic": room.topic,
        "mode": room.mode.value,
        "status": room.status.value,
        "turn_count": len(room.turns),
        "max_turns": room.max_turns,
        "max_rounds": room.max_rounds,
        "next_role": next_role,
        "transcript": transcript,
    }
