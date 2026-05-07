"""Unit tests for consensus prompts (Phase 4: Consensus Implementation + VTP).

Tests the Wind/Wall approval prompt formatters:
- format_wind_approval_prompt
- format_wall_approval_prompt
- Prompt structure and content
- DEBATE_STATE reference for VTP pattern

VTP Pattern: The orchestrator pre-fetches debate state and injects it into
the prompt via <DEBATE_STATE> tags. Agents receive state passively instead
of needing to call get_debate() themselves.
"""

import json

from debate_hall_mcp.prompts import (
    format_door_consensus_prompt,
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
        """Wind approval prompt should include thread_id for reference."""
        prompt = format_wind_approval_prompt(topic="Test topic", thread_id="2026-01-30-test-abc")
        assert "2026-01-30-test-abc" in prompt

    def test_includes_debate_state_reference(self) -> None:
        """Wind approval prompt should reference DEBATE_STATE for VTP pattern."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "DEBATE_STATE" in prompt

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
        """Wall approval prompt should include thread_id for reference."""
        prompt = format_wall_approval_prompt(topic="Test topic", thread_id="2026-01-30-test-xyz")
        assert "2026-01-30-test-xyz" in prompt

    def test_includes_debate_state_reference(self) -> None:
        """Wall approval prompt should reference DEBATE_STATE for VTP pattern."""
        prompt = format_wall_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        assert "DEBATE_STATE" in prompt

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


class TestConsensusDoorCarriesPathContractCitation:
    """RFC-0001 Fix 4: the CONSENSUS-phase Door prompt MUST carry the citation
    rule for PATH_CONTRACT_DIFF entries (accepted/disputed/reframed). This is the
    counterpart to TestInitialDoorOmitsPathContractCitation in test_prompts.py.
    """

    def test_consensus_door_prompt_demands_path_contract_diff_citation(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test", thread_id="2026-01-30-test", rejector="Wind", feedback="needs more rigor"
        )
        assert "PATH_CONTRACT_DIFF" in prompt
        assert "accepted" in prompt
        assert "disputed" in prompt
        assert "reframed" in prompt

    def test_consensus_door_prompt_includes_citation_syntax_example(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test", thread_id="2026-01-30-test", rejector="Wall", feedback=None
        )
        # The bracketed citation syntax that lets a reader verify each claim.
        assert "[path_N.accepted:" in prompt
        assert "[path_N.disputed:" in prompt
        assert "[path_N.reframed:" in prompt

    def test_consensus_door_prompt_enforces_hard_fail_rule(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test", thread_id="2026-01-30-test", rejector="Wind", feedback="x"
        )
        # The constraint-as-catalyst proof obligation.
        assert "HARD_fail" in prompt
        assert "terminal_rationale" in prompt

    def test_consensus_door_prompt_includes_topic_thread_and_feedback(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Governance",
            thread_id="2026-01-30-gov",
            rejector="Wall",
            feedback="risk surface incomplete",
        )
        assert "Governance" in prompt
        assert "2026-01-30-gov" in prompt
        assert "Wall" in prompt
        assert "risk surface incomplete" in prompt

    def test_consensus_door_prompt_handles_none_feedback(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test", thread_id="2026-01-30-test", rejector="Wind", feedback=None
        )
        assert "No specific feedback provided." in prompt

    def test_consensus_door_prompt_acknowledges_divergence_marker(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test", thread_id="2026-01-30-test", rejector="Wind", feedback=None
        )
        # Door must know how to react to NO_NEW_DIVERGENCE rather than fabricating citations.
        assert "NO_NEW_DIVERGENCE" in prompt
        assert "divergence_marker" in prompt


class TestWindConsensusSentinelIsJsonCompatible:
    """RFC-0001 Fix 3: the NO_NEW_DIVERGENCE sentinel must be emitted in a
    JSON-compatible form so it does not collide with the JSON path_contract.diff
    output mandated elsewhere in the prompt. The schema-level signal is the
    `divergence_marker` field on `DiffRevision` (RFC §3.1).
    """

    def test_wind_consensus_prompt_emits_sentinel_inside_json(self) -> None:
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        # The schema field carries the sentinel; raw NO_NEW_DIVERGENCE without JSON
        # framing is the bug being fixed.
        assert "divergence_marker" in prompt
        assert "NO_NEW_DIVERGENCE" in prompt

    def test_wind_consensus_prompt_sentinel_block_parses_as_json(self) -> None:
        """The example sentinel block in the prompt must be valid JSON when
        extracted (after str.format brace-escaping is applied)."""
        prompt = format_wind_approval_prompt(topic="Test", thread_id="2026-01-30-test")
        # Locate a JSON object containing divergence_marker and ensure it parses.
        # The prompt embeds the example with literal braces (already unescaped by f-string).
        marker_idx = prompt.find('"divergence_marker"')
        assert marker_idx != -1, "divergence_marker example missing from prompt"
        # Walk back to the nearest '{' and forward to its matching '}' to extract the object.
        start = prompt.rfind("{", 0, marker_idx)
        depth = 0
        end = -1
        for i in range(start, len(prompt)):
            ch = prompt[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        assert end != -1, "could not find balanced JSON object around divergence_marker"
        snippet = prompt[start:end]
        parsed = json.loads(snippet)
        assert parsed["divergence_marker"] == "NO_NEW_DIVERGENCE"
        assert parsed["accepted"] == []
        assert parsed["disputed"] == []
        assert parsed["reframed"] == []
