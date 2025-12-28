"""Tests for debate_init tool (T1).

TDD Discipline: RED→GREEN→REFACTOR
Immutables: I1 (state isolation), I3 (finite limits)
"""

import json
from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init


def test_debate_init_creates_fixed_mode_debate(tmp_path: Path) -> None:
    """Test creating a debate in fixed mode (default)."""
    result = debate_init(
        thread_id="2025-01-01-test-thread-001",
        topic="Is structured debate valuable?",
        state_dir=tmp_path,
    )

    # Check return structure
    assert result["thread_id"] == "2025-01-01-test-thread-001"
    assert result["topic"] == "Is structured debate valuable?"
    assert result["mode"] == "fixed"
    assert result["status"] == "active"
    assert result["max_turns"] == 12
    assert result["max_rounds"] == 4
    assert result["turn_count"] == 0

    # Verify state file created
    state_file = tmp_path / "2025-01-01-test-thread-001.json"
    assert state_file.exists()

    # Verify state file content
    with open(state_file) as f:
        state_data = json.load(f)

    assert state_data["thread_id"] == "2025-01-01-test-thread-001"
    assert state_data["mode"] == "fixed"
    assert state_data["status"] == "active"
    assert state_data["turns"] == []


def test_debate_init_creates_mediated_mode_debate(tmp_path: Path) -> None:
    """Test creating a debate in mediated mode."""
    result = debate_init(
        thread_id="2025-01-01-test-thread-002",
        topic="Should AI make decisions?",
        mode="mediated",
        state_dir=tmp_path,
    )

    assert result["mode"] == "mediated"

    # Verify state file
    state_file = tmp_path / "2025-01-01-test-thread-002.json"
    with open(state_file) as f:
        state_data = json.load(f)

    assert state_data["mode"] == "mediated"


def test_debate_init_custom_limits(tmp_path: Path) -> None:
    """Test creating debate with custom resource limits (I3 compliance)."""
    result = debate_init(
        thread_id="2025-01-01-test-thread-003",
        topic="Custom limits test",
        max_turns=6,
        max_rounds=2,
        state_dir=tmp_path,
    )

    assert result["max_turns"] == 6
    assert result["max_rounds"] == 2

    # Verify in state file
    state_file = tmp_path / "2025-01-01-test-thread-003.json"
    with open(state_file) as f:
        state_data = json.load(f)

    assert state_data["max_turns"] == 6
    assert state_data["max_rounds"] == 2


def test_debate_init_thread_id_already_exists(tmp_path: Path) -> None:
    """Test that creating duplicate thread_id raises error."""
    debate_init(
        thread_id="2025-01-01-test-thread-004",
        topic="First debate",
        state_dir=tmp_path,
    )

    # Try to create same thread_id again
    with pytest.raises(FileExistsError, match="already exists"):
        debate_init(
            thread_id="2025-01-01-test-thread-004",
            topic="Second debate",
            state_dir=tmp_path,
        )


def test_debate_init_invalid_mode(tmp_path: Path) -> None:
    """Test that invalid mode raises error."""
    with pytest.raises(ValueError, match="Invalid mode"):
        debate_init(
            thread_id="2025-01-01-test-thread-005",
            topic="Invalid mode test",
            mode="invalid_mode",  # pyright: ignore[reportArgumentType]
            state_dir=tmp_path,
        )


def test_debate_init_creates_state_directory(tmp_path: Path) -> None:
    """Test that state directory is created if it doesn't exist."""
    state_dir = tmp_path / "debates"
    assert not state_dir.exists()

    debate_init(
        thread_id="2025-01-01-test-thread-006",
        topic="Directory creation test",
        state_dir=state_dir,
    )

    assert state_dir.exists()
    assert state_dir.is_dir()
