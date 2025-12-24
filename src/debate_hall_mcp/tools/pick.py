"""debate_pick tool - Set next speaker in mediated mode (T6).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server

TDD: Implements minimal functionality to pass tests.

Note: This tool is only valid for mediated mode debates.
In fixed mode, role sequence is automatic (Wind→Wall→Door).
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.state import DebateMode, DebateStatus, load_debate_state

VALID_ROLES = {"Wind", "Wall", "Door"}


def debate_pick(
    thread_id: str,
    role: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Set next expected speaker role in mediated mode.

    Args:
        thread_id: Thread identifier
        role: Role to pick (Wind, Wall, Door)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with pick summary:
        - thread_id: Thread identifier
        - next_role: Role that was picked
        - mode: Orchestration mode (mediated)

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If not mediated mode, invalid role, or debate not active

    Note:
        In current implementation, this is informational only.
        debate_turn in mediated mode accepts any role.
        Future versions may enforce the picked role.
    """
    # Validate role
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {', '.join(VALID_ROLES)}")

    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Validate mediated mode
    if room.mode != DebateMode.MEDIATED:
        raise ValueError(
            f"debate_pick is only valid for mediated mode (current mode: {room.mode.value})"
        )

    # Validate active status
    if room.status != DebateStatus.ACTIVE:
        raise ValueError(f"Debate is not active (status: {room.status.value})")

    # Note: In current implementation, we don't persist the picked role
    # because debate_turn in mediated mode accepts any role anyway.
    # This tool is informational/coordination only.
    # Future enhancement could add expected_next_role field to DebateRoom.

    return {
        "thread_id": room.thread_id,
        "next_role": role,
        "mode": room.mode.value,
    }
