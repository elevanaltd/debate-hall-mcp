"""RED-stage unit tests for ``debate_hall_mcp.path_contract_validator`` (RFC-0001 #200).

Acceptance bound to the AMENDED RFC at
``docs/rfc-0001-path-contract-wind-learning-loop.md``:

* §3.1 — Ownership rule (Wind→frame/diff, Wall→verdict, Door read-only).
* §3.2 — REQUIRED CONTENT RULE for ``diff`` revisions, **per HARD_fail invariant**
  (each HARD_fail needs its own qualifying ``accepted``-with-``terminal_rationale``
  OR ``reframed``-with-``new_possibility`` entry); ``NO_NEW_DIVERGENCE`` legal only
  when zero HARD_fail verdicts; sentinel MAY coexist with a non-empty ``disputed``
  list (Finding D).
* §3.3 — Findings C (per-invariant tightening), D (sentinel+disputed coexistence),
  E (``synthesis_guidance`` slot — Door-citation enforcement is the validator's
  ``validate_door_citations`` responsibility for *existence* of cited invariants;
  the *requirement* to cite ``synthesis_guidance`` when present is downstream
  prompt-level (#198) and Door-side context (#199), out of scope here).
* §6 item 2 — citation existence check for Door.
* §6 item 3 — ``VALIDATOR_FAILURE`` events with failure-type metadata.

Out of scope here (downstream issues): orchestrator call-site wiring (depends on
#197/#198 to thread ``PathContract`` objects through ``_execute_consensus_loop``);
prompt edits (#198); state serialization (#197); feature flag wiring (#201/#205).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.path_contract import (
    DiffRevision,
    FrameRevision,
    InvariantEntry,
    InvariantVerdict,
    PathContract,
    PathDiff,
    PathFrame,
    VerdictRevision,
    new_path_contract,
)


# ---------------------------------------------------------------------------
# Fixture helpers — minimal contract builders used across the RED matrix.
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _frame_rev(rev: int = 0, invariants: list[str] | None = None) -> FrameRevision:
    return FrameRevision(
        rev=rev,
        written_at=_now(),
        written_by="Wind",
        value=PathFrame(
            assumed_problem="x",
            success_criterion="y",
            accepted_failure_mode="z",
            invariants_touched=invariants or ["inv_a"],
        ),
    )


def _verdict_rev(
    rev: int,
    verdicts: dict[str, tuple[str, str]],
) -> VerdictRevision:
    return VerdictRevision(
        rev=rev,
        written_at=_now(),
        written_by="Wall",
        value={
            name: InvariantVerdict(status=status, rationale=rationale)  # type: ignore[typeddict-item]
            for name, (status, rationale) in verdicts.items()
        },
    )


def _entry(invariant: str, **extra: str) -> InvariantEntry:
    base: InvariantEntry = InvariantEntry(invariant=invariant, rationale="r")
    for k, v in extra.items():
        base[k] = v  # type: ignore[literal-required]
    return base


def _diff_rev(
    rev: int,
    *,
    accepted: list[InvariantEntry] | None = None,
    disputed: list[InvariantEntry] | None = None,
    reframed: list[InvariantEntry] | None = None,
    divergence_marker: str | None = None,
    synthesis_guidance: str | None = None,
    written_by: str = "Wind",
) -> DiffRevision:
    diff: DiffRevision = DiffRevision(
        rev=rev,
        written_at=_now(),
        written_by=written_by,  # type: ignore[typeddict-item]
        value=PathDiff(
            accepted=accepted or [],
            disputed=disputed or [],
            reframed=reframed or [],
        ),
    )
    if divergence_marker is not None:
        diff["divergence_marker"] = divergence_marker  # type: ignore[typeddict-item]
    if synthesis_guidance is not None:
        diff["synthesis_guidance"] = synthesis_guidance
    return diff


def _contract_with_verdicts(
    verdicts: dict[str, tuple[str, str]],
    *,
    path_id: str = "path_1",
) -> PathContract:
    contract = new_path_contract(path_id)
    contract["frame_history"].append(
        _frame_rev(invariants=list(verdicts.keys()))
    )
    contract["verdict_history"].append(_verdict_rev(0, verdicts))
    return contract


# ---------------------------------------------------------------------------
# Module importability.
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """The validator module must be importable from the package root."""
    import debate_hall_mcp.path_contract_validator  # noqa: F401


def test_validator_failure_dataclass_shape() -> None:
    """``ValidatorFailure`` exposes failure_type, path_id, invariant, role, details."""
    from debate_hall_mcp.path_contract_validator import ValidatorFailure

    failure = ValidatorFailure(
        failure_type="missing_required_entry",
        path_id="path_1",
        invariant="inv_a",
        role="Wind",
        details="explanation",
    )
    assert failure.failure_type == "missing_required_entry"
    assert failure.path_id == "path_1"
    assert failure.invariant == "inv_a"
    assert failure.role == "Wind"
    assert failure.details == "explanation"


def test_failure_type_constants_present() -> None:
    """Failure-type discriminators are exposed as module constants for #203 A/B grouping."""
    from debate_hall_mcp.path_contract_validator import (
        DOOR_CITATION_NOT_FOUND,
        EMPTY_NEW_POSSIBILITY,
        EMPTY_TERMINAL_RATIONALE,
        ILLEGAL_NO_NEW_DIVERGENCE,
        MISSING_REQUIRED_ENTRY,
        OWNERSHIP_VIOLATION,
    )

    # All constants are non-empty strings; values are stable identifiers.
    for c in (
        MISSING_REQUIRED_ENTRY,
        EMPTY_TERMINAL_RATIONALE,
        EMPTY_NEW_POSSIBILITY,
        ILLEGAL_NO_NEW_DIVERGENCE,
        OWNERSHIP_VIOLATION,
        DOOR_CITATION_NOT_FOUND,
    ):
        assert isinstance(c, str) and c


