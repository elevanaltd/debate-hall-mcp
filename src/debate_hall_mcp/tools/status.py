"""debate_status tool - View debate state (T4).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits visible

TDD: Implements minimal functionality to pass tests.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import get_next_speaker
from debate_hall_mcp.state import DebateStatus, load_debate_state


def debate_status(
    thread_id: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """View current debate state and status.

    Args:
        thread_id: Thread identifier
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate state:
        - thread_id: Thread identifier
        - topic: Debate topic
        - mode: Orchestration mode
        - status: Current status
        - turn_count: Total turns so far
        - max_turns: Turn limit
        - max_rounds: Round limit
        - next_role: Expected next role (None for mediated/closed)
        - synthesis: Final synthesis (if present)

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

    # Build result
    result = {
        "thread_id": room.thread_id,
        "topic": room.topic,
        "mode": room.mode.value,
        "status": room.status.value,
        "turn_count": len(room.turns),
        "max_turns": room.max_turns,
        "max_rounds": room.max_rounds,
        "next_role": next_role,
    }

    # Include synthesis if present
    if room.synthesis is not None:
        result["synthesis"] = room.synthesis

    return result
