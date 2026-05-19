"""Path-contract validator (RFC-0001 §3.2 / §3.3 / §6 — issue #200).

This module enforces the policy rules layered on top of the
``debate_hall_mcp.path_contract`` schema. The schema module (#196) is the
wire-format boundary; this module is the policy boundary — the split is
deliberate so the schema module remains stable and the policy can iterate
independently. See the BOUNDARY docstring on
``path_contract.path_contract_from_json`` for the matching note.

Two-phase validation pattern (CE+CRS rework on PR #217):
-------------------------------------------------------

Per RFC §6 item 3 the validator is the structural-rejection point for
LLM-emitted payloads. The schema module deliberately does NOT validate
structure (see the BOUNDARY docstring on ``path_contract_from_json``), so
this module must defend itself against malformed payloads — an unhandled
``KeyError`` / ``TypeError`` would crash the orchestrator instead of
producing an auditable ``VALIDATOR_FAILURE`` event on the I4 ledger.

Validation therefore runs in two phases:

  PHASE 1 — SHAPE pre-pass (``validate_contract_shape`` /
  ``validate_revision_shape``): checks that the payload is a ``Mapping``
  with the required keys carrying the required runtime types. Each
  structural defect emits a ``ValidatorFailure`` with
  ``failure_type=SCHEMA_SHAPE_VIOLATION`` and a granular ``defect``
  discriminator on the payload (``missing_key:...`` or ``type_error:...``)
  so the #203 A/B harness can group by defect class.

  PHASE 2 — SEMANTIC checks (existing functions: REQUIRED CONTENT RULE,
  sentinel legality, ownership rule, Door citation existence). These run
  ONLY when the shape pre-pass returned no failures. If the shape is
  invalid, the public entry points return the shape failures immediately
  and do NOT attempt semantic interpretation (fail-fast, never crash).

The semantic-check functions therefore assume well-shaped inputs and may
use direct dict access; the contract is that shape validation passed
upstream.

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

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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

SCHEMA_SHAPE_VIOLATION = "schema_shape_violation"
"""Structural pre-pass defect on a contract or revision payload.

Emitted by ``validate_contract_shape`` / ``validate_revision_shape`` for any
malformed LLM-emitted payload: missing required keys, non-``Mapping`` /
non-``list`` runtime types where the schema requires them, etc. The granular
defect identifier (``missing_key:...``, ``type_error:...``) is carried on the
event payload's ``defect`` field so the #203 A/B harness can group by defect
class without parsing free text.

This is the structural counterpart to the semantic failure-types above:
shape defects short-circuit semantic interpretation entirely, preserving
I4 (auditable ledger) by emitting an event rather than letting a
``KeyError`` / ``TypeError`` crash the orchestrator.
"""


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
        defect: Granular structural-defect discriminator for
            ``SCHEMA_SHAPE_VIOLATION`` failures (e.g.
            ``"missing_key:verdict_history"``,
            ``"type_error:diff_history[0].value.accepted_not_list"``).
            ``None`` for non-shape failure-types; preserved as a stable
            identifier so the #203 harness can group shape defects by
            class. Defaults to ``None`` for backward compatibility with
            existing semantic-check call sites.
    """

    failure_type: str
    path_id: str
    invariant: str | None
    role: str | None
    details: str
    defect: str | None = None


# ---------------------------------------------------------------------------
# PHASE 1 — Shape pre-pass (CE+CRS rework on PR #217).
#
# Defends every public entry point against malformed LLM-emitted payloads.
# Returns ``SCHEMA_SHAPE_VIOLATION`` failures with a granular ``defect``
# discriminator instead of letting ``KeyError`` / ``TypeError`` propagate.
# ---------------------------------------------------------------------------


