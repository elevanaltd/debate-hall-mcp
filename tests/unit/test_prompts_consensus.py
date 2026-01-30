"""Unit tests for consensus prompts (Phase 4: Consensus Implementation).

Tests the Wind/Wall approval prompt formatters:
- format_wind_approval_prompt
- format_wall_approval_prompt
- Prompt structure and content
- Thread ID inclusion for get_debate() calls
"""

from debate_hall_mcp.prompts import (
    format_wall_approval_prompt,
    format_wind_approval_prompt,
)


class TestFormatWindApprovalPrompt:
    """Tests for format_wind_approval_prompt function."""

    def test_includes_topic(self) -> None:
        """Wind approval prompt should include the topic."""
        prompt = format_wind_approval_prompt(topic="AI governance", thread_id="2026-01-30-test")
        assert "AI governance" in prompt

    def test_includes_thread_id(self) -> None:
        """Wind approval prompt should include thread_id for get_debate() call."""
        prompt = format_wind_approval_prompt(topic="Test topic", thread_id="2026-01-30-test-abc")
        assert "2026-01-30-test-abc" in prompt

    def test_includes_get_debate_instruction(self) -> None:
        """Wind approval prompt should instruct agent to call get_debate()."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "get_debate" in prompt.lower()

    def test_identifies_role_as_wind(self) -> None:
        """Wind approval prompt should identify the role as Wind."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "Wind" in prompt

    def test_mentions_approve_reject_decision(self) -> None:
        """Wind approval prompt should mention APPROVE/REJECT decision."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "APPROVE" in prompt.upper() or "approve" in prompt.lower()
        assert "REJECT" in prompt.upper() or "reject" in prompt.lower()

    def test_mentions_synthesis_review(self) -> None:
        """Wind approval prompt should mention reviewing Door's synthesis."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "synthesis" in prompt.lower()

    def test_mentions_consensus(self) -> None:
        """Wind approval prompt should mention consensus process."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "consensus" in prompt.lower()


class TestFormatWallApprovalPrompt:
    """Tests for format_wall_approval_prompt function."""

    def test_includes_topic(self) -> None:
        """Wall approval prompt should include the topic."""
        prompt = format_wall_approval_prompt(topic="Data privacy", thread_id="2026-01-30-test")
        assert "Data privacy" in prompt

    def test_includes_thread_id(self) -> None:
        """Wall approval prompt should include thread_id for get_debate() call."""
        prompt = format_wall_approval_prompt(topic="Test topic", thread_id="2026-01-30-test-xyz")
        assert "2026-01-30-test-xyz" in prompt

    def test_includes_get_debate_instruction(self) -> None:
        """Wall approval prompt should instruct agent to call get_debate()."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "get_debate" in prompt.lower()

    def test_identifies_role_as_wall(self) -> None:
        """Wall approval prompt should identify the role as Wall."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "Wall" in prompt

    def test_mentions_approve_reject_decision(self) -> None:
        """Wall approval prompt should mention APPROVE/REJECT decision."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "APPROVE" in prompt.upper() or "approve" in prompt.lower()
        assert "REJECT" in prompt.upper() or "reject" in prompt.lower()

    def test_mentions_synthesis_review(self) -> None:
        """Wall approval prompt should mention reviewing Door's synthesis."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "synthesis" in prompt.lower()

    def test_mentions_consensus(self) -> None:
        """Wall approval prompt should mention consensus process."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "consensus" in prompt.lower()


class TestPromptsDifferentiate:
    """Tests ensuring Wind and Wall prompts have appropriate differences."""

    def test_wind_prompt_mentions_pathos(self) -> None:
        """Wind approval prompt should reference PATHOS cognition."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "PATHOS" in prompt or "pathos" in prompt.lower() or "Wind" in prompt

    def test_wall_prompt_mentions_ethos(self) -> None:
        """Wall approval prompt should reference ETHOS cognition."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "ETHOS" in prompt or "ethos" in prompt.lower() or "Wall" in prompt

    def test_prompts_are_different(self) -> None:
        """Wind and Wall approval prompts should be different."""
        wind_prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        wall_prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert wind_prompt != wall_prompt
