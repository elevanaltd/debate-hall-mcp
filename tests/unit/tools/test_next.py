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
        thread_id="2025-01-01-test-thread-001",
        topic="Test topic",
        mode="fixed",
        octave_preamble=False,  # Disable preamble for transcript length testing
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-thread-001", state_dir=tmp_path)

    assert result["thread_id"] == "2025-01-01-test-thread-001"
    assert result["next_role"] == "Wind"
    assert result["turn_count"] == 0
    assert result["status"] == "active"
    assert "transcript" in result
    assert isinstance(result["transcript"], list)
    assert len(result["transcript"]) == 0  # No turns yet (preamble disabled)


def test_debate_next_fixed_mode_with_history(tmp_path: Path) -> None:
    """Test getting next prompt with turn history."""
    debate_init(
        thread_id="2025-01-01-test-thread-002",
        topic="Test topic",
        mode="fixed",
        octave_preamble=False,  # Disable preamble for transcript length testing
        state_dir=tmp_path,
    )

    # Add Wind turn
    debate_turn(
        thread_id="2025-01-01-test-thread-002",
        role="Wind",
        content="POSITION::Wind position",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-thread-002", state_dir=tmp_path)

    assert result["next_role"] == "Wall"  # After Wind comes Wall
    assert result["turn_count"] == 1
    assert len(result["transcript"]) == 1  # Just the Wind turn (preamble disabled)
    assert result["transcript"][0]["role"] == "Wind"


def test_debate_next_mediated_mode_returns_none(tmp_path: Path) -> None:
    """Test that mediated mode returns None for next_role."""
    debate_init(
        thread_id="2025-01-01-test-thread-003",
        topic="Test topic",
        mode="mediated",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-thread-003", state_dir=tmp_path)

    assert result["next_role"] is None  # Orchestrator must pick
    assert result["mode"] == "mediated"


def test_debate_next_context_lines_limits_transcript(tmp_path: Path) -> None:
    """Test that context_lines parameter limits transcript length."""
    debate_init(
        thread_id="2025-01-01-test-thread-004",
        topic="Test topic",
        octave_preamble=False,  # Disable preamble for transcript length testing
        state_dir=tmp_path,
    )

    # Add 5 turns
    debate_turn("2025-01-01-test-thread-004", "Wind", "W1", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-004", "Wall", "W2", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-004", "Door", "D1", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-004", "Wind", "W3", state_dir=tmp_path)
    debate_turn("2025-01-01-test-thread-004", "Wall", "W4", state_dir=tmp_path)

    # Request only last 2 turns
    result = debate_next(
        thread_id="2025-01-01-test-thread-004", context_lines=2, state_dir=tmp_path
    )

    assert result["turn_count"] == 5  # Total turns
    assert len(result["transcript"]) == 2  # Limited to last 2 (preamble disabled)
    assert result["transcript"][0]["role"] == "Wind"  # W3
    assert result["transcript"][1]["role"] == "Wall"  # W4


def test_debate_next_inactive_debate(tmp_path: Path) -> None:
    """Test that next returns info even for closed debates."""
    debate_init(
        thread_id="2025-01-01-test-thread-005",
        topic="Test topic",
        state_dir=tmp_path,
    )

    # Close debate
    from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state

    room = load_debate_state("2025-01-01-test-thread-005", tmp_path)
    room.status = DebateStatus.SYNTHESIS
    save_debate_state(room, tmp_path)

    result = debate_next(thread_id="2025-01-01-test-thread-005", state_dir=tmp_path)

    assert result["status"] == "synthesis"
    assert result["next_role"] is None  # No next role for closed debate


def test_debate_next_thread_not_found(tmp_path: Path) -> None:
    """Test that non-existent thread raises error."""
    with pytest.raises(FileNotFoundError, match="No state file found"):
        debate_next(thread_id="nonexistent", state_dir=tmp_path)


def test_debate_next_includes_topic_and_limits(tmp_path: Path) -> None:
    """Test that result includes topic and resource limits."""
    debate_init(
        thread_id="2025-01-01-test-thread-006",
        topic="Specific topic",
        max_turns=6,
        max_rounds=2,
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-thread-006", state_dir=tmp_path)

    assert result["topic"] == "Specific topic"
    assert result["max_turns"] == 6
    assert result["max_rounds"] == 2


# ============================================================================
# Holographic Preamble Tests
# ============================================================================


def test_debate_next_preamble_prepended_by_default(tmp_path: Path) -> None:
    """Test that System preamble is prepended to transcript when octave_preamble=True (default)."""
    debate_init(
        thread_id="2025-01-01-test-preamble-001",
        topic="Preamble test",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-preamble-001", state_dir=tmp_path)

    # Should have System preamble as first item (even with no real turns)
    assert len(result["transcript"]) == 1
    assert result["transcript"][0]["role"] == "System"
    assert "===PROTOCOL===" in result["transcript"][0]["content"]
    assert "FORMAT::OCTAVE" in result["transcript"][0]["content"]
    # turn_count should still be 0 (preamble is synthetic, not stored)
    assert result["turn_count"] == 0


def test_debate_next_preamble_with_existing_turns(tmp_path: Path) -> None:
    """Test that System preamble is prepended before existing turns."""
    debate_init(
        thread_id="2025-01-01-test-preamble-002",
        topic="Preamble with turns test",
        state_dir=tmp_path,
    )

    # Add a Wind turn
    debate_turn(
        thread_id="2025-01-01-test-preamble-002",
        role="Wind",
        content="POSITION::Test position",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-preamble-002", state_dir=tmp_path)

    # Should have System preamble first, then Wind turn
    assert len(result["transcript"]) == 2
    assert result["transcript"][0]["role"] == "System"
    assert result["transcript"][1]["role"] == "Wind"
    # turn_count reflects real turns only
    assert result["turn_count"] == 1


def test_debate_next_no_preamble_when_disabled(tmp_path: Path) -> None:
    """Test that System preamble is NOT prepended when octave_preamble=False."""
    debate_init(
        thread_id="2025-01-01-test-preamble-003",
        topic="Preamble disabled test",
        octave_preamble=False,
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-preamble-003", state_dir=tmp_path)

    # No preamble, no turns = empty transcript
    assert len(result["transcript"]) == 0


def test_debate_next_preamble_not_stored_in_db(tmp_path: Path) -> None:
    """Test that preamble is view-layer only - not stored in state."""
    from debate_hall_mcp.state import load_debate_state

    debate_init(
        thread_id="2025-01-01-test-preamble-004",
        topic="Preamble storage test",
        state_dir=tmp_path,
    )

    # Call debate_next (should show preamble)
    result = debate_next(thread_id="2025-01-01-test-preamble-004", state_dir=tmp_path)
    assert len(result["transcript"]) == 1
    assert result["transcript"][0]["role"] == "System"

    # Load state directly - should have NO turns
    room = load_debate_state("2025-01-01-test-preamble-004", tmp_path)
    assert len(room.turns) == 0


def test_debate_next_preamble_not_in_hash_chain(tmp_path: Path) -> None:
    """Test that preamble does not affect hash chain of real turns."""
    debate_init(
        thread_id="2025-01-01-test-preamble-005",
        topic="Preamble hash chain test",
        state_dir=tmp_path,
    )

    # Add a Wind turn
    debate_turn(
        thread_id="2025-01-01-test-preamble-005",
        role="Wind",
        content="POSITION::Hash test",
        state_dir=tmp_path,
    )

    # Add a Wall turn
    debate_turn(
        thread_id="2025-01-01-test-preamble-005",
        role="Wall",
        content="POSITION::Hash test response",
        state_dir=tmp_path,
    )

    # Load state directly and check hash chain
    from debate_hall_mcp.state import load_debate_state

    room = load_debate_state("2025-01-01-test-preamble-005", tmp_path)

    # First real turn should have previous_hash=None (not preamble's hash)
    assert room.turns[0].previous_hash is None
    # Second turn should chain to first turn
    assert room.turns[1].previous_hash == room.turns[0].hash


def test_debate_next_preamble_content_is_octave_format(tmp_path: Path) -> None:
    """Test that preamble content contains expected OCTAVE syntax guide."""
    debate_init(
        thread_id="2025-01-01-test-preamble-006",
        topic="Preamble content test",
        state_dir=tmp_path,
    )

    result = debate_next(thread_id="2025-01-01-test-preamble-006", state_dir=tmp_path)

    preamble_content = result["transcript"][0]["content"]

    # Verify expected structure
    assert "===PROTOCOL===" in preamble_content
    assert "FORMAT::OCTAVE" in preamble_content
    assert "SYNTAX::" in preamble_content
    assert "OPERATORS::" in preamble_content
    assert "===END===" in preamble_content


def test_debate_next_preamble_with_context_lines(tmp_path: Path) -> None:
    """Test that context_lines works correctly with preamble."""
    debate_init(
        thread_id="2025-01-01-test-preamble-007",
        topic="Preamble context lines test",
        state_dir=tmp_path,
    )

    # Add 3 turns
    debate_turn("2025-01-01-test-preamble-007", "Wind", "W1", state_dir=tmp_path)
    debate_turn("2025-01-01-test-preamble-007", "Wall", "W2", state_dir=tmp_path)
    debate_turn("2025-01-01-test-preamble-007", "Door", "D1", state_dir=tmp_path)

    # Request last 2 turns - should get preamble + 2 most recent turns
    result = debate_next(
        thread_id="2025-01-01-test-preamble-007", context_lines=2, state_dir=tmp_path
    )

    # Preamble + 2 context lines = 3 items
    assert len(result["transcript"]) == 3
    assert result["transcript"][0]["role"] == "System"  # Preamble
    assert result["transcript"][1]["role"] == "Wall"  # W2
    assert result["transcript"][2]["role"] == "Door"  # D1
