"""Tests for debate_next tool (T3).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.next import debate_next
from debate_hall_mcp.tools.turn import debate_turn


def test_debate_next_fixed_mode_first_turn(tmp_path: Path) -> None:
    """Test getting next prompt for first turn in fixed mode."""
    debate_init(
        thread_id="test-thread-001",
        topic="Test topic",
        mode="fixed",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="test-thread-001", state_dir=tmp_path)

    assert result["thread_id"] == "test-thread-001"
    assert result["next_role"] == "Wind"
    assert result["turn_count"] == 0
    assert result["status"] == "active"
    assert "transcript" in result
    assert isinstance(result["transcript"], list)
    assert len(result["transcript"]) == 0  # No turns yet


def test_debate_next_fixed_mode_with_history(tmp_path: Path) -> None:
    """Test getting next prompt with turn history."""
    debate_init(
        thread_id="test-thread-002",
        topic="Test topic",
        mode="fixed",
        state_dir=tmp_path,
    )

    # Add Wind turn
    debate_turn(
        thread_id="test-thread-002",
        role="Wind",
        content="POSITION::Wind position",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="test-thread-002", state_dir=tmp_path)

    assert result["next_role"] == "Wall"  # After Wind comes Wall
    assert result["turn_count"] == 1
    assert len(result["transcript"]) == 1
    assert result["transcript"][0]["role"] == "Wind"


def test_debate_next_mediated_mode_returns_none(tmp_path: Path) -> None:
    """Test that mediated mode returns None for next_role."""
    debate_init(
        thread_id="test-thread-003",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="test-thread-003", state_dir=tmp_path)

    assert result["next_role"] is None  # Orchestrator must pick
    assert result["mode"] == "mediated"


def test_debate_next_context_lines_limits_transcript(tmp_path: Path) -> None:
    """Test that context_lines parameter limits transcript length."""
    debate_init(
        thread_id="test-thread-004",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Add 5 turns
    debate_turn("test-thread-004", "Wind", "W1", state_dir=tmp_path)
    debate_turn("test-thread-004", "Wall", "W2", state_dir=tmp_path)
    debate_turn("test-thread-004", "Door", "D1", state_dir=tmp_path)
    debate_turn("test-thread-004", "Wind", "W3", state_dir=tmp_path)
    debate_turn("test-thread-004", "Wall", "W4", state_dir=tmp_path)

    # Request only last 2 turns
    result = debate_next(thread_id="test-thread-004", context_lines=2, state_dir=tmp_path)

    assert result["turn_count"] == 5  # Total turns
    assert len(result["transcript"]) == 2  # Limited to last 2
    assert result["transcript"][0]["role"] == "Wind"  # W3
    assert result["transcript"][1]["role"] == "Wall"  # W4


def test_debate_next_inactive_debate(tmp_path: Path) -> None:
    """Test that next returns info even for closed debates."""
    debate_init(
        thread_id="test-thread-005",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Close debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("test-thread-005", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    result = debate_next(thread_id="test-thread-005", state_dir=tmp_path)

    assert result["status"] == "synthesis"
    assert result["next_role"] is None  # No next role for closed debate


def test_debate_next_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_next(thread_id="nonexistent", state_dir=tmp_path)


def test_debate_next_includes_topic_and_limits(tmp_path: Path) -> None:
    """Test that result includes topic and resource limits."""
    debate_init(
        thread_id="test-thread-006",
        topic="Specific topic",
        max_turns=6,
        max_rounds=2,
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="test-thread-006", state_dir=tmp_path)

    assert result["topic"] == "Specific topic"
    assert result["max_turns"] == 6
    assert result["max_rounds"] == 2
