"""Tests for debate_turn tool (T2).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation), I4 (hash chain)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import load_debate_state
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


def test_debate_turn_adds_turn_to_fixed_mode_debate(tmp_path: Path) -> None:
    """Test adding a turn to fixed mode debate."""
    # Create debate
    debate_init(
        thread_id="2025-01-01-test-thread-001",
        topic="Test topic",
        mode="fixed",
        state_dir=tmp_path,
    )

    # Add Wind turn
    result = debate_turn(
        thread_id="2025-01-01-test-thread-001",
        role="Wind",
        content="POSITION::Test position",
        state_dir=tmp_path,
    )

    # Check return structure
    assert result["thread_id"] == "2025-01-01-test-thread-001"
    assert result["turn_count"] == 1
    assert result["role"] == "Wind"
    assert result["status"] == "active"

    # Verify state file updated
    room = load_debate_state("2025-01-01-test-thread-001", tmp_path)
    assert len(room.turns) == 1
    assert room.turns[0].role == "Wind"
    assert room.turns[0].content == "POSITION::Test position"
    assert room.turns[0].previous_hash is None  # First turn


def test_debate_turn_maintains_hash_chain(tmp_path: Path) -> None:
    """Test that hash chain is maintained across turns (I4 compliance)."""
    debate_init(
        thread_id="2025-01-01-test-thread-002",
        topic="Hash chain test",
        state_dir=tmp_path,
    )

    # Add three turns
    debate_turn(
        thread_id="2025-01-01-test-thread-002",
        role="Wind",
        content="POSITION::Wind position",
        state_dir=tmp_path,
    )

    debate_turn(
        thread_id="2025-01-01-test-thread-002",
        role="Wall",
        content="COUNTER::Wall counter",
        state_dir=tmp_path,
    )

    debate_turn(
        thread_id="2025-01-01-test-thread-002",
        role="Door",
        content="SYNTHESIS::Door synthesis",
        state_dir=tmp_path,
    )

    # Verify hash chain
    room = load_debate_state("2025-01-01-test-thread-002", tmp_path)
    assert len(room.turns) == 3

    # First turn: no previous hash
    assert room.turns[0].previous_hash is None
    assert room.turns[0].hash

    # Second turn: links to first
    assert room.turns[1].previous_hash == room.turns[0].hash
    assert room.turns[1].hash

    # Third turn: links to second
    assert room.turns[2].previous_hash == room.turns[1].hash
    assert room.turns[2].hash


def test_debate_turn_validates_role_in_fixed_mode(tmp_path: Path) -> None:
    """Test that fixed mode enforces role sequence."""
    debate_init(
        thread_id="2025-01-01-test-thread-003",
        topic="Role validation test",
        mode="fixed",
        state_dir=tmp_path,
    )

    # First turn must be Wind
    debate_turn(
        thread_id="2025-01-01-test-thread-003",
        role="Wind",
        content="POSITION::Wind",
        state_dir=tmp_path,
    )

    # Second turn must be Wall (not Wind)
    with pytest.raises(ValueError, match="Expected role 'Wall'"):
        debate_turn(
            thread_id="2025-01-01-test-thread-003",
            role="Wind",
            content="POSITION::Wrong",
            state_dir=tmp_path,
        )

    # Correct role should work
    debate_turn(
        thread_id="2025-01-01-test-thread-003",
        role="Wall",
        content="COUNTER::Wall",
        state_dir=tmp_path,
    )


def test_debate_turn_allows_any_role_in_mediated_mode(tmp_path: Path) -> None:
    """Test that mediated mode allows any role (orchestrator picks)."""
    debate_init(
        thread_id="2025-01-01-test-thread-004",
        topic="Mediated mode test",
        mode="mediated",
        state_dir=tmp_path,
    )

    # In mediated mode, any role can go first
    result = debate_turn(
        thread_id="2025-01-01-test-thread-004",
        role="Door",
        content="SYNTHESIS::Door first",
        state_dir=tmp_path,
    )

    assert result["role"] == "Door"
    assert result["turn_count"] == 1


def test_debate_turn_rejects_inactive_debate(tmp_path: Path) -> None:
    """Test that turns cannot be added to inactive debates."""
    debate_init(
        thread_id="2025-01-01-test-thread-005",
        topic="Inactive debate test",
        state_dir=tmp_path,
    )

    # Close the debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("2025-01-01-test-thread-005", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    # Try to add turn to closed debate
    with pytest.raises(ValueError, match="not active"):
        debate_turn(
            thread_id="2025-01-01-test-thread-005",
            role="Wind",
            content="POSITION::Should fail",
            state_dir=tmp_path,
        )


def test_debate_turn_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_turn(
            thread_id="nonexistent-thread",
            role="Wind",
            content="POSITION::Should fail",
            state_dir=tmp_path,
        )


def test_debate_turn_respects_max_turns_limit(tmp_path: Path) -> None:
    """Test that max_turns limit is enforced (I3 compliance)."""
    debate_init(
        thread_id="2025-01-01-test-thread-006",
        topic="Max turns test",
        max_turns=3,
        max_rounds=10,  # High enough to not interfere
        state_dir=tmp_path,
    )

    # Add 3 turns (limit)
    debate_turn("2025-01-01-test-thread-006", "Wind", "POSITION::1", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-006", "Wall", "COUNTER::2", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-006", "Door", "SYNTHESIS::3", state_dir=tmp_path)

    # 4th turn should fail
    with pytest.raises(ValueError, match="exhausted"):
        debate_turn("2025-01-01-test-thread-006", "Wind", "POSITION::4", state_dir=tmp_path)


def test_debate_turn_validation_warnings_non_strict(tmp_path: Path) -> None:
    """Test that cognition validation warnings are returned but don't block (default)."""
    debate_init(
        thread_id="2025-01-01-test-thread-007",
        topic="Validation test",
        state_dir=tmp_path,
    )

    # Wind turn missing options (WARN level)
    result = debate_turn(
        thread_id="2025-01-01-test-thread-007",
        role="Wind",
        content="Should we proceed? Yes.",
        cognition="PATHOS",
        state_dir=tmp_path,
    )

    # Turn should be accepted (non-strict mode)
    assert result["turn_count"] == 1
    assert "cognition_warnings" in result
    assert len(result["cognition_warnings"]) > 0
    assert any(
        "question" in w.lower() and "option" in w.lower() for w in result["cognition_warnings"]
    )