def _shape_failure(path_id: str, defect: str, details: str) -> ValidatorFailure:
    """Build a ``SCHEMA_SHAPE_VIOLATION`` failure with a granular ``defect``."""
    return ValidatorFailure(
        failure_type=SCHEMA_SHAPE_VIOLATION,
        path_id=path_id,
        invariant=None,
        role=None,
        details=details,
        defect=defect,
    )


# Allowed Literal value sets per RFC §3.1. Centralised here so the shape
# pre-pass enforces VALUE membership (not just key presence) — addresses
# Cubic P2 on PR #217: previously ``status="HARD_FAIL"`` (caps) or
# ``written_by="wind"`` (lowercase) passed shape validation and either
# silently bypassed semantic checks (false negative on REQUIRED CONTENT
# RULE) or were mis-categorised as ``OWNERSHIP_VIOLATION``.
_ALLOWED_STATUS: frozenset[str] = frozenset({"HARD_pass", "HARD_fail", "SOFT_disputed"})
_ALLOWED_WRITTEN_BY: dict[RevisionKind, frozenset[str]] = {
    "frame": frozenset({"Wind"}),
    "verdict": frozenset({"Wall"}),
    "diff": frozenset({"Wind"}),
}
_ALLOWED_DIVERGENCE_MARKER: frozenset[str] = frozenset({"NO_NEW_DIVERGENCE"})


def _check_literal_value(
    value: object,
    *,
    allowed: frozenset[str],
    path_id: str,
    locator: str,
) -> ValidatorFailure | None:
    """Verify ``value`` is one of the ``allowed`` Literal strings.

    Returns ``None`` when ``value`` is a valid member, otherwise a
    ``SCHEMA_SHAPE_VIOLATION`` with defect ``invalid_literal:<locator>:<repr>``.
    A ``None`` ``value`` (caller already determined the key is absent and
    that absence is permitted — e.g. ``NotRequired`` slot) should not be
    passed here; callers gate on presence first.
    """
    if isinstance(value, str) and value in allowed:
        return None
    return _shape_failure(
        path_id,
        f"invalid_literal:{locator}:{value!r}",
        (
            f"{locator} must be one of {sorted(allowed)!r}; "
            f"got {value!r} (type {type(value).__name__})."
        ),
    )


def _check_invariant_entries(
    entries: object,
    *,
    path_id: str,
    locator_prefix: str,
) -> list[ValidatorFailure]:
    """Validate a list of ``InvariantEntry`` dicts.

    Each entry must be a ``Mapping`` carrying at least an ``invariant`` (str)
    and ``rationale`` (str) field. ``terminal_rationale`` / ``new_possibility``
    are ``NotRequired`` per the schema and intentionally NOT shape-required —
    their presence/contents are a semantic concern (handled by
    ``validate_diff_revision``).
    """
    failures: list[ValidatorFailure] = []
    if not isinstance(entries, list):
        return [
            _shape_failure(
                path_id,
                f"type_error:{locator_prefix}_not_list",
                f"{locator_prefix} must be a list (got {type(entries).__name__}).",
            )
        ]
    for index, entry in enumerate(entries):
        locator = f"{locator_prefix}[{index}]"
        if not isinstance(entry, Mapping):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}_not_mapping",
                    f"{locator} must be a Mapping (got {type(entry).__name__}).",
                )
            )
            continue
        if "invariant" not in entry:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:{locator}.invariant",
                    f"{locator} missing required key 'invariant'.",
                )
            )
        elif not isinstance(entry["invariant"], str):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}.invariant_not_str",
                    f"{locator}.invariant must be a string.",
                )
            )
        if "rationale" not in entry:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:{locator}.rationale",
                    f"{locator} missing required key 'rationale'.",
                )
            )
        elif not isinstance(entry["rationale"], str):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}.rationale_not_str",
                    f"{locator}.rationale must be a string.",
                )
            )
    return failures


