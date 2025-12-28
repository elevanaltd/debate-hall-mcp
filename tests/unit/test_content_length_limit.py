"""Tests for content length limit DoS protection (MUST FIX Issue #2).

This test file validates that oversized content is rejected BEFORE regex operations
to prevent memory/CPU spike attacks.

TDD Discipline: RED→GREEN→REFACTOR
Security Requirement: DoS protection via early content size validation
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn
from debate_hall_mcp.validation import MAX_TURN_CONTENT_LENGTH


def test_content_within_limit_accepted(tmp_path: Path) -> None:
    """Test that content within MAX_TURN_CONTENT_LENGTH is accepted."""
    debate_init(
        thread_id="2025-01-01-test-size-ok",
        topic="Size test",
        state_dir=tmp_path,
    )

    # Content within limit (small valid content)
    content = (
        """
[VERDICT]
APPROVED

[EVIDENCE]
- All tests pass
"""
        * 10
    )  # Small repeated content (well under 32k)

    result = debate_turn(
        thread_id="2025-01-01-test-size-ok",
        role="Wind",
        content=content,
        cognition="ETHOS",
        state_dir=tmp_path,
    )

    assert result["turn_count"] == 1


def test_content_at_exact_limit_accepted(tmp_path: Path) -> None:
    """Test that content at exactly MAX_TURN_CONTENT_LENGTH is accepted."""
    debate_init(
        thread_id="2025-01-01-test-size-exact",
        topic="Exact size test",
        state_dir=tmp_path,
    )

    # Content at exact limit
    content = "X" * MAX_TURN_CONTENT_LENGTH

    result = debate_turn(
        thread_id="2025-01-01-test-size-exact",
        role="Wind",
        content=content,
        state_dir=tmp_path,
    )

    assert result["turn_count"] == 1


def test_content_exceeds_limit_rejected(tmp_path: Path) -> None:
    """Test that content exceeding MAX_TURN_CONTENT_LENGTH is rejected."""
    debate_init(
        thread_id="2025-01-01-test-size-too-big",
        topic="Oversized content test",
        state_dir=tmp_path,
    )

    # Content exceeding limit
    oversized_content = "X" * (MAX_TURN_CONTENT_LENGTH + 1)

    with pytest.raises(
        ValueError,
        match=rf"Content exceeds maximum length of {MAX_TURN_CONTENT_LENGTH} characters",
    ):
        debate_turn(
            thread_id="2025-01-01-test-size-too-big",
            role="Wind",
            content=oversized_content,
            state_dir=tmp_path,
        )


def test_content_limit_enforced_before_cognition_validation(tmp_path: Path) -> None:
    """Test that content length check happens BEFORE regex-heavy cognition validation."""
    debate_init(
        thread_id="2025-01-01-test-size-order",
        topic="Validation order test",
        strict_cognition=True,
        state_dir=tmp_path,
    )

    # Oversized content should fail on size check, not cognition validation
    oversized_content = "X" * (MAX_TURN_CONTENT_LENGTH + 100)

    with pytest.raises(ValueError) as exc_info:
        debate_turn(
            thread_id="2025-01-01-test-size-order",
            role="Wind",
            content=oversized_content,
            cognition="PATHOS",
            state_dir=tmp_path,
        )

    # Error should be about content length, not cognition validation
    assert "exceeds maximum length" in str(exc_info.value).lower()
    assert "cognition validation failed" not in str(exc_info.value).lower()


def test_content_limit_applies_to_all_cognitions(tmp_path: Path) -> None:
    """Test that content length limit applies regardless of cognition type."""
    debate_init(
        thread_id="2025-01-01-test-size-all-cognitions",
        topic="All cognitions test",
        state_dir=tmp_path,
    )

    oversized_content = "X" * (MAX_TURN_CONTENT_LENGTH + 1)

    # PATHOS
    with pytest.raises(ValueError, match="exceeds maximum length"):
        debate_turn(
            thread_id="2025-01-01-test-size-all-cognitions",
            role="Wind",
            content=oversized_content,
            cognition="PATHOS",
            state_dir=tmp_path,
        )

    # ETHOS
    with pytest.raises(ValueError, match="exceeds maximum length"):
        debate_turn(
            thread_id="2025-01-01-test-size-all-cognitions",
            role="Wind",
            content=oversized_content,
            cognition="ETHOS",
            state_dir=tmp_path,
        )

    # LOGOS
    with pytest.raises(ValueError, match="exceeds maximum length"):
        debate_turn(
            thread_id="2025-01-01-test-size-all-cognitions",
            role="Wind",
            content=oversized_content,
            cognition="LOGOS",
            state_dir=tmp_path,
        )

    # None cognition
    with pytest.raises(ValueError, match="exceeds maximum length"):
        debate_turn(
            thread_id="2025-01-01-test-size-all-cognitions",
            role="Wind",
            content=oversized_content,
            cognition=None,
            state_dir=tmp_path,
        )
