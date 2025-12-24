"""debate_admin tools - Administrative controls (T7).

Immutables Compliance:
- I5 (SOVEREIGN_SAFETY_OVERRIDE): Force close capability
- I4 (VERIFIABLE_EVENT_LEDGER): Tombstone preserves hash chain

TDD: Implements minimal functionality to pass tests.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state


def debate_force_close(
    thread_id: str,
    reason: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Force close a debate immediately (I5 safety override).

    This is an administrative kill switch that works regardless of debate state.
    Unlike normal close, this does NOT require the debate to be active.

    Args:
        thread_id: Thread identifier
        reason: Reason for force close
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with force close summary:
        - thread_id: Thread identifier
        - status: New status (force_closed)
        - reason: Reason for force close

    Raises:
        FileNotFoundError: If thread doesn't exist
    """
    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Force close (I5: safety override - works regardless of current status)
    room.status = DebateStatus.FORCE_CLOSED

    # Save updated state
    save_debate_state(room, state_dir)

    return {
        "thread_id": room.thread_id,
        "status": room.status.value,
        "reason": reason,
    }


def debate_tombstone(
    thread_id: str,
    turn_index: int,
    reason: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Redact a turn's content while preserving hash chain (I4).

    Tombstoning replaces turn content with "[REDACTED: reason]" but preserves
    the cryptographic hash chain. This allows content removal while maintaining
    ledger integrity.

    Args:
        thread_id: Thread identifier
        turn_index: Index of turn to tombstone (0-based)
        reason: Reason for redaction
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with tombstone summary:
        - thread_id: Thread identifier
        - turn_index: Index of tombstoned turn
        - reason: Reason for redaction

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If turn_index is invalid
    """
    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Validate turn index
    if turn_index < 0 or turn_index >= len(room.turns):
        raise ValueError(
            f"Invalid turn index: {turn_index}. Valid range: 0-{len(room.turns) - 1}"
        )

    # Redact content (hash remains unchanged - I4 compliance)
    room.turns[turn_index].content = f"[REDACTED: {reason}]"

    # Save updated state
    save_debate_state(room, state_dir)

    return {
        "thread_id": room.thread_id,
        "turn_index": turn_index,
        "reason": reason,
    }
