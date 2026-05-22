"""Unit tests for prompt templates (Phase 3: Auto-orchestration + VTP).

Tests prompt generation for Wind/Wall/Door agents with:
- Thread ID reference for state access
- DEBATE_STATE reference for VTP (Virtual Tool Preload) pattern
- Role-specific task instructions

VTP Pattern: The orchestrator pre-fetches debate state and injects it into
the prompt via <DEBATE_STATE> tags. Agents receive state passively instead
of needing to call get_debate() themselves.
"""

import pytest

from debate_hall_mcp.prompts import (
    DOOR_PROMPT,
    WALL_PROMPT,
    WIND_PROMPT,
    format_door_user_prompt,
    format_wall_user_prompt,
    format_wind_user_prompt,
)


class TestBasePrompts:
    """Test that base system prompts exist and have expected structure."""

    def test_wind_prompt_exists(self) -> None:
        """WIND_PROMPT should exist and contain PATHOS role."""
        assert WIND_PROMPT is not None
        assert "PATHOS" in WIND_PROMPT
        assert "Wind" in WIND_PROMPT

    def test_wall_prompt_exists(self) -> None:
        """WALL_PROMPT should exist and contain ETHOS role."""
        assert WALL_PROMPT is not None
        assert "ETHOS" in WALL_PROMPT
        assert "Wall" in WALL_PROMPT

    def test_door_prompt_exists(self) -> None:
        """DOOR_PROMPT should exist and contain LOGOS role."""
        assert DOOR_PROMPT is not None
        assert "LOGOS" in DOOR_PROMPT
        assert "Door" in DOOR_PROMPT


class TestWindUserPrompt:
    """Tests for format_wind_user_prompt (PATHOS - The Ideator)."""

    def test_includes_topic(self) -> None:
        """User prompt should include the debate topic."""
        prompt = format_wind_user_prompt(
            topic="API design patterns", thread_id="2026-01-30-api-design"
        )
        assert "API design patterns" in prompt

    def test_includes_thread_id(self) -> None:
        """User prompt should include thread_id for state access."""
        prompt = format_wind_user_prompt(topic="Testing strategy", thread_id="2026-01-30-testing")
        assert "2026-01-30-testing" in prompt

    def test_includes_debate_state_reference(self) -> None:
        """User prompt should reference DEBATE_STATE for VTP pattern."""
        prompt = format_wind_user_prompt(topic="Architecture", thread_id="2026-01-30-arch")
        # Must reference DEBATE_STATE tags (injected by orchestrator)
        assert "DEBATE_STATE" in prompt
        assert "2026-01-30-arch" in prompt

    def test_includes_wind_role_description(self) -> None:
        """User prompt should describe Wind's role (ideation/expansion)."""
        prompt = format_wind_user_prompt(topic="Feature design", thread_id="2026-01-30-feature")
        # Should mention Wind role or PATHOS cognition
        assert "Wind" in prompt or "PATHOS" in prompt
        # Should mention ideation or expansion
        assert any(
            term in prompt.lower()
            for term in ["expand", "explore", "possibilit", "ideat", "divergent"]
        )

    def test_prompt_is_non_empty_string(self) -> None:
        """User prompt should return a non-empty string."""
        prompt = format_wind_user_prompt(topic="Test", thread_id="2026-01-30-test")
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt


class TestWallUserPrompt:
    """Tests for format_wall_user_prompt (ETHOS - The Validator)."""

    def test_includes_topic(self) -> None:
        """User prompt should include the debate topic."""
        prompt = format_wall_user_prompt(topic="Security audit", thread_id="2026-01-30-security")
        assert "Security audit" in prompt

    def test_includes_thread_id(self) -> None:
        """User prompt should include thread_id for state access."""
        prompt = format_wall_user_prompt(topic="Code review", thread_id="2026-01-30-review")
        assert "2026-01-30-review" in prompt

    def test_includes_debate_state_reference(self) -> None:
        """User prompt should reference DEBATE_STATE for VTP pattern."""
        prompt = format_wall_user_prompt(topic="Validation", thread_id="2026-01-30-val")
        # Must reference DEBATE_STATE tags (injected by orchestrator)
        assert "DEBATE_STATE" in prompt
        assert "2026-01-30-val" in prompt

    def test_includes_wall_role_description(self) -> None:
        """User prompt should describe Wall's role (validation/constraints)."""
        prompt = format_wall_user_prompt(topic="Constraints", thread_id="2026-01-30-const")
        # Should mention Wall role or ETHOS cognition
        assert "Wall" in prompt or "ETHOS" in prompt
        # Should mention validation or constraints
        assert any(
            term in prompt.lower()
            for term in ["validat", "constrain", "evidence", "verify", "assess"]
        )

    def test_prompt_is_non_empty_string(self) -> None:
        """User prompt should return a non-empty string."""
        prompt = format_wall_user_prompt(topic="Test", thread_id="2026-01-30-test")
        assert isinstance(prompt, str)
        assert len(prompt) > 100


