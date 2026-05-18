"""Path-contract validator (RFC-0001 §3.2 / §3.3 / §6 — issue #200).

This module enforces the policy rules layered on top of the
``debate_hall_mcp.path_contract`` schema. The schema module (#196) is the
wire-format boundary; this module is the policy boundary — the split is
deliberate so the schema module remains stable and the policy can iterate
independently. See the BOUNDARY docstring on
``path_contract.path_contract_from_json`` for the matching note.

Scope per RFC-0001 #200:

* Per-invariant REQUIRED CONTENT RULE (§3.2 amended; §3.3 Finding C):
  every ``HARD_fail`` invariant in the latest ``verdict`` revision MUST
  have its own qualifying entry in the diff — either in
  ``accepted`` with a non-empty ``terminal_rationale`` OR in ``reframed``
  with a non-empty ``new_possibility``. A sibling entry on a different
  invariant does NOT satisfy the requirement for another invariant on the
  same path.
* ``NO_NEW_DIVERGENCE`` sentinel legality (§3.2; §3.3 Finding D): the
  sentinel is legal ONLY when zero ``HARD_fail`` verdicts exist for the
  path. The sentinel MAY coexist with a non-empty ``disputed`` list when
  Wind has legitimate pushback on ``SOFT_disputed`` verdicts.
* Ownership rule (§3.1): only Wind may append to ``frame_history`` or
  ``diff_history``; only Wall may append to ``verdict_history``; Door is
  read-only.
* Door citation existence (§6 item 2): every invariant Door cites in
  synthesis MUST appear in the latest ``verdict`` revision; otherwise
  Door is hallucinating provenance.
* ``VALIDATOR_FAILURE`` event emission (§6 item 3): every rejection is
  recorded as a structured event on the I4 append-only ledger with
  failure-type discrimination in the payload so the A/B harness (#203)
  can compute invalid-contract-rate by failure type without parsing
  free text.

Out of scope (deliberately deferred — see PR body):

* Orchestrator call-site wiring into ``_execute_consensus_loop``. Today
  the loop exchanges only Wind/Wall ``vote.approved`` booleans + free-text
  feedback; ``PathContract`` objects are not yet threaded through. Wiring
  depends on #197 (state plumbing) and #198 (prompts producing diff
  content). The RFC §3 invariant "consensus loop, max_refinement_loops,
  and Wall re-approval invariant at line 507 are unchanged" is honoured.
* Prompt edits enforcing the Door synthesis_guidance citation rule
  (Finding E) — that is prompt/context-compiler territory (#198/#199).
  This module's responsibility for ``synthesis_guidance`` is bounded to
  the citation-existence check on the invariants Door names; the
  *requirement* to cite ``synthesis_guidance`` when present is a Door
  prompt concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from debate_hall_mcp.events import DebateEvent, EventType, append_event
from debate_hall_mcp.path_contract import (
    DiffRevision,
    FrameRevision,
    InvariantEntry,
    PathContract,
    VerdictRevision,
)

# ---------------------------------------------------------------------------
# Failure-type discriminators (stable identifiers for #203 A/B grouping).
# ---------------------------------------------------------------------------

MISSING_REQUIRED_ENTRY = "missing_required_entry"
"""HARD_fail invariant lacks any qualifying entry in the diff."""

EMPTY_TERMINAL_RATIONALE = "empty_terminal_rationale"
"""``accepted`` entry on a HARD_fail invariant has empty/missing ``terminal_rationale``."""

EMPTY_NEW_POSSIBILITY = "empty_new_possibility"
"""``reframed`` entry on a HARD_fail invariant has empty/missing ``new_possibility``."""

ILLEGAL_NO_NEW_DIVERGENCE = "illegal_no_new_divergence"
"""``NO_NEW_DIVERGENCE`` sentinel emitted on a path with at least one HARD_fail verdict."""

ILLEGAL_SENTINEL_WITH_ACCEPTED = "illegal_sentinel_with_accepted"
"""``NO_NEW_DIVERGENCE`` sentinel emitted alongside a non-empty ``accepted`` list.

Per RFC §3.1 ``divergence_marker`` docstring: when the sentinel is set,
``value.accepted`` and ``value.reframed`` MUST be empty (``disputed`` MAY
be non-empty per Finding D).
"""

ILLEGAL_SENTINEL_WITH_REFRAMED = "illegal_sentinel_with_reframed"
"""``NO_NEW_DIVERGENCE`` sentinel emitted alongside a non-empty ``reframed`` list.

