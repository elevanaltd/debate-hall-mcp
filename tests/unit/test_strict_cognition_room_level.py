"""Tests for room-level strict_cognition enforcement (MUST FIX Issue #1).

This test file validates that strict_cognition is a room-level configuration,
not a per-turn parameter, preventing client bypass of the behavioral firewall.

TDD Discipline: RED→GREEN→REFACTOR
Security Requirement: Caller cannot bypass cognition validation
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


def test_room_with_strict_cognition_false_allows_invalid_content(tmp_path: Path) -> None:
    """Test that room with strict_cognition=False allows BLOCK-level violations."""
    # Create room with strict_cognition=False (default)
    debate_init(
        thread_id="2025-01-01-test-non-strict",
        topic="Non-strict room",
        mode="fixed",
        strict_cognition=False,
        state_dir=tmp_path,
    )

    # Invalid PATHOS content (missing options and questions) should be accepted with warnings
    result = debate_turn(
        thread_id="2025-01-01-test-non-strict",
        role="Wind",
        content="This is a statement.",  # No questions, no options (BLOCK level)
        cognition="PATHOS",
        state_dir=tmp_path,
    )

    # Turn should be accepted with warnings
    assert result["turn_count"] == 1
    assert "cognition_warnings" in result
    assert len(result["cognition_warnings"]) > 0


def test_room_with_strict_cognition_true_blocks_invalid_content(tmp_path: Path) -> None:
    """Test that room with strict_cognition=True blocks BLOCK-level violations."""
    # Create room with strict_cognition=True
    debate_init(
        thread_id="2025-01-01-test-strict",
        topic="Strict room",
        mode="fixed",
        strict_cognition=True,
        state_dir=tmp_path,
    )

    # Invalid PATHOS content should be BLOCKED
    with pytest.raises(ValueError, match="Missing multiple options"):
        debate_turn(
            thread_id="2025-01-01-test-strict",
            role="Wind",
            content="This is a statement.",  # No questions, no options (BLOCK level)
            cognition="PATHOS",
            state_dir=tmp_path,
        )

    # Verify turn was NOT added
    from debate_hall_mcp.state import load_debate_state

    room = load_debate_state("2025-01-01-test-strict", tmp_path)
    assert len(room.turns) == 0


def test_strict_cognition_persists_across_turns(tmp_path: Path) -> None:
    """Test that strict_cognition setting persists for all turns in room."""
    # Create strict room
    debate_init(
        thread_id="2025-01-01-test-persist",
        topic="Persistence test",
        mode="fixed",
        strict_cognition=True,
        state_dir=tmp_path,
    )

    # First turn: valid content passes
    debate_turn(
        thread_id="2025-01-01-test-persist",
        role="Wind",
        content="""
[POSSIBILITIES]
1. Option A
2. Option B

Which should we choose?
""",
        cognition="PATHOS",
        state_dir=tmp_path,
    )

    # Second turn: invalid content still blocked (strict_cognition persists)
    with pytest.raises(ValueError, match="Missing \\[VERDICT\\]"):
        debate_turn(
            thread_id="2025-01-01-test-persist",
            role="Wall",
            content="This looks good.",  # Missing [VERDICT] and [EVIDENCE]
            cognition="ETHOS",
            state_dir=tmp_path,
        )


def test_strict_cognition_default_is_false(tmp_path: Path) -> None:
    """Test that strict_cognition defaults to False (backward compatibility)."""
    # Create room without specifying strict_cognition
    debate_init(
        thread_id="2025-01-01-test-default",
        topic="Default test",
        mode="fixed",
        state_dir=tmp_path,
    )

    # Invalid content should be accepted (non-strict default)
    result = debate_turn(
        thread_id="2025-01-01-test-default",
        role="Wind",
        content="Simple statement.",
        cognition="PATHOS",
        state_dir=tmp_path,
    )

    assert result["turn_count"] == 1
    assert "cognition_warnings" in result  # Warnings present but not blocking