def _check_frame_history(history: list[Any], path_id: str) -> list[ValidatorFailure]:
    """Shape-check each ``FrameRevision`` in ``frame_history``."""
    failures: list[ValidatorFailure] = []
    for index, rev in enumerate(history):
        locator = f"frame_history[{index}]"
        if not isinstance(rev, Mapping):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}_not_mapping",
                    f"{locator} must be a Mapping.",
                )
            )
            continue
        for key in ("rev", "written_at", "written_by", "value"):
            if key not in rev:
                failures.append(
                    _shape_failure(
                        path_id,
                        f"missing_key:{locator}.{key}",
                        f"{locator} missing required key '{key}'.",
                    )
                )
        # Literal VALUE membership for ``written_by`` (RFC §3.1).
        if "written_by" in rev:
            wb_failure = _check_literal_value(
                rev["written_by"],
                allowed=_ALLOWED_WRITTEN_BY["frame"],
                path_id=path_id,
                locator=f"{locator}.written_by",
            )
            if wb_failure is not None:
                failures.append(wb_failure)
    return failures


def _check_verdict_history(history: list[Any], path_id: str) -> list[ValidatorFailure]:
    """Shape-check each ``VerdictRevision`` in ``verdict_history``."""
    failures: list[ValidatorFailure] = []
    for index, rev in enumerate(history):
        locator = f"verdict_history[{index}]"
        if not isinstance(rev, Mapping):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}_not_mapping",
                    f"{locator} must be a Mapping.",
                )
            )
            continue
        for key in ("rev", "written_at", "written_by", "value"):
            if key not in rev:
                failures.append(
                    _shape_failure(
                        path_id,
                        f"missing_key:{locator}.{key}",
                        f"{locator} missing required key '{key}'.",
                    )
                )
        # Literal VALUE membership for ``written_by`` (RFC §3.1).
        if "written_by" in rev:
            wb_failure = _check_literal_value(
                rev["written_by"],
                allowed=_ALLOWED_WRITTEN_BY["verdict"],
                path_id=path_id,
                locator=f"{locator}.written_by",
            )
            if wb_failure is not None:
                failures.append(wb_failure)
        # value must be a Mapping[str, Mapping] with status/rationale fields.
        if "value" in rev:
            value = rev["value"]
            if not isinstance(value, Mapping):
                failures.append(
                    _shape_failure(
                        path_id,
                        f"type_error:{locator}.value_not_dict",
                        f"{locator}.value must be a Mapping[invariant, verdict].",
                    )
                )
                continue
            for inv_name, verdict in value.items():
                v_loc = f"{locator}.value[{inv_name!r}]"
                if not isinstance(verdict, Mapping):
                    failures.append(
                        _shape_failure(
                            path_id,
                            f"type_error:{v_loc}_not_mapping",
                            f"{v_loc} must be a Mapping with 'status' and 'rationale'.",
                        )
                    )
                    continue
                for key in ("status", "rationale"):
                    if key not in verdict:
                        failures.append(
                            _shape_failure(
                                path_id,
                                f"missing_key:{v_loc}.{key}",
                                f"{v_loc} missing required key '{key}'.",
                            )
                        )
                # Literal VALUE membership for ``status`` (RFC §3.1).
                if "status" in verdict:
                    status_failure = _check_literal_value(
                        verdict["status"],
                        allowed=_ALLOWED_STATUS,
                        path_id=path_id,
                        locator=f"{v_loc}.status",
                    )
                    if status_failure is not None:
                        failures.append(status_failure)
    return failures


