"""Unit tests for RACI-specific prompt formatters.

Tests for the four RACI prompt formatters:
- format_raci_proposal_prompt: R's initial proposal
- format_raci_advice_prompt: C's feedback
- format_raci_rebuttal_prompt: R's synthesis of C feedback
- format_raci_verdict_prompt: A's GO/NO-GO decision

TDD: These tests are written first (RED phase) before implementation.
"""

from debate_hall_mcp.prompts import (
    RACI_ACCOUNTABLE_PROMPT,
    RACI_CONSULTED_PROMPT,
    RACI_RESPONSIBLE_PROMPT,
    format_raci_advice_prompt,
    format_raci_proposal_prompt,
    format_raci_rebuttal_prompt,
    format_raci_verdict_prompt,
)


class TestRACISystemPrompts:
    """Tests for RACI system prompt constants."""

    def test_responsible_prompt_exists(self) -> None:
        """RACI Responsible system prompt should exist."""
        assert RACI_RESPONSIBLE_PROMPT is not None
        assert len(RACI_RESPONSIBLE_PROMPT) > 0

    def test_consulted_prompt_exists(self) -> None:
        """RACI Consulted system prompt should exist."""
        assert RACI_CONSULTED_PROMPT is not None
        assert len(RACI_CONSULTED_PROMPT) > 0

    def test_accountable_prompt_exists(self) -> None:
        """RACI Accountable system prompt should exist."""
        assert RACI_ACCOUNTABLE_PROMPT is not None
        assert len(RACI_ACCOUNTABLE_PROMPT) > 0

    def test_responsible_prompt_contains_role_identity(self) -> None:
        """Responsible prompt should reference the proposer/responsible role."""
        assert "Responsible" in RACI_RESPONSIBLE_PROMPT or "responsible" in RACI_RESPONSIBLE_PROMPT

    def test_consulted_prompt_contains_role_identity(self) -> None:
        """Consulted prompt should reference the advisor/consulted role."""
        assert "Consulted" in RACI_CONSULTED_PROMPT or "advisor" in RACI_CONSULTED_PROMPT.lower()

    def test_accountable_prompt_contains_verdict(self) -> None:
        """Accountable prompt should reference GO/NO-GO verdict."""
        prompt_lower = RACI_ACCOUNTABLE_PROMPT.lower()
        assert "go" in prompt_lower or "verdict" in prompt_lower


class TestFormatRACIProposalPrompt:
    """Tests for format_raci_proposal_prompt."""

    def test_includes_topic(self) -> None:
        """Proposal prompt should include the topic."""
        prompt = format_raci_proposal_prompt("Deploy new API", "2026-02-13-deploy-test")
        assert "Deploy new API" in prompt

    def test_includes_thread_id(self) -> None:
        """Proposal prompt should include the thread_id."""
        prompt = format_raci_proposal_prompt("Deploy new API", "2026-02-13-deploy-test")
        assert "2026-02-13-deploy-test" in prompt

    def test_indicates_raci_context(self) -> None:
        """Proposal prompt should indicate RACI governance context."""
        prompt = format_raci_proposal_prompt("Test topic", "2026-02-13-test")
        prompt_lower = prompt.lower()
        assert "raci" in prompt_lower or "proposal" in prompt_lower

    def test_indicates_responsible_role(self) -> None:
        """Proposal prompt should indicate Responsible role."""
        prompt = format_raci_proposal_prompt("Test topic", "2026-02-13-test")
        prompt_lower = prompt.lower()
        assert (
            "responsible" in prompt_lower
            or "proposer" in prompt_lower
            or "proposal" in prompt_lower
        )


class TestFormatRACIAdvicePrompt:
    """Tests for format_raci_advice_prompt."""

    def test_includes_topic(self) -> None:
        """Advice prompt should include the topic."""
        prompt = format_raci_advice_prompt("Deploy new API", "2026-02-13-test", "security-reviewer")
        assert "Deploy new API" in prompt

    def test_includes_thread_id(self) -> None:
        """Advice prompt should include the thread_id."""
        prompt = format_raci_advice_prompt("Deploy new API", "2026-02-13-test", "security-reviewer")
        assert "2026-02-13-test" in prompt

    def test_includes_advisor_name(self) -> None:
        """Advice prompt should include the advisor's name."""
        prompt = format_raci_advice_prompt("Deploy new API", "2026-02-13-test", "security-reviewer")
        assert "security-reviewer" in prompt

    def test_indicates_consulted_role(self) -> None:
        """Advice prompt should indicate Consulted/advisor role."""
        prompt = format_raci_advice_prompt("Test", "2026-02-13-test", "reviewer")
        prompt_lower = prompt.lower()
        assert "consulted" in prompt_lower or "advisor" in prompt_lower or "advice" in prompt_lower


class TestFormatRACIRebuttalPrompt:
    """Tests for format_raci_rebuttal_prompt."""

    def test_includes_topic(self) -> None:
        """Rebuttal prompt should include the topic."""
        prompt = format_raci_rebuttal_prompt("Deploy new API", "2026-02-13-test")
        assert "Deploy new API" in prompt

    def test_includes_thread_id(self) -> None:
        """Rebuttal prompt should include the thread_id."""
        prompt = format_raci_rebuttal_prompt("Deploy new API", "2026-02-13-test")
        assert "2026-02-13-test" in prompt

    def test_indicates_synthesis_of_feedback(self) -> None:
        """Rebuttal prompt should indicate synthesis of consulted feedback."""
        prompt = format_raci_rebuttal_prompt("Test", "2026-02-13-test")
        prompt_lower = prompt.lower()
        assert (
            "synthesis" in prompt_lower
            or "synthesize" in prompt_lower
            or "rebuttal" in prompt_lower
            or "feedback" in prompt_lower
        )


class TestFormatRACIVerdictPrompt:
    """Tests for format_raci_verdict_prompt."""

    def test_includes_topic(self) -> None:
        """Verdict prompt should include the topic."""
        prompt = format_raci_verdict_prompt("Deploy new API", "2026-02-13-test")
        assert "Deploy new API" in prompt

    def test_includes_thread_id(self) -> None:
        """Verdict prompt should include the thread_id."""
        prompt = format_raci_verdict_prompt("Deploy new API", "2026-02-13-test")
        assert "2026-02-13-test" in prompt

    def test_requires_structured_decision(self) -> None:
        """Verdict prompt MUST instruct A-role to output GO/NO-GO/CONDITIONAL."""
        prompt = format_raci_verdict_prompt("Test", "2026-02-13-test")
        prompt_upper = prompt.upper()
        assert "GO" in prompt_upper
        assert "NO-GO" in prompt_upper or "NO_GO" in prompt_upper or "NOGO" in prompt_upper

    def test_requires_reasons(self) -> None:
        """Verdict prompt should require reasons for the decision."""
        prompt = format_raci_verdict_prompt("Test", "2026-02-13-test")
        prompt_lower = prompt.lower()
        assert "reason" in prompt_lower or "rationale" in prompt_lower or "justif" in prompt_lower

    def test_indicates_accountable_role(self) -> None:
        """Verdict prompt should indicate Accountable role."""
        prompt = format_raci_verdict_prompt("Test", "2026-02-13-test")
        prompt_lower = prompt.lower()
        assert (
            "accountable" in prompt_lower or "verdict" in prompt_lower or "decision" in prompt_lower
        )
