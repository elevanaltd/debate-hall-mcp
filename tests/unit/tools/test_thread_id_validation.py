"""Tests for thread_id validation - date-first format (Issue #30).

TDD Discipline: RED->GREEN->REFACTOR
Issue: https://github.com/elevanaltd/debate-hall-mcp/issues/30

The HestAI ecosystem uses date-first naming convention (YYYY-MM-DD-subject)
for chronological sorting and ISO 8601 alignment.

Valid formats:
- 2025-12-28-debate-topic
- 2025-01-01-north-star-review
- 2024-06-15-api-design

Invalid formats:
- debate-topic-2025-12-28 (subject-first)
- north-star-review (no date)
- 2025-12-28 (date only, no subject)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init


class TestThreadIdValidation:
    """Tests for date-first thread_id validation (Issue #30)."""

    def test_valid_date_first_thread_id(self, tmp_path: Path) -> None:
        """Test that date-first thread_id is accepted."""
        result = debate_init(
            thread_id="2025-12-28-debate-topic",
            topic="Test topic",
            state_dir=tmp_path,
        )
        assert result["thread_id"] == "2025-12-28-debate-topic"

    def test_valid_date_first_with_multiple_parts(self, tmp_path: Path) -> None:
        """Test date-first with multi-word subject."""
        result = debate_init(
            thread_id="2025-01-15-north-star-architecture-review",
            topic="Architecture review",
            state_dir=tmp_path,
        )
        assert result["thread_id"] == "2025-01-15-north-star-architecture-review"

    def test_invalid_subject_first_thread_id(self, tmp_path: Path) -> None:
        """Test that subject-first thread_id is rejected."""
        with pytest.raises(ValueError, match="date-first format"):
            debate_init(
                thread_id="debate-topic-2025-12-28",
                topic="Test topic",
                state_dir=tmp_path,
            )

    def test_invalid_no_date_thread_id(self, tmp_path: Path) -> None:
        """Test that thread_id without date is rejected."""
        with pytest.raises(ValueError, match="date-first format"):
            debate_init(
                thread_id="north-star-review",
                topic="Test topic",
                state_dir=tmp_path,
            )

    def test_invalid_date_only_thread_id(self, tmp_path: Path) -> None:
        """Test that date-only thread_id is rejected (needs subject)."""
        with pytest.raises(ValueError, match="date-first format"):
            debate_init(
                thread_id="2025-12-28",
                topic="Test topic",
                state_dir=tmp_path,
            )

    def test_invalid_partial_date_thread_id(self, tmp_path: Path) -> None:
        """Test that partial date format is rejected."""
        with pytest.raises(ValueError, match="date-first format"):
            debate_init(
                thread_id="25-12-28-topic",  # YY-MM-DD instead of YYYY-MM-DD
                topic="Test topic",
                state_dir=tmp_path,
            )

    def test_invalid_date_format_thread_id(self, tmp_path: Path) -> None:
        """Test that invalid date values are rejected."""
        with pytest.raises(ValueError, match="date-first format"):
            debate_init(
                thread_id="2025-13-45-topic",  # Invalid month and day
                topic="Test topic",
                state_dir=tmp_path,
            )

    def test_valid_leap_year_date(self, tmp_path: Path) -> None:
        """Test valid leap year date is accepted."""
        result = debate_init(
            thread_id="2024-02-29-leap-year-topic",
            topic="Leap year test",
            state_dir=tmp_path,
        )
        assert result["thread_id"] == "2024-02-29-leap-year-topic"

    def test_valid_minimum_subject_length(self, tmp_path: Path) -> None:
        """Test that single-word subject is accepted."""
        result = debate_init(
            thread_id="2025-12-28-x",
            topic="Minimal subject",
            state_dir=tmp_path,
        )
        assert result["thread_id"] == "2025-12-28-x"
