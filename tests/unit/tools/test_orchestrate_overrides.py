"""Unit tests for run_debate and resume_debate tier override parameters (Issue #132).

Tests the optional compression_tier and primer_tier override parameters:
- Override values replace tier defaults
- None values preserve tier defaults (backward compatible)
- Overrides work for both run_debate and resume_debate
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateResult
from debate_hall_mcp.tools.orchestrate import resume_debate, run_debate


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def mock_tier_config() -> TierConfig:
    """Create a mock tier config with default settings."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=False,
            max_turns=12,
            max_refinement_loops=3,
            primer_tier="standard",  # Default
            compression_tier="aggressive",  # Default
        ),
    )


@pytest.fixture
def mock_debate_result() -> DebateResult:
    """Create a mock debate result."""
    return DebateResult(
        thread_id="2026-02-03-test-topic-abc12345",
        topic="Test topic",
        status="synthesis",
        turn_count=3,
        synthesis="## DOOR (LOGOS) - Final Synthesis\n1. Step\n2. Step",
    )


class TestRunDebateCompressionTierOverride:
    """Tests for compression_tier override in run_debate."""

    @pytest.mark.anyio
    async def test_run_debate_compression_tier_override(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate should override compression_tier when provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Test topic",
                compression_tier="ultra",  # Override from "aggressive" default
            )

        # Verify the TierConfig passed to orchestrator has overridden compression_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "ultra"

    @pytest.mark.anyio
    async def test_run_debate_compression_tier_none_uses_default(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate with compression_tier=None should use tier default."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Test topic",
                compression_tier=None,  # Explicitly None
            )

        # Verify the TierConfig passed to orchestrator retains default compression_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "aggressive"


class TestRunDebatePrimerTierOverride:
    """Tests for primer_tier override in run_debate."""

    @pytest.mark.anyio
    async def test_run_debate_primer_tier_override(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate should override primer_tier when provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Test topic",
                primer_tier="none",  # Override from "standard" default
            )

        # Verify the TierConfig passed to orchestrator has overridden primer_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.primer_tier == "none"

    @pytest.mark.anyio
    async def test_run_debate_primer_tier_none_uses_default(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate with primer_tier=None should use tier default."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Test topic",
                primer_tier=None,  # Explicitly None
            )

        # Verify the TierConfig passed to orchestrator retains default primer_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.primer_tier == "standard"


class TestRunDebateBothOverrides:
    """Tests for using both overrides together."""

    @pytest.mark.anyio
    async def test_run_debate_both_overrides(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate should override both when both are provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Test topic",
                compression_tier="basic",
                primer_tier="advanced",
            )

        # Verify both overrides are applied
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "basic"
        assert tier_config_passed.settings.primer_tier == "advanced"


class TestRunDebateNoneUsesDefaults:
    """Tests for backward compatibility when no overrides are provided."""

    @pytest.mark.anyio
    async def test_run_debate_none_uses_tier_default(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate without overrides should use tier defaults."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir

            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            # Call without any override parameters
            await run_debate(topic="Test topic")

        # Verify tier defaults are preserved
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "aggressive"
        assert tier_config_passed.settings.primer_tier == "standard"


class TestResumeDebateOverrides:
    """Tests for override parameters in resume_debate."""

    @pytest.fixture
    def mock_paused_debate_state(self) -> MagicMock:
        """Create a mock paused debate state."""
        from debate_hall_mcp.state import DebateStatus

        mock_room = MagicMock()
        mock_room.status = DebateStatus.PAUSED
        mock_room.topic = "Paused test topic"
        mock_room.turns = []
        return mock_room

    @pytest.mark.anyio
    async def test_resume_debate_compression_tier_override(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
        mock_paused_debate_state: MagicMock,
    ) -> None:
        """resume_debate should override compression_tier when provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_debate_state") as mock_load_state,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_state.return_value = mock_paused_debate_state

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(
                thread_id="2026-02-03-test-topic-abc12345",
                compression_tier="none",  # Override
            )

        # Verify the TierConfig passed to orchestrator has overridden compression_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "none"

    @pytest.mark.anyio
    async def test_resume_debate_primer_tier_override(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
        mock_paused_debate_state: MagicMock,
    ) -> None:
        """resume_debate should override primer_tier when provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_debate_state") as mock_load_state,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_state.return_value = mock_paused_debate_state

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(
                thread_id="2026-02-03-test-topic-abc12345",
                primer_tier="literacy",  # Override
            )

        # Verify the TierConfig passed to orchestrator has overridden primer_tier
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.primer_tier == "literacy"

    @pytest.mark.anyio
    async def test_resume_debate_both_overrides(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
        mock_paused_debate_state: MagicMock,
    ) -> None:
        """resume_debate should override both when both are provided."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_debate_state") as mock_load_state,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_state.return_value = mock_paused_debate_state

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(
                thread_id="2026-02-03-test-topic-abc12345",
                compression_tier="ultra",
                primer_tier="advanced",
            )

        # Verify both overrides are applied
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "ultra"
        assert tier_config_passed.settings.primer_tier == "advanced"

    @pytest.mark.anyio
    async def test_resume_debate_none_uses_tier_default(
        self,
        temp_state_dir: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
        mock_paused_debate_state: MagicMock,
    ) -> None:
        """resume_debate without overrides should use tier defaults."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_debate_state") as mock_load_state,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_load_config.return_value = mock_tier_config
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_state.return_value = mock_paused_debate_state

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_debate_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            # Call without any override parameters
            await resume_debate(thread_id="2026-02-03-test-topic-abc12345")

        # Verify tier defaults are preserved
        call_args = mock_orchestrator_class.call_args
        tier_config_passed: TierConfig = call_args[0][0]
        assert tier_config_passed.settings.compression_tier == "aggressive"
        assert tier_config_passed.settings.primer_tier == "standard"
