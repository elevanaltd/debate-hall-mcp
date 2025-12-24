"""Unit tests for debate_hall_mcp.engine module.

Tests cover:
- Turn sequence logic (fixed and mediated modes)
- Mode switching behavior
- Resource limit enforcement (max_turns, max_rounds)
- Termination conditions (synthesis, stalemate, exhaustion, force_close)
- Next speaker determination
"""

from datetime import datetime, timezone

import pytest

from debate_hall_mcp.engine import (
    DebateEngine,
    TerminationReason,
    get_next_speaker,
    is_debate_exhausted,
    can_add_turn,
)
from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn


class TestGetNextSpeaker:
    """Test next speaker determination logic."""

    def test_fixed_mode_sequence_wind_first(self) -> None:
        """Fixed mode: empty debate starts with Wind."""
        room = DebateRoom(
            thread_id="test-001",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        assert get_next_speaker(room) == "Wind"

    def test_fixed_mode_sequence_wind_wall_door(self) -> None:
        """Fixed mode: follows Wind→Wall→Door→Wind cycle."""
        room = DebateRoom(
            thread_id="test-002",
            topic="Test",
            mode=DebateMode.FIXED,
        )

        # Wind turn
        room.turns.append(Turn(
            role="Wind",
            content="Test",
            timestamp=datetime.now(timezone.utc),
            previous_hash=None,
        ))
        assert get_next_speaker(room) == "Wall"

        # Wall turn
        room.turns.append(Turn(
            role="Wall",
            content="Test",
            timestamp=datetime.now(timezone.utc),
            previous_hash=room.turns[-1].hash,
        ))
        assert get_next_speaker(room) == "Door"

        # Door turn
        room.turns.append(Turn(
            role="Door",
            content="Test",
            timestamp=datetime.now(timezone.utc),
            previous_hash=room.turns[-1].hash,
        ))
        assert get_next_speaker(room) == "Wind"

    def test_mediated_mode_requires_explicit_role(self) -> None:
        """Mediated mode: cannot determine next speaker automatically."""
        room = DebateRoom(
            thread_id="test-003",
            topic="Test",
            mode=DebateMode.MEDIATED,
        )
        # In mediated mode, orchestrator must explicitly pick next role
        # get_next_speaker returns None to signal manual selection needed
        assert get_next_speaker(room) is None


class TestIsDebateExhausted:
    """Test resource exhaustion detection."""

    def test_not_exhausted_empty(self) -> None:
        """Empty debate is not exhausted."""
        room = DebateRoom(
            thread_id="test-004",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=12,
        )
        assert is_debate_exhausted(room) is False

    def test_exhausted_max_turns(self) -> None:
        """Debate exhausted when max_turns reached."""
        room = DebateRoom(
            thread_id="test-005",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=3,
        )

        # Add 3 turns
        for i in range(3):
            role = ["Wind", "Wall", "Door"][i]
            prev_hash = room.turns[-1].hash if room.turns else None
            room.turns.append(Turn(
                role=role,
                content=f"Turn {i}",
                timestamp=datetime.now(timezone.utc),
                previous_hash=prev_hash,
            ))

        assert is_debate_exhausted(room) is True

    def test_exhausted_max_rounds(self) -> None:
        """Debate exhausted when max_rounds completed (3 turns per round)."""
        room = DebateRoom(
            thread_id="test-006",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=100,  # High turn limit
            max_rounds=2,  # Only 2 rounds allowed (6 turns)
        )

        # Add 6 turns (2 complete rounds: Wind→Wall→Door × 2)
        roles = ["Wind", "Wall", "Door", "Wind", "Wall", "Door"]
        for i, role in enumerate(roles):
            prev_hash = room.turns[-1].hash if room.turns else None
            room.turns.append(Turn(
                role=role,
                content=f"Turn {i}",
                timestamp=datetime.now(timezone.utc),
                previous_hash=prev_hash,
            ))

        assert is_debate_exhausted(room) is True


class TestCanAddTurn:
    """Test turn addition validation."""

    def test_can_add_turn_when_active(self) -> None:
        """Can add turn when debate is ACTIVE and not exhausted."""
        room = DebateRoom(
            thread_id="test-007",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=12,
        )
        assert can_add_turn(room) is True

    def test_cannot_add_turn_when_exhausted(self) -> None:
        """Cannot add turn when debate is exhausted."""
        room = DebateRoom(
            thread_id="test-008",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=1,
        )

        room.turns.append(Turn(
            role="Wind",
            content="Only turn",
            timestamp=datetime.now(timezone.utc),
            previous_hash=None,
        ))

        assert can_add_turn(room) is False

    def test_cannot_add_turn_when_closed(self) -> None:
        """Cannot add turn when debate status is not ACTIVE."""
        room = DebateRoom(
            thread_id="test-009",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        assert can_add_turn(room) is False


class TestDebateEngine:
    """Test DebateEngine orchestration logic."""

    def test_engine_initialization(self) -> None:
        """Engine initializes with debate room."""
        room = DebateRoom(
            thread_id="test-010",
            topic="Test Topic",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)
        assert engine.room == room

    def test_add_turn_success(self) -> None:
        """Add turn to active debate."""
        room = DebateRoom(
            thread_id="test-011",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.add_turn("Wind", "First turn content")

        assert len(room.turns) == 1
        assert room.turns[0].role == "Wind"
        assert room.turns[0].content == "First turn content"
        assert room.turns[0].previous_hash is None

    def test_add_turn_maintains_hash_chain(self) -> None:
        """Adding turns maintains hash chain."""
        room = DebateRoom(
            thread_id="test-012",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.add_turn("Wind", "First")
        engine.add_turn("Wall", "Second")
        engine.add_turn("Door", "Third")

        assert room.turns[0].previous_hash is None
        assert room.turns[1].previous_hash == room.turns[0].hash
        assert room.turns[2].previous_hash == room.turns[1].hash

    def test_add_turn_raises_when_exhausted(self) -> None:
        """Adding turn raises when debate exhausted."""
        room = DebateRoom(
            thread_id="test-013",
            topic="Test",
            mode=DebateMode.FIXED,
            max_turns=1,
        )
        engine = DebateEngine(room)

        engine.add_turn("Wind", "Only turn")

        with pytest.raises(ValueError, match="exhausted"):
            engine.add_turn("Wall", "Should fail")

    def test_add_turn_raises_when_not_active(self) -> None:
        """Adding turn raises when debate not ACTIVE."""
        room = DebateRoom(
            thread_id="test-014",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        engine = DebateEngine(room)

        with pytest.raises(ValueError, match="not active"):
            engine.add_turn("Wind", "Should fail")

    def test_close_debate_synthesis(self) -> None:
        """Close debate with synthesis."""
        room = DebateRoom(
            thread_id="test-015",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.close_debate(
            reason=TerminationReason.SYNTHESIS,
            synthesis="Final synthesis content"
        )

        assert room.status == DebateStatus.SYNTHESIS
        assert room.synthesis == "Final synthesis content"

    def test_close_debate_exhaustion(self) -> None:
        """Close debate due to exhaustion."""
        room = DebateRoom(
            thread_id="test-016",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.close_debate(reason=TerminationReason.EXHAUSTION)

        assert room.status == DebateStatus.EXHAUSTION
        assert room.synthesis is None

    def test_close_debate_stalemate(self) -> None:
        """Close debate due to stalemate."""
        room = DebateRoom(
            thread_id="test-017",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.close_debate(reason=TerminationReason.STALEMATE)

        assert room.status == DebateStatus.STALEMATE

    def test_close_debate_force_close(self) -> None:
        """Force close debate (I5: Sovereign Safety Override)."""
        room = DebateRoom(
            thread_id="test-018",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        engine = DebateEngine(room)

        engine.close_debate(reason=TerminationReason.FORCE_CLOSE)

        assert room.status == DebateStatus.FORCE_CLOSED

    def test_close_debate_raises_when_already_closed(self) -> None:
        """Cannot close already closed debate."""
        room = DebateRoom(
            thread_id="test-019",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        engine = DebateEngine(room)

        with pytest.raises(ValueError, match="already closed"):
            engine.close_debate(reason=TerminationReason.STALEMATE)


class TestTerminationReason:
    """Test TerminationReason enum."""

    def test_termination_reason_values(self) -> None:
        """Verify all termination reasons exist."""
        assert TerminationReason.SYNTHESIS.value == "synthesis"
        assert TerminationReason.STALEMATE.value == "stalemate"
        assert TerminationReason.EXHAUSTION.value == "exhaustion"
        assert TerminationReason.FORCE_CLOSE.value == "force_close"
