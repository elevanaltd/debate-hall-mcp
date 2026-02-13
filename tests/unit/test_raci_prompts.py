"""Unit tests for RACI-specific prompt formatters.

Tests for the four RACI prompt formatters:
- format_raci_proposal_prompt: R's initial proposal
- format_raci_advice_prompt: C's feedback
- format_raci_rebuttal_prompt: R's synthesis of C feedback
- format_raci_verdict_prompt: A's GO/NO-GO decision

Also tests for agent file resolution in RACI mode:
- _get_raci_prompt: resolves agent files or falls back to generic constants
- _get_raci_turn_instruction: returns concise RACI governance instruction per turn type

TDD: These tests are written first (RED phase) before implementation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator
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


# --- Fixtures for agent file resolution tests ---


@pytest.fixture
def orchestrator(tmp_path: Path) -> DebateOrchestrator:
    """Create a DebateOrchestrator instance for testing _get_raci_prompt."""
    tier_config = TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(
            consensus_required=False,
            max_turns=12,
            max_refinement_loops=0,
        ),
    )
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return DebateOrchestrator(tier_config=tier_config, state_dir=state_dir)


# --- Tests for _get_raci_prompt with agent file resolution ---


class TestGetRACIPromptAgentResolution:
    """Tests for _get_raci_prompt() with agent file resolution.

    When an agent file exists for the given role_name, _get_raci_prompt
    should return the agent file content with the RACI turn instruction appended.
    When no agent file exists, it should fall back to the generic RACI constants.
    """

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_returns_agent_prompt_with_raci_instruction_for_proposal(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When agent file exists, proposal turn returns agent content + RACI instruction."""
        mock_get_agent.return_value = "===AGENT::critical-engineer==="
        result = orchestrator._get_raci_prompt("proposal", "critical-engineer")
        assert "===AGENT::critical-engineer===" in result
        assert "RESPONSIBLE" in result
        assert "proposal" in result.lower() or "propose" in result.lower()
        mock_get_agent.assert_called_once_with("critical-engineer")

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_returns_agent_prompt_with_raci_instruction_for_advice(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When agent file exists, advice turn returns agent content + RACI instruction."""
        mock_get_agent.return_value = "===AGENT::security-reviewer==="
        result = orchestrator._get_raci_prompt("advice", "security-reviewer")
        assert "===AGENT::security-reviewer===" in result
        assert "CONSULTED" in result
        mock_get_agent.assert_called_once_with("security-reviewer")

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_returns_agent_prompt_with_raci_instruction_for_rebuttal(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When agent file exists, rebuttal turn returns agent content + RACI instruction."""
        mock_get_agent.return_value = "===AGENT::architect==="
        result = orchestrator._get_raci_prompt("rebuttal", "architect")
        assert "===AGENT::architect===" in result
        assert "RESPONSIBLE" in result
        assert "synthesize" in result.lower() or "feedback" in result.lower()
        mock_get_agent.assert_called_once_with("architect")

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_returns_agent_prompt_with_raci_instruction_for_verdict(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When agent file exists, verdict turn returns agent content + RACI instruction."""
        mock_get_agent.return_value = "===AGENT::tech-lead==="
        result = orchestrator._get_raci_prompt("verdict", "tech-lead")
        assert "===AGENT::tech-lead===" in result
        assert "ACCOUNTABLE" in result
        assert "GO" in result or "verdict" in result.lower()
        mock_get_agent.assert_called_once_with("tech-lead")

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_falls_back_to_generic_prompt_when_no_agent_file(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When no agent file exists, falls back to generic RACI constant."""
        mock_get_agent.return_value = None
        result = orchestrator._get_raci_prompt("proposal", "unknown-role")
        assert result == RACI_RESPONSIBLE_PROMPT
        mock_get_agent.assert_called_once_with("unknown-role")

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_falls_back_to_consulted_prompt_for_advice(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When no agent file, advice turn falls back to RACI_CONSULTED_PROMPT."""
        mock_get_agent.return_value = None
        result = orchestrator._get_raci_prompt("advice", "unknown-advisor")
        assert result == RACI_CONSULTED_PROMPT

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_falls_back_to_accountable_prompt_for_verdict(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When no agent file, verdict turn falls back to RACI_ACCOUNTABLE_PROMPT."""
        mock_get_agent.return_value = None
        result = orchestrator._get_raci_prompt("verdict", "unknown-lead")
        assert result == RACI_ACCOUNTABLE_PROMPT

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_falls_back_to_responsible_prompt_for_rebuttal(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """When no agent file, rebuttal turn falls back to RACI_RESPONSIBLE_PROMPT."""
        mock_get_agent.return_value = None
        result = orchestrator._get_raci_prompt("rebuttal", "unknown-role")
        assert result == RACI_RESPONSIBLE_PROMPT

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_agent_prompt_and_raci_instruction_are_separated(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """Agent prompt and RACI instruction should be separated by double newline."""
        mock_get_agent.return_value = "Agent identity content"
        result = orchestrator._get_raci_prompt("proposal", "test-agent")
        # The agent content and RACI instruction should be separated
        assert "Agent identity content\n\n" in result

    @patch("debate_hall_mcp.orchestrator.get_agent_prompt")
    def test_role_name_passed_through_correctly(
        self, mock_get_agent: MagicMock, orchestrator: DebateOrchestrator
    ) -> None:
        """The role_name parameter should be passed directly to get_agent_prompt."""
        mock_get_agent.return_value = None
        orchestrator._get_raci_prompt("proposal", "my-special-role")
        mock_get_agent.assert_called_once_with("my-special-role")


class TestGetRACITurnInstruction:
    """Tests for _get_raci_turn_instruction() helper.

    This method returns concise RACI governance instructions to append
    to agent identity prompts.
    """

    def test_proposal_instruction_mentions_responsible(
        self, orchestrator: DebateOrchestrator
    ) -> None:
        """Proposal instruction should mention RESPONSIBLE role."""
        instruction = orchestrator._get_raci_turn_instruction("proposal")
        assert "RESPONSIBLE" in instruction

    def test_advice_instruction_mentions_consulted(self, orchestrator: DebateOrchestrator) -> None:
        """Advice instruction should mention CONSULTED role."""
        instruction = orchestrator._get_raci_turn_instruction("advice")
        assert "CONSULTED" in instruction

    def test_rebuttal_instruction_mentions_responsible(
        self, orchestrator: DebateOrchestrator
    ) -> None:
        """Rebuttal instruction should mention RESPONSIBLE role."""
        instruction = orchestrator._get_raci_turn_instruction("rebuttal")
        assert "RESPONSIBLE" in instruction

    def test_verdict_instruction_mentions_accountable(
        self, orchestrator: DebateOrchestrator
    ) -> None:
        """Verdict instruction should mention ACCOUNTABLE role."""
        instruction = orchestrator._get_raci_turn_instruction("verdict")
        assert "ACCOUNTABLE" in instruction

    def test_verdict_instruction_mentions_go_nogo(self, orchestrator: DebateOrchestrator) -> None:
        """Verdict instruction should mention GO/NO-GO/CONDITIONAL."""
        instruction = orchestrator._get_raci_turn_instruction("verdict")
        assert "GO" in instruction
        assert "NO-GO" in instruction

    def test_unknown_turn_type_returns_responsible(self, orchestrator: DebateOrchestrator) -> None:
        """Unknown turn type should default to responsible instruction."""
        instruction = orchestrator._get_raci_turn_instruction("unknown")
        assert "RESPONSIBLE" in instruction
