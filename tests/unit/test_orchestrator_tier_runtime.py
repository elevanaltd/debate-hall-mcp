"""Tier settings must be honoured at runtime by DebateOrchestrator.

Regression tests for three defects where the tier YAML declared behaviour the
runtime did not implement (blocking PR #233):

1. settings.fallback was never executed. A primary provider failure on a role
   turn or consensus vote paused the debate instead of retrying once on the
   configured fallback model.
2. Timeout precedence was wrong. RoleConfig.timeout / fallback.timeout were
   not consulted, and OpenRouter used a hard-coded 120s read timeout.
3. settings.max_turns never reached debate_init, so the room default applied.

Fallback contract under test:
- Only transport/provider failures (provider API errors, timeouts) trigger it.
- Exactly ONE fallback attempt per failed call (I3: finite closure, no loop).
- The role's prompts are unchanged; only the model changes.
- Fallback use is recorded in the transcript and event ledger (I4).
- If the fallback also fails, the debate is PAUSED (today's behaviour).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from debate_hall_mcp.config import (
    FallbackConfig,
    RoleConfig,
    TierConfig,
    TierSettings,
    _load_tiers_from_yaml,
)
from debate_hall_mcp.events import EventType, load_events
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import ProviderResponse
from debate_hall_mcp.providers.cli import CliProviderError
from debate_hall_mcp.providers.openrouter import OpenRouterApiError
from debate_hall_mcp.state import DebateStatus, load_debate_state

REPO_ROOT = Path(__file__).resolve().parents[2]

PRIMARY_MODELS = {
    "Wind": "primary/wind-model",
    "Wall": "primary/wall-model",
    "Door": "primary/door-model",
}
FALLBACK_MODEL = "fallback/rescue-model"
MODEL_NOT_FOUND = OpenRouterApiError("OpenRouter API error: 404 - model not found")


def _response(content: str, model: str) -> ProviderResponse:
    return ProviderResponse(content=content, model=model, token_input=10, token_output=20)


def _tier_config(
    *,
    fallback_enabled: bool = True,
    consensus_required: bool = False,
    max_turns: int = 12,
    provider_timeout: int = 300,
    role_timeouts: dict[str, int | None] | None = None,
    fallback_timeout: int = 60,
    max_refinement_loops: int = 3,
) -> TierConfig:
    role_timeouts = role_timeouts or {}
    return TierConfig(
        wind=RoleConfig(
            provider="openrouter",
            model=PRIMARY_MODELS["Wind"],
            role="wind-agent",
            timeout=role_timeouts.get("Wind"),
        ),
        wall=RoleConfig(
            provider="openrouter",
            model=PRIMARY_MODELS["Wall"],
            role="wall-agent",
            timeout=role_timeouts.get("Wall"),
        ),
        door=RoleConfig(
            provider="openrouter",
            model=PRIMARY_MODELS["Door"],
            role="door-agent",
            timeout=role_timeouts.get("Door"),
        ),
        settings=TierSettings(
            consensus_required=consensus_required,
            max_turns=max_turns,
            max_refinement_loops=max_refinement_loops,
            provider_timeout=provider_timeout,
            fallback=FallbackConfig(
                enabled=fallback_enabled,
                provider="openrouter",
                model=FALLBACK_MODEL,
                timeout=fallback_timeout,
            ),
        ),
    )


class RoutingFactory:
    """Provider factory that routes by model and records every RoleConfig it sees.

    - One AsyncMock per primary role model (Wind/Wall/Door).
    - One AsyncMock for the fallback model.
    """

    def __init__(self) -> None:
        self.primary: dict[str, AsyncMock] = {}
        for role, model in PRIMARY_MODELS.items():
            mock = AsyncMock()
            mock.complete.return_value = _response(f"{role} primary content", model)
            self.primary[role] = mock
        self.fallback = AsyncMock()
        self.fallback.complete.return_value = _response("fallback content", FALLBACK_MODEL)
        self.configs: list[RoleConfig] = []

    def __call__(self, role_config: RoleConfig) -> AsyncMock:
        self.configs.append(role_config)
        if role_config.model == FALLBACK_MODEL:
            return self.fallback
        for role, model in PRIMARY_MODELS.items():
            if role_config.model == model:
                return self.primary[role]
        raise AssertionError(f"Unexpected role config: {role_config}")

    def configs_for(self, model: str) -> list[RoleConfig]:
        return [c for c in self.configs if c.model == model]


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    d = tmp_path / "debates"
    d.mkdir()
    return d


def _turn_events(thread_id: str, state_dir: Path, role: str) -> list[Any]:
    return [
        e
        for e in load_events(thread_id, state_dir)
        if e.event_type == EventType.TURN_ADDED and e.payload.get("role") == role
    ]


def _vote_events(thread_id: str, state_dir: Path, role: str) -> list[Any]:
    return [
        e
        for e in load_events(thread_id, state_dir)
        if e.event_type == EventType.CONSENSUS_VOTE and e.payload.get("role") == role
    ]


# ---------------------------------------------------------------------------
# (a) Role turns: primary API error (e.g. 404 model-not-found) -> fallback
# ---------------------------------------------------------------------------


class TestRoleTurnFallback:
    @pytest.mark.anyio
    @pytest.mark.parametrize("failing_role", ["Wind", "Wall", "Door"])
    async def test_primary_api_error_invokes_fallback_and_records_model(
        self, failing_role: str, state_dir: Path
    ) -> None:
        thread_id = f"2026-09-26-fallback-turn-{failing_role.lower()}"
        factory = RoutingFactory()
        factory.primary[failing_role].complete.side_effect = MODEL_NOT_FOUND

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        result = await orchestrator.run(topic="Fallback test", thread_id=thread_id)

        assert result.status == "synthesis"

        # Exactly one fallback attempt, with the SAME prompts as the primary call
        assert factory.fallback.complete.await_count == 1
        primary_kwargs = factory.primary[failing_role].complete.await_args.kwargs
        fallback_kwargs = factory.fallback.complete.await_args.kwargs
        assert fallback_kwargs["system_prompt"] == primary_kwargs["system_prompt"]
        assert fallback_kwargs["user_prompt"] == primary_kwargs["user_prompt"]

        # Transcript records the fallback model on the turn (I4)
        room = load_debate_state(thread_id, state_dir)
        turn = next(t for t in room.turns if t.role == failing_role)
        assert turn.model == FALLBACK_MODEL
        assert turn.content == "fallback content"

        # Event ledger records which primary failed, why, and what replaced it (I4)
        events = _turn_events(thread_id, state_dir, failing_role)
        assert len(events) == 1
        record = events[0].payload["fallback"]
        assert record["primary_model"] == PRIMARY_MODELS[failing_role]
        assert record["failure"] == "provider_error"
        assert record["error_type"] == "OpenRouterApiError"
        assert record["fallback_model"] == FALLBACK_MODEL
        assert record["fallback_provider"] == "openrouter"

        # Roles that did not fail carry no fallback record
        for other in {"Wind", "Wall", "Door"} - {failing_role}:
            other_events = _turn_events(thread_id, state_dir, other)
            assert "fallback" not in other_events[0].payload

    @pytest.mark.anyio
    async def test_cli_provider_error_invokes_fallback(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-fallback-cli-error"
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = CliProviderError("claude exited 1")

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        result = await orchestrator.run(topic="CLI error", thread_id=thread_id)

        assert result.status == "synthesis"
        record = _turn_events(thread_id, state_dir, "Wind")[0].payload["fallback"]
        assert record["error_type"] == "CliProviderError"


# ---------------------------------------------------------------------------
# (b) Consensus votes: primary API error -> fallback
# ---------------------------------------------------------------------------


class TestConsensusVoteFallback:
    @pytest.mark.anyio
    @pytest.mark.parametrize("failing_role", ["Wind", "Wall"])
    async def test_vote_primary_api_error_invokes_fallback(
        self, failing_role: str, state_dir: Path
    ) -> None:
        thread_id = f"2026-09-26-fallback-vote-{failing_role.lower()}"
        factory = RoutingFactory()
        # Role turn succeeds on primary; the consensus vote fails on primary
        factory.primary["Wind"].complete.side_effect = [
            _response("wind turn", PRIMARY_MODELS["Wind"]),
            _response("APPROVE", PRIMARY_MODELS["Wind"]),
        ]
        factory.primary["Wall"].complete.side_effect = [
            _response("wall turn", PRIMARY_MODELS["Wall"]),
            _response("APPROVE", PRIMARY_MODELS["Wall"]),
        ]
        factory.primary[failing_role].complete.side_effect = [
            _response(f"{failing_role} turn", PRIMARY_MODELS[failing_role]),
            MODEL_NOT_FOUND,
        ]
        factory.fallback.complete.return_value = _response("APPROVE", FALLBACK_MODEL)

        orchestrator = DebateOrchestrator(
            _tier_config(consensus_required=True), state_dir, provider_factory=factory
        )
        result = await orchestrator.run(topic="Vote fallback", thread_id=thread_id)

        assert result.status == "synthesis"
        assert factory.fallback.complete.await_count == 1

        votes = _vote_events(thread_id, state_dir, failing_role)
        assert len(votes) == 1
        assert votes[0].payload["approved"] is True
        record = votes[0].payload["fallback"]
        assert record["primary_model"] == PRIMARY_MODELS[failing_role]
        assert record["failure"] == "provider_error"
        assert record["error_type"] == "OpenRouterApiError"
        assert record["fallback_model"] == FALLBACK_MODEL

    @pytest.mark.anyio
    async def test_consensus_parse_failure_does_not_trigger_fallback(self, state_dir: Path) -> None:
        """Unparseable votes already fail safe to REJECT; they are not transport failures."""
        thread_id = "2026-09-26-no-fallback-on-parse"
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = [
            _response("wind turn", PRIMARY_MODELS["Wind"]),
        ] + [_response("gibberish with no verdict", PRIMARY_MODELS["Wind"])] * 10

        orchestrator = DebateOrchestrator(
            _tier_config(consensus_required=True), state_dir, provider_factory=factory
        )
        result = await orchestrator.run(topic="Parse failure", thread_id=thread_id)

        assert result.status == "stalemate"
        factory.fallback.complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# (c) Primary timeout -> fallback
# ---------------------------------------------------------------------------


class TestTimeoutFallback:
    @pytest.mark.anyio
    async def test_primary_timeout_triggers_fallback(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-fallback-timeout"
        factory = RoutingFactory()

        async def hang(*_args: Any, **_kwargs: Any) -> ProviderResponse:
            await asyncio.sleep(300)
            raise AssertionError("unreachable")

        factory.primary["Wall"].complete.side_effect = hang

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        with patch.object(orchestrator, "_get_provider_timeout", return_value=0.05):
            result = await orchestrator.run(topic="Timeout", thread_id=thread_id)

        assert result.status == "synthesis"
        assert factory.fallback.complete.await_count == 1
        record = _turn_events(thread_id, state_dir, "Wall")[0].payload["fallback"]
        assert record["failure"] == "timeout"
        assert record["error_type"] == "TimeoutError"


# ---------------------------------------------------------------------------
# (d) Fallback disabled -> today's PAUSED behaviour
# ---------------------------------------------------------------------------


class TestFallbackDisabled:
    @pytest.mark.anyio
    async def test_disabled_fallback_pauses_debate(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-fallback-disabled"
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = MODEL_NOT_FOUND

        orchestrator = DebateOrchestrator(
            _tier_config(fallback_enabled=False), state_dir, provider_factory=factory
        )
        with pytest.raises(OpenRouterApiError, match="404"):
            await orchestrator.run(topic="Disabled", thread_id=thread_id)

        assert load_debate_state(thread_id, state_dir).status == DebateStatus.PAUSED
        factory.fallback.complete.assert_not_awaited()
        assert factory.configs_for(FALLBACK_MODEL) == []

    @pytest.mark.anyio
    async def test_non_provider_error_does_not_trigger_fallback(self, state_dir: Path) -> None:
        """Programming errors are not transport failures and must surface unchanged."""
        thread_id = "2026-09-26-fallback-not-for-bugs"
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = ValueError("bug")

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        with pytest.raises(ValueError, match="bug"):
            await orchestrator.run(topic="Bug", thread_id=thread_id)

        factory.fallback.complete.assert_not_awaited()
        assert load_debate_state(thread_id, state_dir).status == DebateStatus.PAUSED


# ---------------------------------------------------------------------------
# (e) Fallback also fails -> PAUSED, exactly one fallback attempt (no loop)
# ---------------------------------------------------------------------------


class TestFallbackAlsoFails:
    @pytest.mark.anyio
    async def test_fallback_failure_pauses_after_single_attempt(self, state_dir: Path) -> None:
        from debate_hall_mcp.orchestrator import ProviderFallbackError

        thread_id = "2026-09-26-fallback-also-fails"
        factory = RoutingFactory()
        factory.primary["Door"].complete.side_effect = MODEL_NOT_FOUND
        factory.fallback.complete.side_effect = OpenRouterApiError(
            "OpenRouter API error: 503 - unavailable"
        )

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        with pytest.raises(ProviderFallbackError) as exc_info:
            await orchestrator.run(topic="Both fail", thread_id=thread_id)

        # Clear error naming both the primary and fallback failure
        message = str(exc_info.value)
        assert "Door" in message
        assert PRIMARY_MODELS["Door"] in message
        assert FALLBACK_MODEL in message
        assert isinstance(exc_info.value.__cause__, OpenRouterApiError)

        assert factory.primary["Door"].complete.await_count == 1
        assert factory.fallback.complete.await_count == 1
        assert load_debate_state(thread_id, state_dir).status == DebateStatus.PAUSED

        errors = [e for e in load_events(thread_id, state_dir) if e.event_type == EventType.ERROR]
        assert errors[-1].payload["error_type"] == "ProviderFallbackError"

    @pytest.mark.anyio
    async def test_fallback_timeout_pauses_after_single_attempt(self, state_dir: Path) -> None:
        from debate_hall_mcp.orchestrator import ProviderFallbackError

        thread_id = "2026-09-26-fallback-times-out"
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = MODEL_NOT_FOUND

        async def hang(*_args: Any, **_kwargs: Any) -> ProviderResponse:
            await asyncio.sleep(300)
            raise AssertionError("unreachable")

        factory.fallback.complete.side_effect = hang

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        with (
            patch.object(orchestrator, "_get_fallback_timeout", return_value=0.05),
            pytest.raises(ProviderFallbackError),
        ):
            await orchestrator.run(topic="Fallback hangs", thread_id=thread_id)

        assert factory.fallback.complete.await_count == 1
        assert load_debate_state(thread_id, state_dir).status == DebateStatus.PAUSED


# ---------------------------------------------------------------------------
# Speed and RACI role turns share the same fallback path
# ---------------------------------------------------------------------------


class TestFallbackOtherModes:
    @pytest.mark.anyio
    async def test_speed_role_turn_uses_fallback(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-fallback-speed"
        factory = RoutingFactory()
        factory.primary["Wall"].complete.side_effect = MODEL_NOT_FOUND

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        result = await orchestrator.run_speed(topic="Speed", thread_id=thread_id)

        assert result.status == "synthesis"
        room = load_debate_state(thread_id, state_dir)
        assert next(t for t in room.turns if t.role == "Wall").model == FALLBACK_MODEL
        record = _turn_events(thread_id, state_dir, "Wall")[0].payload["fallback"]
        assert record["primary_model"] == PRIMARY_MODELS["Wall"]

    @pytest.mark.anyio
    async def test_raci_role_turn_uses_fallback(self, state_dir: Path) -> None:
        from debate_hall_mcp.raci import RACIConfig

        thread_id = "2026-09-26-fallback-raci"
        factory = RoutingFactory()
        # RACI uses the Wind provider for every turn; fail only the first call
        factory.primary["Wind"].complete.side_effect = [MODEL_NOT_FOUND] + [
            _response("raci content", PRIMARY_MODELS["Wind"])
        ] * 10

        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)
        await orchestrator.run_raci(
            topic="RACI",
            raci_config=RACIConfig(responsible="architect", accountable="tech-lead"),
            thread_id=thread_id,
        )

        room = load_debate_state(thread_id, state_dir)
        assert room.turns[0].model == FALLBACK_MODEL
        assert factory.fallback.complete.await_count == 1


# ---------------------------------------------------------------------------
# (f) Timeout precedence
#     role-level RoleConfig.timeout > settings.provider_timeout;
#     fallback call uses settings.fallback.timeout.
# ---------------------------------------------------------------------------


class _WaitForRecorder:
    """Wrap asyncio.wait_for to record the timeout each provider call used."""

    def __init__(self) -> None:
        self.timeouts: list[float | None] = []
        self._real = asyncio.wait_for

    async def __call__(self, awaitable: Any, timeout: float | None) -> Any:
        self.timeouts.append(timeout)
        return await self._real(awaitable, timeout)


class TestTimeoutPrecedence:
    @pytest.mark.anyio
    async def test_role_timeout_overrides_provider_timeout(self, state_dir: Path) -> None:
        factory = RoutingFactory()
        config = _tier_config(provider_timeout=300, role_timeouts={"Wall": 45})
        recorder = _WaitForRecorder()

        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        with patch("debate_hall_mcp.orchestrator.asyncio.wait_for", recorder):
            await orchestrator.run(topic="Precedence", thread_id="2026-09-26-precedence")

        # Wind, Wall, Door in order: outer bound honours the role override
        assert recorder.timeouts == [300, 45, 300]

        # Providers are constructed with the effective timeout so the transport
        # layer (e.g. OpenRouter read timeout) honours the same value.
        assert factory.configs_for(PRIMARY_MODELS["Wind"])[0].timeout == 300
        assert factory.configs_for(PRIMARY_MODELS["Wall"])[0].timeout == 45
        assert factory.configs_for(PRIMARY_MODELS["Door"])[0].timeout == 300

    @pytest.mark.anyio
    async def test_fallback_call_uses_fallback_timeout(self, state_dir: Path) -> None:
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = MODEL_NOT_FOUND
        config = _tier_config(provider_timeout=300, fallback_timeout=42)
        recorder = _WaitForRecorder()

        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        with patch("debate_hall_mcp.orchestrator.asyncio.wait_for", recorder):
            await orchestrator.run(topic="Fallback timeout", thread_id="2026-09-26-fb-timeout")

        # Wind primary (300) -> Wind fallback (42) -> Wall (300) -> Door (300)
        assert recorder.timeouts == [300, 42, 300, 300]
        fallback_configs = factory.configs_for(FALLBACK_MODEL)
        assert len(fallback_configs) == 1
        assert fallback_configs[0].timeout == 42
        assert fallback_configs[0].provider == "openrouter"
        # Identity preserved: the fallback keeps the role's prompt identity
        assert fallback_configs[0].role == "wind-agent"


class TestOpenRouterEffectiveReadTimeout:
    def _capture_client_timeout(self) -> tuple[Any, list[Any]]:
        seen: list[Any] = []

        def client_factory(*_args: Any, **kwargs: Any) -> Any:
            seen.append(kwargs.get("timeout"))
            client = AsyncMock()
            response = AsyncMock()
            response.raise_for_status = lambda: None
            response.json = lambda: {
                "choices": [{"message": {"content": "ok"}}],
                "model": "m",
                "usage": {},
            }
            client.post = AsyncMock(return_value=response)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            return client

        return client_factory, seen

    @pytest.mark.anyio
    async def test_create_provider_passes_role_timeout_to_openrouter_read(self) -> None:
        from debate_hall_mcp.providers import create_provider

        provider = create_provider(RoleConfig(provider="openrouter", model="m", timeout=300))
        client_factory, seen = self._capture_client_timeout()
        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "k"}),
            patch("httpx.AsyncClient", side_effect=client_factory),
        ):
            await provider.complete(system_prompt="s", user_prompt="u")

        assert seen[0].read == 300

    @pytest.mark.anyio
    async def test_create_provider_timeout_override_reaches_openrouter_read(self) -> None:
        from debate_hall_mcp.providers import create_provider

        provider = create_provider(
            RoleConfig(provider="openrouter", model="m", timeout=300), timeout_override=77
        )
        client_factory, seen = self._capture_client_timeout()
        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "k"}),
            patch("httpx.AsyncClient", side_effect=client_factory),
        ):
            await provider.complete(system_prompt="s", user_prompt="u")

        assert seen[0].read == 77

    @pytest.mark.anyio
    async def test_openrouter_defaults_to_120_when_nothing_configured(self) -> None:
        from debate_hall_mcp.providers import create_provider

        provider = create_provider(RoleConfig(provider="openrouter", model="m"))
        client_factory, seen = self._capture_client_timeout()
        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "k"}),
            patch("httpx.AsyncClient", side_effect=client_factory),
        ):
            await provider.complete(system_prompt="s", user_prompt="u")

        assert seen[0].read == 120


# ---------------------------------------------------------------------------
# (g) settings.max_turns reaches debate_init
# ---------------------------------------------------------------------------


class TestMaxTurnsPropagation:
    @pytest.mark.anyio
    async def test_configured_max_turns_reaches_room(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-max-turns"
        factory = RoutingFactory()

        orchestrator = DebateOrchestrator(
            _tier_config(max_turns=7), state_dir, provider_factory=factory
        )
        await orchestrator.run(topic="Max turns", thread_id=thread_id)

        assert load_debate_state(thread_id, state_dir).max_turns == 7

    @pytest.mark.anyio
    async def test_configured_max_turns_passed_to_debate_init(self, state_dir: Path) -> None:
        factory = RoutingFactory()
        orchestrator = DebateOrchestrator(
            _tier_config(max_turns=9), state_dir, provider_factory=factory
        )

        from debate_hall_mcp.tools import init as init_module

        with patch(
            "debate_hall_mcp.orchestrator.debate_init", wraps=init_module.debate_init
        ) as spy:
            await orchestrator.run(topic="Max turns spy", thread_id="2026-09-26-max-turns-spy")

        assert spy.call_args.kwargs["max_turns"] == 9


# ---------------------------------------------------------------------------
# Existing configs keep loading unchanged (no schema change)
# ---------------------------------------------------------------------------


class TestShippedConfigsStillLoad:
    def test_debate_tiers_yaml_loads(self) -> None:
        tiers = _load_tiers_from_yaml(REPO_ROOT / "config" / "debate-tiers.yaml")
        assert tiers["standard"].settings.fallback.enabled is True

    def test_tiers_yaml_example_loads(self) -> None:
        tiers = _load_tiers_from_yaml(REPO_ROOT / "tiers.yaml.example")
        assert tiers


# ---------------------------------------------------------------------------
# Credential hygiene: raw provider messages never reach logs or error text
# ---------------------------------------------------------------------------

# Unique, deliberately NOT key-shaped (secret scanners must not match it)
SECRET = "LEAK-SENTINEL-7f3a9c"


class TestFallbackCredentialHygiene:
    @pytest.mark.anyio
    async def test_fallback_warning_does_not_log_raw_error_message(
        self, state_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = OpenRouterApiError(
            f"OpenRouter API error: 401 - invalid key {SECRET}"
        )
        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)

        with caplog.at_level(logging.DEBUG, logger="debate_hall_mcp"):
            await orchestrator.run(topic="Hygiene", thread_id="2026-09-26-hygiene-log")

        assert "fallback" in caplog.text.lower()
        assert "OpenRouterApiError" in caplog.text
        assert SECRET not in caplog.text
        events_text = " ".join(
            str(e.payload) for e in load_events("2026-09-26-hygiene-log", state_dir)
        )
        assert SECRET not in events_text

    @pytest.mark.anyio
    async def test_fallback_error_message_has_no_raw_provider_text(
        self, state_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from debate_hall_mcp.orchestrator import ProviderFallbackError

        factory = RoutingFactory()
        factory.primary["Wind"].complete.side_effect = CliProviderError(f"stderr: {SECRET}")
        factory.fallback.complete.side_effect = OpenRouterApiError(f"body: {SECRET}")
        orchestrator = DebateOrchestrator(_tier_config(), state_dir, provider_factory=factory)

        with (
            caplog.at_level(logging.DEBUG, logger="debate_hall_mcp"),
            pytest.raises(ProviderFallbackError) as exc_info,
        ):
            await orchestrator.run(topic="Hygiene 2", thread_id="2026-09-26-hygiene-exc")

        message = str(exc_info.value)
        assert SECRET not in message
        assert "CliProviderError" in message
        assert "OpenRouterApiError" in message
        assert SECRET not in caplog.text


# ---------------------------------------------------------------------------
# I3: refinements stop at the room's turn budget and close as EXHAUSTION
# ---------------------------------------------------------------------------


def _always_wall_rejects(factory: RoutingFactory) -> None:
    factory.primary["Wind"].complete.return_value = _response("APPROVE", PRIMARY_MODELS["Wind"])
    factory.primary["Wall"].complete.return_value = _response(
        "REJECT - still missing constraints", PRIMARY_MODELS["Wall"]
    )


class TestRefinementTurnBudget:
    @pytest.mark.anyio
    async def test_low_max_turns_closes_as_exhaustion_not_paused(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-budget-exhaustion"
        factory = RoutingFactory()
        _always_wall_rejects(factory)
        config = _tier_config(consensus_required=True, max_turns=4, max_refinement_loops=3)

        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        result = await orchestrator.run(topic="Budget", thread_id=thread_id)

        room = load_debate_state(thread_id, state_dir)
        assert result.status == "exhaustion"
        assert room.status == DebateStatus.EXHAUSTION
        assert len(room.turns) == 4  # Wind, Wall, Door + one refinement
        assert result.turn_count == 4
        assert room.consensus_metadata is not None
        assert room.consensus_metadata.consensus_reached is False
        closed = [
            e for e in load_events(thread_id, state_dir) if e.event_type == EventType.DEBATE_CLOSED
        ]
        assert closed[-1].payload["status"] == "exhaustion"

    @pytest.mark.anyio
    async def test_resume_at_turn_budget_closes_instead_of_looping(self, state_dir: Path) -> None:
        thread_id = "2026-09-26-budget-resume"
        factory = RoutingFactory()
        _always_wall_rejects(factory)
        # Pause the debate exactly at its turn budget: W, Wa, D, refinement D = 4 turns,
        # then the next Wind vote fails with fallback disabled -> PAUSED.
        factory.primary["Wind"].complete.side_effect = [
            _response("wind turn", PRIMARY_MODELS["Wind"]),
            _response("APPROVE", PRIMARY_MODELS["Wind"]),
            MODEL_NOT_FOUND,
        ]
        config = _tier_config(
            consensus_required=True, max_turns=4, max_refinement_loops=3, fallback_enabled=False
        )
        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        with pytest.raises(OpenRouterApiError):
            await orchestrator.run(topic="Budget resume", thread_id=thread_id)
        room = load_debate_state(thread_id, state_dir)
        assert room.status == DebateStatus.PAUSED
        assert len(room.turns) == 4

        # Resume: votes still happen (they are not turns) but no refinement fits
        factory.primary["Wind"].complete.side_effect = None
        factory.primary["Wind"].complete.return_value = _response("APPROVE", PRIMARY_MODELS["Wind"])
        door_calls_before = factory.primary["Door"].complete.await_count
        result = await orchestrator.resume(thread_id)

        room = load_debate_state(thread_id, state_dir)
        assert result.status == "exhaustion"
        assert room.status == DebateStatus.EXHAUSTION
        assert len(room.turns) == 4
        assert factory.primary["Door"].complete.await_count == door_calls_before


class TestNonConsensusCloseValidation:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ("max_turns", "max_refinement_loops", "path"),
        [(4, 3, "exhaustion"), (12, 0, "stalemate")],
    )
    async def test_blank_synthesis_is_rejected_on_both_non_consensus_paths(
        self, state_dir: Path, max_turns: int, max_refinement_loops: int, path: str
    ) -> None:
        """Exhaustion and stalemate closes validate the synthesis identically."""
        thread_id = f"2026-09-26-blank-synthesis-{path}"
        factory = RoutingFactory()
        _always_wall_rejects(factory)
        factory.primary["Door"].complete.return_value = _response("   ", PRIMARY_MODELS["Door"])
        config = _tier_config(
            consensus_required=True,
            max_turns=max_turns,
            max_refinement_loops=max_refinement_loops,
        )

        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        with pytest.raises(ValueError, match="Synthesis required"):
            await orchestrator.run(topic=f"Blank {path}", thread_id=thread_id)

        assert load_debate_state(thread_id, state_dir).status == DebateStatus.PAUSED


# ---------------------------------------------------------------------------
# max_turns is the effective ceiling (max_rounds must not bind below it)
# ---------------------------------------------------------------------------


class TestMaxTurnsIsEffectiveCeiling:
    @pytest.mark.anyio
    async def test_max_turns_16_records_more_than_12_turns_and_caps_at_16(
        self, state_dir: Path
    ) -> None:
        thread_id = "2026-09-26-max-turns-16"
        factory = RoutingFactory()
        _always_wall_rejects(factory)
        config = _tier_config(consensus_required=True, max_turns=16, max_refinement_loops=20)

        orchestrator = DebateOrchestrator(config, state_dir, provider_factory=factory)
        result = await orchestrator.run(topic="Sixteen", thread_id=thread_id)

        room = load_debate_state(thread_id, state_dir)
        assert len(room.turns) == 16
        assert result.status == "exhaustion"
        assert room.max_turns == 16
        assert room.max_rounds * 3 >= room.max_turns
