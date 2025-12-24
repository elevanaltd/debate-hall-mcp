"""debate_init tool - Initialize new debate thread (T1).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits enforced

TDD: Implements minimal functionality to pass tests.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.state import DebateMode, DebateRoom, save_debate_state


def debate_init(
    thread_id: str,
    topic: str,
    mode: str = "fixed",
    max_turns: int = 12,
    max_rounds: int = 4,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Initialize a new debate thread.

    Args:
        thread_id: Unique thread identifier
        topic: Debate topic
        mode: Orchestration mode ("fixed" or "mediated")
        max_turns: Maximum turns allowed (I3 compliance)
        max_rounds: Maximum rounds allowed (I3 compliance)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate summary:
        - thread_id: Thread identifier
        - topic: Debate topic
        - mode: Orchestration mode
        - status: Current status
        - max_turns: Turn limit
        - max_rounds: Round limit
        - turn_count: Current turn count (0 for new debate)

    Raises:
        ValueError: If mode is invalid
        FileExistsError: If thread_id already exists
    """
    # Validate mode
    if mode not in ("fixed", "mediated"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'fixed' or 'mediated'")

    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Check if thread already exists
    state_file = state_dir / f"{thread_id}.json"
    if state_file.exists():
        raise FileExistsError(
            f"Thread {thread_id} already exists at {state_file}"
        )

    # Create debate room
    room = DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode(mode),
        max_turns=max_turns,
        max_rounds=max_rounds,
    )

    # Save state
    save_debate_state(room, state_dir)

    # Return summary
    return {
        "thread_id": room.thread_id,
        "topic": room.topic,
        "mode": room.mode.value,
        "status": room.status.value,
        "max_turns": room.max_turns,
        "max_rounds": room.max_rounds,
        "turn_count": len(room.turns),
    }
