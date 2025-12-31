"""debate_close tool - Finalize debate (T5).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server

TDD: Implements minimal functionality to pass tests.

Issue #38: Synthesis semantics validation
- Synthesis validated against LOGOS rules (numbered steps, synthesis markers)
- Non-strict mode: WARN on invalid structure (close proceeds)
- Strict mode: BLOCK on invalid structure (close fails)
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

    Synthesis content is validated against LOGOS/Door cognition rules:
    - Numbered reasoning steps (BLOCK if missing in strict mode)
    - Synthesis markers like TENSION, PATTERN, CLARITY (WARN if missing)

    Args:
        thread_id: Thread identifier
        synthesis: Final Door synthesis content
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with close summary:
        - thread_id: Thread identifier
        - status: New status (synthesis)
        - synthesis: Final synthesis content
        - validation_warnings: List of validation warnings (if any, non-strict only)

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate already closed or synthesis empty
        ValueError: If synthesis fails validation in strict_cognition mode
    """
    # Validate synthesis is non-empty
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis required for debate close")

    # Default state directory
    if state_dir is None:
        state_dir = Path("./debates")

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Close debate via engine (validates active state and synthesis content)
    engine = DebateEngine(room)
    validation_result = engine.close_debate(TerminationReason.SYNTHESIS, synthesis=synthesis)

    # Save updated state
    save_debate_state(room, state_dir)

    # Build response
    result: dict[str, Any] = {
        "thread_id": room.thread_id,
        "status": room.status.value,
        "synthesis": room.synthesis,
    }

    # Include validation warnings if any (WARN level, non-strict mode)
    if validation_result is not None and validation_result.violations:
        result["validation_warnings"] = validation_result.violations

    return result
