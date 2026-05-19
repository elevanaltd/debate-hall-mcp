"""Tests for <PATH_CONTRACTS> rendering and <SYNTHESIS_STATUS> signaling (RFC-0001 #199).

Covers:

* RFC §6 item 1 — latest-revision-per-field + revision-count rendering
* Feature-off byte-identity: empty contracts list ⇒ no <PATH_CONTRACTS> block emitted
* Finding F — explicit <SYNTHESIS_STATUS> flag (PENDING_INITIAL | PRESENT |
  PENDING_REFINEMENT) so Wind/Wall/Door prompts can branch unambiguously without
  the APPROVE/REJECT-vs-no-synthesis conflation reported in #204
* RFC §8 Q3 — token-budget worst-case ≤ ~3.6k tokens for 3 paths × 3 fields
* Finding I — orchestrator's Door prompt construction never reads from disk;
  the in-memory debate_state envelope is the sole source of truth

TDD Discipline: RED → GREEN → REFACTOR.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.path_contract import (
    DiffRevision,
    FrameRevision,
    PathContract,
    VerdictRevision,
    new_path_contract,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ts(minute: int = 0) -> datetime:
    return datetime(2026, 5, 19, 12, minute, 0, tzinfo=UTC)


def _contract_frame_only(path_id: str = "path_1") -> PathContract:
    contract = new_path_contract(path_id)
    contract["frame_history"].append(
        FrameRevision(
            rev=0,
            written_at=_ts(),
            written_by="Wind",
            value={
                "assumed_problem": "users cannot reset their password without contacting support",
                "success_criterion": "password reset completes in under 60 seconds end-to-end",
                "accepted_failure_mode": "email delivery latency may exceed 60s in adverse network conditions",
                "invariants_touched": ["halting", "single_wall_coherence"],
            },
        )
    )
    return contract


def _contract_frame_and_verdict(path_id: str = "path_1") -> PathContract:
    contract = _contract_frame_only(path_id)
    contract["verdict_history"].append(
        VerdictRevision(
            rev=0,
            written_at=_ts(1),
            written_by="Wall",
            value={
                "halting": {"status": "HARD_pass", "rationale": "reset loop has a 3-attempt cap"},
                "single_wall_coherence": {
                    "status": "SOFT_disputed",
                    "rationale": "second factor may be missing on legacy accounts",
                },
            },
        )
    )
    return contract


def _contract_full(path_id: str = "path_1") -> PathContract:
    contract = _contract_frame_and_verdict(path_id)
    contract["diff_history"].append(
        DiffRevision(
            rev=0,
            written_at=_ts(2),
            written_by="Wind",
            value={
                "accepted": [
                    {
                        "invariant": "halting",
                        "rationale": "the 3-attempt cap is correct and not negotiable",
                    }
                ],
                "disputed": [
                    {
                        "invariant": "single_wall_coherence",
                        "rationale": "legacy accounts can be migrated as a precondition rather than blocked",
                    }
                ],
                "reframed": [],
            },
        )
    )
    return contract


def _make_orchestrator(tmp_path: Path) -> DebateOrchestrator:
    tier_config = TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(),
    )
    return DebateOrchestrator(tier_config, tmp_path)


# ---------------------------------------------------------------------------
# Pure renderer tests (context_compiler.render_path_contracts_block)
# ---------------------------------------------------------------------------


class TestRenderPathContractsBlock:
    """Pure-function tests for the <PATH_CONTRACTS> sub-block renderer."""

    def test_empty_contracts_returns_empty_string(self) -> None:
        """Feature-off: an empty contracts list renders no <PATH_CONTRACTS> block.

        This guarantees byte-identity with the legacy envelope when path contracts
        are not yet plumbed by the orchestrator (e.g. before #197 persistence lands
        or when the feature flag is off in #201/#205).
        """
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        assert render_path_contracts_block([]) == ""

    def test_frame_only_emits_frame_and_revcount(self) -> None:
        """Single path with frame only (Wind initial) shows frame + rev count, no verdict/diff."""
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        block = render_path_contracts_block([_contract_frame_only("path_1")])

        assert "<PATH_CONTRACTS>" in block
        assert "</PATH_CONTRACTS>" in block
        assert "path_1" in block
        # Frame rendered
        assert "FRAME" in block
        assert "frame_rev_count::1" in block
        assert "assumed_problem" in block
        # Verdict and diff absent (no rev yet)
        assert "verdict_rev_count::0" in block
        assert "diff_rev_count::0" in block

    def test_frame_and_verdict_shows_both_no_diff(self) -> None:
        """Single path with frame + verdict (Wind→Wall done) shows both, no diff."""
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        block = render_path_contracts_block([_contract_frame_and_verdict("path_1")])

        assert "frame_rev_count::1" in block
        assert "verdict_rev_count::1" in block
        assert "diff_rev_count::0" in block
        assert "HARD_pass" in block
        assert "SOFT_disputed" in block

    def test_full_lifecycle_shows_all_three(self) -> None:
        """Single path with frame + verdict + diff shows all three (latest rev only)."""
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        block = render_path_contracts_block([_contract_full("path_1")])

        assert "frame_rev_count::1" in block
        assert "verdict_rev_count::1" in block
        assert "diff_rev_count::1" in block
        # Diff content rendered
        assert "accepted" in block
        assert "disputed" in block

    def test_latest_revision_only_full_history_not_rendered(self) -> None:
        """RFC §6 item 1: only the latest revision per field is rendered in-prompt.

        Earlier revisions stay in storage (I4 append-only) but must NOT appear in
        the prompt context.
        """
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        contract = _contract_full("path_1")
        # Append a second (latest) frame revision with a distinct marker
        contract["frame_history"].append(
            FrameRevision(
                rev=1,
                written_at=_ts(3),
                written_by="Wind",
                value={
                    "assumed_problem": "REVISED_PROBLEM_MARKER",
                    "success_criterion": "REVISED_SUCCESS",
                    "accepted_failure_mode": "REVISED_FAILURE",
                    "invariants_touched": ["halting"],
                },
            )
        )

        block = render_path_contracts_block([contract])

        # Latest is shown
        assert "REVISED_PROBLEM_MARKER" in block
        # Revision count reflects both revisions
        assert "frame_rev_count::2" in block
        # The earlier frame's distinctive substring MUST NOT appear
        assert "users cannot reset their password" not in block

    def test_token_budget_three_paths_under_3600(self) -> None:
        """RFC §8 Q3: worst-case ≤ ~3.6k tokens for 3 paths × 3 fields.

        Uses character-count / 4 as a portable token approximation (tiktoken-free).
        """
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        contracts = [_contract_full(f"path_{i}") for i in (1, 2, 3)]
        block = render_path_contracts_block(contracts)

        approx_tokens = len(block) // 4
        # Per RFC §8 Q3, the ceiling is ~3.6k tokens worst-case for 3 paths × 3 fields.
        # Real-world content is shorter than the simulation worst case; assert headroom.
        assert approx_tokens <= 3600, (
            f"PATH_CONTRACTS rendering exceeded RFC §8 Q3 ceiling: "
            f"{approx_tokens} tokens for 3 paths × 3 fields"
        )


# ---------------------------------------------------------------------------
# Orchestrator integration tests (_format_debate_state)
# ---------------------------------------------------------------------------


class TestOrchestratorEnvelopeIntegration:
    """End-to-end envelope assembly via DebateOrchestrator._format_debate_state."""

    def _base_state(self, **overrides: Any) -> dict[str, Any]:
        state: dict[str, Any] = {
            "thread_id": "2026-05-19-rfc0001-test",
            "topic": "Test topic",
            "status": "in_progress",
            "turn_count": 0,
            "transcript": [],
        }
        state.update(overrides)
        return state

    # ---- Finding F: SYNTHESIS_STATUS ----

    def test_synthesis_status_pending_initial_before_any_turns(self, tmp_path: Path) -> None:
        """No synthesis + zero turns ⇒ SYNTHESIS_STATUS::PENDING_INITIAL."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(self._base_state(turn_count=0))
        assert "SYNTHESIS_STATUS::PENDING_INITIAL" in block

    def test_synthesis_status_pending_initial_before_door_speaks(self, tmp_path: Path) -> None:
        """No synthesis + Wind/Wall spoken but no Door yet ⇒ still PENDING_INITIAL."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(self._base_state(turn_count=2))
        assert "SYNTHESIS_STATUS::PENDING_INITIAL" in block

    def test_synthesis_status_present_when_synthesis_set(self, tmp_path: Path) -> None:
        """Door has synthesised ⇒ SYNTHESIS_STATUS::PRESENT."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(turn_count=3, synthesis="Door's initial synthesis text")
        )
        assert "SYNTHESIS_STATUS::PRESENT" in block

    def test_synthesis_status_pending_refinement_after_door_but_no_synthesis_field(
        self, tmp_path: Path
    ) -> None:
        """Door's synthesis was rejected and cleared pending refinement ⇒ PENDING_REFINEMENT.

        The orchestrator clears ``synthesis`` while keeping turn_count ≥ 3 when a
        refinement loop is in flight; this distinguishes "never synthesised" from
        "synthesis withdrawn for refinement".
        """
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(self._base_state(turn_count=4, synthesis=None))
        assert "SYNTHESIS_STATUS::PENDING_REFINEMENT" in block

    # ---- PATH_CONTRACTS injection ----

    def test_no_path_contracts_no_block(self, tmp_path: Path) -> None:
        """When debate_state has no path_contracts key, no <PATH_CONTRACTS> block is emitted.

        Byte-identity guarantee for the feature-off path.
        """
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(self._base_state())
        assert "<PATH_CONTRACTS>" not in block
        assert "</PATH_CONTRACTS>" not in block

    def test_empty_path_contracts_list_no_block(self, tmp_path: Path) -> None:
        """Empty list also yields no <PATH_CONTRACTS> block."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(self._base_state(path_contracts=[]))
        assert "<PATH_CONTRACTS>" not in block

    def test_path_contracts_present_block_injected(self, tmp_path: Path) -> None:
        """Non-empty path_contracts ⇒ block injected inside <DEBATE_STATE>."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(path_contracts=[_contract_full("path_1")])
        )
        # Sub-block appears inside the envelope
        assert "<DEBATE_STATE>" in block
        assert "</DEBATE_STATE>" in block
        assert "<PATH_CONTRACTS>" in block
        assert "</PATH_CONTRACTS>" in block
        # Sub-block is BEFORE the envelope's closing tag
        assert block.index("<PATH_CONTRACTS>") < block.index("</DEBATE_STATE>")
        # Frame content appears
        assert "frame_rev_count::1" in block