# ---------------------------------------------------------------------------
# REQUIRED CONTENT RULE — per-invariant (RFC §3.2 / §3.3 Finding C).
# ---------------------------------------------------------------------------


def test_diff_satisfies_when_accepted_has_terminal_rationale() -> None:
    """HARD_fail invariant with matching ``accepted`` + non-empty ``terminal_rationale`` PASSES."""
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(
        0,
        accepted=[_entry("inv_a", terminal_rationale="no creative reframe exists")],
    )
    failures = validate_diff_revision(contract, diff)
    assert failures == []


def test_diff_satisfies_when_reframed_has_new_possibility() -> None:
    """HARD_fail invariant with matching ``reframed`` + non-empty ``new_possibility`` PASSES."""
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(
        0,
        reframed=[_entry("inv_a", new_possibility="catalyst-opened path b")],
    )
    failures = validate_diff_revision(contract, diff)
    assert failures == []


def test_diff_fails_when_hard_fail_invariant_silently_omitted() -> None:
    """HARD_fail with NO matching entry anywhere → MISSING_REQUIRED_ENTRY."""
    from debate_hall_mcp.path_contract_validator import (
        MISSING_REQUIRED_ENTRY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0)  # all buckets empty
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a"
        for f in failures
    )


def test_diff_fails_when_accepted_entry_has_empty_terminal_rationale() -> None:
    """``accepted`` on HARD_fail with empty ``terminal_rationale`` → EMPTY_TERMINAL_RATIONALE."""
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_TERMINAL_RATIONALE,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0, accepted=[_entry("inv_a", terminal_rationale="")])
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == EMPTY_TERMINAL_RATIONALE and f.invariant == "inv_a"
        for f in failures
    )


def test_diff_fails_when_accepted_entry_missing_terminal_rationale() -> None:
    """``accepted`` on HARD_fail with NO ``terminal_rationale`` key → EMPTY_TERMINAL_RATIONALE."""
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_TERMINAL_RATIONALE,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0, accepted=[_entry("inv_a")])  # no terminal_rationale at all
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == EMPTY_TERMINAL_RATIONALE and f.invariant == "inv_a"
        for f in failures
    )


def test_diff_fails_when_reframed_entry_has_empty_new_possibility() -> None:
    """``reframed`` on HARD_fail with empty ``new_possibility`` → EMPTY_NEW_POSSIBILITY."""
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_NEW_POSSIBILITY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0, reframed=[_entry("inv_a", new_possibility="")])
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == EMPTY_NEW_POSSIBILITY and f.invariant == "inv_a"
        for f in failures
    )


def test_diff_fails_when_reframed_entry_missing_new_possibility() -> None:
    """``reframed`` on HARD_fail with NO ``new_possibility`` key → EMPTY_NEW_POSSIBILITY."""
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_NEW_POSSIBILITY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0, reframed=[_entry("inv_a")])  # no new_possibility at all
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == EMPTY_NEW_POSSIBILITY and f.invariant == "inv_a"
        for f in failures
    )


