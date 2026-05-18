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
    contract["frame_history"].append(_frame_rev(invariants=list(verdicts.keys())))
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
        f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a" for f in failures
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
        f.failure_type == EMPTY_TERMINAL_RATIONALE and f.invariant == "inv_a" for f in failures
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
        f.failure_type == EMPTY_TERMINAL_RATIONALE and f.invariant == "inv_a" for f in failures
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
    assert any(f.failure_type == EMPTY_NEW_POSSIBILITY and f.invariant == "inv_a" for f in failures)


def test_diff_fails_when_reframed_entry_missing_new_possibility() -> None:
    """``reframed`` on HARD_fail with NO ``new_possibility`` key → EMPTY_NEW_POSSIBILITY."""
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_NEW_POSSIBILITY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(0, reframed=[_entry("inv_a")])  # no new_possibility at all
    failures = validate_diff_revision(contract, diff)
    assert any(f.failure_type == EMPTY_NEW_POSSIBILITY and f.invariant == "inv_a" for f in failures)


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
    diff = _diff_rev(0, reframed=[_entry("inv_b", new_possibility="covers inv_b only")])
    failures = validate_diff_revision(contract, diff)
    inv_a_misses = [
        f for f in failures if f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a"
    ]
    inv_b_misses = [
        f for f in failures if f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_b"
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

    contract = _contract_with_verdicts({"inv_soft": ("SOFT_disputed", "discuss")})
    diff = _diff_rev(
        0,
        divergence_marker="NO_NEW_DIVERGENCE",
        disputed=[_entry("inv_soft")],
    )
    failures = validate_diff_revision(contract, diff)
    assert failures == [], "RFC §3.3 Finding D: sentinel may coexist with non-empty disputed"


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
    assert any(f.failure_type == ILLEGAL_NO_NEW_DIVERGENCE for f in failures)


# ---------------------------------------------------------------------------
# Per-entry rationale checks — Cubic bot-resolution P1 (RFC §3.2 per-entry rule).
# ---------------------------------------------------------------------------


def test_diff_fails_per_entry_when_sibling_accepted_entry_empty_terminal_rationale() -> None:
    """RFC §3.2 per-entry rule: even when ONE ``accepted`` entry on a HARD_fail invariant
    has a valid ``terminal_rationale``, a SIBLING ``accepted`` entry on the SAME invariant
    with an empty/missing ``terminal_rationale`` MUST emit EMPTY_TERMINAL_RATIONALE.

    The per-invariant existence check is satisfied by the valid entry (no
    MISSING_REQUIRED_ENTRY), but the malformed sibling is still a per-entry
    violation and must surface to the A/B harness.
    """
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_TERMINAL_RATIONALE,
        MISSING_REQUIRED_ENTRY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(
        0,
        accepted=[
            _entry("inv_a", terminal_rationale="valid reason — no creative reframe"),
            _entry("inv_a", terminal_rationale=""),  # malformed sibling
        ],
    )
    failures = validate_diff_revision(contract, diff)
    # The valid entry satisfies the per-invariant existence check.
    assert not any(
        f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a" for f in failures
    )
    # But the malformed sibling must still emit a per-entry failure.
    empty_tr = [
        f for f in failures if f.failure_type == EMPTY_TERMINAL_RATIONALE and f.invariant == "inv_a"
    ]
    assert len(empty_tr) == 1, (
        "RFC §3.2 per-entry: each malformed accepted entry must emit its own "
        "EMPTY_TERMINAL_RATIONALE; the per-invariant existence check does not absorb it."
    )


def test_diff_fails_per_entry_when_sibling_reframed_entry_empty_new_possibility() -> None:
    """RFC §3.2 per-entry rule: even when ONE ``reframed`` entry on a HARD_fail invariant
    has a valid ``new_possibility``, a SIBLING ``reframed`` entry on the SAME invariant
    with an empty/missing ``new_possibility`` MUST emit EMPTY_NEW_POSSIBILITY.
    """
    from debate_hall_mcp.path_contract_validator import (
        EMPTY_NEW_POSSIBILITY,
        MISSING_REQUIRED_ENTRY,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(
        0,
        reframed=[
            _entry("inv_a", new_possibility="catalyst-opened path b"),
            _entry("inv_a", new_possibility=""),  # malformed sibling
        ],
    )
    failures = validate_diff_revision(contract, diff)
    assert not any(
        f.failure_type == MISSING_REQUIRED_ENTRY and f.invariant == "inv_a" for f in failures
    )
    empty_np = [
        f for f in failures if f.failure_type == EMPTY_NEW_POSSIBILITY and f.invariant == "inv_a"
    ]
    assert len(empty_np) == 1, (
        "RFC §3.2 per-entry: each malformed reframed entry must emit its own "
        "EMPTY_NEW_POSSIBILITY; the per-invariant existence check does not absorb it."
    )


# ---------------------------------------------------------------------------
# Sentinel-with-accepted/reframed rejection — Cubic bot-resolution P2 (§3.1 docstring).
# ---------------------------------------------------------------------------


def test_no_new_divergence_with_non_empty_accepted_is_illegal() -> None:
    """RFC §3.1 ``divergence_marker`` docstring: when sentinel is set, ``accepted`` MUST be
    empty. Sentinel + non-empty ``accepted`` → ILLEGAL_SENTINEL_WITH_ACCEPTED.
    """
    from debate_hall_mcp.path_contract_validator import (
        ILLEGAL_SENTINEL_WITH_ACCEPTED,
        validate_diff_revision,
    )

    # No HARD_fail verdicts so the existing sentinel-vs-HARD_fail check does NOT
    # fire — we are isolating the new sentinel-vs-accepted rule.
    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    diff = _diff_rev(
        0,
        divergence_marker="NO_NEW_DIVERGENCE",
        accepted=[_entry("inv_a", terminal_rationale="anything")],
    )
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == ILLEGAL_SENTINEL_WITH_ACCEPTED for f in failures
    ), "RFC §3.1: NO_NEW_DIVERGENCE sentinel + non-empty accepted is illegal"


def test_no_new_divergence_with_non_empty_reframed_is_illegal() -> None:
    """RFC §3.1 ``divergence_marker`` docstring: when sentinel is set, ``reframed`` MUST be
    empty. Sentinel + non-empty ``reframed`` → ILLEGAL_SENTINEL_WITH_REFRAMED.
    """
    from debate_hall_mcp.path_contract_validator import (
        ILLEGAL_SENTINEL_WITH_REFRAMED,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    diff = _diff_rev(
        0,
        divergence_marker="NO_NEW_DIVERGENCE",
        reframed=[_entry("inv_a", new_possibility="anything")],
    )
    failures = validate_diff_revision(contract, diff)
    assert any(
        f.failure_type == ILLEGAL_SENTINEL_WITH_REFRAMED for f in failures
    ), "RFC §3.1: NO_NEW_DIVERGENCE sentinel + non-empty reframed is illegal"


def test_no_new_divergence_with_non_empty_disputed_only_is_legal_finding_d_regression_guard() -> (
    None
):
    """RFC §3.3 Finding D regression guard: sentinel + non-empty ``disputed`` only
    (with empty ``accepted`` and ``reframed``) remains LEGAL.

    Duplicates the spirit of ``test_no_new_divergence_finding_d_may_coexist_with_disputed``
    but explicitly guards against the P2 fix over-rejecting the disputed bucket.
    """
    from debate_hall_mcp.path_contract_validator import validate_diff_revision

    contract = _contract_with_verdicts({"inv_soft": ("SOFT_disputed", "discuss")})
    diff = _diff_rev(
        0,
        divergence_marker="NO_NEW_DIVERGENCE",
        disputed=[_entry("inv_soft")],
    )
    failures = validate_diff_revision(contract, diff)
    assert failures == [], (
        "RFC §3.3 Finding D: sentinel + non-empty disputed (only) must remain legal "
        "after the sentinel-with-accepted/reframed rejection is added"
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

    events = emit_validator_failures(thread_id="t-1", failures=failures, state_dir=tmp_path)
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

    events = emit_validator_failures(thread_id="t-empty", failures=[], state_dir=tmp_path)
    assert events == []
    # No events file written for an empty failure list.
    events_file = tmp_path / "t-empty.events.jsonl"
    assert not events_file.exists()


# ---------------------------------------------------------------------------
# SCHEMA_SHAPE_VIOLATION pre-pass — CE+CRS rework on PR #217.
#
# These tests cover the structural pre-pass that must run BEFORE any semantic
# check on a contract/revision payload originating from an LLM. Malformed
# payloads MUST yield ValidatorFailure events with failure_type
# SCHEMA_SHAPE_VIOLATION and a granular ``defect`` discriminator on the
# payload (for #203 grouping) — NOT raise KeyError or TypeError.
# ---------------------------------------------------------------------------


def test_schema_shape_violation_constant_present() -> None:
    """``SCHEMA_SHAPE_VIOLATION`` is exported as a module constant."""
    from debate_hall_mcp.path_contract_validator import SCHEMA_SHAPE_VIOLATION

    assert SCHEMA_SHAPE_VIOLATION == "schema_shape_violation"


def test_validator_failure_carries_defect_discriminator() -> None:
    """``ValidatorFailure`` exposes a ``defect`` field; default is ``None``."""
    from debate_hall_mcp.path_contract_validator import ValidatorFailure

    f = ValidatorFailure(
        failure_type="schema_shape_violation",
        path_id="path_1",
        invariant=None,
        role=None,
        details="missing required top-level key",
        defect="missing_key:verdict_history",
    )
    assert f.defect == "missing_key:verdict_history"

    # Backwards compatible: defect defaults to None for existing call sites.
    g = ValidatorFailure(
        failure_type="missing_required_entry",
        path_id="path_1",
        invariant="inv_a",
        role="Wind",
        details="x",
    )
    assert g.defect is None


def test_validate_contract_shape_accepts_well_formed_contract() -> None:
    """A semantically-valid, well-shaped contract emits zero shape failures."""
    from debate_hall_mcp.path_contract_validator import validate_contract_shape

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    contract["diff_history"].append(_diff_rev(0))
    assert validate_contract_shape(contract) == []


def test_validate_contract_shape_rejects_non_dict_input() -> None:
    """A non-Mapping input → SCHEMA_SHAPE_VIOLATION (defect: not_a_mapping)."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    failures = validate_contract_shape("not a dict")  # type: ignore[arg-type]
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "not_a_mapping" for f in failures
    )


def test_validate_contract_shape_rejects_missing_path_id() -> None:
    """Contract missing ``path_id`` → SCHEMA_SHAPE_VIOLATION (defect: missing_key:path_id)."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    bad = {
        "frame_history": [],
        "verdict_history": [],
        "diff_history": [],
    }
    failures = validate_contract_shape(bad)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "missing_key:path_id"
        for f in failures
    )


def test_validate_contract_shape_rejects_missing_verdict_history() -> None:
    """Contract missing ``verdict_history`` → SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    bad = {"path_id": "p", "frame_history": [], "diff_history": []}
    failures = validate_contract_shape(bad)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "missing_key:verdict_history"
        for f in failures
    )


def test_validate_contract_shape_rejects_history_not_a_list() -> None:
    """``verdict_history`` is a dict instead of list → SCHEMA_SHAPE_VIOLATION (type_error)."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    bad = {
        "path_id": "p",
        "frame_history": [],
        "verdict_history": {"not": "a list"},
        "diff_history": [],
    }
    failures = validate_contract_shape(bad)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION
        and f.defect == "type_error:verdict_history_not_list"
        for f in failures
    )


