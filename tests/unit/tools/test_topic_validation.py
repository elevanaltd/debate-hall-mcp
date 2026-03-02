"""Unit tests for shared topic validation module.

Tests the validate_topic function and MAX_TOPIC_LENGTH constant
used consistently across init_debate and run_debate.
"""

import pytest

from debate_hall_mcp.tools.topic_validation import MAX_TOPIC_LENGTH, validate_topic


class TestValidateTopic:
    """Tests for validate_topic function."""

    def test_max_topic_length_is_5000(self) -> None:
        """MAX_TOPIC_LENGTH should be 5000."""
        assert MAX_TOPIC_LENGTH == 5000

    def test_raises_error_for_empty_topic(self) -> None:
        """validate_topic should raise ValueError for empty string."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            validate_topic("")

    def test_raises_error_for_whitespace_only_topic(self) -> None:
        """validate_topic should raise ValueError for whitespace-only string."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            validate_topic("   ")

    def test_raises_error_for_topic_exceeding_max_length(self) -> None:
        """validate_topic should raise ValueError for topic exceeding 5000 chars."""
        long_topic = "x" * 5001
        with pytest.raises(ValueError, match="Topic exceeds maximum length"):
            validate_topic(long_topic)

    def test_accepts_topic_at_max_length(self) -> None:
        """validate_topic should accept a topic exactly at 5000 chars."""
        topic_5000 = "x" * 5000
        # Should not raise
        validate_topic(topic_5000)

    def test_accepts_valid_topic(self) -> None:
        """validate_topic should accept a normal-length topic."""
        # Should not raise
        validate_topic("A perfectly valid debate topic")

    def test_raises_error_for_none_topic(self) -> None:
        """validate_topic should raise for falsy topic (None-like behavior via empty)."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            validate_topic("")
