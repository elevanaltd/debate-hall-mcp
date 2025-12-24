"""debate_close tool - Finalize debate (T5).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server

TDD: Implements minimal functionality to pass tests.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import DebateEngine, TerminationReason
from debate_hall_mcp.state import load_debate_state, save_debate_state


def debate_close(
    thread_id: str,
    synthesis: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Close debate with final synthesis.

    Args:
        thread_id: Thread identifier
        synthesis: Final Door synthesis content
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with close summary:
        - thread_id: Thread identifier
        - status: New status (synthesis)
        - synthesis: Final synthesis content

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate already closed or synthesis empty
    """
    # Validate synthesis
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis required for debate close")

    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Close debate via engine (validates active state)
    engine = DebateEngine(room)
    engine.close_debate(TerminationReason.SYNTHESIS, synthesis=synthesis)

    # Save updated state
    save_debate_state(room, state_dir)

    # Return summary
    return {
        "thread_id": room.thread_id,
        "status": room.status.value,
        "synthesis": room.synthesis,
    }