def test_validate_contract_shape_rejects_diff_entry_missing_value() -> None:
    """``diff_history[0]`` missing ``value`` → SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    contract["diff_history"].append(
        {  # type: ignore[arg-type]
            "rev": 0,
            "written_at": _now(),
            "written_by": "Wind",
            # value: deliberately missing
        }
    )
    failures = validate_contract_shape(contract)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "missing_key:diff_history[0].value"
        for f in failures
    )


def test_validate_contract_shape_rejects_diff_value_accepted_not_list() -> None:
    """``diff_history[0].value.accepted`` is a dict instead of list → SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    contract["diff_history"].append(
        {  # type: ignore[arg-type]
            "rev": 0,
            "written_at": _now(),
            "written_by": "Wind",
            "value": {
                "accepted": {"oops": "dict not list"},
                "disputed": [],
                "reframed": [],
            },
        }
    )
    failures = validate_contract_shape(contract)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION
        and f.defect == "type_error:diff_history[0].value.accepted_not_list"
        for f in failures
    )


def test_validate_contract_shape_rejects_verdict_value_not_dict() -> None:
    """``verdict_history[0].value`` is a list instead of dict → SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    bad: dict[str, object] = {
        "path_id": "p",
        "frame_history": [],
        "verdict_history": [
            {
                "rev": 0,
                "written_at": _now(),
                "written_by": "Wall",
                "value": ["not", "a", "dict"],
            }
        ],
        "diff_history": [],
    }
    failures = validate_contract_shape(bad)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION
        and f.defect == "type_error:verdict_history[0].value_not_dict"
        for f in failures
    )


def test_validate_contract_shape_rejects_invariant_entry_missing_invariant() -> None:
    """``InvariantEntry`` missing ``invariant`` key → SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_contract_shape,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_pass", "ok")})
    contract["diff_history"].append(
        {  # type: ignore[arg-type]
            "rev": 0,
            "written_at": _now(),
            "written_by": "Wind",
            "value": {
                "accepted": [{"rationale": "r"}],  # invariant missing
                "disputed": [],
                "reframed": [],
            },
        }
    )
    failures = validate_contract_shape(contract)
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION
        and f.defect == "missing_key:diff_history[0].value.accepted[0].invariant"
        for f in failures
    )


