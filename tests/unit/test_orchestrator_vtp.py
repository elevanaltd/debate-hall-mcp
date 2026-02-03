"""Unit tests for VTP (Virtual Tool Preload) primer and compression injection.

Tests cover:
- Orchestrator primer injection based on primer_tier setting
- Orchestrator compression directive injection based on compression_tier setting
- Integration of primers and compression directives into enhanced_prompt

VTP enables provider-agnostic design: agents receive state and context passively
instead of needing to call tools themselves.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import ProviderResponse


@pytest.fixture
def mock_provider_factory() -> MagicMock:
    """Create a mock provider factory that returns mock providers."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(
        return_value=ProviderResponse(
            content="Mock response content",
            model="mock-model",
            token_input=100,
            token_output=50,
        )
    )

    def factory(_config: RoleConfig) -> MagicMock:
        return mock_provider

    return MagicMock(side_effect=factory)


@pytest.fixture
def base_tier_config() -> TierConfig:
    """Create a base tier config for testing."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(),
    )


class TestOrchestratorPrimerInjection:
    """Test primer injection based on primer_tier setting."""

    def test_get_primer_content_returns_literacy_for_literacy_tier(self, tmp_path: Path) -> None:
        """_get_primer_content returns octave-literacy-primer for literacy tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="literacy"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        primer_content = orchestrator._get_primer_content()

        assert primer_content is not None
        assert "OCTAVE" in primer_content  # Literacy primer contains OCTAVE syntax

    def test_get_primer_content_returns_literacy_and_compression_for_standard_tier(
        self, tmp_path: Path
    ) -> None:
        """_get_primer_content returns literacy + compression for standard tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="standard"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        primer_content = orchestrator._get_primer_content()

        assert primer_content is not None
        # Standard tier includes both literacy and compression
        assert "OCTAVE" in primer_content

    def test_get_primer_content_returns_all_primers_for_advanced_tier(self, tmp_path: Path) -> None:
        """_get_primer_content returns literacy + compression + ultra-mythic for advanced."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="advanced"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        primer_content = orchestrator._get_primer_content()

        assert primer_content is not None

    def test_get_primer_content_returns_empty_for_none_tier(self, tmp_path: Path) -> None:
        """_get_primer_content returns empty string for none tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        primer_content = orchestrator._get_primer_content()

        assert primer_content == ""


class TestOrchestratorCompressionDirective:
    """Test compression directive injection based on compression_tier setting."""

    def test_get_compression_directive_returns_basic_directive(self, tmp_path: Path) -> None:
        """_get_compression_directive returns basic directive for basic tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(compression_tier="basic"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        directive = orchestrator._get_compression_directive()

        assert directive is not None
        assert "OCTAVE structure" in directive
        assert "preserving nuance" in directive

    def test_get_compression_directive_returns_aggressive_directive(self, tmp_path: Path) -> None:
        """_get_compression_directive returns aggressive directive for aggressive tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(compression_tier="aggressive"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        directive = orchestrator._get_compression_directive()

        assert directive is not None
        assert "OCTAVE compression" in directive
        assert "Drop nuance" in directive

    def test_get_compression_directive_returns_ultra_directive(self, tmp_path: Path) -> None:
        """_get_compression_directive returns ultra directive for ultra tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(compression_tier="ultra"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        directive = orchestrator._get_compression_directive()

        assert directive is not None
        assert "ULTRA compression" in directive
        assert "protocol only" in directive

    def test_get_compression_directive_returns_empty_for_none_tier(self, tmp_path: Path) -> None:
        """_get_compression_directive returns empty string for none tier."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(compression_tier="none"),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        directive = orchestrator._get_compression_directive()

        assert directive == ""


class TestOrchestratorVTPIntegration:
    """Test that primers and compression directives are injected into prompts."""

    @pytest.mark.asyncio
    async def test_execute_role_turn_injects_primers_before_state(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """_execute_role_turn injects primers BEFORE <DEBATE_STATE> block."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="literacy", compression_tier="none"),
        )
        orchestrator = DebateOrchestrator(
            tier_config, tmp_path, provider_factory=mock_provider_factory
        )

        # Mock debate state
        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="Test prompt",
                    timeout=60,
                )

                # Verify the enhanced prompt structure
                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                # Primers should appear BEFORE <DEBATE_STATE>
                primer_pos = user_prompt.find("OCTAVE")
                state_pos = user_prompt.find("<DEBATE_STATE>")
                assert primer_pos < state_pos, "Primers should appear before DEBATE_STATE"

    @pytest.mark.asyncio
    async def test_execute_role_turn_injects_compression_directive(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """_execute_role_turn injects compression directive between primers and state."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none", compression_tier="aggressive"),
        )
        orchestrator = DebateOrchestrator(
            tier_config, tmp_path, provider_factory=mock_provider_factory
        )

        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="Test prompt",
                    timeout=60,
                )

                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                # Should contain compression directive
                assert "<COMPRESSION_DIRECTIVE>" in user_prompt
                assert "OCTAVE compression" in user_prompt
                assert "</COMPRESSION_DIRECTIVE>" in user_prompt

    @pytest.mark.asyncio
    async def test_execute_role_turn_skips_injection_for_none_tiers(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """_execute_role_turn skips injection when both tiers are 'none'."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none", compression_tier="none"),
        )
        orchestrator = DebateOrchestrator(
            tier_config, tmp_path, provider_factory=mock_provider_factory
        )

        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="Test prompt",
                    timeout=60,
                )

                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                # Should NOT contain compression directive tags
                assert "<COMPRESSION_DIRECTIVE>" not in user_prompt
                # Should start with state block directly
                assert user_prompt.startswith("<DEBATE_STATE>")