Per RFC §3.1 ``divergence_marker`` docstring: when the sentinel is set,
``value.reframed`` MUST be empty.
"""

OWNERSHIP_VIOLATION = "ownership_violation"
"""A revision was written by a role other than the legal owner for its kind."""

DOOR_CITATION_NOT_FOUND = "door_citation_not_found"
"""Door cited an invariant that does not appear in the latest verdict revision."""


RevisionKind = Literal["frame", "verdict", "diff"]


# ---------------------------------------------------------------------------
# Structured failure record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatorFailure:
    """A single validator rejection.

    Carries enough discriminated metadata for the A/B harness (#203) to
    group failures by ``failure_type`` and correlate per ``path_id``,
    ``invariant``, and ``role`` without parsing free text.

    Attributes:
        failure_type: One of the module-level discriminator constants
            (e.g. ``MISSING_REQUIRED_ENTRY``).
        path_id: The path the failure relates to.
        invariant: The invariant name when the failure is invariant-scoped;
            ``None`` otherwise (e.g. ownership violations are not
            invariant-scoped).
        role: The acting role when the failure is role-scoped (ownership
            violations); ``None`` otherwise.
        details: Human-readable explanation. Not a stable identifier — for
            grouping use ``failure_type``.
    """

    failure_type: str
    path_id: str
    invariant: str | None
    role: str | None
    details: str


# ---------------------------------------------------------------------------
# Per-invariant REQUIRED CONTENT RULE + sentinel legality (§3.2 / §3.3 C+D).
# ---------------------------------------------------------------------------


def _latest_verdict_value(
    contract: PathContract,
) -> dict[str, dict[str, str]] | None:
    """Return the ``value`` dict of the latest ``VerdictRevision`` or ``None``."""
    history = contract["verdict_history"]
    if not history:
        return None
    # ``value`` is typed as ``dict[Invariant, InvariantVerdict]``; the cast
    # is for the runtime helper only.
    return history[-1]["value"]  # type: ignore[return-value]


def _hard_fail_invariants(contract: PathContract) -> list[str]:
    """List the invariant keys whose latest verdict is ``HARD_fail``."""
    latest = _latest_verdict_value(contract)
    if latest is None:
        return []
    return [name for name, verdict in latest.items() if verdict.get("status") == "HARD_fail"]


def _qualifying_accepted(diff: DiffRevision, invariant: str) -> list[InvariantEntry]:
    """Return ``accepted`` entries matching ``invariant`` (irrespective of content)."""
    return [e for e in diff["value"]["accepted"] if e.get("invariant") == invariant]


def _qualifying_reframed(diff: DiffRevision, invariant: str) -> list[InvariantEntry]:
    """Return ``reframed`` entries matching ``invariant``."""
    return [e for e in diff["value"]["reframed"] if e.get("invariant") == invariant]


def validate_diff_revision(contract: PathContract, diff: DiffRevision) -> list[ValidatorFailure]:
    """Validate ``diff`` against the latest verdict for ``contract``.

    Enforces RFC §3.2 / §3.3 Findings C and D:

    * For every ``HARD_fail`` invariant in the latest verdict, the diff
      MUST contain at least one qualifying entry on the SAME invariant —
      ``accepted`` with non-empty ``terminal_rationale`` OR ``reframed``
      with non-empty ``new_possibility``.
    * ``NO_NEW_DIVERGENCE`` is legal only when zero ``HARD_fail`` verdicts
      exist for the path; it MAY coexist with a non-empty ``disputed``
      list (Finding D).

    Returns:
        A list of ``ValidatorFailure`` records — empty when valid.
    """
    failures: list[ValidatorFailure] = []
    path_id = contract["path_id"]
    hard_fail = _hard_fail_invariants(contract)

    # Sentinel legality — Finding D allows sentinel + disputed; the sentinel
    # is illegal when (a) any HARD_fail is in the latest verdict, OR (b) the
    # diff carries a non-empty ``accepted`` or ``reframed`` list (RFC §3.1
    # ``divergence_marker`` docstring: only ``disputed`` MAY be non-empty).
    # Each of the three conditions is independently audit-worthy so all
    # applicable failures are emitted (the A/B harness in #203 groups by
    # ``failure_type`` and the three discriminators do not occlude each
    # other).
    if diff.get("divergence_marker") == "NO_NEW_DIVERGENCE":
        if hard_fail:
            failures.append(
                ValidatorFailure(
                    failure_type=ILLEGAL_NO_NEW_DIVERGENCE,
                    path_id=path_id,
                    invariant=None,
                    role="Wind",
                    details=(
                        "NO_NEW_DIVERGENCE sentinel emitted on a path whose "
                        f"latest verdict contains HARD_fail invariants: {hard_fail}"
                    ),
                )
            )
        if diff["value"]["accepted"]:
            failures.append(
                ValidatorFailure(
                    failure_type=ILLEGAL_SENTINEL_WITH_ACCEPTED,
                    path_id=path_id,
                    invariant=None,
                    role="Wind",
                    details=(
                        "NO_NEW_DIVERGENCE sentinel emitted with a non-empty "
                        "accepted list; RFC §3.1 requires accepted to be empty "
                        "when the sentinel is set."
                    ),
                )
            )
        if diff["value"]["reframed"]:
            failures.append(
                ValidatorFailure(
                    failure_type=ILLEGAL_SENTINEL_WITH_REFRAMED,
                    path_id=path_id,
                    invariant=None,
                    role="Wind",
                    details=(
                        "NO_NEW_DIVERGENCE sentinel emitted with a non-empty "
                        "reframed list; RFC §3.1 requires reframed to be empty "
                        "when the sentinel is set."
                    ),
                )
            )
        # Continue checking REQUIRED CONTENT regardless — sentinel-class
        # failures and per-invariant content failures are independently
        # audit-worthy.

    # Per-invariant REQUIRED CONTENT RULE.
    #
    # Two complementary checks per HARD_fail invariant, both emitted:
    #
    # 1. Existence (per-invariant, §3.3 Finding C): at least ONE qualifying
    #    entry must exist (``accepted`` with non-empty ``terminal_rationale``
    #    OR ``reframed`` with non-empty ``new_possibility``); otherwise
    #    emit MISSING_REQUIRED_ENTRY.
    #
    # 2. Per-entry validity (per-entry, §3.2): EVERY matching ``accepted``
    #    entry must carry a non-empty ``terminal_rationale``, and EVERY
    #    matching ``reframed`` entry must carry a non-empty ``new_possibility``;
    #    each malformed entry emits its own EMPTY_TERMINAL_RATIONALE or
    #    EMPTY_NEW_POSSIBILITY failure. A sibling entry satisfying the
    #    existence check does NOT absorb a sibling's per-entry malformation
    #    — the §3.2 rule is per-entry, not per-invariant.
    for invariant in hard_fail:
        accepted_matches = _qualifying_accepted(diff, invariant)
        reframed_matches = _qualifying_reframed(diff, invariant)

        accepted_has_valid = any(
            isinstance(e.get("terminal_rationale"), str) and e.get("terminal_rationale")
            for e in accepted_matches
        )
        reframed_has_valid = any(
            isinstance(e.get("new_possibility"), str) and e.get("new_possibility")
            for e in reframed_matches
        )

        if not accepted_has_valid and not reframed_has_valid:
            failures.append(
                ValidatorFailure(
                    failure_type=MISSING_REQUIRED_ENTRY,
                    path_id=path_id,
                    invariant=invariant,
                    role="Wind",
                    details=(
                        f"HARD_fail invariant {invariant!r} has no qualifying "
                        "entry in diff.accepted or diff.reframed (§3.3 "
                        "Finding C: per-invariant requirement, sibling entry "
                        "on a different invariant does not satisfy)."
                    ),
                )
            )

        # Per-entry validity — always run, independent of the existence
        # check above. Each malformed entry emits its own failure so the
        # A/B harness in #203 can group per-entry violations accurately.
        for entry in accepted_matches:
            tr = entry.get("terminal_rationale")
            if not (isinstance(tr, str) and tr):
                failures.append(
                    ValidatorFailure(
                        failure_type=EMPTY_TERMINAL_RATIONALE,
                        path_id=path_id,
                        invariant=invariant,
                        role="Wind",
                        details=(
                            f"accepted entry on HARD_fail invariant {invariant!r} "
                            "has empty or missing terminal_rationale (§3.2 per-entry "
                            "rule: each malformed entry is a validator-failure event)."
                        ),
                    )
                )
        for entry in reframed_matches:
            np = entry.get("new_possibility")
            if not (isinstance(np, str) and np):
                failures.append(
                    ValidatorFailure(
                        failure_type=EMPTY_NEW_POSSIBILITY,
                        path_id=path_id,
                        invariant=invariant,
                        role="Wind",
                        details=(
                            f"reframed entry on HARD_fail invariant {invariant!r} "
                            "has empty or missing new_possibility (§3.2 per-entry "
                            "rule: each malformed entry is a validator-failure event)."
                        ),
                    )
                )

    return failures


# ---------------------------------------------------------------------------
# Ownership rule (§3.1).
# ---------------------------------------------------------------------------


_LEGAL_OWNER: dict[RevisionKind, str] = {
    "frame": "Wind",
    "verdict": "Wall",
    "diff": "Wind",
}


def validate_revision_ownership(
    revision: FrameRevision | VerdictRevision | DiffRevision,
    *,
    kind: RevisionKind,
    path_id: str,
) -> list[ValidatorFailure]:
    """Validate that ``revision.written_by`` matches the legal owner for ``kind``.

    RFC §3.1: only Wind may append to ``frame_history`` or ``diff_history``;
    only Wall may append to ``verdict_history``; Door is read-only and
    therefore can never legally appear as a writer of any revision.

    Args:
        revision: The revision wrapper whose owner is being checked.
        kind: The kind of revision (``frame``, ``verdict``, or ``diff``)
            — caller knows which history the revision is destined for.
        path_id: The path-id the revision relates to (for failure
            correlation; revisions themselves do not carry ``path_id``).

    Returns:
        A list with at most one ``ValidatorFailure`` of type
        ``OWNERSHIP_VIOLATION``.
    """
    expected = _LEGAL_OWNER[kind]
    actual = revision["written_by"]
    if actual == expected:
        return []
    return [
        ValidatorFailure(
            failure_type=OWNERSHIP_VIOLATION,
            path_id=path_id,
            invariant=None,
            role=actual,
            details=(
                f"{kind}_history append by {actual!r} rejected; "
                f"only {expected!r} may write {kind} revisions (§3.1)."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Door citation existence (§6 item 2).
# ---------------------------------------------------------------------------


def validate_door_citations(
    contract: PathContract, *, cited_invariants: list[str]
) -> list[ValidatorFailure]:
    """Validate that each cited invariant exists in the latest verdict.

    RFC §6 item 2: "when Door's synthesis is produced, validate that every
    cited entry exists in the contract (no fabricated citations)."

    The caller is responsible for parsing Door's synthesis text and
    extracting the list of cited invariant names; this function does the
    membership check against the latest verdict revision.

    Returns:
        One ``DOOR_CITATION_NOT_FOUND`` failure per cited invariant that
        does NOT appear in the latest verdict revision. If there is no
        verdict revision at all, every cited invariant is reported.
    """
    latest = _latest_verdict_value(contract)
    known: set[str] = set(latest.keys()) if latest is not None else set()
    return [
        ValidatorFailure(
            failure_type=DOOR_CITATION_NOT_FOUND,
            path_id=contract["path_id"],
            invariant=name,
            role="Door",
            details=(
                f"Door cited invariant {name!r} which does not appear in the "
                "latest verdict revision (§6 item 2: no fabricated citations)."
            ),
        )
        for name in cited_invariants
        if name not in known
    ]


# ---------------------------------------------------------------------------
# VALIDATOR_FAILURE event emission (§6 item 3).
# ---------------------------------------------------------------------------


def _failure_payload(failure: ValidatorFailure) -> dict[str, object]:
    """Project a ``ValidatorFailure`` into a flat JSON-safe event payload."""
    return {
        "failure_type": failure.failure_type,
        "path_id": failure.path_id,
        "invariant": failure.invariant,
        "role": failure.role,
        "details": failure.details,
    }


def emit_validator_failures(
    *,
    thread_id: str,
    failures: list[ValidatorFailure],
    state_dir: Path,
) -> list[DebateEvent]:
    """Append one ``VALIDATOR_FAILURE`` event per failure to the ledger.

    Failure-type discrimination lives in the ``failure_type`` payload key
    (NOT in the ``EventType``) so the A/B harness (#203) can group
    failures without inflating the ``EventType`` enum and breaking
    consumers iterating its members.

    Returns:
        The list of created ``DebateEvent`` records (empty when no
        failures were supplied; no events file is touched in that case).
    """
    return [
        append_event(
            thread_id=thread_id,
            event_type=EventType.VALIDATOR_FAILURE,
            payload=_failure_payload(f),
            state_dir=state_dir,
        )
        for f in failures
    ]


__all__ = [
    "DOOR_CITATION_NOT_FOUND",
    "EMPTY_NEW_POSSIBILITY",
    "EMPTY_TERMINAL_RATIONALE",
    "ILLEGAL_NO_NEW_DIVERGENCE",
    "ILLEGAL_SENTINEL_WITH_ACCEPTED",
    "ILLEGAL_SENTINEL_WITH_REFRAMED",
    "MISSING_REQUIRED_ENTRY",
    "OWNERSHIP_VIOLATION",
    "RevisionKind",
    "ValidatorFailure",
    "emit_validator_failures",
    "validate_diff_revision",
    "validate_door_citations",
    "validate_revision_ownership",
]
