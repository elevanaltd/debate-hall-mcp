"""debate_get tool - Unified read operation for debate state.

Consolidates get_status + get_next_prompt into single tool.
Difference: include_transcript parameter controls transcript inclusion.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): Resource limits visible

Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import get_next_speaker
from debate_hall_mcp.state import DebateStatus, load_debate_state

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


# View-layer only: never stored in DB, never affects hash chain
OCTAVE_PREAMBLE_CONTENT = """===PROTOCOL===
FORMAT::OCTAVE[recommended]
SYNTAX::[KEY::value, LIST::[a,b], FLOW::A->B->C]
OPERATORS::[::=assignment, []=list, ->=flow, +=synthesis]
NOTE::"Using OCTAVE format improves token efficiency. Optional but recommended."
===END==="""


def debate_get(
    thread_id: str,
    include_transcript: bool = False,
    include_metadata: bool = False,
    context_lines: int | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Get debate state, optionally with transcript.

    Args:
        thread_id: Thread identifier
        include_transcript: If True, include turn history
        include_metadata: If True, include agent_role/model/cognition for each turn
        context_lines: Limit transcript to N recent turns (None = all)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate state (always):
        - thread_id, topic, mode, status, turn_count, max_turns, max_rounds, next_role
        - synthesis (if present)
        - transcript (if include_transcript=True)

    Raises:
        FileNotFoundError: If thread doesn't exist
    """
    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

    room = load_debate_state(thread_id, state_dir)

    next_role = None
    if room.status == DebateStatus.ACTIVE:
        next_role = get_next_speaker(room)

    result: dict[str, Any] = {
        "thread_id": room.thread_id,
        "topic": room.topic,
        "mode": room.mode.value,
        "status": room.status.value,
        "turn_count": len(room.turns),
        "max_turns": room.max_turns,
        "max_rounds": room.max_rounds,
        "next_role": next_role,
        "octave_mode": room.octave_mode,
    }

    if room.synthesis is not None:
        result["synthesis"] = room.synthesis

    if include_transcript:
        turns_to_include = room.turns
        if context_lines is not None and context_lines > 0:
            turns_to_include = room.turns[-context_lines:]

        transcript: list[dict[str, Any]] = []

        # Prepend OCTAVE preamble if enabled (view-layer only)
        if room.octave_preamble:
            transcript.append(
                {
                    "role": "System",
                    "content": OCTAVE_PREAMBLE_CONTENT,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        # Add actual turns
        transcript.extend(
            {
                "role": turn.role,
                **(
                    {
                        "agent_role": turn.agent_role,
                        "model": turn.model,
                        "cognition": turn.cognition,
                    }
                    if include_metadata
                    else {}
                ),
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in turns_to_include
        )

        result["transcript"] = transcript

    return result
