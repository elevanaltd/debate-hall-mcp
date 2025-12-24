"""Debate engine logic for debate-hall-mcp.

This module implements:
- Turn sequence logic (fixed vs mediated modes)
- Resource limit enforcement (I3: Finite Dialectic Closure)
- Termination logic (synthesis, stalemate, exhaustion, force_close)
- Debate state transitions

Immutables Compliance:
- I3 (FINITE_DIALECTIC_CLOSURE): Hard resource limits enforced
- I5 (SOVEREIGN_SAFETY_OVERRIDE): Force close capability
"""

from datetime import UTC, datetime
from enum import Enum

from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn


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

    def add_turn(self, role: str, content: str) -> None:
        """Add a turn to the debate with validation.

        Args:
            role: Agent role (Wind, Wall, Door)
            content: Turn content (should be OCTAVE format)

        Raises:
            ValueError: If debate is not active or exhausted

        Side effects:
            - Appends Turn to room.turns
            - Maintains hash chain (previous_hash linkage)
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

        # Create turn
        turn = Turn(
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            previous_hash=previous_hash,
        )

        # Add to room
        self.room.turns.append(turn)

    def close_debate(self, reason: TerminationReason, synthesis: str | None = None) -> None:
        """Close debate with specified termination reason.

        Args:
            reason: Why debate is ending
            synthesis: Final Door synthesis (required for SYNTHESIS reason)

        Raises:
            ValueError: If debate already closed

        Side effects:
            - Updates room.status
            - Sets room.synthesis if provided
        """
        if self.room.status != DebateStatus.ACTIVE:
            raise ValueError(
                f"Cannot close debate: already closed (status={self.room.status.value})"
            )

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
