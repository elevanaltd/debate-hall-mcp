"""Path-contract schema and append-only typed wrappers (RFC-0001 §3.1).

This module is intentionally type-only: it defines the data shapes Wind, Wall,
and Door exchange via a path's contract, plus minimal JSON (de)serialisation
helpers and a prompt-context view helper used by #198/#199/#200.

Scope per RFC-0001 #196:

* Schema (§3.1): ``Invariant = str`` (open set; Wall-discipline naming convention
  per Finding A), TypedDicts for ``PathFrame`` / ``InvariantVerdict`` /
  ``PathDiff`` / ``InvariantEntry``, and append-only ``FrameRevision`` /
  ``VerdictRevision`` / ``DiffRevision`` wrappers carrying Wind/Wall ownership
  ``Literal``s. Door is read-only and has no revision wrapper.
* Findings (§3.3): ``DiffRevision.divergence_marker`` (Finding D) and
  ``DiffRevision.synthesis_guidance`` (Finding E) as ``NotRequired`` slots.
  ``NO_NEW_DIVERGENCE`` may coexist with a non-empty ``disputed`` list.
* Helpers: ``new_path_contract``, ``path_contract_to_json`` /
  ``path_contract_from_json``, and ``prompt_context_view``.

Out of scope (deliberately not implemented here):

* Validator behaviour — REQUIRED CONTENT RULE, ownership enforcement, sentinel
  legality — belongs to #200.
* State persistence integration belongs to #197.
* Prompt edits belong to #198.
* Feature flag wiring belongs to #201 / #205.

Wall-discipline naming convention for ``Invariant``: lowercase ``snake_case``,
semantically distinct per orthogonal concern (e.g. ``spec_grammar_coherence``,
``sync_api_contract``). The type system does *not* enumerate them — Wall is
responsible for assigning distinct names per orthogonal verdict so that
``dict[Invariant, InvariantVerdict]`` keying preserves verdict nuance.
"""

import json
from datetime import datetime
from typing import Any, Literal

# NOTE: ``TypedDict`` / ``NotRequired`` are imported from ``typing_extensions``
# (not ``typing``) because Pydantic 2 on Python < 3.12 requires the
# ``typing_extensions`` variant for runtime introspection — see the longer
# comment block below for the full rationale.
from typing_extensions import NotRequired, TypedDict  # noqa: UP035

# NOTE: ``from __future__ import annotations`` is intentionally NOT used.
# Under PEP 563 stringification, the runtime ``TypedDict`` machinery in
# CPython 3.11 fails to detect ``NotRequired[...]`` wrappers and folds the
# fields into ``__required_keys__``. The schema's ``NotRequired`` slots
# (``terminal_rationale``, ``new_possibility``, ``divergence_marker``,
# ``synthesis_guidance``) are load-bearing for the validator in #200, so we
# evaluate annotations eagerly here.
#
# NOTE: ``TypedDict`` and ``NotRequired`` are imported from ``typing_extensions``
# (not ``typing``) because Pydantic 2 on Python < 3.12 requires the
# ``typing_extensions`` variant for runtime introspection — ``TypeAdapter(...)``
# raises ``PydanticUserError`` (see https://errors.pydantic.dev/2.12/u/typed-dict-version)
# when given a ``typing.TypedDict``. This module's TypedDicts are consumed by
# #197 state serialisation via Pydantic, so the source must be ``typing_extensions``.

# ---------------------------------------------------------------------------
# Open-set invariant name (RFC §3.1 / §3.3 Finding A).
# ---------------------------------------------------------------------------

Invariant = str
"""Free-text invariant identifier (Wall-discipline naming convention).

Closed-enum ``HardInvariant`` was superseded by the amended RFC (Finding A) —
real Wall verdicts are topic-shaped, not protocol-shaped, so the type is an
open set. Wall is responsible for assigning distinct ``snake_case`` names per
orthogonal concern so the ``dict[Invariant, InvariantVerdict]`` keying in
``VerdictRevision.value`` preserves verdict nuance.
"""


# ---------------------------------------------------------------------------
# Per-path frame, verdict, and diff payloads (RFC §3.1).
# ---------------------------------------------------------------------------


class PathFrame(TypedDict):
    """Wind's framing of a single path (rev 0 written turn 1)."""

    assumed_problem: str
    success_criterion: str
    accepted_failure_mode: str
    invariants_touched: list[Invariant]


