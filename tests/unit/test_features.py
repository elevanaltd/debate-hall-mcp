"""Unit tests for ``debate_hall_mcp.features`` (RFC-0001 #205).

Covers the ADR-0003 migration-shim wrapper:

* ``is_enabled(flag, ctx)`` returns ``True``/``False`` per
  ``TierSettings.<flag>_enabled`` when present.
* ``is_enabled(flag, ctx)`` returns the FLAG_REGISTRY default when the
  TierSettings attribute is missing (current main, pre-#201 state).
* ``is_enabled("undefined_flag", ctx)`` raises ``KeyError`` mentioning the
  flag name and FLAG_REGISTRY (NO silent ``False``; mirrors PROD::I5
  refuse-to-degrade invariant).
* ``FLAG_REGISTRY["path_contract"]`` carries ADR-0003 Layer 3 lifecycle
  metadata: ``layer="experimentation"``, ``classification="temporary_experiment"``,
  ``default=False``, ``owner="debate-hall-mcp-core"``, ``sunset_date=None``.
* Pydantic ``TypeAdapter(FlagSpec)`` validates a registry entry — forward-compat
  smoke test that mirrors the #196 ``typing_extensions.TypedDict`` lesson
  (Pydantic 2 + Python 3.11 ``TypeAdapter`` requires ``typing_extensions``).
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from debate_hall_mcp import features
from debate_hall_mcp.config import (
    FallbackConfig,
    RoleConfig,
    TierConfig,
    TierSettings,
)


def _make_tier_config(**settings_kwargs: object) -> TierConfig:
    """Build a minimal TierConfig with overridable TierSettings kwargs.

    Uses ``model_construct`` for settings so we can inject attributes (like
    ``path_contract_enabled``) that are NOT yet declared on TierSettings —
    this models the post-#201 world without requiring #201 to land first.
    """
    role = RoleConfig(provider="cli", cli="claude")
    base_settings = TierSettings(fallback=FallbackConfig())
    if settings_kwargs:
        # ``model_copy(update=...)`` would reject unknown fields; we use
        # ``__dict__`` mutation to simulate a future TierSettings carrying
        # ``<flag>_enabled`` attributes (#201's scope).
        for key, value in settings_kwargs.items():
            object.__setattr__(base_settings, key, value)
    return TierConfig(wind=role, wall=role, door=role, settings=base_settings)


# ---------------------------------------------------------------------------
# is_enabled() behaviour
# ---------------------------------------------------------------------------


def test_is_enabled_returns_true_when_tier_settings_attr_true() -> None:
    ctx: features.FeatureContext = {
        "tier_config": _make_tier_config(path_contract_enabled=True),
    }
    assert features.is_enabled("path_contract", ctx) is True


def test_is_enabled_returns_false_when_tier_settings_attr_false() -> None:
    ctx: features.FeatureContext = {
        "tier_config": _make_tier_config(path_contract_enabled=False),
    }
    assert features.is_enabled("path_contract", ctx) is False


def test_is_enabled_returns_registry_default_when_tier_settings_attr_missing() -> None:
    # On current main TierSettings has NO path_contract_enabled attribute
    # (added in #201). Wrapper must fall back to FLAG_REGISTRY default (False).
    ctx: features.FeatureContext = {"tier_config": _make_tier_config()}
    assert features.is_enabled("path_contract", ctx) is False
    assert features.FLAG_REGISTRY["path_contract"]["default"] is False


def test_is_enabled_unknown_flag_raises_keyerror_with_clear_message() -> None:
    ctx: features.FeatureContext = {"tier_config": _make_tier_config()}
    with pytest.raises(KeyError) as excinfo:
        features.is_enabled("undefined_flag", ctx)
    message = str(excinfo.value)
    assert "undefined_flag" in message
    assert "FLAG_REGISTRY" in message


# ---------------------------------------------------------------------------
# FLAG_REGISTRY / lifecycle metadata (ADR-0003 Layer 3)
# ---------------------------------------------------------------------------


def test_flag_registry_path_contract_has_adr_0003_layer3_metadata() -> None:
    spec = features.FLAG_REGISTRY["path_contract"]
    assert spec["name"] == "path_contract"
    assert spec["default"] is False
    lifecycle = spec["lifecycle"]
    assert lifecycle["layer"] == "experimentation"  # ADR-0003 Layer 3
    assert lifecycle["classification"] == "temporary_experiment"
    assert lifecycle["owner"] == "debate-hall-mcp-core"
    assert lifecycle["sunset_date"] is None


# ---------------------------------------------------------------------------
# Pydantic TypeAdapter smoke test (forward-compat per #196 lesson)
# ---------------------------------------------------------------------------


def test_flag_spec_validates_via_pydantic_typeadapter() -> None:
    adapter = TypeAdapter(features.FlagSpec)
    validated = adapter.validate_python(features.FLAG_REGISTRY["path_contract"])
    assert validated["name"] == "path_contract"
    assert validated["lifecycle"]["layer"] == "experimentation"


def test_lifecycle_policy_validates_via_pydantic_typeadapter() -> None:
    adapter = TypeAdapter(features.LifecyclePolicy)
    validated = adapter.validate_python(features.FLAG_REGISTRY["path_contract"]["lifecycle"])
    assert validated["layer"] == "experimentation"
    assert validated["classification"] == "temporary_experiment"
