"""RED tests for RFC-0001 #201 — path_contract_enabled flag wiring (RFC §6 / §11.2 row 6).

Covers three concerns:

1. **TierSettings field**: ``path_contract_enabled`` is declared on
   ``TierSettings`` with ``default=False``. Until #201 lands, the field
   does not exist and these tests fail with ``AttributeError``.

2. **Orchestrator gating (off-mode byte-identity)**: With the flag
   ``False``, ``DebateOrchestrator._format_debate_state`` MUST NOT emit
   the ``<PATH_CONTRACTS>`` block nor ``SYNTHESIS_STATUS::`` — even when
   the in-memory ``path_contracts`` list is non-empty. This is the
   acceptance criterion called out by #202 (byte-identity to pre-#218).

3. **features.is_enabled hardening (CE carry-forward from #220 review)**:
   The wrapper MUST reject malformed contexts (``None`` settings,
   non-Pydantic settings, non-boolean flag value) by returning ``False``
   rather than coercing. This closes the "malformed settings silently
   disables/enables feature" hole flagged in #220 review.

TDD Discipline: RED ⇒ these tests fail on current ``main`` (no
``path_contract_enabled`` field; orchestrator emits ``<PATH_CONTRACTS>``
unconditionally on non-empty list; ``features.is_enabled`` does not
validate ``settings`` type).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp import features
from debate_hall_mcp.config import (
    RoleConfig,
    TierConfig,
    TierSettings,
)
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.path_contract import (
    FrameRevision,
    PathContract,
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
                "accepted_failure_mode": (
                    "email delivery latency may exceed 60s in adverse network conditions"
                ),
                "invariants_touched": ["halting", "single_wall_coherence"],
            },
        )
    )
    return contract


def _make_orchestrator(tmp_path: Path, *, path_contract_enabled: bool) -> DebateOrchestrator:
    settings = TierSettings(path_contract_enabled=path_contract_enabled)
    tier_config = TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=settings,
    )
    return DebateOrchestrator(tier_config, tmp_path)


def _base_state(*, path_contracts: list[PathContract]) -> dict[str, Any]:
    return {
        "thread_id": "test-thread",
        "topic": "test topic",
        "status": "ACTIVE",
        "turn_count": 1,
        "path_contracts": path_contracts,
    }


# ---------------------------------------------------------------------------
# 1. TierSettings field declaration (#201 scope)
# ---------------------------------------------------------------------------


class TestTierSettingsPathContractEnabledField:
    """``path_contract_enabled: bool = False`` is declared on TierSettings."""

    def test_default_is_false(self) -> None:
        settings = TierSettings()
        assert settings.path_contract_enabled is False

    def test_can_be_set_true(self) -> None:
        settings = TierSettings(path_contract_enabled=True)
        assert settings.path_contract_enabled is True

    def test_is_declared_on_model_schema(self) -> None:
        # Must be a real Pydantic field, not a runtime ``__dict__`` attribute.
        # Locks in the "single source of truth" intent — call sites route via
        # features.is_enabled(), and the field must exist on the schema so
        # mypy + the YAML loader recognise it.
        assert "path_contract_enabled" in TierSettings.model_fields
        field = TierSettings.model_fields["path_contract_enabled"]
        assert field.default is False
        assert field.annotation is bool


# ---------------------------------------------------------------------------
# 2. features.is_enabled wired into TierSettings field (no synthetic injection)
# ---------------------------------------------------------------------------


class TestIsEnabledReadsRealTierSettingsField:
    """Post-#201, ``features.is_enabled`` reads the real field, not an
    injected ``__dict__`` attribute (the #205 work used ``object.__setattr__``
    to simulate the future state — that workaround MUST become unnecessary).
    """

    def _ctx(self, path_contract_enabled: bool) -> features.FeatureContext:
        settings = TierSettings(path_contract_enabled=path_contract_enabled)
        role = RoleConfig(provider="cli", cli="claude")
        return {"tier_config": TierConfig(wind=role, wall=role, door=role, settings=settings)}

    def test_returns_true_when_field_true(self) -> None:
        assert features.is_enabled("path_contract", self._ctx(True)) is True

    def test_returns_false_when_field_false(self) -> None:
        assert features.is_enabled("path_contract", self._ctx(False)) is False

    def test_returns_false_by_default_for_default_tier_settings(self) -> None:
        # Default TierSettings() has path_contract_enabled=False, so the
        # wrapper must return False — this is the rollout-sequence step 1
        # ("Flag-off in main") invariant from the #201 issue body.
        role = RoleConfig(provider="cli", cli="claude")
        tier_config = TierConfig(wind=role, wall=role, door=role, settings=TierSettings())
        ctx: features.FeatureContext = {"tier_config": tier_config}
        assert features.is_enabled("path_contract", ctx) is False


# ---------------------------------------------------------------------------
# 3. CE hardening (carry-forward from #220 review)
# ---------------------------------------------------------------------------


class TestIsEnabledHardening:
    """``features.is_enabled`` validates ``context`` shape strictly.

    Per PROD::I2 (UNIVERSAL_OCTAVE_BINDING — semantic validity precedes
    processing): malformed settings ⇒ fail-safe-off, never silent coerce.
    Per PROD::I5 (SOVEREIGN_SAFETY_OVERRIDE): the off-mode default is the
    kill-switch, so any ambiguity resolves to False — not to a stack
    trace deep inside a downstream call site.
    """

    def test_settings_is_none_returns_false(self) -> None:
        # A bogus context where ``tier_config.settings`` is None must
        # fail-safe-off, not raise AttributeError downstream.
        class _FakeTier:
            settings = None

        ctx: features.FeatureContext = {"tier_config": _FakeTier()}  # type: ignore[typeddict-item]
        assert features.is_enabled("path_contract", ctx) is False

    def test_settings_is_dict_returns_false(self) -> None:
        # A dict masquerading as TierSettings must be rejected — Pydantic
        # normally enforces this at TierConfig construction, but the
        # wrapper is the chokepoint and must not assume the caller
        # constructed the context via Pydantic.
        class _FakeTier:
            settings = {"path_contract_enabled": True}

        ctx: features.FeatureContext = {"tier_config": _FakeTier()}  # type: ignore[typeddict-item]
        assert features.is_enabled("path_contract", ctx) is False

    def test_flag_value_non_bool_returns_false(self) -> None:
        # A truthy non-bool value (e.g. the string "true" from a
        # mis-typed YAML file that bypassed Pydantic) must NOT be
        # truthy-coerced. Strict bool-only.
        settings = TierSettings()
        # Inject a non-bool to simulate a malformed runtime mutation.
        object.__setattr__(settings, "path_contract_enabled", "true")
        role = RoleConfig(provider="cli", cli="claude")
        tier_config = TierConfig(wind=role, wall=role, door=role, settings=settings)
        ctx: features.FeatureContext = {"tier_config": tier_config}
        assert features.is_enabled("path_contract", ctx) is False

    def test_flag_value_integer_one_returns_false(self) -> None:
        # ``1`` is truthy in Python but is NOT bool — must be rejected.
        settings = TierSettings()
        object.__setattr__(settings, "path_contract_enabled", 1)
        role = RoleConfig(provider="cli", cli="claude")
        tier_config = TierConfig(wind=role, wall=role, door=role, settings=settings)
        ctx: features.FeatureContext = {"tier_config": tier_config}
        assert features.is_enabled("path_contract", ctx) is False


# ---------------------------------------------------------------------------
# 4. Orchestrator gating — off-mode byte-identity (#202 acceptance criterion)
# ---------------------------------------------------------------------------


class TestFormatDebateStateRespectsPathContractFlag:
    """``DebateOrchestrator._format_debate_state`` routes the
    ``<PATH_CONTRACTS>`` / ``SYNTHESIS_STATUS`` emission through
    ``features.is_enabled("path_contract", ...)``.

    Off-mode contract (flag=False): byte-identical to pre-#218 — no
    ``<PATH_CONTRACTS>`` block, no ``SYNTHESIS_STATUS::`` line — even
    when in-memory ``path_contracts`` is non-empty (defence in depth
    against state-leak through the rendering boundary).

    On-mode contract (flag=True): existing PR #218 joint emission
    contract holds — non-empty list ⇒ both ``<PATH_CONTRACTS>`` block
    and ``SYNTHESIS_STATUS::`` emitted.
    """

    def test_flag_off_omits_path_contracts_block_even_when_list_non_empty(
        self, tmp_path: Path
    ) -> None:
        orchestrator = _make_orchestrator(tmp_path, path_contract_enabled=False)
        state = _base_state(path_contracts=[_contract_frame_only("path_1")])

        result = orchestrator._format_debate_state(state)

        assert "<PATH_CONTRACTS>" not in result
        assert "</PATH_CONTRACTS>" not in result
        assert "SYNTHESIS_STATUS::" not in result

    def test_flag_off_byte_identical_to_empty_list_envelope(self, tmp_path: Path) -> None:
        # The whole point of off-mode: a debate that happens to have
        # accumulated path_contracts (e.g. left over from a treatment
        # build) MUST produce the same envelope as a fresh debate with
        # no contracts. This is the #202 acceptance criterion.
        orchestrator = _make_orchestrator(tmp_path, path_contract_enabled=False)
        with_contracts = orchestrator._format_debate_state(
            _base_state(path_contracts=[_contract_frame_only("path_1")])
        )
        without_contracts = orchestrator._format_debate_state(_base_state(path_contracts=[]))
        assert with_contracts == without_contracts

    def test_flag_on_emits_path_contracts_block_when_list_non_empty(self, tmp_path: Path) -> None:
        orchestrator = _make_orchestrator(tmp_path, path_contract_enabled=True)
        state = _base_state(path_contracts=[_contract_frame_only("path_1")])

        result = orchestrator._format_debate_state(state)

        assert "<PATH_CONTRACTS>" in result
        assert "</PATH_CONTRACTS>" in result
        assert "SYNTHESIS_STATUS::" in result

    def test_flag_on_with_empty_list_still_omits_block(self, tmp_path: Path) -> None:
        # The pre-existing #218 joint emission contract: empty list ⇒
        # no block, regardless of flag state. This guards against
        # accidentally emitting empty <PATH_CONTRACTS></PATH_CONTRACTS>
        # tags when the flag is on but no contracts exist yet.
        orchestrator = _make_orchestrator(tmp_path, path_contract_enabled=True)
        state = _base_state(path_contracts=[])

        result = orchestrator._format_debate_state(state)

        assert "<PATH_CONTRACTS>" not in result
        assert "SYNTHESIS_STATUS::" not in result


# ---------------------------------------------------------------------------
# 5. Direct attribute-read audit (single source of truth invariant)
# ---------------------------------------------------------------------------


class TestNoDirectAttributeReads:
    """Production code (under ``src/``) MUST NOT read
    ``tier_config.settings.path_contract_enabled`` directly. Every check
    routes through ``features.is_enabled()``. The wrapper itself is the
    only sanctioned reader.

    This test greps the installed package and fails if anything else
    references the attribute path.
    """

    def test_no_direct_reads_outside_features_module(self) -> None:
        import re
        from pathlib import Path as _Path

        src_root = _Path(__file__).resolve().parents[2] / "src" / "debate_hall_mcp"
        pattern = re.compile(r"\.path_contract_enabled\b")
        offenders: list[str] = []
        for py_file in src_root.rglob("*.py"):
            # features.py is the single sanctioned reader (via
            # ``getattr(settings, attr, ...)``); allow it.
            if py_file.name == "features.py":
                continue
            text = py_file.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    offenders.append(f"{py_file.relative_to(src_root)}:{line_no}: {line.strip()}")
        assert offenders == [], (
            "Direct `.path_contract_enabled` attribute reads found outside "
            "features.py. All call sites must route through "
            "features.is_enabled('path_contract', ctx):\n  " + "\n  ".join(offenders)
        )