def test_diff_fails_per_invariant_not_per_path_finding_c() -> None:
    """RFC §3.3 Finding C: sibling entry on different invariant does NOT satisfy.

    Two HARD_fail invariants (inv_a, inv_b); a reframed entry on inv_b does NOT
    cover the requirement on inv_a. Validator must emit MISSING_REQUIRED_ENTRY
    for inv_a specifically.
    """
    from debate_hall_mcp.path_contract_validator import (
        MISSING_REQUIRED_ENTRY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts(
        {"inv_a": ("HARD_fail", "blocked"), "inv_b": ("HARD_fail", "blocked")}
    )
    diff = _diff_rev(
        0, reframed=[_entry("inv_b", new_possibility="covers inv_b only")]
    )
    failures = validate_diff_revision(contract, diff)
    inv_a_misses = [
        f for f in failures
        if f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a"
    ]
    inv_b_misses = [
        f for f in failures
        if f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_b"
    ]
    assert inv_a_misses, "inv_a HARD_fail must be flagged as missing"
    assert not inv_b_misses, "inv_b is satisfied by reframed entry"


def test_diff_clean_when_no_hard_fail_verdicts() -> None:
    """All-pass-or-disputed verdicts impose no REQUIRED CONTENT requirement."""
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts(
        {"inv_a": ("HARD_pass", "ok"), "inv_b": ("SOFT_disputed", "discuss")}
    )
    diff = _diff_rev(0)  # empty buckets allowed
    failures = validate_diff_revision(contract, diff)
    assert failures == []


# ---------------------------------------------------------------------------
# NO_NEW_DIVERGENCE sentinel rules (RFC §3.2 / §3.3 Finding D).
# ---------------------------------------------------------------------------


def test_no_new_divergence_legal_when_zero_hard_fail() -> None:
    """Sentinel legal when every verdict is HARD_pass or SOFT_disputed."""
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts(
        {"inv_a": ("HARD_pass", "ok"), "inv_b": ("SOFT_disputed", "discuss")}
    )
    diff = _diff_rev(0, divergence_marker="NO_NEW_DIVERGENCE")
    failures = validate_diff_revision(contract, diff)
    assert failures == []


def test_no_new_divergence_finding_d_may_coexist_with_disputed() -> None:
    """Finding D: sentinel + non-empty ``disputed`` list is LEGAL."""
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts(
        {"inv_soft": ("SOFT_disputed", "discuss")}
    )
    diff = _diff_rev(
        0,
        divergence_marker="NO_NEW_DIVERGENCE",
        disputed=[_entry("inv_soft")],
    )
    failures = validate_diff_revision(contract, diff)
    assert failures == [], (
        "RFC §3.3 Finding D: sentinel may coexist with non-empty disputed"
    )


def test_no_new_divergence_fails_on_any_hard_fail_verdict() -> None:
    """Sentinel on a path whose verdict contains any HARD_fail → ILLEGAL_NO_NEW_DIVERGENCE."""
    from debate_hall_mcp.path_contract_validator import (
        ILLEGAL_NO_NEW_DIVERGENCE,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts(
        {"inv_a": ("HARD_pass", "ok"), "inv_b": ("HARD_fail", "blocked")}
    )
    diff = _diff_rev(0, divergence_marker="NO_NEW_DIVERGENCE")
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == ILLEGAL_NO_NEW_DIVERGENCE for f in failures
    )


# ---------------------------------------------------------------------------
# Ownership rule (RFC §3.1).
# ---------------------------------------------------------------------------


def test_ownership_wind_writing_verdict_fails() -> None:
    """Wind writing a VerdictRevision → OWNERSHIP_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        OWNERSHIP_VIOLATION,
        validate_revision_ownership,
    )

    bad: VerdictRevision = VerdictRevision(
        rev=0,
        written_at=_now(),
        written_by="Wind",  # type: ignore[typeddict-item]
        value={},
    )
    failures = validate_revision_ownership(bad, kind="verdict", path_id="path_1")
    assert any(f.failure_type == OWNERSHIP_VIOLATION and f.role == "Wind" for f in failures)


def test_ownership_wall_writing_frame_fails() -> None:
    """Wall writing a FrameRevision → OWNERSHIP_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        OWNERSHIP_VIOLATION,
        validate_revision_ownership,
    )

    bad: FrameRevision = FrameRevision(
        rev=0,
        written_at=_now(),
        written_by="Wall",  # type: ignore[typeddict-item]
        value=PathFrame(
            assumed_problem="x",
            success_criterion="y",
            accepted_failure_mode="z",
            invariants_touched=[],
        ),
    )
    failures = validate_revision_ownership(bad, kind="frame", path_id="path_1")
    assert any(f.failure_type == OWNERSHIP_VIOLATION and f.role == "Wall" for f in failures)


def test_ownership_door_writing_diff_fails() -> None:
    """Door writing a DiffRevision → OWNERSHIP_VIOLATION (Door is read-only)."""
    from debate_hall_mcp.path_contract_validator import (
        OWNERSHIP_VIOLATION,
        validate_revision_ownership,
    )

    bad = _diff_rev(0, written_by="Door")
    failures = validate_revision_ownership(bad, kind="diff", path_id="path_1")
    assert any(f.failure_type == OWNERSHIP_VIOLATION and f.role == "Door" for f in failures)


