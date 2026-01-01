"""debate_pick tool - Set next speaker in mediated mode (T6).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server

TDD: Implements minimal functionality to pass tests.

Note: This tool is only valid for mediated mode debates.
In fixed mode, role sequence is automatic (Wind->Wall->Door).

Issue #37: Now persists expected_next_role for enforcement in debate_turn.
Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

import os
from pathlib import Path
from typing import Any

from debate_hall_mcp.state import DebateMode, DebateStatus, load_debate_state, save_debate_state

# Environment variable for state directory (Issue #33)
STATE_DIR_ENV_VAR = "DEBATE_HALL_STATE_DIR"
DEFAULT_STATE_DIR = Path("./debates")


def get_state_dir() -> Path:
    """Get state directory from environment or use default.

    Returns:
        Path to state directory. Uses DEBATE_HALL_STATE_DIR env var if set
        and non-empty, otherwise falls back to ./debates for backwards
        compatibility.
    """
    env_value = os.environ.get(STATE_DIR_ENV_VAR, "")
    if env_value:
        return Path(env_value)
    return DEFAULT_STATE_DIR


# Use tuple for deterministic ordering in error messages (Issue #50)
VALID_ROLES = ("Wind", "Wall", "Door")


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

    Note (Issue #37):
        The picked role is persisted to expected_next_role field.
        debate_turn in mediated mode enforces this - wrong role is rejected.
        Calling pick again overwrites the expected role.
    """
    # Validate role
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {', '.join(VALID_ROLES)}")

    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

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

    # Persist expected role for enforcement (Issue #37)
    room.expected_next_role = role
    save_debate_state(room, state_dir)

    return {
        "thread_id": room.thread_id,
        "next_role": role,
        "mode": room.mode.value,
    }