class InvariantVerdict(TypedDict):
    """Wall's verdict on one invariant.

    ``HARD_pass`` / ``HARD_fail`` are non-negotiable; ``SOFT_disputed`` is
    tradeable and Wind may push back on it in a subsequent diff.
    """

    status: Literal["HARD_pass", "HARD_fail", "SOFT_disputed"]
    rationale: str


class InvariantEntry(TypedDict):
    """Wind's per-invariant entry inside a ``PathDiff`` bucket.

    ``terminal_rationale`` is required on ``accepted`` items where the verdict
    was ``HARD_fail`` and no creative reframe is possible (validator-enforced
    in #200; here it is ``NotRequired`` because the same dict-shape is reused
    for ``disputed`` and ``reframed`` buckets that do not need it).

    ``new_possibility`` is required on ``reframed`` items — the
    catalyst-opened possibility this constraint reveals.
    """

    invariant: Invariant
    rationale: str
    terminal_rationale: NotRequired[str]
    new_possibility: NotRequired[str]


class PathDiff(TypedDict):
    """Wind's consensus-turn diff against Wall's latest verdict revision."""

    accepted: list[InvariantEntry]
    disputed: list[InvariantEntry]
    reframed: list[InvariantEntry]


# ---------------------------------------------------------------------------
# Append-only revision wrappers (RFC §3.1).
#
# Ownership ``Literal``s carry the role discipline at the type level so the
# runtime validator in #200 can reject a write from a non-owning role.
# Door is read-only — there is intentionally no ``DoorRevision``.
# ---------------------------------------------------------------------------


class FrameRevision(TypedDict):
    """Append-only frame revision; only Wind may write."""

    rev: int
    written_at: datetime
    written_by: Literal["Wind"]
    value: PathFrame


class VerdictRevision(TypedDict):
    """Append-only verdict revision; only Wall may write."""

    rev: int
    written_at: datetime
    written_by: Literal["Wall"]
    value: dict[Invariant, InvariantVerdict]


class DiffRevision(TypedDict):
    """Append-only consensus-phase diff; only Wind may write.

    ``divergence_marker`` (Finding D) is a sentinel for paths where Wind has
    no new catalyst content to add. It is legal only when every invariant
    verdict for the path is ``HARD_pass`` or ``SOFT_disputed``; the sentinel
    *may* coexist with a non-empty ``value.disputed`` list when Wind has
    legitimate pushback on ``SOFT_disputed`` verdicts.

    ``synthesis_guidance`` (Finding E) is free-text cross-path / synthesis-level
    insight that does not fit any per-path entry. Door's citation rule (§5.4)
    requires explicit citation when present. Both fields are validator-checked
    in #200; here they are merely typed.
    """

    rev: int
    written_at: datetime
    written_by: Literal["Wind"]
    value: PathDiff
    divergence_marker: NotRequired[Literal["NO_NEW_DIVERGENCE"]]
    synthesis_guidance: NotRequired[str]


# ---------------------------------------------------------------------------
# Top-level container (RFC §3.1).
# ---------------------------------------------------------------------------


class PathContract(TypedDict):
    """Per-path append-only contract: identity plus three revision histories."""

    path_id: str
    frame_history: list[FrameRevision]
    verdict_history: list[VerdictRevision]
    diff_history: list[DiffRevision]


# ---------------------------------------------------------------------------
# Constructor / factory helper.
# ---------------------------------------------------------------------------


def new_path_contract(path_id: str) -> PathContract:
    """Return an empty, valid ``PathContract`` for ``path_id``.

    Histories default to empty lists so existing call sites that read the
    contract before Wind writes rev 0 do not crash.
    """
    return PathContract(
        path_id=path_id,
        frame_history=[],
        verdict_history=[],
        diff_history=[],
    )


# ---------------------------------------------------------------------------
# JSON (de)serialisation helpers.
#
# Storage layer (#197) needs a stable wire format; the round-trip must
# preserve absence of ``NotRequired`` keys (do not coerce missing keys to
# ``None``). ``datetime`` objects are serialised as ISO-8601 strings and
# restored on read.
# ---------------------------------------------------------------------------


