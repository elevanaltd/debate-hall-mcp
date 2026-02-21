"""debate_turn tool - Record agent turn (T2).

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I4 (VERIFIABLE_EVENT_LEDGER): Hash chain maintained

TDD: Implements minimal functionality to pass tests.

Issue #37: Enforces expected_next_role in mediated mode.
Issue #33: State directory configurable via DEBATE_HALL_STATE_DIR env var.
Issue #178: Committee member tracking (awaiting/responses) post-turn hook.
"""

import re
from pathlib import Path
from typing import Any

from debate_hall_mcp.engine import DebateEngine, get_next_speaker
from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    SessionType,
    get_state_dir,
    load_debate_state,
    save_debate_state,
)
from debate_hall_mcp.validation import CognitionValidator

# Pattern to match NO-GO/NOGO at start of content (Issue #178)
_GO_NOGO_PATTERN = re.compile(
    r"^(?:NO[-\s]?GO|NOGO)\b",
    re.IGNORECASE,
)
# Pattern to match GO at start of content (Issue #178)
_GO_PATTERN = re.compile(
    r"^GO\b",
    re.IGNORECASE,
)


def _extract_go_nogo(content: str) -> str:
    """Extract GO/NO-GO signal from turn content (Issue #178).

    Attempts to identify GO or NO-GO from the start of content.
    NO-GO is checked first (since "GO" is a substring of "NO-GO").

    Args:
        content: The turn content to parse

    Returns:
        "GO", "NO-GO", or the full content if extraction fails
    """
    stripped = content.strip()
    if _GO_NOGO_PATTERN.match(stripped):
        return "NO-GO"
    if _GO_PATTERN.match(stripped):
        return "GO"
    return content


def _update_committee_tracking(
    room: DebateRoom,
    role: str,
    content: str,
) -> None:
    """Post-turn hook for committee member tracking (Issue #178).

    When a turn is added to a committee session and the role is in
    committee_metadata.awaiting:
    - Remove the role from awaiting
    - Add to responses dict (with GO/NO-GO extraction for go_nogo type)

    This function mutates room state in-place. The caller is responsible
    for saving the updated state.

    Args:
        room: The DebateRoom (mutated in-place)
        role: The role that just spoke
        content: The turn content
    """
    if room.session_type != SessionType.COMMITTEE:
        return
    if room.committee_metadata is None:
        return
    if role not in room.committee_metadata.awaiting:
        return

    # Remove from awaiting
    room.committee_metadata.awaiting.remove(role)

    # Determine response value
    if room.committee_metadata.decision_type == "go_nogo":
        response_value = _extract_go_nogo(content)
    else:
        response_value = content

    # Record response
    room.committee_metadata.responses[role] = response_value


def debate_turn(
    thread_id: str,
    role: str,
    content: str,
    state_dir: Path | None = None,
    agent_role: str | None = None,
    model: str | None = None,
    cognition: str | None = None,
    token_input: int | None = None,
    token_output: int | None = None,
    token_total: int | None = None,
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
        token_input: Optional input token count for this turn
        token_output: Optional output token count for this turn
        token_total: Optional total token count for this turn

    Returns:
        Dictionary with turn summary:
        - thread_id: Thread identifier
        - turn_count: Total turns after this one
        - role: Role that just spoke
        - status: Current debate status
        - turn_hash: SHA-256 hash of the turn (Issue #147: for event correlation)
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

    # Cognition validation conditional on Wind/Wall/Door roles (Issue #174)
    # Non-triad roles skip cognition validation entirely — accept cognition as-is
    _TRIAD_ROLES = {"Wind", "Wall", "Door"}
    is_triad_role = role in _TRIAD_ROLES

    # Validate cognition before state modification (behavioral firewall)
    # Read strict_cognition from room configuration (prevents client bypass)
    validator = CognitionValidator()
    if is_triad_role:
        validation_result = validator.validate(
            role=role, content=content, cognition=cognition, strict=room.strict_cognition
        )
    else:
        # Non-triad roles: only enforce content length (DoS protection)
        validation_result = validator.validate(
            role=role, content=content, cognition=None, strict=False
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
    # For non-triad roles, strip cognition to None since Turn model only accepts
    # PATHOS/ETHOS/LOGOS (Issue #174: non-triad roles skip cognition entirely)
    effective_cognition = cognition if is_triad_role else None

    engine = DebateEngine(room)
    engine.add_turn(
        role=role,
        content=content,
        agent_role=agent_role,
        model=model,
        cognition=effective_cognition,
        token_input=token_input,
        token_output=token_output,
        token_total=token_total,
    )

    # Clear expected_next_role after successful turn (Issue #37)
    # This requires a new pick before the next turn in mediated mode
    if room.mode == DebateMode.MEDIATED:
        room.expected_next_role = None

    # Post-turn hook: committee member tracking (Issue #178)
    # When a committee member adds a turn, update awaiting/responses
    _update_committee_tracking(room, role, content)

    # Save updated state
    save_debate_state(room, state_dir)

    # Build response with optional warnings
    # Include turn_hash for event correlation (Issue #147)
    response: dict[str, Any] = {
        "thread_id": room.thread_id,
        "turn_count": len(room.turns),
        "role": role,
        "status": room.status.value,
        "turn_hash": room.turns[-1].hash,
    }

    # Include validation warnings if any (WARN or non-strict BLOCK)
    if validation_result.violations and validation_result.level in ("WARN", "BLOCK"):
        response["cognition_warnings"] = validation_result.violations

    return response
