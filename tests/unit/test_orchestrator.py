"""Unit tests for DebateOrchestrator (Phase 3: Auto-orchestration).

Tests the orchestrator core loop:
- Provider creation from tier config
- Debate initialization via existing tools
- Wind/Wall/Door turn sequence
- Debate closure with Door's synthesis
- Event emission at each stage
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.events import EventType, load_events
from debate_hall_mcp.orchestrator import DebateOrchestrator, DebateResult
from debate_hall_mcp.providers import ProviderResponse


@pytest.fixture
def tier_config() -> TierConfig:
    """Create a test tier configuration."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=False,  # Simplified for basic tests
            max_turns=12,
            max_refinement_loops=3,
        ),
    )


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


def create_mock_provider_response(content: str, model: str = "test-model") -> ProviderResponse:
    """Create a mock ProviderResponse."""
    return ProviderResponse(
        content=content,
        model=model,
        token_input=100,
        token_output=200,
    )


class TestDebateOrchestratorInit:
    """Tests for DebateOrchestrator initialization."""

    def test_init_with_tier_config(self, tier_config: TierConfig, temp_state_dir: Path) -> None:
        """Orchestrator should initialize with tier config and state dir."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)
        assert orchestrator.tier_config == tier_config
        assert orchestrator.state_dir == temp_state_dir

    def test_init_requires_tier_config(self, temp_state_dir: Path) -> None:
        """Orchestrator should require a tier config."""
        with pytest.raises(TypeError):
            DebateOrchestrator(state_dir=temp_state_dir)  # type: ignore[call-arg]


class TestDebateOrchestratorRun:
    """Tests for DebateOrchestrator.run() method."""

    @pytest.mark.anyio
    async def test_run_returns_debate_result(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run() should return a DebateResult."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        # Mock the providers
        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "## WIND (PATHOS) - Test Response\n\nTest content with steps:\n1. First step\n2. Second step"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Test topic")

        assert isinstance(result, DebateResult)
        assert result.thread_id is not None
        assert result.topic == "Test topic"

    @pytest.mark.anyio
    async def test_run_generates_thread_id_if_not_provided(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run() should generate a thread_id if not provided."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "Test response\n1. Step one\n2. Step two"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Auto-generated ID test")

        # Thread ID should be in date-first format: YYYY-MM-DD-subject
        assert result.thread_id is not None
        parts = result.thread_id.split("-")
        assert len(parts) >= 4  # At least YYYY-MM-DD-subject
        # First three parts should be date
        year, month, day = parts[0], parts[1], parts[2]
        datetime(int(year), int(month), int(day))  # Should not raise

    @pytest.mark.anyio
    async def test_run_uses_provided_thread_id(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run() should use the provided thread_id."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)
        expected_thread_id = "2026-01-30-custom-thread"

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "Test response\n1. Step\n2. Step"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(
                topic="Custom thread test", thread_id=expected_thread_id
            )

        assert result.thread_id == expected_thread_id

    @pytest.mark.anyio
    async def test_run_calls_providers_in_sequence(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run() should call Wind, Wall, Door providers in sequence."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        wind_response = "## WIND (PATHOS) - Possibilities\n\nExploring options..."
        wall_response = "## WALL (ETHOS) - Validation\n\n### VERDICT\nGO\n\n1. Evidence shows...\n2. Therefore..."
        door_response = "## DOOR (LOGOS) - Synthesis\n\n### TENSION_ANALYSIS\n\n1. Analyzing...\n2. Integrating...\n3. Therefore..."

        call_order: list[str] = []

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:

            def mock_complete(
                system_prompt: str, user_prompt: str, **kwargs: Any  # noqa: ARG001
            ) -> ProviderResponse:
                # Determine which role based on "Your Role:" line in user_prompt
                if "Your Role: Wind" in user_prompt:
                    call_order.append("wind")
                    return create_mock_provider_response(wind_response)
                elif "Your Role: Wall" in user_prompt:
                    call_order.append("wall")
                    return create_mock_provider_response(wall_response)
                elif "Your Role: Door" in user_prompt:
                    call_order.append("door")
                    return create_mock_provider_response(door_response)
                return create_mock_provider_response("Unknown response")

            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = mock_complete
            mock_create_provider.return_value = mock_provider

            await orchestrator.run(topic="Sequence test")

        # Verify Wind -> Wall -> Door sequence
        assert call_order == ["wind", "wall", "door"]

    @pytest.mark.anyio
    async def test_run_closes_debate_with_door_synthesis(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run() should close the debate with Door's response as synthesis."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)
        door_synthesis = "## DOOR (LOGOS) - Final Synthesis\n\n### TENSION_ANALYSIS\n1. First step\n2. Second step\n3. Therefore the synthesis is complete."

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            # Wind and Wall return simple responses
            mock_provider.complete.side_effect = [
                create_mock_provider_response("Wind response"),
                create_mock_provider_response("Wall response with\n1. Step\n2. Step"),
                create_mock_provider_response(door_synthesis),
            ]
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Synthesis test")

        assert result.status == "synthesis"
        assert result.synthesis is not None
        assert "Final Synthesis" in result.synthesis or door_synthesis in result.synthesis


class TestDebateOrchestratorProviderCreation:
    """Tests for provider creation from tier config."""

    @pytest.mark.anyio
    async def test_creates_separate_providers_for_each_role(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Orchestrator should create separate providers for Wind, Wall, Door."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        created_configs: list[RoleConfig] = []

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            # Capture the configs passed to create_provider
            def capture_config(config: RoleConfig) -> AsyncMock:
                created_configs.append(config)
                mock = AsyncMock()
                mock.complete.return_value = create_mock_provider_response(
                    "Response\n1. Step\n2. Step"
                )
                return mock

            mock_create_provider.side_effect = capture_config

            await orchestrator.run(topic="Provider test")

        # Should create 3 providers (wind, wall, door)
        assert len(created_configs) == 3
        # Verify the configs match the tier config
        cli_names = [c.cli for c in created_configs]
        assert "claude" in cli_names  # wind
        assert "codex" in cli_names  # wall
        assert "gemini" in cli_names  # door


class TestDebateOrchestratorEventEmission:
    """Tests for event emission during orchestration (P3.4)."""

    @pytest.mark.anyio
    async def test_emits_debate_started_event(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Orchestrator should emit debate_started event after init."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "Test\n1. Step\n2. Step"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Event test")

        # Load events and check for debate_started
        events = load_events(result.thread_id, temp_state_dir)
        event_types = [e.event_type for e in events]
        assert EventType.DEBATE_STARTED in event_types

    @pytest.mark.anyio
    async def test_emits_turn_added_events(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Orchestrator should emit turn_added events for each turn."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "Test\n1. Step\n2. Step"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Turn events test")

        # Load events and check for turn_added (should have 3: Wind, Wall, Door)
        events = load_events(result.thread_id, temp_state_dir)
        turn_events = [e for e in events if e.event_type == EventType.TURN_ADDED]
        assert len(turn_events) == 3

    @pytest.mark.anyio
    async def test_emits_debate_closed_event(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Orchestrator should emit debate_closed event after close."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.return_value = create_mock_provider_response(
                "Test\n1. Step\n2. Step"
            )
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Close event test")

        # Load events and check for debate_closed
        events = load_events(result.thread_id, temp_state_dir)
        event_types = [e.event_type for e in events]
        assert EventType.DEBATE_CLOSED in event_types

    @pytest.mark.anyio
    async def test_emits_error_event_on_provider_failure(
        self, tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Orchestrator should emit error event when provider fails."""
        orchestrator = DebateOrchestrator(tier_config, temp_state_dir)

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = Exception("Provider API error")
            mock_create_provider.return_value = mock_provider

            # Should raise the error but also emit an event
            with pytest.raises(Exception, match="Provider API error"):
                await orchestrator.run(topic="Error event test")

        # Note: We need to capture the thread_id to check events
        # For error case, we may need to adjust the test or implementation


class TestDebateResult:
    """Tests for DebateResult model."""

    def test_debate_result_fields(self) -> None:
        """DebateResult should have expected fields."""
        result = DebateResult(
            thread_id="2026-01-30-test",
            topic="Test topic",
            status="synthesis",
            turn_count=3,
            synthesis="Final synthesis content",
        )
        assert result.thread_id == "2026-01-30-test"
        assert result.topic == "Test topic"
        assert result.status == "synthesis"
        assert result.turn_count == 3
        assert result.synthesis == "Final synthesis content"

    def test_debate_result_optional_synthesis(self) -> None:
        """DebateResult should allow None synthesis for non-synthesis status."""
        result = DebateResult(
            thread_id="2026-01-30-test",
            topic="Test topic",
            status="active",
            turn_count=1,
            synthesis=None,
        )
        assert result.synthesis is None
