"""Tests for debate_pick tool (T6).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation)

Note: debate_pick is only valid for mediated mode debates.
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick


def test_debate_pick_mediated_mode(tmp_path: Path) -> None:
    """Test picking next role in mediated mode."""
    debate_init(
        thread_id="test-thread-001",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    result = debate_pick(
        thread_id="test-thread-001",
        role="Door",
        state_dir=tmp_path,
    )

    assert result["thread_id"] == "test-thread-001"
    assert result["next_role"] == "Door"
    assert result["mode"] == "mediated"


def test_debate_pick_fixed_mode_rejected(tmp_path: Path) -> None:
    """Test that pick is rejected in fixed mode."""
    debate_init(
        thread_id="test-thread-002",
        topic="Test topic",
        mode="fixed",
        state_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="only valid for mediated mode"):
        debate_pick(
            thread_id="test-thread-002",
            role="Wind",
            state_dir=tmp_path,
        )


def test_debate_pick_invalid_role(tmp_path: Path) -> None:
    """Test that invalid role is rejected."""
    debate_init(
        thread_id="test-thread-003",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="Invalid role"):
        debate_pick(
            thread_id="test-thread-003",
            role="InvalidRole",
            state_dir=tmp_path,
        )


def test_debate_pick_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_pick(
            thread_id="nonexistent",
            role="Wind",
            state_dir=tmp_path,
        )


def test_debate_pick_inactive_debate(tmp_path: Path) -> None:
    """Test that pick is rejected for closed debates."""
    debate_init(
        thread_id="test-thread-004",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    # Close debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("test-thread-004", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    with pytest.raises(ValueError, match="Debate is not active"):
        debate_pick(
            thread_id="test-thread-004",
            role="Wind",
            state_dir=tmp_path,
        )