def _encode(obj: Any) -> Any:
    """Recursively convert ``datetime`` instances to ISO-8601 strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode(item) for item in obj]
    return obj


def _decode_revision(rev: dict[str, Any]) -> dict[str, Any]:
    """Restore the ``written_at`` ISO string on a revision dict to a datetime."""
    if "written_at" in rev and isinstance(rev["written_at"], str):
        rev["written_at"] = datetime.fromisoformat(rev["written_at"])
    return rev


def path_contract_to_json(contract: PathContract) -> str:
    """Serialise a ``PathContract`` to a JSON string.

    ``datetime`` objects are encoded as ISO-8601. ``NotRequired`` keys that
    are absent on the input remain absent in the output.
    """
    return json.dumps(_encode(contract))


def path_contract_from_json(payload: str) -> PathContract:
    """Deserialise the JSON produced by :func:`path_contract_to_json`.

    Restores ``datetime`` instances on every revision in every history. Keys
    that were absent on the source object remain absent on the result.

    BOUNDARY (deliberate non-validation):

    This function performs JSON deserialisation and ``datetime`` conversion
    ONLY. It does NOT validate the structural correctness of the resulting
    ``PathContract``. Specifically, it does NOT check that:

    * ``frame_history`` / ``verdict_history`` / ``diff_history`` are lists,
    * revisions are monotonically ordered by ``rev``,
    * ``written_by`` respects the ownership ``Literal`` for the revision kind
      (``Wind`` for frame/diff, ``Wall`` for verdict),
    * ``status`` values inside ``InvariantVerdict`` are members of the closed
      ``Literal["HARD_pass", "HARD_fail", "SOFT_disputed"]``,
    * the ``NO_NEW_DIVERGENCE`` sentinel co-occurs only with legal verdict
      states (see RFC-0001 §3.3 Finding D), or
    * ``terminal_rationale`` / ``new_possibility`` are present where
      ``InvariantEntry`` semantics require them.

    Per RFC-0001 §6, all such schema-shape violations are enforced as
    ``VALIDATOR_FAILURE`` events by the orchestrator validator (#200), not
    here. The same separation-of-concerns rationale that keeps
    ``from __future__ import annotations`` out of this module (see the
    module-level note above) keeps validation logic out as well: this module
    is the wire-format I/O boundary; #200 is the policy boundary.

    Callers MUST NOT treat the return value as a validated contract — it is
    structurally typed for the type checker but is not runtime-checked. Pass
    the result through the #200 validator before relying on any invariant
    that is not encoded in the JSON wire format itself (i.e. anything beyond
    "this parsed as JSON and any ``written_at`` strings decoded as ISO-8601
    datetimes").
    """
    raw: dict[str, Any] = json.loads(payload)
    for key in ("frame_history", "verdict_history", "diff_history"):
        history = raw.get(key, [])
        for rev in history:
            _decode_revision(rev)
    return raw  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Prompt-context view helper.
#
# Per RFC §3.1: each role sees the *latest* revision per field plus the
# revision count (so the agent knows "this is Wall's Nth verdict, after
# Wind's reframe"). Full history is stored but not blasted into every prompt
# (token discipline). #199 owns the integration into the orchestrator's
# prompt context block; this helper provides the contract's view-shape.
# ---------------------------------------------------------------------------


class PromptContextView(TypedDict):
    """Latest-revision-only view of a ``PathContract`` for prompt context."""

    path_id: str
    latest_frame: FrameRevision | None
    latest_verdict: VerdictRevision | None
    latest_diff: DiffRevision | None
    frame_count: int
    verdict_count: int
    diff_count: int


def prompt_context_view(contract: PathContract) -> PromptContextView:
    """Project a ``PathContract`` to its prompt-context view.

    Empty histories are handled safely: ``latest_*`` are ``None`` and the
    corresponding ``*_count`` is ``0``.
    """
    frame_history = contract["frame_history"]
    verdict_history = contract["verdict_history"]
    diff_history = contract["diff_history"]
    return PromptContextView(
        path_id=contract["path_id"],
        latest_frame=frame_history[-1] if frame_history else None,
        latest_verdict=verdict_history[-1] if verdict_history else None,
        latest_diff=diff_history[-1] if diff_history else None,
        frame_count=len(frame_history),
        verdict_count=len(verdict_history),
        diff_count=len(diff_history),
    )


__all__ = [
    "DiffRevision",
    "FrameRevision",
    "Invariant",
    "InvariantEntry",
    "InvariantVerdict",
    "PathContract",
    "PathDiff",
    "PathFrame",
    "PromptContextView",
    "VerdictRevision",
    "new_path_contract",
    "path_contract_from_json",
    "path_contract_to_json",
    "prompt_context_view",
]
