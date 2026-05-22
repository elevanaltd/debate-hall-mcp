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
            topic="Test",
            thread_id="2026-01-30-test",
            rejector="Wind",
            feedback="needs more rigor",
            path_contract_enabled=True,
        )
        assert "PATH_CONTRACT_DIFF" in prompt
        assert "accepted" in prompt
        assert "disputed" in prompt
        assert "reframed" in prompt

    def test_consensus_door_prompt_includes_citation_syntax_example(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test",
            thread_id="2026-01-30-test",
            rejector="Wall",
            feedback=None,
            path_contract_enabled=True,
        )
        # The bracketed citation syntax that lets a reader verify each claim.
        assert "[path_N.accepted:" in prompt
        assert "[path_N.disputed:" in prompt
        assert "[path_N.reframed:" in prompt

    def test_consensus_door_prompt_enforces_hard_fail_rule(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="Test",
            thread_id="2026-01-30-test",
            rejector="Wind",
            feedback="x",
            path_contract_enabled=True,
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
            topic="Test",
            thread_id="2026-01-30-test",
            rejector="Wind",
            feedback=None,
            path_contract_enabled=True,
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
        prompt = format_wind_approval_prompt(
            topic="Test", thread_id="2026-01-30-test", path_contract_enabled=True
        )
        # The schema field carries the sentinel; raw NO_NEW_DIVERGENCE without JSON
        # framing is the bug being fixed.
        assert "divergence_marker" in prompt
        assert "NO_NEW_DIVERGENCE" in prompt

    def test_wind_consensus_prompt_sentinel_block_parses_as_json(self) -> None:
        """The example sentinel block in the prompt must be valid JSON when
        extracted (after str.format brace-escaping is applied)."""
        prompt = format_wind_approval_prompt(
            topic="Test", thread_id="2026-01-30-test", path_contract_enabled=True
        )
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


class TestDoorConsensusCitesSynthesisGuidanceFindingE:
    """RFC-0001 §3.3 Finding E — ``synthesis_guidance`` on DiffRevision.

    Wind may record cross-path / synthesis-level insight in
    ``DiffRevision.synthesis_guidance`` (NotRequired). When present, Door's
    consensus citation rule (§5.4) is EXTENDED to require explicit citation
    alongside per-path citations. The prompt must surface this obligation so
    the agent does not silently drop the cross-path insight.
    """

    def test_consensus_door_prompt_mentions_synthesis_guidance(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="T",
            thread_id="2026-05-21-t",
            rejector="Wind",
            feedback=None,
            path_contract_enabled=True,
        )
        assert "synthesis_guidance" in prompt

    def test_consensus_door_prompt_demands_citation_when_present(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="T",
            thread_id="2026-05-21-t",
            rejector="Wind",
            feedback=None,
            path_contract_enabled=True,
        )
        idx = prompt.find("synthesis_guidance")
        assert idx != -1
        # Within a ~400 char window around the mention, the prompt must use the
        # word "cite" (or "citation") so the obligation is unambiguous.
        window = prompt[max(0, idx - 200) : idx + 400].lower()
        assert "cite" in window or "citation" in window


class TestConsensusPromptsBranchOnSynthesisStatus:
    """RFC-0001 #198 — consensus prompts branch on SYNTHESIS_STATUS.

    * Wind consensus turn fires under PRESENT (initial review) or PENDING_REFINEMENT
      (after a prior synthesis was withdrawn).
    * Wall consensus turn (CRS Finding 2 rework) fires under PRESENT (initial review)
      or PENDING_REFINEMENT and MUST carry the path_contract verdict-revision
      instructions that were previously misplaced in ``format_wall_user_prompt``.
    * Door consensus turn fires under PRESENT during refinement, or
      PENDING_REFINEMENT after rejection. TMG Finding 5 requires explicit
      assertion of the PENDING_REFINEMENT branch.
    """

    def test_wind_approval_prompt_references_pending_refinement(self) -> None:
        prompt = format_wind_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "SYNTHESIS_STATUS" in prompt
        assert "PENDING_REFINEMENT" in prompt

    def test_door_consensus_prompt_references_synthesis_status_present(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="T",
            thread_id="2026-05-21-t",
            rejector="Wind",
            feedback=None,
            path_contract_enabled=True,
        )
        assert "SYNTHESIS_STATUS" in prompt
        assert "PRESENT" in prompt

    def test_door_consensus_prompt_references_pending_refinement(self) -> None:
        """TMG Finding 5: Door consensus must explicitly cover PENDING_REFINEMENT.

        Code already handles this branch but the prior test suite only asserted
        the PRESENT branch; this asserts the PENDING_REFINEMENT branch too so
        regressions are caught.
        """
        prompt = format_door_consensus_prompt(
            topic="T",
            thread_id="2026-05-21-t",
            rejector="Wall",
            feedback="x",
            path_contract_enabled=True,
        )
        assert "PENDING_REFINEMENT" in prompt


class TestWallApprovalPromptCarriesPathContractConsensus:
    """RFC-0001 #221 CRS Finding 2 — Wall consensus prompt must carry the
    path_contract verdict-revision instructions.

    The previous implementation placed the PRESENT branch (instructing Wall to
    emit a NEW verdict revision against the refined synthesis) inside
    ``format_wall_user_prompt`` — but that function is only called for Wall's
    INITIAL turn (when SYNTHESIS_STATUS is always PENDING_INITIAL). The PRESENT
    branch was therefore dead code. The instructions belong in the consensus-
    phase prompt: ``format_wall_approval_prompt``.
    """

    def test_wall_approval_prompt_references_synthesis_status(self) -> None:
        prompt = format_wall_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "SYNTHESIS_STATUS" in prompt

    def test_wall_approval_prompt_references_present(self) -> None:
        prompt = format_wall_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "PRESENT" in prompt

    def test_wall_approval_prompt_references_pending_refinement(self) -> None:
        prompt = format_wall_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "PENDING_REFINEMENT" in prompt

    def test_wall_approval_prompt_mentions_verdict_revision(self) -> None:
        """Wall's consensus turn appends a NEW PATH_CONTRACT_VERDICT revision
        re-validating against the refined synthesis. The prompt must surface
        this obligation so the agent does not silently skip it.
        """
        prompt = format_wall_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "PATH_CONTRACT_VERDICT" in prompt
        # The "new verdict revision" language is the load-bearing instruction.
        assert "verdict revision" in prompt.lower() or "new verdict" in prompt.lower()


class TestDoorConsensusCoexistenceRuleFindingD:
    """TMG Finding 6 — RFC-0001 §3.3 Finding D coexistence rule.

    ``divergence_marker: NO_NEW_DIVERGENCE`` MAY coexist with non-empty
    ``disputed`` entries (the sentinel only requires zero HARD_fail verdicts,
    not zero disputed entries). The Door consensus prompt must instruct the
    agent to cite the disputed entries even when the sentinel is present —
    otherwise the cross-path emergent insight is silently dropped.

    The implementation already covers this; the test asserts the instruction
    appears within a tight semantic window so a future regression that drops
    the coexistence clause is caught immediately.
    """

    def test_door_consensus_prompt_covers_no_new_divergence_with_disputed(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="T",
            thread_id="2026-05-21-t",
            rejector="Wind",
            feedback=None,
            path_contract_enabled=True,
        )
        # The coexistence clause must appear: NO_NEW_DIVERGENCE may coexist with
        # non-empty `disputed`; cite any disputed entries present even when the
        # sentinel is set.
        assert "NO_NEW_DIVERGENCE" in prompt
        idx = prompt.find("NO_NEW_DIVERGENCE")
        # The "coexist" language and the "disputed" mention must appear in the
        # same instruction window.
        window = prompt[idx : idx + 600]
        assert (
            "coexist" in window.lower()
        ), "Finding D coexistence rule must use the word 'coexist' near NO_NEW_DIVERGENCE"
        assert (
            "disputed" in window.lower()
        ), "Finding D coexistence rule must reference 'disputed' near NO_NEW_DIVERGENCE"


class TestConsensusOffModeByteIdentity:
    """RFC-0001 #221 CRS Finding 3 — off-mode prompt byte-identity for consensus prompts.

    When ``path_contract_enabled`` is ``False`` (the default), the
    Wind/Wall consensus and Door refinement prompts MUST NOT carry any
    path_contract instruction block.
    """

    def test_wind_approval_off_mode_has_no_path_contract_block(self) -> None:
        prompt = format_wind_approval_prompt(topic="T", thread_id="2026-05-21-t")
        assert "[RFC-0001 — path_contract" not in prompt
        assert "PATH_CONTRACT_DIFF" not in prompt
        assert "SYNTHESIS_STATUS" not in prompt
        assert "NO_NEW_DIVERGENCE" not in prompt
        # The basic APPROVE/REJECT machinery must still be present.
        assert "APPROVE" in prompt
        assert "REJECT" in prompt

    def test_wall_approval_off_mode_has_no_path_contract_block(self) -> None:
        prompt = format_wall_approval_prompt(topic="T", thread_id="2026-05-21-t")
        assert "[RFC-0001 — path_contract" not in prompt
        assert "PATH_CONTRACT_VERDICT" not in prompt
        assert "SYNTHESIS_STATUS" not in prompt
        assert "APPROVE" in prompt
        assert "REJECT" in prompt

    def test_door_consensus_off_mode_has_no_path_contract_block(self) -> None:
        prompt = format_door_consensus_prompt(
            topic="T", thread_id="2026-05-21-t", rejector="Wind", feedback="x"
        )
        assert "[RFC-0001 — path_contract" not in prompt
        assert "PATH_CONTRACT_DIFF" not in prompt
        assert "SYNTHESIS_STATUS" not in prompt
        assert "synthesis_guidance" not in prompt
        # Standard refinement language must remain.
        assert "REJECTED" in prompt
        assert "refine" in prompt.lower()


class TestWindConsensusPerInvariantContentRule:
    """RFC-0001 §3.2 / Finding C — per-invariant REQUIRED CONTENT RULE.

    Wind's consensus prompt must instruct that EACH HARD_fail invariant
    requires its OWN qualifying entry (cross-invariant substitution is
    invalid).
    """

    def test_wind_consensus_prompt_mentions_each_invariant_obligation(self) -> None:
        prompt = format_wind_approval_prompt(
            topic="T", thread_id="2026-05-21-t", path_contract_enabled=True
        )
        assert "HARD_fail" in prompt
        # The per-invariant phrasing must be explicit (substitution disallowed).
        assert "each HARD_fail invariant" in prompt or "every HARD_fail invariant" in prompt


class TestWindConsensusSentinelGatedOnHardFail:
    """RFC-0001 follow-up: Wind's NO_NEW_DIVERGENCE sentinel must be gated on
    the absence of HARD_fail verdicts for the path. Otherwise it conflicts with
    Door's HARD_fail coverage rule (Door cannot cite a reframed/accepted entry
    that does not exist), violating the constraint-as-catalyst proof.
    """

    def test_wind_consensus_prompt_gates_sentinel_on_no_hard_fail(self) -> None:
        """Sentinel instruction must explicitly require zero HARD_fail verdicts."""
        prompt = format_wind_approval_prompt(
            topic="Test", thread_id="2026-01-30-test", path_contract_enabled=True
        )
        # The precondition language must be present in some form.
        assert (
            "no HARD_fail" in prompt
        ), "Sentinel instruction must gate NO_NEW_DIVERGENCE on absence of HARD_fail verdicts"

    def test_wind_consensus_prompt_forbids_sentinel_on_hard_fail_paths(self) -> None:
        """Prompt must explicitly state that NO_NEW_DIVERGENCE is invalid for
        any path with one or more HARD_fail verdicts."""
        prompt = format_wind_approval_prompt(
            topic="Test", thread_id="2026-01-30-test", path_contract_enabled=True
        )
        # The counterpart prohibition must be present.
        assert (
            "INVALID for HARD_fail paths" in prompt
        ), "Prompt must explicitly mark NO_NEW_DIVERGENCE as INVALID for HARD_fail paths"
