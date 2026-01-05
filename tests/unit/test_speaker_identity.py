"""Tests for speaker identity metadata (Issue #4).

TDD: RED phase - These tests should FAIL until implementation complete.

Tests verify:
- Turn model accepts optional speaker identity fields
- Backward compatibility (Turn creation without identity still works)
- debate_turn tool passes identity to Turn model
- Identity fields excluded from hash chain
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.engine import DebateEngine
from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn, calculate_turn_hash


class TestTurnModelWithIdentity:
    """Test Turn model with speaker identity fields."""

    def test_turn_with_speaker_identity(self) -> None:
        """Turn model accepts optional speaker identity fields."""
        # Create turn with all identity fields
        turn = Turn(
            role="Wind",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
            agent_role="implementation-lead",
            model="claude-opus-4-5",
            cognition="LOGOS",
        )

        # Verify fields stored correctly
        assert turn.agent_role == "implementation-lead"
        assert turn.model == "claude-opus-4-5"
        assert turn.cognition == "LOGOS"
        assert turn.role == "Wind"
        assert turn.content == "Test content"

    def test_turn_without_speaker_identity_backward_compatible(self) -> None:
        """Existing Turn creation without identity still works."""
        # Create turn WITHOUT identity fields (backward compatibility)
        turn = Turn(
            role="Wall",
            content="Legacy content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )

        # Verify turn created successfully
        assert turn.role == "Wall"
        assert turn.content == "Legacy content"

        # Verify identity fields default to None
        assert turn.agent_role is None
        assert turn.model is None
        assert turn.cognition is None

    def test_turn_partial_identity(self) -> None:
        """Turn accepts partial identity (not all fields required)."""
        # Create turn with only some identity fields
        turn = Turn(
            role="Door",
            content="Partial identity",
            timestamp=datetime.now(UTC),
            previous_hash=None,
            agent_role="critical-engineer",
            # model and cognition omitted
        )

        assert turn.agent_role == "critical-engineer"
        assert turn.model is None
        assert turn.cognition is None

    def test_turn_rejects_multiline_identity(self) -> None:
        """Identity fields reject multiline values to avoid log injection."""
        with pytest.raises(ValueError, match="printable ASCII"):
            Turn(
                role="Wind",
                content="Test content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
                agent_role="bad\nrole",
            )

    def test_turn_rejects_non_ascii_identity(self) -> None:
        """Identity fields reject non-ASCII/control characters (e.g., C1)."""
        with pytest.raises(ValueError, match="printable ASCII"):
            Turn(
                role="Wind",
                content="Test content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
                agent_role="bad\u0085role",
            )

    def test_turn_rejects_invalid_cognition(self) -> None:
        """Cognition is allowlisted to PATHOS|ETHOS|LOGOS."""
        with pytest.raises(ValueError, match="Invalid cognition"):
            Turn(
                role="Wind",
                content="Test content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
                cognition="INVALID",
            )


class TestIdentityExcludedFromHash:
    """Test that identity fields are NOT included in hash calculation."""

    def test_identity_excluded_from_hash_chain(self) -> None:
        """Identity fields do NOT affect hash calculation."""
        timestamp = datetime.now(UTC)

        # Create two turns with same debate data but different identity
        turn1 = Turn(
            role="Wind",
            content="Same content",
            timestamp=timestamp,
            previous_hash=None,
            agent_role="agent-1",
            model="model-1",
            cognition="PATHOS",
        )

        turn2 = Turn(
            role="Wind",
            content="Same content",
            timestamp=timestamp,
            previous_hash=None,
            agent_role="agent-2",
            model="model-2",
            cognition="ETHOS",
        )

        # Hash should be IDENTICAL (identity excluded from hash)
        assert turn1.hash == turn2.hash

    def test_hash_function_signature_unchanged(self) -> None:
        """calculate_turn_hash() function signature remains unchanged."""
        # Hash function should only take 4 parameters (not identity fields)
        timestamp = datetime.now(UTC)
        hash_result = calculate_turn_hash(
            role="Wind",
            content="Test",
            timestamp=timestamp,
            previous_hash=None,
        )

        # Verify hash is valid SHA-256 (64 hex chars)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestDebateEngineWithIdentity:
    """Test DebateEngine.add_turn() with identity parameters."""

    def test_debate_engine_add_turn_accepts_identity(self) -> None:
        """DebateEngine.add_turn() accepts optional identity parameters."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        engine = DebateEngine(room)

        # Add turn with identity parameters
        engine.add_turn(
            role="Wind",
            content="Test content",
            agent_role="test-agent",
            model="test-model",
            cognition="LOGOS",
        )

        # Verify turn added with identity
        assert len(room.turns) == 1
        turn = room.turns[0]
        assert turn.agent_role == "test-agent"
        assert turn.model == "test-model"
        assert turn.cognition == "LOGOS"

    def test_debate_engine_add_turn_backward_compatible(self) -> None:
        """DebateEngine.add_turn() works without identity (backward compatible)."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        engine = DebateEngine(room)

        # Add turn WITHOUT identity parameters (old behavior)
        engine.add_turn(role="Wind", content="Test content")

        # Verify turn added successfully
        assert len(room.turns) == 1
        turn = room.turns[0]
        assert turn.agent_role is None
        assert turn.model is None
        assert turn.cognition is None


class TestDebateTurnToolWithIdentity:
    """Test debate_turn tool function with identity parameters."""

    def test_debate_turn_tool_accepts_identity(self, tmp_path: Path) -> None:
        """debate_turn tool passes identity to Turn model."""
        from debate_hall_mcp.tools.init import debate_init
        from debate_hall_mcp.tools.turn import debate_turn

        state_dir = tmp_path / "debates"

        # Initialize debate
        debate_init(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode="fixed",
            state_dir=state_dir,
        )

        # Add turn with identity via tool
        result = debate_turn(
            thread_id="2025-01-01-test",
            role="Wind",
            content="Test content",
            state_dir=state_dir,
            agent_role="test-agent",
            model="test-model",
            cognition="PATHOS",
        )

        # Verify turn added
        assert result["turn_count"] == 1

        # Load state and verify identity stored
        from debate_hall_mcp.state import load_debate_state

        room = load_debate_state("2025-01-01-test", state_dir)
        turn = room.turns[0]
        assert turn.agent_role == "test-agent"
        assert turn.model == "test-model"
        assert turn.cognition == "PATHOS"

    def test_debate_turn_tool_backward_compatible(self, tmp_path: Path) -> None:
        """debate_turn tool works without identity parameters."""
        from debate_hall_mcp.tools.init import debate_init
        from debate_hall_mcp.tools.turn import debate_turn

        state_dir = tmp_path / "debates"

        # Initialize debate
        debate_init(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode="fixed",
            state_dir=state_dir,
        )

        # Add turn WITHOUT identity (old behavior)
        result = debate_turn(
            thread_id="2025-01-01-test",
            role="Wind",
            content="Test content",
            state_dir=state_dir,
        )

        # Verify turn added
        assert result["turn_count"] == 1

        # Load state and verify identity is None
        from debate_hall_mcp.state import load_debate_state

        room = load_debate_state("2025-01-01-test", state_dir)
        turn = room.turns[0]
        assert turn.agent_role is None
        assert turn.model is None
        assert turn.cognition is None
