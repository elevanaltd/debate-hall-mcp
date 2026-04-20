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

Issue #138: Context Compiler integration
- export_decision parameter: Export DecisionRecord to context directory
- Exports to .hestai/state/context/decisions/{date}-{topic-slug}.oct.md
"""

from pathlib import Path
from typing import Any, Literal

from debate_hall_mcp.context_compiler import (
    export_decision_to_context,
    get_context_dir,
)
from debate_hall_mcp.decision import extract_decision_record
from debate_hall_mcp.engine import DebateEngine, TerminationReason
from debate_hall_mcp.octave_formatter import format_debate_as_octave, seal_debate_transcript
from debate_hall_mcp.state import get_state_dir, load_debate_state, save_debate_state

# Valid output format values
OutputFormat = Literal["json", "octave", "both"]


def debate_close(
    thread_id: str,
    synthesis: str,
    state_dir: Path | None = None,
    output_format: OutputFormat | None = None,
    status: str | None = None,
    seal: bool = False,
    export_decision: bool = False,
    context_dir: Path | None = None,
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
        status: Override termination reason - 'synthesis' (default) or 'stalemate'.
            Used by auto-orchestration for consensus loop failures.
        seal: If True, add cryptographic seal to OCTAVE output (v1.0.0 feature).
            The seal enables tamper detection - any modification to the transcript
            will invalidate the seal. Only applies to 'octave' and 'both' formats.
        export_decision: If True, export DecisionRecord to context directory
            (Issue #138). Creates .hestai/state/context/decisions/{date}-{topic}.oct.md
        context_dir: Directory for context exports. Defaults to project-relative
            .hestai/state/context or DEBATE_HALL_CONTEXT_DIR env var.

    Returns:
        Depends on output_format:
        - 'json': Dictionary with close summary (backwards compatible)
        - 'octave': OCTAVE-formatted string (sealed if seal=True)
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

    # Determine termination reason from status parameter (Phase 4: consensus loop)
    termination_reason = TerminationReason.SYNTHESIS
    if status == "stalemate":
        termination_reason = TerminationReason.STALEMATE

    # Close debate via engine (validates active state and synthesis content)
    engine = DebateEngine(room)
    validation_result = engine.close_debate(termination_reason, synthesis=synthesis)

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

    # Export decision to context if requested (Issue #138: Context Compiler)
    if export_decision:
        # Extract decision record from closed debate
        decision_record = extract_decision_record(room)

        # Use provided context_dir or auto-detect
        effective_context_dir = context_dir if context_dir is not None else get_context_dir()

        # Export to context directory
        export_path = export_decision_to_context(decision_record, effective_context_dir)
        json_result["export_path"] = str(export_path)

    # Return based on effective_format (Issue #26: respects octave_mode default)
    if effective_format == "json":
        return json_result
    elif effective_format == "octave":
        octave_output = format_debate_as_octave(room)
        if seal:
            octave_output = seal_debate_transcript(octave_output)
        return octave_output
    else:  # effective_format == "both"
        octave_output = format_debate_as_octave(room)
        if seal:
            octave_output = seal_debate_transcript(octave_output)
        return {
            "json": json_result,
            "octave": octave_output,
        }