class TestDoorUserPrompt:
    """Tests for format_door_user_prompt (LOGOS - The Synthesizer)."""

    def test_includes_topic(self) -> None:
        """User prompt should include the debate topic."""
        prompt = format_door_user_prompt(
            topic="System integration", thread_id="2026-01-30-integration"
        )
        assert "System integration" in prompt

    def test_includes_thread_id(self) -> None:
        """User prompt should include thread_id for state access."""
        prompt = format_door_user_prompt(topic="Synthesis", thread_id="2026-01-30-synth")
        assert "2026-01-30-synth" in prompt

    def test_includes_debate_state_reference(self) -> None:
        """User prompt should reference DEBATE_STATE for VTP pattern."""
        prompt = format_door_user_prompt(topic="Resolution", thread_id="2026-01-30-res")
        # Must reference DEBATE_STATE tags (injected by orchestrator)
        assert "DEBATE_STATE" in prompt
        assert "2026-01-30-res" in prompt

    def test_includes_door_role_description(self) -> None:
        """User prompt should describe Door's role (synthesis/resolution)."""
        prompt = format_door_user_prompt(topic="Resolution", thread_id="2026-01-30-resolve")
        # Should mention Door role or LOGOS cognition
        assert "Door" in prompt or "LOGOS" in prompt
        # Should mention synthesis or integration
        assert any(
            term in prompt.lower()
            for term in ["synthesi", "integrat", "resolv", "converge", "third"]
        )

    def test_prompt_is_non_empty_string(self) -> None:
        """User prompt should return a non-empty string."""
        prompt = format_door_user_prompt(topic="Test", thread_id="2026-01-30-test")
        assert isinstance(prompt, str)
        assert len(prompt) > 100


class TestInitialDoorOmitsPathContractCitation:
    """RFC-0001 Fix 4: the INITIAL Door synthesis prompt MUST NOT mandate citation
    of PATH_CONTRACT_DIFF entries — those entries do not exist yet at the initial
    Door turn (Wind emits PATH_CONTRACT_DIFF only in the consensus phase). This
    test guards against the prior bug where the initial prompt forced fabrication.
    """

    def test_initial_door_prompt_does_not_demand_path_contract_diff_citation(self) -> None:
        """Initial Door prompt MUST NOT mandate citation of PATH_CONTRACT_DIFF entries.

        The prompt MAY mention PATH_CONTRACT_DIFF to explain that it does not exist
        yet (educational), but it MUST NOT carry the citation syntax or the
        accepted/disputed/reframed mandate that forces fabrication.
        """
        prompt = format_door_user_prompt(topic="Test", thread_id="2026-01-30-test")
        # The citation syntax for diff entries belongs only to the consensus prompt.
        assert "[path_N.accepted:" not in prompt
        assert "[path_N.disputed:" not in prompt
        assert "[path_N.reframed:" not in prompt
        # And the explicit "must cite EVERY non-empty category" mandate must be absent.
        assert "must cite EVERY non-empty category" not in prompt
        assert "must cite, for that path" not in prompt

    def test_initial_door_prompt_still_acknowledges_frame_and_verdict(self) -> None:
        """Initial Door prompt should still note that FRAME and VERDICT exist (those are emitted by turn 1 / turn 2)."""
        prompt = format_door_user_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "PATH_CONTRACT_FRAME" in prompt
        assert "PATH_CONTRACT_VERDICT" in prompt