def _check_diff_history(history: list[Any], path_id: str) -> list[ValidatorFailure]:
    """Shape-check each ``DiffRevision`` in ``diff_history``."""
    failures: list[ValidatorFailure] = []
    for index, rev in enumerate(history):
        locator = f"diff_history[{index}]"
        if not isinstance(rev, Mapping):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}_not_mapping",
                    f"{locator} must be a Mapping.",
                )
            )
            continue
        for key in ("rev", "written_at", "written_by", "value"):
            if key not in rev:
                failures.append(
                    _shape_failure(
                        path_id,
                        f"missing_key:{locator}.{key}",
                        f"{locator} missing required key '{key}'.",
                    )
                )
        # Literal VALUE membership for ``written_by`` (RFC §3.1).
        if "written_by" in rev:
            wb_failure = _check_literal_value(
                rev["written_by"],
                allowed=_ALLOWED_WRITTEN_BY["diff"],
                path_id=path_id,
                locator=f"{locator}.written_by",
            )
            if wb_failure is not None:
                failures.append(wb_failure)
        # Literal VALUE membership for ``divergence_marker`` (NotRequired —
        # only checked when present). RFC §3.1: Literal["NO_NEW_DIVERGENCE"].
        if "divergence_marker" in rev:
            dm_failure = _check_literal_value(
                rev["divergence_marker"],
                allowed=_ALLOWED_DIVERGENCE_MARKER,
                path_id=path_id,
                locator=f"{locator}.divergence_marker",
            )
            if dm_failure is not None:
                failures.append(dm_failure)
        if "value" not in rev:
            continue
        value = rev["value"]
        if not isinstance(value, Mapping):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{locator}.value_not_dict",
                    f"{locator}.value must be a Mapping with accepted/disputed/reframed.",
                )
            )
            continue
        for bucket in ("accepted", "disputed", "reframed"):
            if bucket not in value:
                failures.append(
                    _shape_failure(
                        path_id,
                        f"missing_key:{locator}.value.{bucket}",
                        f"{locator}.value missing required bucket '{bucket}'.",
                    )
                )
                continue
            failures.extend(
                _check_invariant_entries(
                    value[bucket],
                    path_id=path_id,
                    locator_prefix=f"{locator}.value.{bucket}",
                )
            )
    return failures


def validate_contract_shape(contract: object) -> list[ValidatorFailure]:
    """Structural pre-pass — verify ``contract`` matches the ``PathContract`` shape.

    Returns ``SCHEMA_SHAPE_VIOLATION`` failures (with granular ``defect``
    discriminators) for every structural defect found. An empty return means
    the payload is well-shaped enough that semantic checks can proceed using
    direct dict access.

    The function is total: it never raises on a malformed input. Non-``Mapping``
    inputs produce a single ``defect="not_a_mapping"`` failure (with
    ``path_id="<unknown>"`` since path_id cannot be read).

    Checks (in order):

    * ``contract`` is a ``Mapping``.
    * Required top-level keys present: ``path_id`` (str), ``frame_history``
      (list), ``verdict_history`` (list), ``diff_history`` (list).
    * For each revision in ``*_history``: a ``Mapping`` carrying ``rev``,
      ``written_at``, ``written_by``, ``value``.
    * For ``VerdictRevision.value``: a ``Mapping[str, Mapping]`` where each
      inner mapping has ``status`` and ``rationale``.
    * For ``DiffRevision.value``: a ``Mapping`` with ``accepted`` /
      ``disputed`` / ``reframed`` lists, each containing ``Mapping`` entries
      with ``invariant`` (str) and ``rationale`` (str).

    ``NotRequired`` schema slots (``terminal_rationale``, ``new_possibility``,
    ``divergence_marker``, ``synthesis_guidance``) are NOT shape-required —
    their presence/contents are semantic concerns handled by
    ``validate_diff_revision`` (per RFC §3.2 per-entry rule).
    """
    if not isinstance(contract, Mapping):
        return [
            _shape_failure(
                "<unknown>",
                "not_a_mapping",
                f"contract must be a Mapping (got {type(contract).__name__}).",
            )
        ]

    # Read path_id defensively for failure correlation.
    path_id_raw = contract.get("path_id")
    path_id: str = path_id_raw if isinstance(path_id_raw, str) else "<unknown>"

    failures: list[ValidatorFailure] = []

    if "path_id" not in contract:
        failures.append(
            _shape_failure(
                path_id, "missing_key:path_id", "contract missing required key 'path_id'."
            )
        )
    elif not isinstance(contract["path_id"], str):
        failures.append(
            _shape_failure(
                path_id, "type_error:path_id_not_str", "contract.path_id must be a string."
            )
        )

    for history_key in ("frame_history", "verdict_history", "diff_history"):
        if history_key not in contract:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:{history_key}",
                    f"contract missing required key '{history_key}'.",
                )
            )
            continue
        if not isinstance(contract[history_key], list):
            failures.append(
                _shape_failure(
                    path_id,
                    f"type_error:{history_key}_not_list",
                    f"contract.{history_key} must be a list.",
                )
            )

    if isinstance(contract.get("frame_history"), list):
        failures.extend(_check_frame_history(contract["frame_history"], path_id))
    if isinstance(contract.get("verdict_history"), list):
        failures.extend(_check_verdict_history(contract["verdict_history"], path_id))
    if isinstance(contract.get("diff_history"), list):
        failures.extend(_check_diff_history(contract["diff_history"], path_id))

    return failures


