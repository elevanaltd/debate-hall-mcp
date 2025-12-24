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
        thread_id="test-thread-001",
        topic="Test topic",
        mode="fixed",
        state_dir=tmp_path,
    )

    # Add Wind turn
    result = debate_turn(
        thread_id="test-thread-001",
        role="Wind",
        content="POSITION::Test position",
        state_dir=tmp_path,
    )

    # Check return structure
    assert result["thread_id"] == "test-thread-001"
    assert result["turn_count"] == 1
    assert result["role"] == "Wind"
    assert result["status"] == "active"

    # Verify state file updated
    room = load_debate_state("test-thread-001", tmp_path)
    assert len(room.turns) == 1
    assert room.turns[0].role == "Wind"
    assert room.turns[0].content == "POSITION::Test position"
    assert room.turns[0].previous_hash is None  # First turn


def test_debate_turn_maintains_hash_chain(tmp_path: Path) -> None:
    """Test that hash chain is maintained across turns (I4 compliance)."""
    debate_init(
        thread_id="test-thread-002",
        topic="Hash chain test",
        state_dir=tmp_path,
    )

    # Add three turns
    debate_turn(
        thread_id="test-thread-002",
        role="Wind",
        content="POSITION::Wind position",
        state_dir=tmp_path,
    )

    debate_turn(
        thread_id="test-thread-002",
        role="Wall",
        content="COUNTER::Wall counter",
        state_dir=tmp_path,
    )

    debate_turn(
        thread_id="test-thread-002",
        role="Door",
        content="SYNTHESIS::Door synthesis",
        state_dir=tmp_path,
    )

    # Verify hash chain
    room = load_debate_state("test-thread-002", tmp_path)
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
        thread_id="test-thread-003",
        topic="Role validation test",
        mode="fixed",
        state_dir=tmp_path,
    )

    # First turn must be Wind
    debate_turn(
        thread_id="test-thread-003",
        role="Wind",
        content="POSITION::Wind",
        state_dir=tmp_path,
    )

    # Second turn must be Wall (not Wind)
    with pytest.raises(ValueError, match="Expected role 'Wall'"):
        debate_turn(
            thread_id="test-thread-003",
            role="Wind",
            content="POSITION::Wrong",
            state_dir=tmp_path,
        )

    # Correct role should work
    debate_turn(
        thread_id="test-thread-003",
        role="Wall",
        content="COUNTER::Wall",
        state_dir=tmp_path,
    )


def test_debate_turn_allows_any_role_in_mediated_mode(tmp_path: Path) -> None:
    """Test that mediated mode allows any role (orchestrator picks)."""
    debate_init(
        thread_id="test-thread-004",
        topic="Mediated mode test",
        mode="mediated",
        state_dir=tmp_path,
    )

    # In mediated mode, any role can go first
    result = debate_turn(
        thread_id="test-thread-004",
        role="Door",
        content="SYNTHESIS::Door first",
        state_dir=tmp_path,
    )

    assert result["role"] == "Door"
    assert result["turn_count"] == 1


def test_debate_turn_rejects_inactive_debate(tmp_path: Path) -> None:
    """Test that turns cannot be added to inactive debates."""
    debate_init(
        thread_id="test-thread-005",
        topic="Inactive debate test",
        state_dir=tmp_path,
    )

    # Close the debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("test-thread-005", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    # Try to add turn to closed debate
    with pytest.raises(ValueError, match="not active"):
        debate_turn(
            thread_id="test-thread-005",
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
        thread_id="test-thread-006",
        topic="Max turns test",
        max_turns=3,
        max_rounds=10,  # High enough to not interfere
        state_dir=tmp_path,
    )

    # Add 3 turns (limit)
    debate_turn("test-thread-006", "Wind", "POSITION::1", state_dir=tmp_path)
    debate_turn("test-thread-006", "Wall", "COUNTER::2", state_dir=tmp_path)
    debate_turn("test-thread-006", "Door", "SYNTHESIS::3", state_dir=tmp_path)

    # 4th turn should fail
    with pytest.raises(ValueError, match="exhausted"):
        debate_turn("test-thread-006", "Wind", "POSITION::4", state_dir=tmp_path)