# ---------------------------------------------------------------------------
# Finding I: Door prompt construction never touches the filesystem
# ---------------------------------------------------------------------------


class TestFindingIDoorPromptNoDiskRead:
    """Finding I (RFC-0001 §3.3) — Door must not look for a non-existent debate thread on disk.

    The simulation reported Door reading a thread file that doesn't exist. The fix is
    structural: the orchestrator provides everything Door needs through the in-memory
    DEBATE_STATE envelope. This test pins that invariant by patching ``Path.open`` /
    ``builtins.open`` while the Door consensus refinement prompt is constructed, and
    asserting they are never called for any debate-thread path.
    """

    @pytest.mark.asyncio
    async def test_door_consensus_refinement_constructs_prompt_without_disk_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Door's consensus-phase refinement prompt is assembled entirely in-memory.

        Patches ``builtins.open`` to raise on any call that mentions the thread id,
        proving the orchestrator never falls back to a filesystem read.
        """
        import builtins

        orch = _make_orchestrator(tmp_path)
        thread_id = "2026-05-19-finding-i-test"

        real_open = builtins.open
        offending_opens: list[str] = []

        def guarded_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                spath = str(path)
            except Exception:
                spath = ""
            if thread_id in spath:
                offending_opens.append(spath)
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", guarded_open)

        # Build a consensus refinement prompt for Door — this is the construction
        # site Finding I flagged. The orchestrator helper is pure string assembly.
        prompt = orch._create_refinement_prompt(
            topic="any topic",
            thread_id=thread_id,
            rejector="Wind",
            feedback="please reframe",
        )

        assert isinstance(prompt, str)
        assert thread_id in prompt
        assert (
            offending_opens == []
        ), f"Door prompt construction performed disk reads for thread paths: {offending_opens}"


# ---------------------------------------------------------------------------
# Smoke: provider call does not break with path_contracts in state
# ---------------------------------------------------------------------------


class TestEnvelopeBackwardsCompat:
    """The added envelope changes must not regress existing VTP prompt assembly."""

    def test_state_without_path_contracts_still_renders(self, tmp_path: Path) -> None:
        """Pre-#199 callers that pass no path_contracts key still get a valid envelope."""
        orch = _make_orchestrator(tmp_path)
        state: dict[str, Any] = {
            "thread_id": "tid",
            "topic": "t",
            "status": "in_progress",
            "turn_count": 0,
            "transcript": [],
        }
        block = orch._format_debate_state(state)
        assert block.startswith("<DEBATE_STATE>")
        assert block.endswith("</DEBATE_STATE>")
