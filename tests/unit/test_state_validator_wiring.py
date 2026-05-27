"""RED tests — wire ``path_contract_validator.validate_diff_revision`` into
``DebateRoom.append_diff_revision`` so every model-produced diff revision is
validate-before-persist (RFC-0001 §3.2 / §3.3 Finding C; CE's #219 boundary note).

Contract under test (validate-before-persist):
    1. When the feature flag is OFF (or no ``tier_config`` is supplied), the
       API is byte-identical to its pre-wiring behavior — validator is NOT
       invoked, append proceeds.
    2. When the feature flag is ON AND the validator returns no failures,
       ``append_diff_revision`` persists the diff (current behavior preserved).
    3. When the feature flag is ON AND the validator returns failures,
       ``append_diff_revision`` does NOT persist the diff — failures are
       propagated as ``PathContractValidationError`` and ``VALIDATOR_FAILURE``
       events are appended to the ledger (per #217 contract, RFC §6 item 3).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.path_contract import PathDiff
from debate_hall_mcp.path_contract_validator import (
    MISSING_REQUIRED_ENTRY,
    ValidatorFailure,
)
from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    PathContractValidationError,
)


def _ts(minute: int = 0) -> datetime:
    return datetime(2026, 5, 26, 12, minute, 0, tzinfo=UTC)


def _empty_diff_value() -> PathDiff:
    return PathDiff(accepted=[], disputed=[], reframed=[])


def _role() -> RoleConfig:
    return RoleConfig(provider="cli", cli="claude")


def _tier_config(*, path_contract_enabled: bool) -> TierConfig:
    """Build a TierConfig with the path_contract flag in the desired state."""
    return TierConfig(
        wind=_role(),
        wall=_role(),
        door=_role(),
        settings=TierSettings(path_contract_enabled=path_contract_enabled),
    )


def _seed_hard_fail_verdict(room: DebateRoom, path_id: str, invariant: str) -> None:
    """Seed a HARD_fail verdict so the validator has a per-invariant requirement."""
    room.append_verdict_revision(
        path_id=path_id,
        written_at=_ts(0),
        value={invariant: {"status": "HARD_fail", "rationale": "fail"}},
    )


class TestOffModeByteIdentity:
    """When tier_config is None or flag is OFF, behavior is unchanged."""

    def test_no_tier_config_skips_validation(self) -> None:
        """No ``tier_config`` kwarg → no validator call, no events, append proceeds.

        This preserves byte-identity with the pre-wiring API for every legacy
        caller that doesn't yet opt in.
        """
        room = DebateRoom(
            thread_id="2026-05-26-off-mode-no-cfg",
            topic="off-mode no cfg",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")

        with patch(
            "debate_hall_mcp.path_contract_validator.validate_diff_revision"
        ) as mock_validate:
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),  # would fail REQUIRED CONTENT if validated
            )

        mock_validate.assert_not_called()
        assert len(room.path_contracts[0]["diff_history"]) == 1

    def test_flag_off_skips_validation(self, tmp_path: Path) -> None:
        """Flag explicitly OFF → no validator call, append proceeds."""
        room = DebateRoom(
            thread_id="2026-05-26-off-mode-flag-off",
            topic="off-mode flag off",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")

        with patch(
            "debate_hall_mcp.path_contract_validator.validate_diff_revision"
        ) as mock_validate:
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=False),
                state_dir=tmp_path,
            )

        mock_validate.assert_not_called()
        assert len(room.path_contracts[0]["diff_history"]) == 1


class TestOnModeValidationProceeds:
    """When flag is ON and validator returns no failures, the diff persists."""

    def test_valid_diff_persists(self, tmp_path: Path) -> None:
        """Validator returns no failures → append proceeds and persists."""
        room = DebateRoom(
            thread_id="2026-05-26-on-mode-valid",
            topic="on-mode valid diff",
            mode=DebateMode.FIXED,
        )
        # No HARD_fail verdicts → empty diff satisfies REQUIRED CONTENT RULE.
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(1),
            value=_empty_diff_value(),
            tier_config=_tier_config(path_contract_enabled=True),
            state_dir=tmp_path,
        )
        assert len(room.path_contracts[0]["diff_history"]) == 1


class TestOnModeRejectionSemantics:
    """When flag is ON and validator returns failures, the diff is REJECTED."""

    def test_failures_raise_and_skip_persist(self, tmp_path: Path) -> None:
        """Validator failure → PathContractValidationError raised; no append.

        Reject semantics: PROD::I4 (VERIFIABLE_EVENT_LEDGER) forbids
        rewriting history, so an invalid diff must be blocked BEFORE it
        reaches the append-only list.
        """
        room = DebateRoom(
            thread_id="2026-05-26-on-mode-reject",
            topic="on-mode reject",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")
        # Empty diff fails REQUIRED CONTENT RULE: HARD_fail invariant 'inv_a'
        # has no qualifying entry in accepted/reframed.
        with pytest.raises(PathContractValidationError) as exc_info:
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=True),
                state_dir=tmp_path,
            )

        # Failures attached to the exception with stable failure_type discriminator.
        failures: list[ValidatorFailure] = exc_info.value.failures
        assert any(f.failure_type == MISSING_REQUIRED_ENTRY for f in failures), failures
        # Diff was NOT persisted.
        assert room.path_contracts[0]["diff_history"] == []

    def test_failures_emit_validator_failure_events(self, tmp_path: Path) -> None:
        """Validator rejection → VALIDATOR_FAILURE events appended to the ledger.

        Per RFC §6 item 3 and the #217 contract, every rejection is an
        auditable event on the I4 ledger — never silently dropped.
        """
        room = DebateRoom(
            thread_id="2026-05-26-on-mode-events",
            topic="on-mode events emitted",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")

        with pytest.raises(PathContractValidationError):
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=True),
                state_dir=tmp_path,
            )

        # The events file for this thread must contain at least one
        # VALIDATOR_FAILURE entry carrying the discriminator on the payload.
        events_file = tmp_path / f"{room.thread_id}.events.jsonl"
        assert events_file.exists(), f"events file missing at {events_file}"
        content = events_file.read_text(encoding="utf-8")
        assert "validator_failure" in content
        assert MISSING_REQUIRED_ENTRY in content


class TestAsymmetricKwargsRejected:
    """When ``tier_config`` is supplied, ``state_dir`` MUST also be supplied.

    Rationale (CRS #1 / cubic P2 on PR #224 follow-up): audit completeness is
    a structural invariant, not a transport-conditional convenience. If
    validation runs, every rejection MUST be capable of emitting a
    ``VALIDATOR_FAILURE`` event on the I4 ledger (PROD::I4). Allowing
    ``tier_config`` without ``state_dir`` creates a silent-audit-drop branch
    on rejection. We collapse that branch at the API boundary by raising at
    function entry instead of inside the post-validation path.
    """

    def test_tier_config_without_state_dir_raises_typeerror(self) -> None:
        """``tier_config`` without ``state_dir`` is an asymmetric kwarg combo.

        The function must raise ``TypeError`` at entry (before any contract
        mutation, before any validator dispatch) so the caller cannot
        accidentally request validation while denying the ledger its audit
        surface.
        """
        room = DebateRoom(
            thread_id="2026-05-26-asymmetric-kwargs",
            topic="asymmetric kwargs rejected",
            mode=DebateMode.FIXED,
        )

        with pytest.raises(TypeError, match=r"state_dir.*required.*tier_config"):
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=True),
                # state_dir intentionally omitted
            )

    def test_tier_config_without_state_dir_raises_even_when_flag_off(self) -> None:
        """The asymmetric-kwargs check fires BEFORE the flag check.

        The contract is a static API shape — ``tier_config`` + missing
        ``state_dir`` is invalid regardless of the runtime flag value.
        Deferring the check until after the flag resolves would leave a
        latent bug that only surfaces when the flag flips on.
        """
        room = DebateRoom(
            thread_id="2026-05-26-asymmetric-flag-off",
            topic="asymmetric kwargs with flag off",
            mode=DebateMode.FIXED,
        )

        with pytest.raises(TypeError, match=r"state_dir.*required.*tier_config"):
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=False),
                # state_dir intentionally omitted
            )

    def test_no_tier_config_no_state_dir_still_works(self) -> None:
        """Off-mode (no ``tier_config``) is the only path that may omit ``state_dir``.

        Preserves byte-identity with legacy callers that never opted in.
        """
        room = DebateRoom(
            thread_id="2026-05-26-off-mode-no-state-dir",
            topic="off-mode legacy",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")

        # No raise, no validation, append proceeds.
        room.append_diff_revision(
            path_id="p1",
            written_at=_ts(1),
            value=_empty_diff_value(),
        )
        assert len(room.path_contracts[0]["diff_history"]) == 1


class TestValidationErrorFailuresTyped:
    """The ``failures`` attribute on ``PathContractValidationError`` carries
    concrete ``ValidatorFailure`` instances, not ``Any``.

    CRS #2 / cubic P2: ``list[Any]`` erasure was a workaround for the
    state→validator→events→state cycle. With the cycle broken, the type
    can be concrete and the workaround removed.
    """

    def test_failures_are_validator_failure_instances(self, tmp_path: Path) -> None:
        """Every element of ``failures`` is a ``ValidatorFailure`` dataclass."""
        room = DebateRoom(
            thread_id="2026-05-26-typed-failures",
            topic="typed failures",
            mode=DebateMode.FIXED,
        )
        _seed_hard_fail_verdict(room, "p1", "inv_a")

        with pytest.raises(PathContractValidationError) as exc_info:
            room.append_diff_revision(
                path_id="p1",
                written_at=_ts(1),
                value=_empty_diff_value(),
                tier_config=_tier_config(path_contract_enabled=True),
                state_dir=tmp_path,
            )

        for failure in exc_info.value.failures:
            assert isinstance(
                failure, ValidatorFailure
            ), f"failures must be ValidatorFailure instances, got {type(failure)}"


class TestCycleBrokenNoLazyImports:
    """The state→validator→events→state cycle is broken at the root.

    CRS #2: ``_validate_thread_id_for_filesystem`` was extracted out of
    ``state.py`` so ``events.py`` can import it without going through
    ``state.py``. Once the cycle is broken, the lazy imports inside
    ``append_diff_revision`` are unnecessary and removed.
    """

    def test_thread_id_helper_lives_in_dedicated_module(self) -> None:
        """The helper is importable from its dedicated module.

        This is the structural proof that the cycle root has been
        relocated — if this import fails, the extraction never happened.
        """
        from debate_hall_mcp._thread_id import (  # noqa: PLC0415
            _validate_thread_id_for_filesystem,
        )

        # And it actually works.
        _validate_thread_id_for_filesystem("safe-thread-id")
        with pytest.raises(ValueError, match="path-unsafe"):
            _validate_thread_id_for_filesystem("../escape")

    def test_state_reexports_helper_for_backward_compatibility(self) -> None:
        """``state.py`` re-exports the helper so legacy imports keep working."""
        from debate_hall_mcp.state import (  # noqa: PLC0415
            _validate_thread_id_for_filesystem as state_helper,
        )
        from debate_hall_mcp._thread_id import (  # noqa: PLC0415
            _validate_thread_id_for_filesystem as canonical_helper,
        )

        assert state_helper is canonical_helper

    def test_events_imports_helper_from_dedicated_module(self) -> None:
        """``events.py`` imports the helper from ``_thread_id``, not ``state``.

        Structural assertion: the source of ``events.py`` does NOT contain
        ``from debate_hall_mcp.state import _validate_thread_id_for_filesystem``;
        it imports from the new dedicated module instead. This is the
        observable proof that the cycle is broken at the source.
        """
        import inspect  # noqa: PLC0415

        from debate_hall_mcp import events  # noqa: PLC0415

        source = inspect.getsource(events)
        assert (
            "from debate_hall_mcp.state import _validate_thread_id_for_filesystem" not in source
        ), "events.py must NOT import _validate_thread_id_for_filesystem from state"
        assert (
            "from debate_hall_mcp._thread_id import _validate_thread_id_for_filesystem" in source
        ), "events.py must import _validate_thread_id_for_filesystem from _thread_id"

    def test_append_diff_revision_has_no_lazy_validator_imports(self) -> None:
        """With the cycle broken, the function body no longer needs lazy imports.

        Structural assertion on the source of ``DebateRoom.append_diff_revision``:
        ``from debate_hall_mcp.path_contract_validator import`` should NOT
        appear inside the function body — it must live at module top.
        """
        import inspect  # noqa: PLC0415

        from debate_hall_mcp.state import DebateRoom  # noqa: PLC0415

        body = inspect.getsource(DebateRoom.append_diff_revision)
        assert "from debate_hall_mcp.path_contract_validator import" not in body, (
            "append_diff_revision must NOT contain lazy validator imports; "
            "the cycle is broken so the imports belong at module top."
        )
        assert "from debate_hall_mcp import features" not in body, (
            "append_diff_revision must NOT contain a lazy features import; "
            "import at module top now that the cycle is gone."
        )