class TestFormatDebateStateNoTruncation:
    """Test that _format_debate_state preserves full content (#131)."""

    def test_format_debate_state_preserves_full_turn_content(self, tmp_path: Path) -> None:
        """Verify turn content is NOT truncated (#131).

        Issue #131: Content truncation to 500 chars destroys context agents need.
        """
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        # Create content longer than 500 chars
        long_content = "x" * 1000
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "OPEN",
            "turn_count": 1,
            "transcript": [{"role": "Wind", "content": long_content}],
        }

        result = orchestrator._format_debate_state(state)

        # Full content must be preserved - no truncation
        assert long_content in result
        # Ensure no truncation ellipsis in turn content
        # (split by role marker to isolate turn content)
        wind_section = result.split("[Wind]::")[1].split("</DEBATE_STATE>")[0]
        assert "..." not in wind_section

    def test_format_debate_state_preserves_full_synthesis(self, tmp_path: Path) -> None:
        """Verify synthesis is NOT truncated (#131).

        Issue #131: Synthesis truncation to 200 chars loses critical context.
        """
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        # Create synthesis longer than 200 chars
        long_synthesis = "s" * 500
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "CLOSED",
            "turn_count": 3,
            "synthesis": long_synthesis,
        }

        result = orchestrator._format_debate_state(state)

        # Full synthesis must be preserved
        assert long_synthesis in result
        # Ensure no truncation ellipsis after synthesis
        synthesis_line = [line for line in result.split("\n") if "SYNTHESIS::" in line][0]
        assert not synthesis_line.endswith("...")

    def test_format_debate_state_handles_multiple_long_turns(self, tmp_path: Path) -> None:
        """Verify multiple long turns are all preserved (#131)."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        # Create multiple turns with long content
        wind_content = "wind_" + "w" * 800
        wall_content = "wall_" + "a" * 800
        door_content = "door_" + "d" * 800
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "CLOSED",
            "turn_count": 3,
            "transcript": [
                {"role": "Wind", "content": wind_content},
                {"role": "Wall", "content": wall_content},
                {"role": "Door", "content": door_content},
            ],
        }

        result = orchestrator._format_debate_state(state)

        # All full content must be preserved
        assert wind_content in result
        assert wall_content in result
        assert door_content in result