def test_validate_diff_revision_returns_shape_failures_instead_of_keyerror() -> None:
    """``validate_diff_revision`` on a malformed contract must NOT raise — returns failures."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_diff_revision,
    )

    # Contract is missing verdict_history entirely; previous code would
    # KeyError on the first access in _hard_fail_invariants.
    malformed = {"path_id": "p"}  # missing all three histories
    diff = _diff_rev(0)

    try:
        failures = validate_diff_revision(malformed, diff)  # type: ignore[arg-type]
    except (KeyError, TypeError) as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"validate_diff_revision must not raise on malformed payload: {exc!r}"
        ) from exc

    assert any(f.failure_type == SCHEMA_SHAPE_VIOLATION for f in failures)


def test_validate_diff_revision_short_circuits_on_shape_failure() -> None:
    """When shape is invalid, semantic checks MUST NOT run — only shape failures returned."""
    from debate_hall_mcp.path_contract_validator import (
        ILLEGAL_NO_NEW_DIVERGENCE,
        MISSING_REQUIRED_ENTRY,
        SCHEMA_SHAPE_VIOLATION,
        validate_diff_revision,
    )

    malformed = {"path_id": "p"}  # missing histories
    diff = _diff_rev(0, divergence_marker="NO_NEW_DIVERGENCE")
    failures = validate_diff_revision(malformed, diff)  # type: ignore[arg-type]

    # Only shape failures; no semantic failures from short-circuit.
    assert all(f.failure_type == SCHEMA_SHAPE_VIOLATION for f in failures)
    assert not any(
        f.failure_type in (MISSING_REQUIRED_ENTRY, ILLEGAL_NO_NEW_DIVERGENCE) for f in failures
    )


def test_validate_door_citations_returns_shape_failures_instead_of_keyerror() -> None:
    """``validate_door_citations`` on a malformed contract must NOT raise — returns failures."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_door_citations,
    )

    malformed = {"frame_history": []}  # missing path_id + verdict_history + diff_history

    try:
        failures = validate_door_citations(malformed, cited_invariants=["x"])  # type: ignore[arg-type]
    except (KeyError, TypeError) as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"validate_door_citations must not raise on malformed payload: {exc!r}"
        ) from exc

    assert any(f.failure_type == SCHEMA_SHAPE_VIOLATION for f in failures)


