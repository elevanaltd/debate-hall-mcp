"""Unit tests for ``debate_hall_mcp.path_contract`` (RFC-0001 #196).

Acceptance derived from the AMENDED RFC (2026-05-16) — specifically:

- §3.1 Schema: ``Invariant = str`` (open-set, Wall-discipline naming), TypedDicts
  ``PathFrame``, ``InvariantVerdict``, ``PathDiff``, ``InvariantEntry``.
- §3.1 Append-only wrappers: ``FrameRevision`` / ``VerdictRevision`` / ``DiffRevision``
  with ownership ``Literal``s (Wind / Wall / Wind respectively); Door is read-only.
- §3.1 ``DiffRevision`` carries ``divergence_marker`` (Finding D) **and**
  ``synthesis_guidance`` (Finding E) as ``NotRequired`` slots.
- §3.1 ``InvariantEntry`` carries ``terminal_rationale`` and ``new_possibility`` as
  ``NotRequired`` slots (semantic enforcement is #200's job; #196 defines the types
  that *enable* it).
- §3.1 ``PathContract`` exposes ``path_id`` plus three append-only history lists.
- Briefing: helper exposing the prompt-context view (latest revision + revision
  count per field, NOT full history) — signature must be present even if the
  implementation is minimal.

This PR explicitly does **not** implement validator behaviour (#200), prompt edits
(#198), state serialization (#197), feature flags (#201), or the features wrapper
(#205). Tests here cover *only* the type-level guarantees and JSON round-trip.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import get_args, get_type_hints

import pytest

# -- Module presence ---------------------------------------------------------


def test_module_importable() -> None:
    """The new module must be importable from the package root."""
    import debate_hall_mcp.path_contract  # noqa: F401


# -- Open-set Invariant alias (Finding A) ------------------------------------


def test_invariant_is_open_set_str_alias() -> None:
    """RFC §3.1 / §3.3 Finding A: ``Invariant`` MUST be ``str`` (open set).

    The previous closed-enum decision (RFC §8 row 1) was superseded
    2026-05-16. Wall is responsible for distinct snake_case names per
    orthogonal concern; the type system does not enumerate them.
    """
    from debate_hall_mcp.path_contract import Invariant

    # The alias resolves to the built-in ``str`` type (or is `str` itself).
    assert Invariant is str


# -- TypedDict required keys -------------------------------------------------


def test_path_frame_required_keys() -> None:
    """RFC §3.1: PathFrame required keys."""
    from debate_hall_mcp.path_contract import PathFrame

    required = set(PathFrame.__required_keys__)
    assert required == {
        "assumed_problem",
        "success_criterion",
        "accepted_failure_mode",
        "invariants_touched",
    }
    assert PathFrame.__optional_keys__ == frozenset()


def test_invariant_verdict_shape() -> None:
    """RFC §3.1: InvariantVerdict status Literal + rationale."""
    from debate_hall_mcp.path_contract import InvariantVerdict

    required = set(InvariantVerdict.__required_keys__)
    assert required == {"status", "rationale"}

    hints = get_type_hints(InvariantVerdict)
    status_args = set(get_args(hints["status"]))
    assert status_args == {"HARD_pass", "HARD_fail", "SOFT_disputed"}


def test_invariant_entry_required_and_optional_slots() -> None:
    """RFC §3.1: InvariantEntry has invariant+rationale required; terminal_rationale
    and new_possibility as NotRequired (semantic enforcement deferred to #200)."""
    from debate_hall_mcp.path_contract import InvariantEntry

    required = set(InvariantEntry.__required_keys__)
    optional = set(InvariantEntry.__optional_keys__)
    assert required == {"invariant", "rationale"}
    assert optional == {"terminal_rationale", "new_possibility"}


def test_path_diff_required_buckets() -> None:
    """RFC §3.1: PathDiff has three required bucket lists."""
    from debate_hall_mcp.path_contract import PathDiff

    required = set(PathDiff.__required_keys__)
    assert required == {"accepted", "disputed", "reframed"}


# -- Revision wrappers & ownership Literals ----------------------------------


def test_frame_revision_ownership_literal_wind() -> None:
    """RFC §3.1 ownership rule: FrameRevision.written_by MUST be Literal['Wind']."""
    from debate_hall_mcp.path_contract import FrameRevision

    required = set(FrameRevision.__required_keys__)
    assert required == {"rev", "written_at", "written_by", "value"}

    hints = get_type_hints(FrameRevision)
    assert get_args(hints["written_by"]) == ("Wind",)


def test_verdict_revision_ownership_literal_wall() -> None:
    """RFC §3.1 ownership rule: VerdictRevision.written_by MUST be Literal['Wall']."""
    from debate_hall_mcp.path_contract import VerdictRevision

    required = set(VerdictRevision.__required_keys__)
    assert required == {"rev", "written_at", "written_by", "value"}

    hints = get_type_hints(VerdictRevision)
    assert get_args(hints["written_by"]) == ("Wall",)


def test_diff_revision_ownership_literal_wind_and_optional_slots() -> None:
    """RFC §3.1: DiffRevision is Wind-owned (consensus phase). Optional slots:

    - ``divergence_marker`` (Finding D) — Literal[``NO_NEW_DIVERGENCE``].
    - ``synthesis_guidance`` (Finding E) — free-text cross-path insight.
    """
    from debate_hall_mcp.path_contract import DiffRevision

    required = set(DiffRevision.__required_keys__)
    optional = set(DiffRevision.__optional_keys__)
    assert required == {"rev", "written_at", "written_by", "value"}
    assert optional == {"divergence_marker", "synthesis_guidance"}

    hints = get_type_hints(DiffRevision)
    assert get_args(hints["written_by"]) == ("Wind",)
    assert get_args(hints["divergence_marker"]) == ("NO_NEW_DIVERGENCE",)


def test_door_has_no_revision_wrapper() -> None:
    """RFC §3.1: Door is read-only. There must be no DoorRevision class."""
    import debate_hall_mcp.path_contract as mod

    assert not hasattr(mod, "DoorRevision")


# -- PathContract container --------------------------------------------------


def test_path_contract_shape() -> None:
    """RFC §3.1: PathContract has path_id + three append-only history lists."""
    from debate_hall_mcp.path_contract import PathContract

    required = set(PathContract.__required_keys__)
    assert required == {
        "path_id",
        "frame_history",
        "verdict_history",
        "diff_history",
    }


def test_new_path_contract_defaults_to_empty_histories() -> None:
    """Briefing: 'Defaults are empty lists (don't crash existing code).'

    A constructor / factory helper must be exposed that returns an empty,
    valid PathContract for a given ``path_id``.
    """
    from debate_hall_mcp.path_contract import new_path_contract

    pc = new_path_contract("path_1")
    assert pc["path_id"] == "path_1"
    assert pc["frame_history"] == []
    assert pc["verdict_history"] == []
    assert pc["diff_history"] == []


# -- JSON round-trip ---------------------------------------------------------


def _make_populated_contract() -> dict[str, object]:
    """Build a richly-populated contract exercising every optional slot."""
    from debate_hall_mcp.path_contract import (
        DiffRevision,
        FrameRevision,
        PathContract,
        VerdictRevision,
    )

    ts = datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC)

    frame_rev: FrameRevision = {
        "rev": 0,
        "written_at": ts,
        "written_by": "Wind",
        "value": {
            "assumed_problem": "Wind cannot react to Wall's critique",
            "success_criterion": "Wind produces a diff that cites Wall verdicts",
            "accepted_failure_mode": "Token cost rises by <40%",
            "invariants_touched": ["spec_grammar_coherence", "sync_api_contract"],
        },
    }

    verdict_rev: VerdictRevision = {
        "rev": 0,
        "written_at": ts,
        "written_by": "Wall",
        "value": {
            "spec_grammar_coherence": {
                "status": "HARD_fail",
                "rationale": "Grammar violates §3.1 ownership rule.",
            },
            "sync_api_contract": {
                "status": "SOFT_disputed",
                "rationale": "Contract is debatable but tradeable.",
            },
        },
    }

    diff_rev: DiffRevision = {
        "rev": 0,
        "written_at": ts,
        "written_by": "Wind",
        "value": {
            "accepted": [],
            "disputed": [
                {
                    "invariant": "sync_api_contract",
                    "rationale": "Still pushing back on the SOFT verdict.",
                }
            ],
            "reframed": [
                {
                    "invariant": "spec_grammar_coherence",
                    "rationale": "Reframed via append-only wrappers.",
                    "new_possibility": "Ownership Literals make violation a type error.",
                }
            ],
        },
        # Finding D: sentinel coexists with non-empty disputed list.
        "divergence_marker": "NO_NEW_DIVERGENCE",
        # Finding E: cross-path emergent insight.
        "synthesis_guidance": "Path-1's reframe only works when merged with path-2.",
    }

    contract: PathContract = {
        "path_id": "path_1",
        "frame_history": [frame_rev],
        "verdict_history": [verdict_rev],
        "diff_history": [diff_rev],
    }
    return dict(contract)