class TestPathContractPromptsBranchOnSynthesisStatus:
    """RFC-0001 #198 — prompt branches keyed off the SYNTHESIS_STATUS line.

    Per the #218 joint-emission contract, the context compiler emits
    ``SYNTHESIS_STATUS::<value>`` inside ``<DEBATE_STATE>`` IFF
    ``<PATH_CONTRACTS>`` is also emitted. Values: PENDING_INITIAL,
    PENDING_REFINEMENT, PRESENT. The Wind/Wall/Door prompts must instruct
    the agent on how to branch deterministically on each value rather than
    inferring intent from heuristics (Finding F prompt-portion).
    """

    def test_wind_initial_prompt_references_synthesis_status_pending_initial(self) -> None:
        """Wind initial prompt must direct the agent on PENDING_INITIAL handling."""
        prompt = format_wind_user_prompt(topic="T", thread_id="2026-05-21-t")
        assert "SYNTHESIS_STATUS" in prompt
        assert "PENDING_INITIAL" in prompt

    def test_wall_prompt_references_synthesis_status_present(self) -> None:
        """Wall reads existing contract under PRESENT (refinement phase)."""
        prompt = format_wall_user_prompt(topic="T", thread_id="2026-05-21-t")
        assert "SYNTHESIS_STATUS" in prompt
        assert "PRESENT" in prompt

    def test_door_initial_prompt_references_synthesis_status_present(self) -> None:
        """Door initial prompt branches on PRESENT (consumes existing contract)."""
        prompt = format_door_user_prompt(topic="T", thread_id="2026-05-21-t")
        assert "SYNTHESIS_STATUS" in prompt
        assert "PRESENT" in prompt


class TestWindInitialPromptInvariantNamingFindingA:
    """RFC-0001 §3.3 Finding A — ``Invariant = str`` with Wall-discipline naming.

    The pre-amendment closed enum ``[halting, single_wall_coherence, re_approval,
    per_turn_role_contract]`` is SUPERSEDED. Wind's initial prompt must instruct
    Wall-discipline snake_case naming, semantically distinct per orthogonal
    concern; it MUST NOT bind invariants to that flow-shaped closed enum.
    """

    def test_wind_initial_prompt_does_not_advertise_closed_enum(self) -> None:
        """Wind prompt must not instruct the agent to pick from the superseded enum."""
        prompt = format_wind_user_prompt(topic="T", thread_id="2026-05-21-t")
        assert "halting, single_wall_coherence, re_approval, per_turn_role_contract" not in prompt
        assert "closed enum" not in prompt
        assert "pick from: halting" not in prompt

    def test_wind_initial_prompt_advertises_topic_specific_snake_case(self) -> None:
        """Wind prompt must teach the agent Wall-discipline naming convention."""
        prompt = format_wind_user_prompt(topic="T", thread_id="2026-05-21-t")
        assert "snake_case" in prompt
        assert "invariants_touched" in prompt
        assert "topic-specific" in prompt or "topic specific" in prompt


class TestPerInvariantContentRuleSurfacedToAgents:
    """RFC-0001 §3.2 (Finding C) — REQUIRED CONTENT RULE is per-invariant.

    Each HARD_fail invariant under ``accepted`` or ``reframed`` requires its
    OWN rationale entry (a `reframed` entry on invariant X does NOT satisfy
    HARD_fail on invariant Y). The Wind initial prompt must surface that
    invariants are independently scored so downstream consensus turns can
    honour the per-entry obligation.
    """

    def test_wind_initial_prompt_warns_about_per_invariant_obligation(self) -> None:
        """Wind initial prompt must surface that invariants are independently scored."""
        prompt = format_wind_user_prompt(topic="T", thread_id="2026-05-21-t")
        # The path may touch multiple invariants; Wall scores each independently.
        text = prompt.lower()
        assert "each" in text and "invariant" in text


class TestPromptConsistency:
    """Tests for consistency across all prompt functions."""

    @pytest.mark.parametrize(
        "format_func",
        [format_wind_user_prompt, format_wall_user_prompt, format_door_user_prompt],
    )
    def test_all_prompts_include_thread_id(self, format_func) -> None:
        """All prompt functions should include the thread_id."""
        thread_id = "2026-01-30-consistency-test"
        prompt = format_func(topic="Test topic", thread_id=thread_id)
        assert thread_id in prompt

    @pytest.mark.parametrize(
        "format_func",
        [format_wind_user_prompt, format_wall_user_prompt, format_door_user_prompt],
    )
    def test_all_prompts_mention_debate_state(self, format_func) -> None:
        """All prompt functions should mention DEBATE_STATE for VTP pattern."""
        prompt = format_func(topic="Test", thread_id="2026-01-30-test")
        assert "DEBATE_STATE" in prompt

    @pytest.mark.parametrize(
        "format_func",
        [format_wind_user_prompt, format_wall_user_prompt, format_door_user_prompt],
    )
    def test_all_prompts_mention_wind_wall_door(self, format_func) -> None:
        """All prompts should mention this is a Wind/Wall/Door debate."""
        prompt = format_func(topic="Test", thread_id="2026-01-30-test")
        # Should reference the debate structure
        assert "Wind" in prompt or "Wall" in prompt or "Door" in prompt
