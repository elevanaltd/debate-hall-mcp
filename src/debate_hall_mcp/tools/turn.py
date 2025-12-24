"""debate_turn tool - Record agent turn (T2).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I4 (VERIFIABLE_EVENT_LEDGER): Hash chain maintained

TDD: Implements minimal functionality to pass tests.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import DebateEngine, get_next_speaker
from debate_hall_mcp.state import DebateMode, load_debate_state, save_debate_state


def debate_turn(
    thread_id: str,
    role: str,
    content: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Record an agent turn in the debate.

    Args:
        thread_id: Thread identifier
        role: Agent role (Wind, Wall, Door)
        content: Turn content (OCTAVE format expected)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with turn summary:
        - thread_id: Thread identifier
        - turn_count: Total turns after this one
        - role: Role that just spoke
        - status: Current debate status

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate is not active, exhausted, or role is wrong
    """
    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # In fixed mode, validate role matches expected
    if room.mode == DebateMode.FIXED:
        expected_role = get_next_speaker(room)
        if role != expected_role:
            raise ValueError(
                f"Expected role '{expected_role}' but got '{role}' in fixed mode"
            )

    # Add turn via engine (validates active state and limits)
    engine = DebateEngine(room)
    engine.add_turn(role, content)

    # Save updated state
    save_debate_state(room, state_dir)

    # Return summary
    return {
        "thread_id": room.thread_id,
        "turn_count": len(room.turns),
        "role": role,
        "status": room.status.value,
    }