def _validate_diff_shape(diff: object, path_id: str) -> list[ValidatorFailure]:
    """Shape-check a single ``DiffRevision`` payload (the one being appended)."""
    if not isinstance(diff, Mapping):
        return [
            _shape_failure(
                path_id,
                "not_a_mapping",
                f"diff revision must be a Mapping (got {type(diff).__name__}).",
            )
        ]
    failures: list[ValidatorFailure] = []
    for key in ("rev", "written_at", "written_by", "value"):
        if key not in diff:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:diff.{key}",
                    f"diff revision missing required key '{key}'.",
                )
            )
    # Literal VALUE membership for ``written_by`` (RFC §3.1: Literal["Wind"]).
    if "written_by" in diff:
        wb_failure = _check_literal_value(
            diff["written_by"],
            allowed=_ALLOWED_WRITTEN_BY["diff"],
            path_id=path_id,
            locator="diff.written_by",
        )
        if wb_failure is not None:
            failures.append(wb_failure)
    # Literal VALUE membership for ``divergence_marker`` (NotRequired).
    if "divergence_marker" in diff:
        dm_failure = _check_literal_value(
            diff["divergence_marker"],
            allowed=_ALLOWED_DIVERGENCE_MARKER,
            path_id=path_id,
            locator="diff.divergence_marker",
        )
        if dm_failure is not None:
            failures.append(dm_failure)
    if "value" not in diff:
        return failures
    value = diff["value"]
    if not isinstance(value, Mapping):
        failures.append(
            _shape_failure(
                path_id,
                "type_error:diff.value_not_dict",
                "diff.value must be a Mapping with accepted/disputed/reframed.",
            )
        )
        return failures
    for bucket in ("accepted", "disputed", "reframed"):
        if bucket not in value:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:diff.value.{bucket}",
                    f"diff.value missing required bucket '{bucket}'.",
                )
            )
            continue
        failures.extend(
            _check_invariant_entries(
                value[bucket],
                path_id=path_id,
                locator_prefix=f"diff.value.{bucket}",
            )
        )
    return failures