def test_ownership_correct_owners_pass() -> None:
    """Correct owners (Wind→frame/diff, Wall→verdict) produce no failures."""
    from debate_hall_mcp.path_contract_validator import validate_revision_ownership

    assert validate_revision_ownership(_frame_rev(), kind="frame", path_id="p") == []
    assert (
        validate_revision_ownership(
            _verdict_rev(0, {"x": ("HARD_pass", "ok")}), kind="verdict", path_id="p"
        )
        == []
    )
    assert validate_revision_ownership(_diff_rev(0), kind="diff", path_id="p") == []


# ---------------------------------------------------------------------------
# Door citation existence (RFC §6 item 2).
# ---------------------------------------------------------------------------


def test_door_citation_of_existing_invariant_passes() -> None:
    """Door citing an invariant present in latest verdict → no failure."""
    from debate_hall_mcp.path_contract_validator import validate_door_citations

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    failures = validate_door_citations(contract, cited_invariants=["inv_a"])
    assert failures == []


def test_door_citation_of_nonexistent_invariant_fails() -> None:
    """Door citing an invariant NOT in latest verdict → DOOR_CITATION_NOT_FOUND."""
    from debate_hall_mcp.path_contract_validator import (
        DOOR_CITATION_NOT_FOUND,
        validate_door_citations,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    failures = validate_door_citations(contract, cited_invariants=["ghost_invariant"])
    assert any(
        f.failure_type == DOOR_CITATION_NOT_FOUND and f.invariant == "ghost_invariant"
        for f in failures
    )


def test_door_citation_with_no_verdict_history_fails_all_citations() -> None:
    """If no verdict revision exists, every cited invariant is a not-found failure."""
    from debate_hall_mcp.path_contract_validator import (
        DOOR_CITATION_NOT_FOUND,
        validate_door_citations,
    )

    contract = new_path_contract("path_1")  # no verdict history
    failures = validate_door_citations(contract, cited_invariants=["any_inv"])
    assert any(f.failure_type == DOOR_CITATION_NOT_FOUND for f in failures)


# ---------------------------------------------------------------------------
# VALIDATOR_FAILURE event emission (RFC §6 item 3).
# ---------------------------------------------------------------------------


def test_event_type_validator_failure_exists() -> None:
    """``EventType.VALIDATOR_FAILURE`` must exist with the exact RFC-§6 string."""
    from debate_hall_mcp.events import EventType

    assert EventType.VALIDATOR_FAILURE.value == "validator_failure"


def test_emit_validator_failures_writes_one_event_per_failure(tmp_path: Path) -> None:
    """``emit_validator_failures`` appends one VALIDATOR_FAILURE event per failure."""
    from debate_hall_mcp.events import EventType, load_events
    from debate_hall_mcp.path_contract_validator import (
        ValidatorFailure,
        emit_validator_failures,
    )

    failures = [
        ValidatorFailure(
            failure_type="missing_required_entry",
            path_id="path_1",
            invariant="inv_a",
            role=None,
            details="HARD_fail on inv_a has no qualifying diff entry",
        ),
        ValidatorFailure(
            failure_type="ownership_violation",
            path_id="path_1",
            invariant=None,
            role="Wind",
            details="Wind attempted verdict write",
        ),
    ]

    events = emit_validator_failures(
        thread_id="t-1", failures=failures, state_dir=tmp_path
    )
    assert len(events) == 2
    assert all(e.event_type == EventType.VALIDATOR_FAILURE for e in events)

    loaded = load_events(thread_id="t-1", state_dir=tmp_path)
    assert len(loaded) == 2

    # Discrimination metadata is in the payload, not the event_type, so #203 can group.
    payloads = [e.payload for e in loaded]
    assert {p["failure_type"] for p in payloads} == {
        "missing_required_entry",
        "ownership_violation",
    }
    # Per-failure correlatable fields preserved.
    missing = next(p for p in payloads if p["failure_type"] == "missing_required_entry")
    assert missing["path_id"] == "path_1"
    assert missing["invariant"] == "inv_a"
    assert missing["details"].startswith("HARD_fail")
    ownership = next(p for p in payloads if p["failure_type"] == "ownership_violation")
    assert ownership["role"] == "Wind"


def test_emit_validator_failures_empty_list_is_noop(tmp_path: Path) -> None:
    """No failures → no events written, no exceptions."""
    from debate_hall_mcp.path_contract_validator import emit_validator_failures

    events = emit_validator_failures(
        thread_id="t-empty", failures=[], state_dir=tmp_path
    )
    assert events == []
    # No events file written for an empty failure list.
    events_file = tmp_path / "t-empty.events.jsonl"
    assert not events_file.exists()
