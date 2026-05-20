"""Feature-flag wrapper module (RFC-0001 #205, ADR-0003 migration shim).

Single entry point for all flag checks. Today delegates to ``TierSettings``;
when ADR-0003's Unified SDK lands, only the body of :func:`is_enabled` changes
— **call sites stay unchanged**. This is the "build aligned with ADR-0003 from
the outset" intent operationalized without the ~7-week cost of building the
full Stratified Layer architecture up front.

ADR-0003 migration path
-----------------------

Today (this module)::

    def is_enabled(flag_name, context):
        # Delegate to TierSettings.<flag>_enabled
        ...

Future (after ADR-0003 Phase 1)::

    def is_enabled(flag_name, context):
        # Route via Unified SDK to the correct Stratified Layer:
        #   Layer 1 (Entitlements)  -> JWT/session
        #   Layer 2 (Operational)   -> local cache via pub/sub
        #   Layer 3 (Experimentation) -> vendor SDK (LaunchDarkly/Unleash)
        return feature_sdk.is_enabled(flag_name, context)

The signature is forward-compatible: :class:`FeatureContext` already carries
``tier_config`` and is the natural slot for future ``tenant_id`` / ``user_id``
/ request-metadata fields the Unified SDK needs for Layer 1/3 resolution.

Refuse-to-degrade contract
--------------------------

Unknown flags raise :class:`KeyError`. This is deliberate (mirrors PROD::I5
SOVEREIGN_SAFETY_OVERRIDE and ADR-0003's auditability requirement): a
mistyped flag name must fail loudly at the call site rather than silently
return ``False`` and disable the safety check the caller meant to gate on.

Type system note (per #196 lesson)
----------------------------------

``TypedDict`` and ``Literal`` are imported from ``typing_extensions`` (not
``typing``). Under Pydantic 2 + Python 3.11, ``pydantic.TypeAdapter(...)``
requires the ``typing_extensions`` flavour for runtime introspection of
``TypedDict`` types; this matches the convention established in
``debate_hall_mcp.path_contract`` (#196).
"""

from __future__ import annotations

from typing_extensions import Literal, TypedDict  # noqa: UP035

from debate_hall_mcp.config import TierConfig

__all__ = [
    "FLAG_REGISTRY",
    "FeatureContext",
    "FlagSpec",
    "LifecyclePolicy",
    "is_enabled",
]


class LifecyclePolicy(TypedDict):
    """ADR-0003 §1 mandates this metadata on every flag.

    Fields:

    * ``layer``: Stratified Layer per ADR-0003 §1
      (1=entitlement, 2=operational, 3=experimentation).
    * ``owner``: Team or individual responsible for the flag's lifecycle.
    * ``sunset_date``: ISO date string; ``None`` = no planned removal.
    * ``classification``: ADR-0003 lifecycle classification used by the
      Auto-Decommissioning subsystem (ADR-0003 "Lifecycle Management").
    """

    layer: Literal["entitlement", "operational", "experimentation"]
    owner: str
    sunset_date: str | None
    classification: Literal["temporary_experiment", "permanent_toggle", "kill_switch"]


class FlagSpec(TypedDict):
    """Schema for a single registered feature flag.

    ADR-0003's future Policy Engine reads :data:`FLAG_REGISTRY` (a mapping of
    flag-name to :class:`FlagSpec`) to drive layer routing and lifecycle
    automation.
    """

    name: str
    description: str
    default: bool
    lifecycle: LifecyclePolicy


class FeatureContext(TypedDict):
    """Per-call context passed to :func:`is_enabled`.

    Today carries only ``tier_config``. Forward-compatible: future ADR-0003
    Unified SDK consumers will extend this with ``tenant_id`` / ``user_id``
    / request metadata for Layer 1 (entitlement) and Layer 3 (experimentation)
    resolution. Existing call sites need not change when those fields are added.
    """

    tier_config: TierConfig


FLAG_REGISTRY: dict[str, FlagSpec] = {
    "path_contract": {
        "name": "path_contract",
        "description": "Enable RFC-0001 path_contract Wind learning loop",
        "default": False,
        "lifecycle": {
            "layer": "experimentation",  # ADR-0003 Layer 3
            "owner": "debate-hall-mcp-core",
            "sunset_date": None,
            "classification": "temporary_experiment",
        },
    },
}


def is_enabled(flag_name: str, context: FeatureContext) -> bool:
    """Return whether ``flag_name`` is enabled in the given ``context``.

    Resolution (current implementation):

    1. ``flag_name`` MUST be registered in :data:`FLAG_REGISTRY`; unknown
       flags raise :class:`KeyError` (refuse-to-degrade).
    2. Look up ``context["tier_config"].settings.<flag_name>_enabled``; if
       present, return its boolean value.
    3. Otherwise, return :data:`FLAG_REGISTRY` ``[flag_name]["default"]``.

    Raises:
        KeyError: If ``flag_name`` is not registered in :data:`FLAG_REGISTRY`.
            The error message includes the flag name and the string
            ``FLAG_REGISTRY`` so the call site can locate the registration
            point quickly.
    """
    if flag_name not in FLAG_REGISTRY:
        raise KeyError(
            f"Unknown feature flag: {flag_name!r}. "
            f"Register it in FLAG_REGISTRY (debate_hall_mcp.features)."
        )
    settings = context["tier_config"].settings
    attr = f"{flag_name}_enabled"
    return bool(getattr(settings, attr, FLAG_REGISTRY[flag_name]["default"]))
