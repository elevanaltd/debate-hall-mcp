"""Debate engine logic for debate-hall-mcp.

This module implements:
- Turn sequence logic (fixed vs mediated modes)
- Resource limit enforcement (I3: Finite Dialectic Closure)
- Termination logic (synthesis, stalemate, exhaustion, force_close)
- Debate state transitions
- Synthesis validation (Issue #38: LOGOS semantics enforcement)

Immutables Compliance:
- I3 (FINITE_DIALECTIC_CLOSURE): Hard resource limits enforced
- I5 (SOVEREIGN_SAFETY_OVERRIDE): Force close capability
"""

from datetime import UTC, datetime
from enum import Enum

from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn
from debate_hall_mcp.validation import CognitionValidator, ValidationResult

# Minimum synthesis length for LOGOS validation (backward compat)
# Short synthesis (<100 chars) skips validation to support existing closes
MIN_SYNTHESIS_LENGTH_FOR_VALIDATION = 100


class TerminationReason(str, Enum):
    """Reasons for debate termination (I3, I5 compliance)."""

    SYNTHESIS = "synthesis"  # Door provided final synthesis
    STALEMATE = "stalemate"  # No convergence possible
    EXHAUSTION = "exhaustion"  # Resource limits reached (I3)
    FORCE_CLOSE = "force_close"  # Admin kill switch (I5)


def get_next_speaker(room: DebateRoom) -> str | None:
    """Determine next speaker based on mode and history.

    Args:
        room: Current debate room state

    Returns:
        Next role ("Wind", "Wall", "Door") for FIXED mode
        None for MEDIATED mode (orchestrator must pick)

    FIXED mode sequence:
        Empty → Wind
        Wind → Wall
        Wall → Door
        Door → Wind (cycle repeats)

    MEDIATED mode:
        Always returns None - orchestrator explicitly picks next role
    """
    if room.mode == DebateMode.MEDIATED:
        # Mediated mode: orchestrator must explicitly select next speaker
        return None

    # Fixed mode: Wind→Wall→Door→Wind cycle
    if not room.turns:
        return "Wind"

    last_role = room.turns[-1].role

    role_sequence = {"Wind": "Wall", "Wall": "Door", "Door": "Wind"}

    return role_sequence.get(last_role, "Wind")


def is_debate_exhausted(room: DebateRoom) -> bool:
    """Check if debate has exhausted resource limits (I3 compliance).

    A debate is exhausted when either:
    - Turn count >= max_turns, OR
    - Complete rounds >= max_rounds (1 round = 3 turns: Wind→Wall→Door)

    Args:
        room: Current debate room state

    Returns:
        True if resource limits exhausted, False otherwise
    """
    turn_count = len(room.turns)

    # Check max_turns limit
    if turn_count >= room.max_turns:
        return True

    # Check max_rounds limit (3 turns per round)
    complete_rounds = turn_count // 3
    return complete_rounds >= room.max_rounds


def can_add_turn(room: DebateRoom) -> bool:
    """Check if a turn can be added to the debate.

    Args:
        room: Current debate room state

    Returns:
        True if turn can be added, False otherwise

    Conditions:
        - Debate must be ACTIVE
        - Debate must not be exhausted
    """
    if room.status != DebateStatus.ACTIVE:
        return False

    return not is_debate_exhausted(room)