def test_round_trip_json_serialization() -> None:
    """Briefing: 'All types JSON-serializable; include a round-trip test.'"""
    from debate_hall_mcp.path_contract import (
        path_contract_from_json,
        path_contract_to_json,
    )

    original = _make_populated_contract()
    encoded = path_contract_to_json(original)  # type: ignore[arg-type]

    # Must be a JSON string (not bytes/dict).
    assert isinstance(encoded, str)

    # Decode independently to confirm valid JSON.
    decoded_raw = json.loads(encoded)
    assert decoded_raw["path_id"] == "path_1"
    # datetimes serialized as ISO strings.
    assert isinstance(decoded_raw["frame_history"][0]["written_at"], str)

    # Round-trip via the helper restores Python-native datetimes.
    restored = path_contract_from_json(encoded)
    assert restored["path_id"] == original["path_id"]
    assert restored["frame_history"][0]["written_at"] == datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC)
    assert (
        restored["diff_history"][0]["divergence_marker"]  # type: ignore[typeddict-item]
        == "NO_NEW_DIVERGENCE"
    )
    assert (
        restored["diff_history"][0]["synthesis_guidance"]  # type: ignore[typeddict-item]
        == "Path-1's reframe only works when merged with path-2."
    )


def test_round_trip_preserves_optional_absence() -> None:
    """Optional NotRequired slots must remain absent (not coerced to None)."""
    from debate_hall_mcp.path_contract import (
        path_contract_from_json,
        path_contract_to_json,
    )

    pc = _make_populated_contract()
    # Strip the optional slots from the lone diff revision.
    diff = pc["diff_history"][0]  # type: ignore[index]
    diff.pop("divergence_marker", None)  # type: ignore[union-attr]
    diff.pop("synthesis_guidance", None)  # type: ignore[union-attr]

    restored = path_contract_from_json(path_contract_to_json(pc))  # type: ignore[arg-type]
    restored_diff = restored["diff_history"][0]
    assert "divergence_marker" not in restored_diff
    assert "synthesis_guidance" not in restored_diff


