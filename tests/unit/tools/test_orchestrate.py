"""Unit tests for run_debate tool (Phase 3: Auto-orchestration).

Tests the MCP tool wrapper for auto-orchestration:
- Tool invocation and response format
- Tier configuration loading
- Integration with DebateOrchestrator
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateResult
from debate_hall_mcp.tools.orchestrate import run_debate


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def mock_tier_config() -> TierConfig:
    """Create a mock tier config."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=False,
            max_turns=12,
            max_refinement_loops=3,
        ),
    )


@pytest.fixture
def mock_debate_result() -> DebateResult:
    """Create a mock debate result."""
    return DebateResult(
        thread_id="2026-01-30-test-topic-abc12345",
        topic="Test topic",
        status="synthesis",
        turn_count=3,
        synthesis="## DOOR (LOGOS) - Final Synthesis\n1. Step\n2. Step",
    )


class TestRunDebateTool:
    """Tests for the run_debate MCP tool."""

    @pytest.mark.anyio
    async def test_run_debate_returns_dict(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate should return a dictionary result."""
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

            result = await run_debate(topic="Test topic")

        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_run_debate_includes_thread_id(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate result should include thread_id."""
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

            result = await run_debate(topic="Thread ID test")

        assert "thread_id" in result
        assert result["thread_id"] is not None

    @pytest.mark.anyio
    async def test_run_debate_includes_status(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate result should include status."""
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

            result = await run_debate(topic="Status test")

        assert "status" in result
        assert result["status"] == "synthesis"

    @pytest.mark.anyio
    async def test_run_debate_loads_tier_config(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate should load the specified tier config."""
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

            await run_debate(topic="Tier test", tier="premium")

        mock_load_config.assert_called_once_with("premium")

    @pytest.mark.anyio
    async def test_run_debate_uses_default_tier(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate should use 'standard' tier by default."""
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

            await run_debate(topic="Default tier test")

        mock_load_config.assert_called_once_with("standard")

    @pytest.mark.anyio
    async def test_run_debate_uses_provided_thread_id(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """run_debate should use the provided thread_id if given."""
        custom_result = DebateResult(
            thread_id="2026-01-30-custom-thread",
            topic="Custom thread test",
            status="synthesis",
            turn_count=3,
            synthesis="Final synthesis",
        )
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
            mock_orchestrator.run = AsyncMock(return_value=custom_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(
                topic="Custom thread test",
                thread_id="2026-01-30-custom-thread",
            )

        assert result["thread_id"] == "2026-01-30-custom-thread"
        # Verify the orchestrator.run was called with the thread_id
        mock_orchestrator.run.assert_called_once_with(
            topic="Custom thread test", thread_id="2026-01-30-custom-thread"
        )

    @pytest.mark.anyio
    async def test_run_debate_includes_synthesis(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """run_debate result should include synthesis when completed."""
        synthesis_result = DebateResult(
            thread_id="2026-01-30-synth-test",
            topic="Synthesis test",
            status="synthesis",
            turn_count=3,
            synthesis="## DOOR (LOGOS) - Final Synthesis\n1. Step\n2. Step",
        )
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
            mock_orchestrator.run = AsyncMock(return_value=synthesis_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(topic="Synthesis test")

        assert "synthesis" in result
        assert result["synthesis"] is not None
        assert "Final Synthesis" in result["synthesis"]

    @pytest.mark.anyio
    async def test_run_debate_includes_turn_count(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate result should include turn_count."""
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

            result = await run_debate(topic="Turn count test")

        assert "turn_count" in result
        assert result["turn_count"] == 3  # Wind, Wall, Door

    @pytest.mark.anyio
    async def test_run_debate_raises_on_invalid_tier(self, temp_state_dir: Path) -> None:
        """run_debate should raise error for invalid tier."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
        ):
            mock_load_config.side_effect = KeyError("Tier 'nonexistent' not found")
            mock_get_state_dir.return_value = temp_state_dir

            with pytest.raises(KeyError, match="nonexistent"):
                await run_debate(topic="Invalid tier test", tier="nonexistent")


class TestM4InputValidation:
    """Tests for M4: Input validation at tool boundary (CE Review mitigation)."""

    @pytest.mark.anyio
    async def test_raises_error_for_empty_topic(self) -> None:
        """run_debate should raise ValueError for empty topic."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            await run_debate(topic="")

    @pytest.mark.anyio
    async def test_raises_error_for_whitespace_only_topic(self) -> None:
        """run_debate should raise ValueError for whitespace-only topic."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            await run_debate(topic="   ")

    @pytest.mark.anyio
    async def test_raises_error_for_topic_exceeding_max_length(self) -> None:
        """run_debate should raise ValueError for topic exceeding 5000 chars."""
        long_topic = "x" * 5001
        with pytest.raises(ValueError, match="Topic exceeds maximum length"):
            await run_debate(topic=long_topic)

    @pytest.mark.anyio
    async def test_accepts_topic_at_max_length(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate should accept a topic exactly at 5000 chars."""
        topic_5000_chars = "x" * 5000
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

            result = await run_debate(topic=topic_5000_chars)

        # Should succeed without error
        assert result["thread_id"] is not None

    @pytest.mark.anyio
    async def test_raises_error_for_thread_id_with_path_traversal(self) -> None:
        """run_debate should raise ValueError for thread_id with path traversal."""
        with pytest.raises(ValueError, match="path-unsafe"):
            await run_debate(topic="Valid topic", thread_id="../evil-path")

    @pytest.mark.anyio
    async def test_raises_error_for_thread_id_with_forward_slash(self) -> None:
        """run_debate should raise ValueError for thread_id with forward slash."""
        with pytest.raises(ValueError, match="path-unsafe"):
            await run_debate(topic="Valid topic", thread_id="foo/bar")

    @pytest.mark.anyio
    async def test_raises_error_for_thread_id_with_backslash(self) -> None:
        """run_debate should raise ValueError for thread_id with backslash."""
        with pytest.raises(ValueError, match="path-unsafe"):
            await run_debate(topic="Valid topic", thread_id="foo\\bar")

    @pytest.mark.anyio
    async def test_accepts_valid_thread_id(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """run_debate should accept valid thread_id format."""
        valid_result = DebateResult(
            thread_id="2026-01-30-valid-thread-id",
            topic="Valid topic",
            status="synthesis",
            turn_count=3,
            synthesis="Synthesis",
        )
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
            mock_orchestrator.run = AsyncMock(return_value=valid_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(
                topic="Valid topic",
                thread_id="2026-01-30-valid-thread-id",
            )

        # Should succeed without error
        assert result["thread_id"] == "2026-01-30-valid-thread-id"

    @pytest.mark.anyio
    async def test_allows_none_thread_id(
        self, temp_state_dir: Path, mock_tier_config: TierConfig, mock_debate_result: DebateResult
    ) -> None:
        """run_debate should allow None thread_id (auto-generated)."""
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

            result = await run_debate(topic="Valid topic", thread_id=None)

        # Should succeed without error
        assert result["thread_id"] is not None