class DebateEngine:
    """Orchestrates debate logic and state transitions.

    Responsibilities:
    - Turn addition with hash chain maintenance (I4)
    - Resource limit enforcement (I3)
    - Debate termination (I3, I5)
    - Mode-specific logic (fixed vs mediated)
    """

    def __init__(self, room: DebateRoom) -> None:
        """Initialize engine with debate room.

        Args:
            room: Debate room to manage
        """
        self.room = room

    def add_turn(
        self,
        role: str,
        content: str,
        agent_role: str | None = None,
        model: str | None = None,
        cognition: str | None = None,
    ) -> None:
        """Add a turn to the debate with validation.

        Args:
            role: Agent role (Wind, Wall, Door)
            content: Turn content (should be OCTAVE format)
            agent_role: Optional operational agent role (Issue #4)
            model: Optional AI model identifier (Issue #4)
            cognition: Optional cognitive archetype (Issue #4)

        Raises:
            ValueError: If debate is not active or exhausted

        Side effects:
            - Appends Turn to room.turns
            - Maintains hash chain (previous_hash linkage)
            - Stores speaker identity metadata if provided
        """
        # Validate debate state
        if self.room.status != DebateStatus.ACTIVE:
            raise ValueError(
                f"Cannot add turn: debate is not active (status={self.room.status.value})"
            )

        if is_debate_exhausted(self.room):
            raise ValueError(
                f"Cannot add turn: debate is exhausted "
                f"(turns={len(self.room.turns)}, max={self.room.max_turns})"
            )

        # Get previous hash for chain
        previous_hash = self.room.turns[-1].hash if self.room.turns else None

        # Create turn with identity metadata (Issue #4)
        turn = Turn(
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            previous_hash=previous_hash,
            agent_role=agent_role,
            model=model,
            cognition=cognition,
        )

        # Add to room
        self.room.turns.append(turn)

    def close_debate(
        self, reason: TerminationReason, synthesis: str | None = None
    ) -> ValidationResult | None:
        """Close debate with specified termination reason.

        Args:
            reason: Why debate is ending
            synthesis: Final Door synthesis (required for SYNTHESIS reason)

        Returns:
            ValidationResult if synthesis was validated (SYNTHESIS reason only),
            None for other termination reasons.

        Raises:
            ValueError: If debate already closed
            ValueError: If synthesis fails validation in strict_cognition mode

        Side effects:
            - Updates room.status
            - Sets room.synthesis if provided
        """
        if self.room.status != DebateStatus.ACTIVE:
            raise ValueError(
                f"Cannot close debate: already closed (status={self.room.status.value})"
            )

        # Enforce synthesis requirement for SYNTHESIS termination (Issue #49)
        if reason == TerminationReason.SYNTHESIS and synthesis is None:
            raise ValueError("Synthesis content is required when closing with SYNTHESIS reason")

        validation_result: ValidationResult | None = None

        # Validate synthesis for SYNTHESIS termination (Issue #38)
        if reason == TerminationReason.SYNTHESIS and synthesis is not None:
            validation_result = self._validate_synthesis(synthesis)

        # Map termination reason to status
        status_map = {
            TerminationReason.SYNTHESIS: DebateStatus.SYNTHESIS,
            TerminationReason.STALEMATE: DebateStatus.STALEMATE,
            TerminationReason.EXHAUSTION: DebateStatus.EXHAUSTION,
            TerminationReason.FORCE_CLOSE: DebateStatus.FORCE_CLOSED,
        }

        self.room.status = status_map[reason]

        if synthesis is not None:
            self.room.synthesis = synthesis

        return validation_result

    def _validate_synthesis(self, synthesis: str) -> ValidationResult:
        """Validate synthesis content against LOGOS rules (Issue #38).

        Synthesis is the final Door output and must follow LOGOS cognition:
        - Numbered reasoning steps (BLOCK if missing in strict mode)
        - Synthesis markers like TENSION, PATTERN, CLARITY (WARN if missing)

        Backward compatibility: Short synthesis (<100 chars) skips validation.

        Args:
            synthesis: Synthesis content to validate

        Returns:
            ValidationResult with level and any violations/hints

        Raises:
            ValueError: If synthesis fails validation in strict_cognition mode
        """
        # Backward compatibility: short synthesis skips validation
        if len(synthesis.strip()) < MIN_SYNTHESIS_LENGTH_FOR_VALIDATION:
            if self.room.strict_cognition:
                # In strict mode, even short synthesis must follow LOGOS rules
                pass  # Fall through to validation
            else:
                # Non-strict: allow short synthesis without validation
                return ValidationResult(level="PASS", violations=[], hints=[])

        # Validate using LOGOS rules (Door cognition)
        validator = CognitionValidator()
        result = validator.validate(
            role="Door",
            content=synthesis,
            cognition="LOGOS",
            strict=self.room.strict_cognition,
        )

        # In strict mode, BLOCK-level violations raise ValueError
        if self.room.strict_cognition and result.level == "BLOCK":
            violations_str = "; ".join(result.violations)
            raise ValueError(f"Synthesis validation failed: {violations_str}")

        return result