# -- Max-token-budget prompt-context view helper -----------------------------


def test_prompt_context_view_helper_signature() -> None:
    """Briefing: max-token-budget helper exposing latest revision + count per field.

    Spec the helper signature even if the implementation is minimal. #199 owns
    the integration into the orchestrator's prompt context block.
    """
    from debate_hall_mcp.path_contract import prompt_context_view

    pc = _make_populated_contract()
    view = prompt_context_view(pc)  # type: ignore[arg-type]

    # Latest revision per field, NOT full history.
    assert view["path_id"] == "path_1"
    assert view["latest_frame"] == pc["frame_history"][-1]  # type: ignore[index]
    assert view["latest_verdict"] == pc["verdict_history"][-1]  # type: ignore[index]
    assert view["latest_diff"] == pc["diff_history"][-1]  # type: ignore[index]

    # Revision counts so the agent knows "this is Wall's Nth verdict, after Wind's reframe".
    assert view["frame_count"] == 1
    assert view["verdict_count"] == 1
    assert view["diff_count"] == 1


def test_prompt_context_view_handles_empty_histories() -> None:
    """Empty contracts MUST NOT crash the view helper; latest_* are None."""
    from debate_hall_mcp.path_contract import new_path_contract, prompt_context_view

    pc = new_path_contract("path_2")
    view = prompt_context_view(pc)

    assert view["latest_frame"] is None
    assert view["latest_verdict"] is None
    assert view["latest_diff"] is None
    assert view["frame_count"] == 0
    assert view["verdict_count"] == 0
    assert view["diff_count"] == 0


# -- Sanity: out-of-scope guards --------------------------------------------


def test_no_closed_hard_invariant_enum_exported() -> None:
    """Finding A explicitly supersedes the closed enum. Guard against re-introduction."""
    import debate_hall_mcp.path_contract as mod

    # Common shapes the superseded design could resurrect under:
    for forbidden in ("HardInvariant", "HARD_INVARIANTS", "HardInvariantEnum"):
        assert not hasattr(
            mod, forbidden
        ), f"{forbidden} contradicts RFC §3.3 Finding A (open-set Invariant=str)."


def test_module_does_not_smuggle_validator_logic() -> None:
    """#196 defines types only; validator behaviour belongs to #200.

    The module must not expose anything that *executes* the per-invariant
    REQUIRED CONTENT RULE or the ownership rule — those are #200's job.
    """
    import debate_hall_mcp.path_contract as mod

    for forbidden in (
        "validate_required_content",
        "validate_ownership",
        "enforce_diff_required_content",
    ):
        assert not hasattr(
            mod, forbidden
        ), f"{forbidden} would conflate #196 with #200 (validator scope)."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
