"""Tests for debate_admin tools (T7).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I5 (safety override)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import load_debate_state
from debate_hall_mcp.tools.admin import debate_force_close, debate_tombstone
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


def test_debate_force_close(tmp_path: Path) -> None:
    """Test force closing a debate (I5 compliance)."""
    debate_init(
        thread_id="2025-01-01-test-thread-001",
        topic="Test topic",
        state_dir=tmp_path,
    )

    result = debate_force_close(
        thread_id="2025-01-01-test-thread-001",
        reason="Emergency shutdown",
        state_dir=tmp_path,
    )

    assert result["thread_id"] == "2025-01-01-test-thread-001"
    assert result["status"] == "force_closed"
    assert result["reason"] == "Emergency shutdown"

    # Verify state updated
    room = load_debate_state("2025-01-01-test-thread-001", tmp_path)
    assert room.status.value == "force_closed"


def test_debate_force_close_already_closed(tmp_path: Path) -> None:
    """Test force closing already closed debate still works (override)."""
    debate_init(
        thread_id="2025-01-01-test-thread-002",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Close normally first
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("2025-01-01-test-thread-002", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    # Force close should still work (I5: safety override)
    result = debate_force_close(
        thread_id="2025-01-01-test-thread-002",
        reason="Override previous close",
        state_dir=tmp_path,
    )

    assert result["status"] == "force_closed"


def test_debate_force_close_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_force_close(
            thread_id="nonexistent",
            reason="Should fail",
            state_dir=tmp_path,
        )


def test_debate_tombstone_redacts_turn(tmp_path: Path) -> None:
    """Test tombstoning a turn (I4 hash chain preservation)."""
    debate_init(
        thread_id="2025-01-01-test-thread-003",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Add turns
    debate_turn("2025-01-01-test-thread-003", "Wind", "Original Wind", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-003", "Wall", "Original Wall", state_dir=tmp_path)

    # Tombstone first turn (index 0)
    result = debate_tombstone(
        thread_id="2025-01-01-test-thread-003",
        turn_index=0,
        reason="Inappropriate content",
        state_dir=tmp_path,
    )

    assert result["thread_id"] == "2025-01-01-test-thread-003"
    assert result["turn_index"] == 0
    assert result["reason"] == "Inappropriate content"

    # Verify turn redacted
    room = load_debate_state("2025-01-01-test-thread-003", tmp_path)
    assert room.turns[0].content == "[REDACTED: Inappropriate content]"
    # Hash chain should still be intact
    assert room.turns[0].hash  # Hash preserved
    assert room.turns[1].previous_hash == room.turns[0].hash  # Chain intact


def test_debate_tombstone_invalid_index(tmp_path: Path) -> None:
    """Test that invalid turn index raises error."""
    debate_init(
        thread_id="2025-01-01-test-thread-004",
        topic="Test topic",
        state_dir=tmp_path,
    )

    debate_turn("2025-01-01-test-thread-004", "Wind", "Original", state_dir=tmp_path)

    # Try to tombstone non-existent turn
    with pytest.raises(ValueError, match="Invalid turn index"):
        debate_tombstone(
            thread_id="2025-01-01-test-thread-004",
            turn_index=5,  # Out of range
            reason="Should fail",
            state_dir=tmp_path,
        )


def test_debate_tombstone_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_tombstone(
            thread_id="nonexistent",
            turn_index=0,
            reason="Should fail",
            state_dir=tmp_path,
        )


def test_debate_tombstone_preserves_hash_chain(tmp_path: Path) -> None:
    """Test that tombstoning preserves hash chain integrity (I4)."""
    debate_init(
        thread_id="2025-01-01-test-thread-005",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Add three turns
    debate_turn("2025-01-01-test-thread-005", "Wind", "Wind content", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-005", "Wall", "Wall content", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-005", "Door", "Door content", state_dir=tmp_path)

    # Store original hashes
    room_before = load_debate_state("2025-01-01-test-thread-005", tmp_path)
    hash_0 = room_before.turns[0].hash
    hash_1 = room_before.turns[1].hash
    hash_2 = room_before.turns[2].hash

    # Tombstone middle turn
    debate_tombstone(
        thread_id="2025-01-01-test-thread-005",
        turn_index=1,
        reason="Redacted",
        state_dir=tmp_path,
    )

    # Verify hashes unchanged (I4: hash chain integrity)
    room_after = load_debate_state("2025-01-01-test-thread-005", tmp_path)
    assert room_after.turns[0].hash == hash_0
    assert room_after.turns[1].hash == hash_1  # Hash preserved even though content changed
    assert room_after.turns[2].hash == hash_2
    # Chain still valid
    assert room_after.turns[1].previous_hash == hash_0
    assert room_after.turns[2].previous_hash == hash_1
