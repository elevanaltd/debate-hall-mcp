"""debate_close tool - Finalize debate (T5).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I2 (UNIVERSAL_OCTAVE_BINDING): OCTAVE output format support (Issue #29)

TDD: Implements minimal functionality to pass tests.

Issue #38: Synthesis semantics validation
- Synthesis validated against LOGOS rules (numbered steps, synthesis markers)
- Non-strict mode: WARN on invalid structure (close proceeds)
- Strict mode: BLOCK on invalid structure (close fails)

Issue #29: OCTAVE auto-generate on close
- output_format parameter: 'json' (default), 'octave', 'both'
- Generates compressed OCTAVE transcript representation

Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
"""

import os
from pathlib import Path
from typing import Any, Literal

from debate_hall_mcp.engine import DebateEngine, TerminationReason
from debate_hall_mcp.octave_formatter import format_debate_as_octave
from debate_hall_mcp.state import load_debate_state, save_debate_state

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


# Valid output format values
OutputFormat = Literal["json", "octave", "both"]


def debate_close(
    thread_id: str,
    synthesis: str,
    state_dir: Path | None = None,
    output_format: OutputFormat | None = None,
) -> dict[str, Any] | str:
    """Close debate with final synthesis.

    Synthesis content is validated against LOGOS/Door cognition rules:
    - Numbered reasoning steps (BLOCK if missing in strict mode)
    - Synthesis markers like TENSION, PATTERN, CLARITY (WARN if missing)

    Args:
        thread_id: Thread identifier
        synthesis: Final Door synthesis content
        state_dir: Directory for state files (defaults to ./debates)
        output_format: Output format - 'json', 'octave', or 'both'.
            If not specified, defaults to 'octave' when octave_mode=True,
            otherwise 'json' (Issue #26)

    Returns:
        Depends on output_format:
        - 'json': Dictionary with close summary (backwards compatible)
        - 'octave': OCTAVE-formatted string
        - 'both': Dictionary with 'json' and 'octave' keys

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate already closed or synthesis empty
        ValueError: If synthesis fails validation in strict_cognition mode
        ValueError: If output_format is not valid
    """
    # Validate synthesis is non-empty
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis required for debate close")

    # Validate output_format if explicitly provided
    valid_formats = ("json", "octave", "both")
    if output_format is not None and output_format not in valid_formats:
        raise ValueError(
            f"Invalid output_format '{output_format}'. Must be one of: {valid_formats}"
        )

    # Default state directory (Issue #33: env var support)
    if state_dir is None:
        state_dir = get_state_dir()

    # Load state
    room = load_debate_state(thread_id, state_dir)

    # Determine effective output format (Issue #26: octave_mode support)
    # If not explicitly specified, use "octave" when octave_mode=True, else "json"
    effective_format: OutputFormat
    if output_format is not None:
        effective_format = output_format
    elif room.octave_mode:
        effective_format = "octave"
    else:
        effective_format = "json"

    # Close debate via engine (validates active state and synthesis content)
    engine = DebateEngine(room)
    validation_result = engine.close_debate(TerminationReason.SYNTHESIS, synthesis=synthesis)

    # Save updated state
    save_debate_state(room, state_dir)

    # Build JSON response (used for 'json' and 'both' formats)
    json_result: dict[str, Any] = {
        "thread_id": room.thread_id,
        "status": room.status.value,
        "synthesis": room.synthesis,
    }

    # Include validation warnings if any (WARN level, non-strict mode)
    if validation_result is not None and validation_result.violations:
        json_result["validation_warnings"] = validation_result.violations

    # Return based on effective_format (Issue #26: respects octave_mode default)
    if effective_format == "json":
        return json_result
    elif effective_format == "octave":
        return format_debate_as_octave(room)
    else:  # effective_format == "both"
        return {
            "json": json_result,
            "octave": format_debate_as_octave(room),
        }