def validate_revision_shape(
    revision: object, *, kind: RevisionKind, path_id: str
) -> list[ValidatorFailure]:
    """Structural pre-pass for a single revision (``FrameRevision`` /
    ``VerdictRevision`` / ``DiffRevision``).

    Used by ``validate_revision_ownership`` to avoid ``KeyError`` on
    ``revision["written_by"]`` when an LLM emits a malformed revision dict.
    """
    if not isinstance(revision, Mapping):
        return [
            _shape_failure(
                path_id,
                "not_a_mapping",
                f"{kind} revision must be a Mapping (got {type(revision).__name__}).",
            )
        ]
    failures: list[ValidatorFailure] = []
    for key in ("rev", "written_at", "written_by", "value"):
        if key not in revision:
            failures.append(
                _shape_failure(
                    path_id,
                    f"missing_key:revision.{key}",
                    f"{kind} revision missing required key '{key}'.",
                )
            )
    # Literal VALUE membership for ``written_by`` per ``kind`` (RFC §3.1).
    # Critical for the two-phase pattern: an invalid Literal here is a
    # shape defect, not a semantic ``OWNERSHIP_VIOLATION`` — the latter
    # only applies when ``written_by`` is a STRUCTURALLY valid Literal but
    # for the wrong revision kind. Without this check, ``written_by="wind"``
    # (lowercase) would be mis-categorised as OWNERSHIP.
    if "written_by" in revision:
        wb_failure = _check_literal_value(
            revision["written_by"],
            allowed=_ALLOWED_WRITTEN_BY[kind],
            path_id=path_id,
            locator="revision.written_by",
        )
        if wb_failure is not None:
            failures.append(wb_failure)
    return failures


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

    Two-phase pattern: the shape pre-pass runs first; if any structural
    defects are found the function returns those failures immediately and
    does NOT proceed to semantic checks (fail-fast, never crash on a
    malformed LLM payload — see module docstring).

    Returns:
        A list of ``ValidatorFailure`` records — empty when valid.
    """
    # PHASE 1: shape pre-pass — never trust LLM-emitted payloads.
    path_id_raw = contract.get("path_id") if isinstance(contract, Mapping) else None
    pid_for_diff: str = path_id_raw if isinstance(path_id_raw, str) else "<unknown>"
    shape_failures = validate_contract_shape(contract)
    shape_failures.extend(_validate_diff_shape(diff, pid_for_diff))
    if shape_failures:
        return shape_failures

    # PHASE 2: semantic checks (shape is now verified).
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

    Two-phase pattern: the per-revision shape pre-pass runs first; if the
    revision is not a ``Mapping`` or is missing ``written_by``, returns
    ``SCHEMA_SHAPE_VIOLATION`` failures and does NOT attempt the ownership
    check (no ``KeyError`` on malformed payloads).

    Args:
        revision: The revision wrapper whose owner is being checked.
        kind: The kind of revision (``frame``, ``verdict``, or ``diff``)
            — caller knows which history the revision is destined for.
        path_id: The path-id the revision relates to (for failure
            correlation; revisions themselves do not carry ``path_id``).

    Returns:
        A list with shape failures (if any) OR at most one ``ValidatorFailure``
        of type ``OWNERSHIP_VIOLATION``.
    """
    shape_failures = validate_revision_shape(revision, kind=kind, path_id=path_id)
    if shape_failures:
        return shape_failures

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

    Two-phase pattern: shape pre-pass runs first; on shape failure the
    function returns those failures and does NOT attempt citation
    membership lookup (no ``KeyError`` on malformed payloads).

    Returns:
        Shape failures (if any) OR one ``DOOR_CITATION_NOT_FOUND`` failure
        per cited invariant that does NOT appear in the latest verdict
        revision. If there is no verdict revision at all, every cited
        invariant is reported.
    """
    shape_failures = validate_contract_shape(contract)
    if shape_failures:
        return shape_failures

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
    """Project a ``ValidatorFailure`` into a flat JSON-safe event payload.

    Includes ``defect`` for ``SCHEMA_SHAPE_VIOLATION`` failures so the #203
    A/B harness can group structural defects by class without parsing the
    free-text ``details`` field.
    """
    return {
        "failure_type": failure.failure_type,
        "path_id": failure.path_id,
        "invariant": failure.invariant,
        "role": failure.role,
        "details": failure.details,
        "defect": failure.defect,
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
    "SCHEMA_SHAPE_VIOLATION",
    "RevisionKind",
    "ValidatorFailure",
    "emit_validator_failures",
    "validate_contract_shape",
    "validate_diff_revision",
    "validate_door_citations",
    "validate_revision_ownership",
    "validate_revision_shape",
]
