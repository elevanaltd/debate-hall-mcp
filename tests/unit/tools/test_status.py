"""Tests for debate_status tool (T4).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation), I3 (finite limits)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.status import debate_status
from debate_hall_mcp.tools.turn import debate_turn


def test_debate_status_new_debate(tmp_path: Path) -> None:
    """Test status of newly created debate."""
    debate_init(
        thread_id="test-thread-001",
        topic="Test topic",
        state_dir=tmp_path,
    )

    result = debate_status(thread_id="test-thread-001", state_dir=tmp_path)

    assert result["thread_id"] == "test-thread-001"
    assert result["topic"] == "Test topic"
    assert result["mode"] == "fixed"
    assert result["status"] == "active"
    assert result["turn_count"] == 0
    assert result["max_turns"] == 12
    assert result["max_rounds"] == 4
    assert result["next_role"] == "Wind"


def test_debate_status_with_turns(tmp_path: Path) -> None:
    """Test status after turns added."""
    debate_init(
        thread_id="test-thread-002",
        topic="Test topic",
        state_dir=tmp_path,
    )

    debate_turn("test-thread-002", "Wind", "W1", state_dir=tmp_path)
    debate_turn("test-thread-002", "Wall", "W2", state_dir=tmp_path)

    result = debate_status(thread_id="test-thread-002", state_dir=tmp_path)

    assert result["turn_count"] == 2
    assert result["next_role"] == "Door"  # After Wall comes Door


def test_debate_status_closed_debate(tmp_path: Path) -> None:
    """Test status of closed debate."""
    debate_init(
        thread_id="test-thread-003",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Close debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("test-thread-003", tmp_path)
    room.status = DebateStatus.FORCE_CLOSED
    save_debate_state(room, tmp_path)

    result = debate_status(thread_id="test-thread-003", state_dir=tmp_path)

    assert result["status"] == "force_closed"
    assert result["next_role"] is None  # No next role for closed debate


def test_debate_status_includes_synthesis_if_present(tmp_path: Path) -> None:
    """Test that synthesis is included if set."""
    debate_init(
        thread_id="test-thread-004",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Set synthesis
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("test-thread-004", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    room.synthesis = "Final synthesis content"
    save_debate_state(room, tmp_path)

    result = debate_status(thread_id="test-thread-004", state_dir=tmp_path)

    assert result["synthesis"] == "Final synthesis content"


def test_debate_status_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_status(thread_id="nonexistent", state_dir=tmp_path)


def test_debate_status_mediated_mode(tmp_path: Path) -> None:
    """Test status for mediated mode debate."""
    debate_init(
        thread_id="test-thread-005",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    result = debate_status(thread_id="test-thread-005", state_dir=tmp_path)

    assert result["mode"] == "mediated"
    assert result["next_role"] is None  # Mediated mode has no automatic next