def test_debate_turn_validation_blocks_strict_mode(tmp_path: Path) -> None:
    """Test that cognition validation blocks turn in strict mode."""
    # Create room with strict_cognition=True
    debate_init(
        thread_id="2025-01-01-test-thread-008",
        topic="Strict validation test",
        strict_cognition=True,  # Room-level configuration
        state_dir=tmp_path,
    )

    # Wind turn missing options (BLOCK level)
    with pytest.raises(ValueError, match="Missing multiple options"):
        debate_turn(
            thread_id="2025-01-01-test-thread-008",
            role="Wind",
            content="This is a statement.",  # No questions, no options
            cognition="PATHOS",
            state_dir=tmp_path,
        )

    # Verify turn was NOT added
    room = load_debate_state("2025-01-01-test-thread-008", tmp_path)
    assert len(room.turns) == 0


def test_debate_turn_validation_passes_valid_cognition(tmp_path: Path) -> None:
    """Test that valid cognition content passes validation."""
    # Create room with strict_cognition=True
    debate_init(
        thread_id="2025-01-01-test-thread-009",
        topic="Valid cognition test",
        strict_cognition=True,  # Room-level configuration
        state_dir=tmp_path,
    )

    # Valid Wind/PATHOS turn
    result = debate_turn(
        thread_id="2025-01-01-test-thread-009",
        role="Wind",
        content="""
[STIMULUS]
Multiple approaches exist.

[POSSIBILITIES]
1. Option A: immediate action
2. Option B: delayed validation
3. Option C: hybrid approach

Which path should we take?
""",
        cognition="PATHOS",
        state_dir=tmp_path,
    )

    # Turn should be accepted with no warnings
    assert result["turn_count"] == 1
    assert "cognition_warnings" not in result or len(result["cognition_warnings"]) == 0


def test_debate_turn_validation_skips_none_cognition(tmp_path: Path) -> None:
    """Test that None cognition behavior depends on strict_cognition flag."""
    # Non-strict room (default): None cognition is accepted (backward compatibility)
    debate_init(
        thread_id="2025-01-01-test-thread-010",
        topic="No cognition test",
        strict_cognition=False,  # Non-strict room (default)
        state_dir=tmp_path,
    )

    result = debate_turn(
        thread_id="2025-01-01-test-thread-010",
        role="Wind",
        content="Any content without cognition validation",
        cognition=None,
        state_dir=tmp_path,
    )
    assert result["turn_count"] == 1
    assert "cognition_warnings" not in result or len(result["cognition_warnings"]) == 0

    # Strict room: None cognition should BLOCK (security requirement)
    debate_init(
        thread_id="2025-01-01-test-thread-011",
        topic="Strict cognition test",
        strict_cognition=True,  # Strict room
        state_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="No cognition specified"):
        debate_turn(
            thread_id="2025-01-01-test-thread-011",
            role="Wind",
            content="Any content without cognition validation",
            cognition=None,
            state_dir=tmp_path,
        )


def test_debate_turn_returns_turn_hash(tmp_path: Path) -> None:
    """Test that debate_turn returns turn_hash for event correlation (Issue #147)."""
    debate_init(
        thread_id="2025-01-01-test-thread-hash",
        topic="Turn hash test",
        state_dir=tmp_path,
    )

    result = debate_turn(
        thread_id="2025-01-01-test-thread-hash",
        role="Wind",
        content="POSITION::Test hash return",
        state_dir=tmp_path,
    )

    # turn_hash must be present and non-empty
    assert "turn_hash" in result
    assert isinstance(result["turn_hash"], str)
    assert len(result["turn_hash"]) == 64  # SHA-256 hex digest

    # turn_hash must match what's stored in state
    room = load_debate_state("2025-01-01-test-thread-hash", tmp_path)
    assert result["turn_hash"] == room.turns[0].hash
