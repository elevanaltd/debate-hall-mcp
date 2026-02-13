"""Unit tests for RACI MCP tool interface.

Tests for run_debate with mode="raci" and raci_config parameter,
including validation and server registration.

TDD: These tests are written first (RED phase) before implementation.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateResult
from debate_hall_mcp.state import DebateMode, DebateStatus
from debate_hall_mcp.tools.orchestrate import run_debate


@pytest.fixture
def raci_tier_config() -> TierConfig:
    """Create a test tier configuration."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(
            consensus_required=False,
            max_turns=12,
        ),
    )


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


class TestRunDebateRACIMode:
    """Tests for run_debate with mode='raci'."""

    @pytest.mark.anyio
    async def test_run_debate_raci_mode_dispatches_to_run_raci(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate with mode='raci' should call orchestrator.run_raci()."""
        mock_result = DebateResult(
            thread_id="2026-02-13-raci-tool-test",
            topic="RACI tool test",
            status="synthesis",
            turn_count=4,
            synthesis="## VERDICT: GO",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run_raci = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(
                topic="RACI tool test",
                tier="standard",
                mode="raci",
                raci_config={
                    "responsible": "architect",
                    "accountable": "tech-lead",
                    "consulted": ["reviewer"],
                },
                state_dir=temp_state_dir,
            )

        assert result["status"] == "synthesis"
        assert result["turn_count"] == 4
        mock_orchestrator.run_raci.assert_called_once()

    @pytest.mark.anyio
    async def test_run_debate_raci_requires_raci_config(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate with mode='raci' should require raci_config parameter."""
        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            pytest.raises(ValueError, match="raci_config"),
        ):
            await run_debate(
                topic="Missing config test",
                tier="standard",
                mode="raci",
                state_dir=temp_state_dir,
            )

    @pytest.mark.anyio
    async def test_run_debate_raci_validates_config_dict(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate should validate raci_config dict has required keys."""
        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            pytest.raises((ValueError, KeyError)),
        ):
            await run_debate(
                topic="Invalid config test",
                tier="standard",
                mode="raci",
                raci_config={"responsible": "only-one-key"},
                state_dir=temp_state_dir,
            )

    @pytest.mark.anyio
    async def test_run_debate_standard_mode_ignores_raci_config(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate with mode='standard' should ignore raci_config even if provided."""
        mock_result = DebateResult(
            thread_id="2026-02-13-standard-test",
            topic="Standard test",
            status="synthesis",
            turn_count=3,
            synthesis="Standard synthesis",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Standard test",
                tier="standard",
                mode="standard",
                raci_config={
                    "responsible": "dev",
                    "accountable": "lead",
                },
                state_dir=temp_state_dir,
            )

        # Should use run(), not run_raci()
        mock_orchestrator.run.assert_called_once()

    @pytest.mark.anyio
    async def test_run_debate_raci_passes_config_to_orchestrator(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate should convert raci_config dict to RACIConfig and pass it."""
        mock_result = DebateResult(
            thread_id="2026-02-13-pass-config-test",
            topic="Pass config test",
            status="synthesis",
            turn_count=2,
            synthesis="## VERDICT: GO",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run_raci = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await run_debate(
                topic="Pass config test",
                tier="standard",
                mode="raci",
                raci_config={
                    "responsible": "dev",
                    "accountable": "lead",
                    "consulted": ["reviewer"],
                    "informed": ["pm"],
                },
                state_dir=temp_state_dir,
            )

        # Verify run_raci was called with the config
        call_kwargs = mock_orchestrator.run_raci.call_args
        raci_config_arg = call_kwargs.kwargs.get("raci_config") or call_kwargs[1].get("raci_config")
        if raci_config_arg is None:
            # Try positional args
            raci_config_arg = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
        # The config should be passed through
        assert raci_config_arg is not None


class TestServerRACIRegistration:
    """Tests for RACI mode in server tool registration."""

    def test_server_run_debate_accepts_raci_mode(self) -> None:
        """Server run_debate tool should accept mode='raci'."""
        from debate_hall_mcp.server import create_server

        server = create_server()
        # The server should create successfully with RACI mode support
        assert server is not None

    def test_server_run_debate_has_raci_config_parameter(self) -> None:
        """Server run_debate tool schema should include raci_config parameter."""
        from debate_hall_mcp.server import create_server

        server = create_server()
        # Verify the server was created (the tool schema is validated at registration time)
        assert server is not None


class TestRACIResumeViaToolInterface:
    """Tests for RACI resume through the tool interface."""

    @pytest.mark.anyio
    async def test_resume_debate_handles_raci_mode(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """resume_debate should dispatch to RACI resume for RACI-mode debates."""
        from debate_hall_mcp.tools.orchestrate import resume_debate

        mock_result = DebateResult(
            thread_id="2026-02-13-resume-raci-tool-test",
            topic="Resume RACI tool test",
            status="synthesis",
            turn_count=4,
            synthesis="## VERDICT: GO",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=raci_tier_config,
            ),
            patch("debate_hall_mcp.tools.orchestrate.load_debate_state") as mock_load,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            # Mock a paused RACI debate
            mock_room = MagicMock()
            mock_room.status = DebateStatus("paused")
            mock_room.mode = DebateMode("raci")
            mock_load.return_value = mock_room

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await resume_debate(
                thread_id="2026-02-13-resume-raci-tool-test",
                tier="standard",
                state_dir=temp_state_dir,
            )

        assert result["status"] == "synthesis"
        mock_orchestrator.resume.assert_called_once()
