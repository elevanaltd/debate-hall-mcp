"""Tests for debate_close tool (T5).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import load_debate_state
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.init import debate_init


def test_debate_close_with_synthesis(tmp_path: Path) -> None:
    """Test closing debate with synthesis."""
    debate_init(
        thread_id="2025-01-01-test-thread-001",
        topic="Test topic",
        state_dir=tmp_path,
    )

    result = debate_close(
        thread_id="2025-01-01-test-thread-001",
        synthesis="Final synthesis content",
        state_dir=tmp_path,
    )

    assert result["thread_id"] == "2025-01-01-test-thread-001"
    assert result["status"] == "synthesis"
    assert result["synthesis"] == "Final synthesis content"

    # Verify state updated
    room = load_debate_state("2025-01-01-test-thread-001", tmp_path)
    assert room.status.value == "synthesis"
    assert room.synthesis == "Final synthesis content"


def test_debate_close_already_closed(tmp_path: Path) -> None:
    """Test that closing already closed debate raises error."""
    debate_init(
        thread_id="2025-01-01-test-thread-002",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Close once
    debate_close(
        thread_id="2025-01-01-test-thread-002",
        synthesis="First close",
        state_dir=tmp_path,
    )

    # Try to close again
    with pytest.raises(ValueError, match="already closed"):
        debate_close(
            thread_id="2025-01-01-test-thread-002",
            synthesis="Second close",
            state_dir=tmp_path,
        )


def test_debate_close_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_close(
            thread_id="nonexistent",
            synthesis="Should fail",
            state_dir=tmp_path,
        )


def test_debate_close_requires_synthesis(tmp_path: Path) -> None:
    """Test that synthesis is required for close."""
    debate_init(
        thread_id="2025-01-01-test-thread-003",
        topic="Test topic",
        state_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="Synthesis required"):
        debate_close(
            thread_id="2025-01-01-test-thread-003",
            synthesis="",  # Empty synthesis
            state_dir=tmp_path,
        )
