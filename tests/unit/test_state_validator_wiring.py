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
