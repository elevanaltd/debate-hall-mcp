"""debate_init tool - Initialize new debate thread (T1).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits enforced

TDD: Implements minimal functionality to pass tests.

Issue #30: Thread IDs must use date-first format (YYYY-MM-DD-subject)
for chronological sorting and HestAI ecosystem alignment.

Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp.state import DebateMode, DebateRoom, save_debate_state

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


# Pattern for date-first thread_id: YYYY-MM-DD-subject
# Subject must start with alphanumeric, followed by alphanumeric, hyphens, underscores, or single dots
# Security: Excludes path separators (/, \) and path traversal (..)
THREAD_ID_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-zA-Z0-9][a-zA-Z0-9._-]*)$")

# Patterns that indicate path traversal or directory injection attempts
PATH_UNSAFE_PATTERNS = ["..", "/", "\\"]


def validate_thread_id(thread_id: str) -> None:
    """Validate thread_id uses date-first format (YYYY-MM-DD-subject).

    Security: Rejects path traversal sequences (..) and directory separators (/, \\)
    to prevent file system injection attacks.

    Args:
        thread_id: Thread identifier to validate

    Raises:
        ValueError: If thread_id doesn't match date-first format, contains unsafe
            characters, or date is invalid

    Examples:
        Valid: "2025-12-28-debate-topic", "2024-02-29-leap-year", "2025-01-01-v1.0"
        Invalid: "debate-topic-2025-12-28", "2025-12-28", "2025-01-01-../etc"
    """
    # Security check: Reject path-unsafe patterns before regex matching
    for pattern in PATH_UNSAFE_PATTERNS:
        if pattern in thread_id:
            raise ValueError(
                f"Invalid thread_id '{thread_id}': must use date-first format "
                "YYYY-MM-DD-subject (e.g., '2025-12-28-debate-topic')"
            )

    match = THREAD_ID_PATTERN.match(thread_id)
    if not match:
        raise ValueError(
            f"Invalid thread_id '{thread_id}': must use date-first format "
            "YYYY-MM-DD-subject (e.g., '2025-12-28-debate-topic')"
        )

    year, month, day, _subject = match.groups()

    # Validate calendar date
    try:
        datetime(int(year), int(month), int(day))
    except ValueError as e:
        raise ValueError(
            f"Invalid thread_id '{thread_id}': {e}. "
            "Must use date-first format with valid calendar date."
        ) from e


def debate_init(
    thread_id: str,
    topic: str,
    mode: str = "fixed",
    max_turns: int = 12,
    max_rounds: int = 4,
    strict_cognition: bool = False,
    octave_preamble: bool = True,
    octave_mode: bool = True,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Initialize a new debate thread.

    Args:
        thread_id: Unique thread identifier in date-first format (YYYY-MM-DD-subject).
            Example: "2025-12-28-north-star-debate". Required for chronological sorting
            and HestAI ecosystem alignment.
        topic: Debate topic
        mode: Orchestration mode ("fixed" or "mediated")
        max_turns: Maximum turns allowed (I3 compliance)
        max_rounds: Maximum rounds allowed (I3 compliance)
        strict_cognition: If True, BLOCK-level cognition violations reject turns (behavioral firewall)
        octave_preamble: If True, prepend OCTAVE format guidance to transcripts (default: True)
        octave_mode: Enable OCTAVE-mode debates with skills-based compression
            and OCTAVE output default on close (Issue #26). Default: True.
            Set False for JSON output.
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate summary:
        - thread_id: Thread identifier
        - topic: Debate topic
        - mode: Orchestration mode
        - status: Current status
        - max_turns: Turn limit
        - max_rounds: Round limit
        - strict_cognition: Cognition enforcement mode
        - octave_preamble: Whether OCTAVE preamble is enabled
        - octave_mode: Whether OCTAVE-mode is enabled (Issue #26)
        - turn_count: Current turn count (0 for new debate)

    Raises:
        ValueError: If mode is invalid or thread_id format is invalid
        FileExistsError: If thread_id already exists
    """
    # Validate thread_id format (Issue #30: date-first convention)
    validate_thread_id(thread_id)

    # Validate mode
    if mode not in ("fixed", "mediated"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'fixed' or 'mediated'")

    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

    # Check if thread already exists
    state_file = state_dir / f"{thread_id}.json"
    if state_file.exists():
        raise FileExistsError(f"Thread {thread_id} already exists at {state_file}")

    # Create debate room
    room = DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode(mode),
        max_turns=max_turns,
        max_rounds=max_rounds,
        strict_cognition=strict_cognition,
        octave_preamble=octave_preamble,
        octave_mode=octave_mode,
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
        "strict_cognition": room.strict_cognition,
        "octave_preamble": room.octave_preamble,
        "octave_mode": room.octave_mode,
        "turn_count": len(room.turns),
    }
