"""Unit tests for resume_debate tool (Phase 4: Consensus Implementation).

Tests the resume_debate MCP tool:
- Resume from PAUSED status
- Validates status is PAUSED before resuming
- Determines resume point from state
- Returns same dict format as run_debate

CE Blocking Issue Fix (Phase 4):
- Test for resume() with turn_count < 3 (incomplete Wind/Wall/Door sequence)
- Verifies resume() completes missing turns before consensus/close
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateResult
from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, save_debate_state
from debate_hall_mcp.tools.orchestrate import resume_debate


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
            consensus_required=True,
            max_turns=12,
            max_refinement_loops=3,
        ),
    )


def create_paused_debate(thread_id: str, state_dir: Path, topic: str = "Test topic") -> DebateRoom:
    """Create a PAUSED debate room in state directory."""
    room = DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode.FIXED,
        status=DebateStatus.PAUSED,
        max_turns=12,
    )
    save_debate_state(room, state_dir)
    return room


def create_active_debate(thread_id: str, state_dir: Path, topic: str = "Test topic") -> DebateRoom:
    """Create an ACTIVE debate room in state directory."""
    room = DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode.FIXED,
        status=DebateStatus.ACTIVE,
        max_turns=12,
    )
    save_debate_state(room, state_dir)
    return room


class TestResumeDebateValidation:
    """Tests for resume_debate input validation."""

    @pytest.mark.anyio
    async def test_raises_error_for_nonexistent_thread(self, temp_state_dir: Path) -> None:
        """resume_debate should raise error for non-existent thread_id."""
        with (patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,):
            mock_get_state_dir.return_value = temp_state_dir

            with pytest.raises(FileNotFoundError):
                await resume_debate(thread_id="nonexistent-thread")

    @pytest.mark.anyio
    async def test_raises_error_for_active_debate(self, temp_state_dir: Path) -> None:
        """resume_debate should raise error if debate is ACTIVE (not PAUSED)."""
        thread_id = "2026-01-30-active-debate"
        create_active_debate(thread_id, temp_state_dir)

        with (patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,):
            mock_get_state_dir.return_value = temp_state_dir

            with pytest.raises(ValueError, match="PAUSED"):
                await resume_debate(thread_id=thread_id)

    @pytest.mark.anyio
    async def test_raises_error_for_synthesis_debate(self, temp_state_dir: Path) -> None:
        """resume_debate should raise error if debate is already SYNTHESIS."""
        thread_id = "2026-01-30-synthesis-debate"
        room = DebateRoom(
            thread_id=thread_id,
            topic="Completed topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Final synthesis",
        )
        save_debate_state(room, temp_state_dir)

        with (patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,):
            mock_get_state_dir.return_value = temp_state_dir

            with pytest.raises(ValueError, match="PAUSED"):
                await resume_debate(thread_id=thread_id)

    @pytest.mark.anyio
    async def test_raises_error_for_path_unsafe_thread_id(self) -> None:
        """resume_debate should raise error for path-unsafe thread_id."""
        with pytest.raises(ValueError, match="path-unsafe"):
            await resume_debate(thread_id="../evil-path")


class TestResumeDebateExecution:
    """Tests for resume_debate execution flow."""

    @pytest.mark.anyio
    async def test_resumes_paused_debate(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume_debate should resume a PAUSED debate."""
        thread_id = "2026-01-30-paused-debate"
        create_paused_debate(thread_id, temp_state_dir, topic="Paused topic")

        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Paused topic",
            status="synthesis",
            turn_count=5,
            synthesis="Resumed synthesis",
        )

        with (
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_config.return_value = mock_tier_config

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await resume_debate(thread_id=thread_id)

        assert result["thread_id"] == thread_id
        assert result["status"] == "synthesis"

    @pytest.mark.anyio
    async def test_returns_dict_format(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume_debate should return same dict format as run_debate."""
        thread_id = "2026-01-30-format-test"
        create_paused_debate(thread_id, temp_state_dir, topic="Format test topic")

        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Format test topic",
            status="synthesis",
            turn_count=4,
            synthesis="Test synthesis",
        )

        with (
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_config.return_value = mock_tier_config

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await resume_debate(thread_id=thread_id)

        # Should have same keys as run_debate
        assert "thread_id" in result
        assert "topic" in result
        assert "status" in result
        assert "turn_count" in result
        assert "synthesis" in result

    @pytest.mark.anyio
    async def test_uses_tier_from_parameter(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume_debate should use specified tier."""
        thread_id = "2026-01-30-tier-test"
        create_paused_debate(thread_id, temp_state_dir)

        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Test topic",
            status="synthesis",
            turn_count=3,
            synthesis="Synthesis",
        )

        with (
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_config.return_value = mock_tier_config

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(thread_id=thread_id, tier="premium")

        mock_load_config.assert_called_once_with("premium")

    @pytest.mark.anyio
    async def test_default_tier_is_standard(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume_debate should use 'standard' tier by default."""
        thread_id = "2026-01-30-default-tier"
        create_paused_debate(thread_id, temp_state_dir)

        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Test topic",
            status="synthesis",
            turn_count=3,
            synthesis="Synthesis",
        )

        with (
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_config.return_value = mock_tier_config

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(thread_id=thread_id)

        mock_load_config.assert_called_once_with("standard")


class TestResumeDebateResumePoint:
    """Tests for determining resume point from state."""

    @pytest.mark.anyio
    async def test_passes_thread_id_to_orchestrator_resume(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume_debate should pass thread_id to orchestrator.resume()."""
        thread_id = "2026-01-30-resume-point"
        create_paused_debate(thread_id, temp_state_dir, topic="Resume point topic")

        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Resume point topic",
            status="synthesis",
            turn_count=5,
            synthesis="Resumed",
        )

        with (
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_get_state_dir,
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load_config,
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_get_state_dir.return_value = temp_state_dir
            mock_load_config.return_value = mock_tier_config

            mock_orchestrator = MagicMock()
            mock_orchestrator.resume = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            await resume_debate(thread_id=thread_id)

        # Verify orchestrator.resume was called with thread_id
        mock_orchestrator.resume.assert_called_once_with(thread_id=thread_id)


class TestResumeDebateIncompleteTurns:
    """Tests for resume() when debate paused before all Wind/Wall/Door turns completed.

    CE blocking issue: If debate pauses at turn_count < 3, resume() would call
    debate_close() with empty synthesis, causing ValueError.

    Fix requirement: resume() must complete missing turns before consensus/close.
    """

    @pytest.mark.anyio
    async def test_resume_completes_missing_turns_when_paused_after_wind(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume() should complete Wall and Door turns when paused after Wind only.

        Scenario:
        - Debate paused after Wind turn (turn_count=1)
        - Resume should complete Wall turn, then Door turn
        - Then proceed to consensus/close
        """
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.state import Turn, load_debate_state

        thread_id = "2026-01-30-paused-after-wind"

        # Create a PAUSED debate with only Wind turn
        room = DebateRoom(
            thread_id=thread_id,
            topic="Test incomplete turns",
            mode=DebateMode.MEDIATED,
            status=DebateStatus.PAUSED,
            max_turns=12,
            turns=[
                Turn(
                    role="Wind",
                    content="Wind's initial exploration",
                    timestamp=datetime.now(tz=UTC),
                    cognition="PATHOS",
                ),
            ],
        )
        save_debate_state(room, temp_state_dir)

        # Verify the debate state has only 1 turn
        loaded = load_debate_state(thread_id, temp_state_dir)
        assert len(loaded.turns) == 1
        assert loaded.turns[0].role == "Wind"

        # Mock providers to return content for Wall and Door turns
        mock_wall_response = ProviderResponse(
            content="Wall's validation response",
            model="test-wall-model",
            token_input=100,
            token_output=50,
        )
        mock_door_response = ProviderResponse(
            content="Door's synthesis after completing missing turns",
            model="test-door-model",
            token_input=200,
            token_output=100,
        )
        mock_wind_approval = ProviderResponse(
            content="APPROVED: The synthesis is valid.",
            model="test-wind-model",
            token_input=50,
            token_output=20,
        )
        mock_wall_approval = ProviderResponse(
            content="APPROVED: The synthesis is valid.",
            model="test-wall-model",
            token_input=50,
            token_output=20,
        )

        # Create mock providers
        mock_wind_provider = AsyncMock()
        mock_wall_provider = AsyncMock()
        mock_door_provider = AsyncMock()

        # Set up the complete() method to return appropriate responses
        mock_wind_provider.complete = AsyncMock(return_value=mock_wind_approval)
        mock_wall_provider.complete = AsyncMock(
            side_effect=[mock_wall_response, mock_wall_approval]
        )
        mock_door_provider.complete = AsyncMock(return_value=mock_door_response)

        with (
            patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider,
            patch("debate_hall_mcp.orchestrator.append_event"),
        ):
            # Mock provider creation to return our test providers
            def create_provider_side_effect(config: RoleConfig) -> AsyncMock:
                if "wind" in str(config.role).lower():
                    return mock_wind_provider
                elif "wall" in str(config.role).lower():
                    return mock_wall_provider
                else:
                    return mock_door_provider

            mock_create_provider.side_effect = create_provider_side_effect

            from debate_hall_mcp.orchestrator import DebateOrchestrator

            orchestrator = DebateOrchestrator(
                tier_config=mock_tier_config,
                state_dir=temp_state_dir,
            )

            # This should NOT raise ValueError about empty synthesis
            result = await orchestrator.resume(thread_id)

        # Verify debate completed successfully
        assert result.status in ("synthesis", "stalemate")
        assert result.synthesis is not None
        assert result.synthesis != ""

        # Verify turns were added (should now have Wind + Wall + Door = 3+ turns)
        final_state = load_debate_state(thread_id, temp_state_dir)
        assert (
            len(final_state.turns) >= 3
        ), f"Expected at least 3 turns after resume, got {len(final_state.turns)}"

        # Check that Wall and Door turns were added
        roles_after_resume = [t.role for t in final_state.turns]
        assert "Wall" in roles_after_resume, "Wall turn should have been added"
        assert "Door" in roles_after_resume, "Door turn should have been added"

    @pytest.mark.anyio
    async def test_resume_completes_door_turn_when_paused_after_wall(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume() should complete Door turn when paused after Wind+Wall only.

        Scenario:
        - Debate paused after Wall turn (turn_count=2)
        - Resume should complete Door turn
        - Then proceed to consensus/close
        """
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.state import Turn, load_debate_state

        thread_id = "2026-01-30-paused-after-wall"

        # Create turns with proper hash chain
        wind_turn = Turn(
            role="Wind",
            content="Wind's exploration",
            timestamp=datetime.now(tz=UTC),
            cognition="PATHOS",
            previous_hash=None,  # First turn has no previous
        )
        wall_turn = Turn(
            role="Wall",
            content="Wall's validation",
            timestamp=datetime.now(tz=UTC),
            cognition="ETHOS",
            previous_hash=wind_turn.hash,  # Chain to Wind's hash
        )

        # Create a PAUSED debate with Wind and Wall turns (no Door)
        room = DebateRoom(
            thread_id=thread_id,
            topic="Test incomplete - missing Door",
            mode=DebateMode.MEDIATED,
            status=DebateStatus.PAUSED,
            max_turns=12,
            turns=[wind_turn, wall_turn],
        )
        save_debate_state(room, temp_state_dir)

        # Verify initial state
        loaded = load_debate_state(thread_id, temp_state_dir)
        assert len(loaded.turns) == 2
        assert "Door" not in [t.role for t in loaded.turns]

        # Mock providers
        mock_door_response = ProviderResponse(
            content="Door's synthesis completing the debate",
            model="test-door-model",
            token_input=200,
            token_output=100,
        )
        mock_wind_approval = ProviderResponse(
            content="APPROVED: Synthesis is valid.",
            model="test-wind-model",
            token_input=50,
            token_output=20,
        )
        mock_wall_approval = ProviderResponse(
            content="APPROVED: Synthesis is valid.",
            model="test-wall-model",
            token_input=50,
            token_output=20,
        )

        mock_wind_provider = AsyncMock()
        mock_wall_provider = AsyncMock()
        mock_door_provider = AsyncMock()

        mock_wind_provider.complete = AsyncMock(return_value=mock_wind_approval)
        mock_wall_provider.complete = AsyncMock(return_value=mock_wall_approval)
        mock_door_provider.complete = AsyncMock(return_value=mock_door_response)

        with (
            patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider,
            patch("debate_hall_mcp.orchestrator.append_event"),
        ):

            def create_provider_side_effect(config: RoleConfig) -> AsyncMock:
                if "wind" in str(config.role).lower():
                    return mock_wind_provider
                elif "wall" in str(config.role).lower():
                    return mock_wall_provider
                else:
                    return mock_door_provider

            mock_create_provider.side_effect = create_provider_side_effect

            from debate_hall_mcp.orchestrator import DebateOrchestrator

            orchestrator = DebateOrchestrator(
                tier_config=mock_tier_config,
                state_dir=temp_state_dir,
            )

            # This should NOT raise ValueError about empty synthesis
            result = await orchestrator.resume(thread_id)

        # Verify debate completed successfully
        assert result.status in ("synthesis", "stalemate")
        assert result.synthesis is not None
        assert result.synthesis != ""

        # Verify Door turn was added
        final_state = load_debate_state(thread_id, temp_state_dir)
        assert len(final_state.turns) >= 3
        roles_after_resume = [t.role for t in final_state.turns]
        assert "Door" in roles_after_resume, "Door turn should have been added"

    @pytest.mark.anyio
    async def test_resume_no_longer_raises_valueerror_after_fix(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """Verify the CE-identified bug is fixed: resume() no longer raises ValueError.

        This test verifies the fix for the CE-identified bug:
        - Debate paused after Wind turn only (turn_count=1)
        - resume() now completes missing Wall and Door turns
        - No ValueError is raised
        """
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.state import Turn, load_debate_state

        thread_id = "2026-01-30-bug-fix-verification"

        # Create a PAUSED debate with only Wind turn (no Door)
        room = DebateRoom(
            thread_id=thread_id,
            topic="Bug fix verification - should not raise ValueError",
            mode=DebateMode.MEDIATED,
            status=DebateStatus.PAUSED,
            max_turns=12,
            turns=[
                Turn(
                    role="Wind",
                    content="Wind's initial content",
                    timestamp=datetime.now(tz=UTC),
                    cognition="PATHOS",
                ),
            ],
        )
        save_debate_state(room, temp_state_dir)

        # Disable consensus to go straight to close (simpler test)
        mock_tier_config_no_consensus = TierConfig(
            wind=mock_tier_config.wind,
            wall=mock_tier_config.wall,
            door=mock_tier_config.door,
            settings=TierSettings(
                consensus_required=False,  # Skip consensus, go straight to close
                max_turns=12,
                max_refinement_loops=3,
            ),
        )

        # Mock providers to return valid content
        mock_wall_response = ProviderResponse(
            content="Wall's validation response",
            model="test-wall-model",
            token_input=100,
            token_output=50,
        )
        mock_door_response = ProviderResponse(
            content="Door's synthesis after completing missing turns",
            model="test-door-model",
            token_input=200,
            token_output=100,
        )

        mock_wind_provider = AsyncMock()
        mock_wall_provider = AsyncMock()
        mock_door_provider = AsyncMock()

        mock_wind_provider.complete = AsyncMock()
        mock_wall_provider.complete = AsyncMock(return_value=mock_wall_response)
        mock_door_provider.complete = AsyncMock(return_value=mock_door_response)

        with (
            patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider,
            patch("debate_hall_mcp.orchestrator.append_event"),
        ):

            def create_provider_side_effect(config: RoleConfig) -> AsyncMock:
                if "wind" in str(config.role).lower():
                    return mock_wind_provider
                elif "wall" in str(config.role).lower():
                    return mock_wall_provider
                else:
                    return mock_door_provider

            mock_create_provider.side_effect = create_provider_side_effect

            from debate_hall_mcp.orchestrator import DebateOrchestrator

            orchestrator = DebateOrchestrator(
                tier_config=mock_tier_config_no_consensus,
                state_dir=temp_state_dir,
            )

            # After fix, this should NOT raise ValueError
            result = await orchestrator.resume(thread_id)

        # Verify debate completed successfully
        assert result.status == "synthesis"
        assert result.synthesis is not None
        assert result.synthesis != ""

        # Verify all turns were added
        final_state = load_debate_state(thread_id, temp_state_dir)
        assert len(final_state.turns) == 3  # Wind + Wall + Door
        roles = [t.role for t in final_state.turns]
        assert "Wind" in roles
        assert "Wall" in roles
        assert "Door" in roles

    @pytest.mark.anyio
    async def test_resume_completes_wind_turn_when_paused_at_zero_turns(
        self, temp_state_dir: Path, mock_tier_config: TierConfig
    ) -> None:
        """resume() should complete Wind, Wall, Door turns when paused with zero turns.

        CE Blocking Issue #2:
        - A debate can be PAUSED with turn_count=0 if Wind fails immediately after init
        - The current resume() fix handles missing Wall/Door but NOT missing Wind
        - This test verifies resume() handles turn_count=0 by completing Wind first

        Scenario:
        - Debate initialized but Wind provider failed before returning
        - Debate is PAUSED with 0 turns
        - Resume should complete Wind turn FIRST, then Wall, then Door
        - Then proceed to consensus/close
        """
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.state import load_debate_state

        thread_id = "2026-01-30-paused-at-zero-turns"

        # Create a PAUSED debate with ZERO turns (Wind failed immediately after init)
        room = DebateRoom(
            thread_id=thread_id,
            topic="Test zero turns - Wind failed at init",
            mode=DebateMode.MEDIATED,
            status=DebateStatus.PAUSED,
            max_turns=12,
            turns=[],  # No turns - Wind failed before completing
        )
        save_debate_state(room, temp_state_dir)

        # Verify the debate state has 0 turns
        loaded = load_debate_state(thread_id, temp_state_dir)
        assert len(loaded.turns) == 0, "Test precondition: debate should have 0 turns"

        # Disable consensus to go straight to close (simpler test path)
        mock_tier_config_no_consensus = TierConfig(
            wind=mock_tier_config.wind,
            wall=mock_tier_config.wall,
            door=mock_tier_config.door,
            settings=TierSettings(
                consensus_required=False,  # Skip consensus, go straight to close
                max_turns=12,
                max_refinement_loops=3,
            ),
        )

        # Mock providers to return valid content for all three turns
        mock_wind_response = ProviderResponse(
            content="Wind's initial exploration of possibilities",
            model="test-wind-model",
            token_input=100,
            token_output=50,
        )
        mock_wall_response = ProviderResponse(
            content="Wall's validation of constraints",
            model="test-wall-model",
            token_input=100,
            token_output=50,
        )
        mock_door_response = ProviderResponse(
            content="Door's synthesis integrating Wind and Wall",
            model="test-door-model",
            token_input=200,
            token_output=100,
        )

        mock_wind_provider = AsyncMock()
        mock_wall_provider = AsyncMock()
        mock_door_provider = AsyncMock()

        mock_wind_provider.complete = AsyncMock(return_value=mock_wind_response)
        mock_wall_provider.complete = AsyncMock(return_value=mock_wall_response)
        mock_door_provider.complete = AsyncMock(return_value=mock_door_response)

        with (
            patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider,
            patch("debate_hall_mcp.orchestrator.append_event"),
        ):

            def create_provider_side_effect(config: RoleConfig) -> AsyncMock:
                if "wind" in str(config.role).lower():
                    return mock_wind_provider
                elif "wall" in str(config.role).lower():
                    return mock_wall_provider
                else:
                    return mock_door_provider

            mock_create_provider.side_effect = create_provider_side_effect

            from debate_hall_mcp.orchestrator import DebateOrchestrator

            orchestrator = DebateOrchestrator(
                tier_config=mock_tier_config_no_consensus,
                state_dir=temp_state_dir,
            )

            # This should complete all three turns: Wind, Wall, Door
            result = await orchestrator.resume(thread_id)

        # Verify debate completed successfully
        assert result.status == "synthesis"
        assert result.synthesis is not None
        assert result.synthesis != ""

        # Verify Wind was called (the key assertion for this bug fix)
        mock_wind_provider.complete.assert_called_once()

        # Verify all three turns were added in correct order
        final_state = load_debate_state(thread_id, temp_state_dir)
        assert len(final_state.turns) == 3, f"Expected 3 turns, got {len(final_state.turns)}"
        roles = [t.role for t in final_state.turns]
        assert roles == ["Wind", "Wall", "Door"], f"Expected ['Wind', 'Wall', 'Door'], got {roles}"