def test_validate_revision_ownership_returns_shape_failure_when_written_by_missing() -> None:
    """Revision missing ``written_by`` must NOT raise — returns SCHEMA_SHAPE_VIOLATION."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_revision_ownership,
    )

    bad = {"rev": 0, "written_at": _now(), "value": {}}  # no written_by

    try:
        failures = validate_revision_ownership(  # type: ignore[arg-type]
            bad, kind="verdict", path_id="path_1"
        )
    except (KeyError, TypeError) as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"validate_revision_ownership must not raise on malformed revision: {exc!r}"
        ) from exc

    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "missing_key:revision.written_by"
        for f in failures
    )


def test_validate_revision_ownership_returns_shape_failure_when_not_a_mapping() -> None:
    """Revision that is not a Mapping → SCHEMA_SHAPE_VIOLATION (defect: not_a_mapping)."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_revision_ownership,
    )

    failures = validate_revision_ownership(  # type: ignore[arg-type]
        "not a dict", kind="verdict", path_id="path_1"
    )
    assert any(
        f.failure_type == SCHEMA_SHAPE_VIOLATION and f.defect == "not_a_mapping" for f in failures
    )


def test_valid_contract_passes_pre_pass_regression_guard() -> None:
    """Semantically-correct contract still passes; pre-pass produces no false positives."""
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        validate_diff_revision,
    )

    contract = _contract_with_verdicts({"inv_a": ("HARD_fail", "blocked")})
    diff = _diff_rev(
        0, accepted=[_entry("inv_a", terminal_rationale="terminal — no creative reframe")]
    )
    failures = validate_diff_revision(contract, diff)
    # No shape failures; semantic check also passes.
    assert not any(f.failure_type == SCHEMA_SHAPE_VIOLATION for f in failures)
    assert failures == []


def test_validator_failure_event_payload_includes_defect(tmp_path: Path) -> None:
    """``emit_validator_failures`` surfaces ``defect`` in the event payload for #203 grouping."""
    from debate_hall_mcp.events import load_events
    from debate_hall_mcp.path_contract_validator import (
        SCHEMA_SHAPE_VIOLATION,
        ValidatorFailure,
        emit_validator_failures,
    )

    failures = [
        ValidatorFailure(
            failure_type=SCHEMA_SHAPE_VIOLATION,
            path_id="path_1",
            invariant=None,
            role=None,
            details="missing required top-level key",
            defect="missing_key:verdict_history",
        )
    ]
    emit_validator_failures(thread_id="t-defect", failures=failures, state_dir=tmp_path)
    loaded = load_events(thread_id="t-defect", state_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].payload["defect"] == "missing_key:verdict_history"
