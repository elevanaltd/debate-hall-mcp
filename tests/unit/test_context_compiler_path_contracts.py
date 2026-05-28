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
    # #201: orchestrator <PATH_CONTRACTS>/SYNTHESIS_STATUS emission is gated
    # on features.is_enabled("path_contract", ctx). Tests in this module
    # exercise the on-mode rendering / joint-emission contract, so flip the
    # TierSettings flag ON. Off-mode byte-identity is verified in
    # tests/unit/test_path_contract_flag_wiring.py.
    tier_config = TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(path_contract_enabled=True),
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
        """RFC §8 Q3 (happy-path): ≤ ~3.6k tokens for 3 paths × 3 fields.

        Assumes reasonably-short agent outputs typical of debate transcripts
        (single-sentence rationales, succinct synthesis_guidance). The
        worst-case upper bound under long-form prose is bounded separately
        by :meth:`test_token_budget_three_paths_with_long_content`.

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

    def test_token_budget_three_paths_with_long_content(self) -> None:
        """Stress-test worst-case: long-form prose in every text field (RFC §8 Q3 envelope).

        Schema text fields (assumed_problem, success_criterion, accepted_failure_mode,
        rationale × N, synthesis_guidance, divergence_marker, new_possibility) are
        unbounded in the schema; this test pushes ~200-token prose into each free-text
        field across 3 paths × 3 revision categories (frame/verdict/diff) and asserts
        the rendered block stays under a documented ceiling.

        This bounds the realistic worst-case empirically. If the measured value
        approaches the assertion ceiling, escalate to #196 (schema input-bounding).
        """
        from debate_hall_mcp.context_compiler import render_path_contracts_block

        # ~200-token prose blob (~800 chars). Multi-sentence to match real worst case.
        long_text = (
            "This rationale captures the full structural argument with caveats, "
            "edge cases, and operational considerations that emerged during the "
            "deliberation. The agent enumerates failure modes, recovery paths, "
            "and the cost of deferred remediation. It cross-references prior "
            "synthesis attempts, notes which invariants are load-bearing, and "
            "explains why the chosen reframing is preferred over the alternatives "
            "considered. Includes references to relevant ADRs and prior debates "
            "so downstream readers can reconstruct provenance without leaving "
            "the prompt. "
        ) * 2  # ~1600 chars, ~400 token-equivalent budget per field — intentionally over

        def _stress_contract(path_id: str) -> PathContract:
            contract = new_path_contract(path_id)
            contract["frame_history"].append(
                FrameRevision(
                    rev=0,
                    written_at=_ts(),
                    written_by="Wind",
                    value={
                        "assumed_problem": long_text,
                        "success_criterion": long_text,
                        "accepted_failure_mode": long_text,
                        "invariants_touched": ["halting", "single_wall_coherence"],
                    },
                )
            )
            contract["verdict_history"].append(
                VerdictRevision(
                    rev=0,
                    written_at=_ts(1),
                    written_by="Wall",
                    value={
                        "halting": {"status": "HARD_pass", "rationale": long_text},
                        "single_wall_coherence": {
                            "status": "SOFT_disputed",
                            "rationale": long_text,
                        },
                    },
                )
            )
            contract["diff_history"].append(
                DiffRevision(
                    rev=0,
                    written_at=_ts(2),
                    written_by="Wind",
                    value={
                        "accepted": [
                            {"invariant": "halting", "rationale": long_text},
                        ],
                        "disputed": [
                            {"invariant": "single_wall_coherence", "rationale": long_text},
                        ],
                        "reframed": [],
                    },
                    divergence_marker=long_text,
                    synthesis_guidance=long_text,
                )
            )
            return contract

        contracts = [_stress_contract(f"path_{i}") for i in (1, 2, 3)]
        block = render_path_contracts_block(contracts)

        approx_tokens = len(block) // 4
        # Documented stress-test ceiling. If this is breached, the renderer is
        # not at fault — long-form rationales must be bounded upstream (#196).
        # Empirical measurement at the time of authoring informs this ceiling.
        WORST_CASE_TOKEN_CEILING = 9000
        assert approx_tokens <= WORST_CASE_TOKEN_CEILING, (
            f"PATH_CONTRACTS long-form stress test exceeded documented ceiling: "
            f"{approx_tokens} tokens (ceiling {WORST_CASE_TOKEN_CEILING}). "
            f"Escalate to #196 for schema input-bounding rather than renderer fix."
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
    #
    # PR #218 rework: SYNTHESIS_STATUS is emitted IFF <PATH_CONTRACTS> is
    # emitted (joint emission contract — see CE finding 1). All Finding F
    # status-derivation tests therefore feed a non-empty ``path_contracts``
    # list so the gated branch is exercised. The Finding F semantics
    # (PRESENT / PENDING_INITIAL / PENDING_REFINEMENT derivation) are
    # unchanged; only the emission gate has been tightened.

    def test_synthesis_status_pending_initial_before_any_turns(self, tmp_path: Path) -> None:
        """No synthesis + zero turns ⇒ SYNTHESIS_STATUS::PENDING_INITIAL (with contracts)."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(turn_count=0, path_contracts=[_contract_frame_only()])
        )
        assert "SYNTHESIS_STATUS::PENDING_INITIAL" in block

    def test_synthesis_status_pending_initial_before_door_speaks(self, tmp_path: Path) -> None:
        """No synthesis + Wind/Wall spoken but no Door yet ⇒ still PENDING_INITIAL."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(turn_count=2, path_contracts=[_contract_frame_only()])
        )
        assert "SYNTHESIS_STATUS::PENDING_INITIAL" in block

    def test_synthesis_status_present_when_synthesis_set(self, tmp_path: Path) -> None:
        """Door has synthesised ⇒ SYNTHESIS_STATUS::PRESENT."""
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(
                turn_count=3,
                synthesis="Door's initial synthesis text",
                path_contracts=[_contract_full()],
            )
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
        block = orch._format_debate_state(
            self._base_state(turn_count=4, synthesis=None, path_contracts=[_contract_full()])
        )
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

    # ---- Byte-identity snapshot (PR #218 rework: CE finding 1) ----

    def _pre_pr_reference_envelope(
        self, debate_state: dict[str, Any], *, show_token_counts: bool = False
    ) -> str:
        """Reproduce the pre-#199 _format_debate_state output verbatim.

        This is the canonical reference for the "feature-off byte-identity"
        guarantee. Any line emitted by the current renderer that does NOT also
        appear here when ``path_contracts`` is absent/empty constitutes envelope
        drift and must be gated on the feature being active.

        Source: orchestrator.py @ commit 354cb9e (immediate parent of #199 merge).
        """
        lines = ["<DEBATE_STATE>"]
        lines.append(f"THREAD_ID::{debate_state['thread_id']}")
        lines.append(f"TOPIC::{debate_state['topic']}")
        lines.append(f"STATUS::{debate_state['status']}")
        lines.append(f"TURN_COUNT::{debate_state['turn_count']}")
        if debate_state.get("synthesis"):
            lines.append(f"SYNTHESIS::{debate_state['synthesis']}")
        if debate_state.get("transcript"):
            lines.append("\nTRANSCRIPT::")
            for turn in debate_state["transcript"]:
                role = turn.get("role", "Unknown")
                cognition = turn.get("cognition")
                content = turn.get("content", "")
                token_output = turn.get("token_output")
                role_label = f"[{role}/{cognition}]" if cognition else f"[{role}]"
                if show_token_counts and token_output:
                    lines.append(f"  {role_label} ({token_output} tokens):: {content}")
                else:
                    lines.append(f"  {role_label}:: {content}")
        lines.append("</DEBATE_STATE>")
        return "\n".join(lines)

    def test_feature_off_envelope_is_byte_identical_to_pre_pr(self, tmp_path: Path) -> None:
        """Feature-off (no path_contracts) ⇒ envelope is byte-identical to pre-#199 output.

        Catches any future unconditional addition to ``_format_debate_state``
        (the original PR #218 CE finding 1 symptom was an unconditional
        ``SYNTHESIS_STATUS::<value>`` line). The contract: any new envelope
        line MUST be gated on ``path_contracts`` being non-empty so the
        legacy callers continue to see exactly the pre-#199 shape.

        Joint emission contract (documented in PR #218 for #198 prompt PR):
        ``SYNTHESIS_STATUS`` is emitted IFF ``<PATH_CONTRACTS>`` is emitted.
        """
        orch = _make_orchestrator(tmp_path)
        state = self._base_state(
            turn_count=2,
            transcript=[
                {"role": "Wind", "cognition": "PATHOS", "content": "hello"},
                {"role": "Wall", "cognition": "ETHOS", "content": "constraint"},
            ],
        )
        actual = orch._format_debate_state(state)
        expected = self._pre_pr_reference_envelope(state)
        assert actual == expected, (
            "Feature-off envelope drifted from pre-#199 byte-identical reference.\n"
            f"--- expected (pre-PR) ---\n{expected}\n"
            f"--- actual (current)   ---\n{actual}"
        )

    def test_feature_off_envelope_byte_identical_minimal_state(self, tmp_path: Path) -> None:
        """Minimal state (no transcript, no synthesis) also byte-identical."""
        orch = _make_orchestrator(tmp_path)
        state = self._base_state()
        actual = orch._format_debate_state(state)
        expected = self._pre_pr_reference_envelope(state)
        assert actual == expected

    def test_feature_on_envelope_emits_synthesis_status_jointly(self, tmp_path: Path) -> None:
        """Joint emission contract: SYNTHESIS_STATUS is emitted IFF <PATH_CONTRACTS> is.

        When ``path_contracts`` is non-empty, both ``SYNTHESIS_STATUS::<value>``
        and the ``<PATH_CONTRACTS>`` sub-block must appear. This is the
        downstream contract #198's Wind prompt branches depend on.
        """
        orch = _make_orchestrator(tmp_path)
        block = orch._format_debate_state(
            self._base_state(path_contracts=[_contract_full("path_1")])
        )
        assert "SYNTHESIS_STATUS::" in block
        assert "<PATH_CONTRACTS>" in block

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

        Patches every reasonable disk-read entry point to record any call that
        mentions the thread id, proving the orchestrator never falls back to a
        filesystem read via ANY of these paths.

        Guard surface (PR #218 CE + TMG concur — Finding I widening):

        * ``builtins.open`` (original guard)
        * ``pathlib.Path.open``
        * ``pathlib.Path.read_text``
        * ``pathlib.Path.read_bytes`` (symmetry)
        * ``io.open``

        Note: ``aiofiles`` is NOT in this project's dependency tree (verified
        against ``pyproject.toml`` at the time of PR #218 rework). If it is
        ever added, extend this guard with an ``aiofiles.open`` patch.
        """
        import builtins
        import contextlib
        import io
        import pathlib

        orch = _make_orchestrator(tmp_path)
        thread_id = "2026-05-19-finding-i-test"

        offending_opens: list[str] = []

        def _record(spath: str) -> None:
            if thread_id in spath:
                offending_opens.append(spath)

        real_builtin_open = builtins.open
        real_io_open = io.open
        real_path_open = pathlib.Path.open
        real_path_read_text = pathlib.Path.read_text
        real_path_read_bytes = pathlib.Path.read_bytes

        def guarded_builtin_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            with contextlib.suppress(Exception):
                _record(str(path))
            return real_builtin_open(path, *args, **kwargs)

        def guarded_io_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            with contextlib.suppress(Exception):
                _record(str(path))
            return real_io_open(path, *args, **kwargs)

        def guarded_path_open(self: pathlib.Path, *args: Any, **kwargs: Any) -> Any:
            with contextlib.suppress(Exception):
                _record(str(self))
            return real_path_open(self, *args, **kwargs)

        def guarded_path_read_text(self: pathlib.Path, *args: Any, **kwargs: Any) -> str:
            with contextlib.suppress(Exception):
                _record(str(self))
            return real_path_read_text(self, *args, **kwargs)

        def guarded_path_read_bytes(self: pathlib.Path) -> bytes:
            with contextlib.suppress(Exception):
                _record(str(self))
            return real_path_read_bytes(self)

        monkeypatch.setattr(builtins, "open", guarded_builtin_open)
        monkeypatch.setattr(io, "open", guarded_io_open)
        monkeypatch.setattr(pathlib.Path, "open", guarded_path_open)
        monkeypatch.setattr(pathlib.Path, "read_text", guarded_path_read_text)
        monkeypatch.setattr(pathlib.Path, "read_bytes", guarded_path_read_bytes)

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
        assert offending_opens == [], (
            "Door prompt construction performed disk reads for thread paths via one "
            f"of builtins.open / io.open / pathlib.Path.{{open,read_text,read_bytes}}: "
            f"{offending_opens}"
        )


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
