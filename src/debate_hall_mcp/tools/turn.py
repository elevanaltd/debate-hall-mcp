"""debate_turn tool - Record agent turn (T2).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I4 (VERIFIABLE_EVENT_LEDGER): Hash chain maintained

TDD: Implements minimal functionality to pass tests.

Issue #37: Enforces expected_next_role in mediated mode.
Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

import os
from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import DebateEngine, get_next_speaker
from debate_hall_mcp.state import DebateMode, load_debate_state, save_debate_state
from debate_hall_mcp.validation import CognitionValidator

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


def debate_turn(
    thread_id: str,
    role: str,
    content: str,
    state_dir: Path | None = None,
    agent_role: str | None = None,
    model: str | None = None,
    cognition: str | None = None,
) -> dict[str, Any]:
    """Record an agent turn in the debate.

    Args:
        thread_id: Thread identifier
        role: Agent role (Wind, Wall, Door)
        content: Turn content (OCTAVE format expected)
        state_dir: Directory for state files (defaults to ./debates)
        agent_role: Optional operational agent role (Issue #4)
        model: Optional AI model identifier (Issue #4)
        cognition: Optional cognitive archetype (Issue #4)

    Returns:
        Dictionary with turn summary:
        - thread_id: Thread identifier
        - turn_count: Total turns after this one
        - role: Role that just spoke
        - status: Current debate status
        - cognition_warnings: List of validation warnings (if any)

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate is not active, exhausted, role is wrong, or cognition validation fails in strict mode

    Note:
        Cognition enforcement mode (strict_cognition) is set at room creation time,
        not per-turn. This prevents callers from bypassing the behavioral firewall.
    """
    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # In fixed mode, validate role matches expected sequence
    if room.mode == DebateMode.FIXED:
        expected_role = get_next_speaker(room)
        if role != expected_role:
            raise ValueError(f"Expected role '{expected_role}' but got '{role}' in fixed mode")

    # In mediated mode, validate role matches pick (if pick was made) - Issue #37
    if (
        room.mode == DebateMode.MEDIATED
        and room.expected_next_role is not None
        and role != room.expected_next_role
    ):
        raise ValueError(
            f"Expected role '{room.expected_next_role}' but got '{role}' in mediated mode"
        )

    # Validate cognition before state modification (behavioral firewall)
    # Read strict_cognition from room configuration (prevents client bypass)
    validator = CognitionValidator()
    validation_result = validator.validate(
        role=role, content=content, cognition=cognition, strict=room.strict_cognition
    )

    # Handle validation result
    if validation_result.level == "BLOCK":
        # Check if this is a content length violation (always blocks, regardless of strict mode)
        is_length_violation = any(
            "exceeds maximum length" in v.lower() for v in validation_result.violations
        )

        if is_length_violation or room.strict_cognition:
            # BLOCK: Content length violations OR strict mode cognition violations
            error_msg = "\n".join(validation_result.violations)
            if validation_result.hints:
                error_msg += "\n\nHints:\n"
                error_msg += "\n".join(f"  - {h}" for h in validation_result.hints)
            raise ValueError(error_msg)

    # Add turn via engine (validates active state and limits)
    engine = DebateEngine(room)
    engine.add_turn(
        role=role,
        content=content,
        agent_role=agent_role,
        model=model,
        cognition=cognition,
    )

    # Clear expected_next_role after successful turn (Issue #37)
    # This requires a new pick before the next turn in mediated mode
    if room.mode == DebateMode.MEDIATED:
        room.expected_next_role = None

    # Save updated state
    save_debate_state(room, state_dir)

    # Build response with optional warnings
    response: dict[str, Any] = {
        "thread_id": room.thread_id,
        "turn_count": len(room.turns),
        "role": role,
        "status": room.status.value,
    }

    # Include validation warnings if any (WARN or non-strict BLOCK)
    if validation_result.violations and validation_result.level in ("WARN", "BLOCK"):
        response["cognition_warnings"] = validation_result.violations

    return response
