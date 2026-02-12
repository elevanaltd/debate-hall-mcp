"""Unit tests for Speed Dialogue Mode (Issue #139).

Speed Mode is a lightweight debate mode (550 tokens vs 90,000 full debate):
- Wind (Proposer): Proposes the action
- Wall (Validator): Validates constraints/risks or yields
- Door (Ratifier): Ratifies the decision

Key characteristics:
- Single-round (max_rounds: 1, max_turns: 3)
- Wall can "YIELD" for zero-friction approval
- No consensus loop (guaranteed 3-turn closure)
- Enforces I3::FINITE_DIALECTIC_CLOSURE

TDD: These tests are written first (RED phase) before implementation.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator, DebateResult
from debate_hall_mcp.providers import ProviderResponse
from debate_hall_mcp.state import DebateMode, load_debate_state
from debate_hall_mcp.tools.init import debate_init


@pytest.fixture
def speed_tier_config() -> TierConfig:
    """Create a test tier configuration for Speed mode."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=False,  # Speed never uses consensus loop
            max_turns=3,  # Speed hard limit
            max_refinement_loops=0,  # No refinement in Speed
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


def create_mock_provider_factory(mock_provider: AsyncMock) -> Any:
    """Create a provider factory that returns the mock provider."""

    def factory(role_config: RoleConfig) -> Any:  # noqa: ARG001
        return mock_provider

    return factory


class TestDebateModeEnum:
    """Tests for Speed in DebateMode enum."""

    def test_debate_mode_has_speed_value(self) -> None:
        """DebateMode enum should include 'speed' as a valid mode."""
        assert DebateMode.SPEED.value == "speed"

    def test_debate_mode_speed_is_str_enum(self) -> None:
        """DebateMode.SPEED should be usable as a string."""
        assert str(DebateMode.SPEED) == "speed"
        assert DebateMode.SPEED.value == "speed"


class TestSpeedDebateInit:
    """Tests for debate_init with Speed mode."""

    def test_init_speed_mode_succeeds(self, temp_state_dir: Path) -> None:
        """debate_init should accept mode='speed'."""
        result = debate_init(
            thread_id="2026-02-08-speed-test",
            topic="Speed test topic",
            mode="speed",
            state_dir=temp_state_dir,
        )
        assert result["mode"] == "speed"

    def test_init_speed_enforces_max_turns_3(self, temp_state_dir: Path) -> None:
        """Speed mode should enforce max_turns=3 regardless of input."""
        result = debate_init(
            thread_id="2026-02-08-speed-turns-test",
            topic="Speed turns test",
            mode="speed",
            max_turns=12,  # User tries to set higher limit
            state_dir=temp_state_dir,
        )
        # Speed enforces max_turns=3
        assert result["max_turns"] == 3

    def test_init_speed_enforces_max_rounds_1(self, temp_state_dir: Path) -> None:
        """Speed mode should enforce max_rounds=1 regardless of input."""
        result = debate_init(
            thread_id="2026-02-08-speed-rounds-test",
            topic="Speed rounds test",
            mode="speed",
            max_rounds=4,  # User tries to set higher limit
            state_dir=temp_state_dir,
        )
        # Speed enforces max_rounds=1
        assert result["max_rounds"] == 1

    def test_init_speed_persists_mode_in_state(self, temp_state_dir: Path) -> None:
        """Speed mode should be persisted in debate state."""
        thread_id = "2026-02-08-speed-persist-test"
        debate_init(
            thread_id=thread_id,
            topic="Speed persist test",
            mode="speed",
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.mode == DebateMode.SPEED


class TestSpeedPrompts:
    """Tests for Speed-specific prompts."""

    def test_speed_wind_prompt_exists(self) -> None:
        """Speed Wind prompt should exist and be distinct from standard."""
        from debate_hall_mcp.prompts import SPEED_WIND_PROMPT, WIND_PROMPT

        assert SPEED_WIND_PROMPT is not None
        assert len(SPEED_WIND_PROMPT) > 0
        # Speed prompt should be more concise
        assert len(SPEED_WIND_PROMPT) < len(WIND_PROMPT)

    def test_speed_wall_prompt_exists(self) -> None:
        """Speed Wall prompt should exist with YIELD option."""
        from debate_hall_mcp.prompts import SPEED_WALL_PROMPT

        assert SPEED_WALL_PROMPT is not None
        assert "YIELD" in SPEED_WALL_PROMPT
        assert "APPROVE" in SPEED_WALL_PROMPT or "VALIDATE" in SPEED_WALL_PROMPT

    def test_speed_door_prompt_exists(self) -> None:
        """Speed Door prompt should exist and focus on ratification."""
        from debate_hall_mcp.prompts import DOOR_PROMPT, SPEED_DOOR_PROMPT

        assert SPEED_DOOR_PROMPT is not None
        assert len(SPEED_DOOR_PROMPT) > 0
        # Speed prompt should be more concise
        assert len(SPEED_DOOR_PROMPT) < len(DOOR_PROMPT)

    def test_format_speed_wind_user_prompt(self) -> None:
        """format_speed_wind_user_prompt should format Speed Wind prompt."""
        from debate_hall_mcp.prompts import format_speed_wind_user_prompt

        prompt = format_speed_wind_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "Proposer" in prompt or "propose" in prompt.lower()
        assert "Test action proposal" in prompt

    def test_format_speed_wall_user_prompt(self) -> None:
        """format_speed_wall_user_prompt should include YIELD option."""
        from debate_hall_mcp.prompts import format_speed_wall_user_prompt

        prompt = format_speed_wall_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "YIELD" in prompt
        assert "Test action proposal" in prompt

    def test_format_speed_door_user_prompt(self) -> None:
        """format_speed_door_user_prompt should focus on ratification."""
        from debate_hall_mcp.prompts import format_speed_door_user_prompt

        prompt = format_speed_door_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "ratif" in prompt.lower() or "Ratifier" in prompt
        assert "Test action proposal" in prompt


class TestSpeedOrchestrator:
    """Tests for Speed mode in DebateOrchestrator."""

    @pytest.mark.anyio
    async def test_run_speed_returns_debate_result(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_speed() should return a DebateResult."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response(
            "## Speed Response\n\nAction proposed."
        )

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_speed(topic="Speed test topic")

        assert isinstance(result, DebateResult)
        assert result.thread_id is not None
        assert result.topic == "Speed test topic"

    @pytest.mark.anyio
    async def test_run_speed_completes_in_exactly_3_turns(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Speed should complete in exactly 3 turns (Wind->Wall->Door)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response content")

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_speed(topic="3-turn test")

        assert result.turn_count == 3
        assert result.status == "synthesis"

    @pytest.mark.anyio
    async def test_run_speed_calls_wind_wall_door_in_sequence(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Speed should call Wind, Wall, Door in sequence."""
        call_order: list[str] = []

        def mock_complete(
            system_prompt: str,
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            # Check system_prompt for Speed role identifiers
            if "SPEED_WIND" in system_prompt or "Proposer" in system_prompt:
                call_order.append("wind")
            elif "SPEED_WALL" in system_prompt or "Validator" in system_prompt:
                call_order.append("wall")
            elif "SPEED_DOOR" in system_prompt or "Ratifier" in system_prompt:
                call_order.append("door")
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.run_speed(topic="Sequence test")

        assert call_order == ["wind", "wall", "door"]

    @pytest.mark.anyio
    async def test_run_speed_skips_consensus_loop(self, temp_state_dir: Path) -> None:
        """Speed should skip consensus loop even if consensus_required=True."""
        # Create config with consensus_required=True
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=True,  # Even with this, Speed skips
                max_refinement_loops=3,
            ),
        )

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_speed(topic="Skip consensus test")

        # Should complete in 3 turns, not more (no consensus loop)
        assert result.turn_count == 3
        # Provider should be called exactly 3 times
        assert mock_provider.complete.call_count == 3

    @pytest.mark.anyio
    async def test_run_speed_uses_speed_prompts(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Speed should use Speed-specific prompts, not standard prompts."""
        captured_prompts: list[str] = []

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            captured_prompts.append(user_prompt)
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.run_speed(topic="Prompt test")

        # Wall prompt should include YIELD option (Speed-specific)
        wall_prompt = captured_prompts[1]  # Second call is Wall
        assert "YIELD" in wall_prompt


class TestSpeedWallYield:
    """Tests for Wall YIELD functionality in Speed mode."""

    def test_wall_yield_counts_as_approval(self) -> None:
        """Wall responding with YIELD should count as implicit approval."""
        from debate_hall_mcp.consensus import parse_consensus_response

        # Test the parser directly
        result = parse_consensus_response("YIELD\n\nNo objections to proceed.")

        assert result.approved is True

    @pytest.mark.anyio
    async def test_wall_yield_completes_speed_successfully(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Speed with Wall YIELD should complete with synthesis status."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Wind
                return create_mock_provider_response("## Proposal\n\nI propose we do X.")
            elif call_count == 2:  # Wall
                return create_mock_provider_response("YIELD\n\nNo objections to the proposal.")
            else:  # Door
                return create_mock_provider_response("## Ratification\n\nProposal is ratified.")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_speed(topic="Yield test")

        assert result.status == "synthesis"
        assert result.turn_count == 3


class TestSpeedTokenEfficiency:
    """Tests for Speed token efficiency (target: <1000 tokens average)."""

    def test_speed_uses_concise_prompts(self) -> None:
        """Speed prompts should be significantly shorter than standard prompts."""
        from debate_hall_mcp.prompts import (
            DOOR_PROMPT,
            SPEED_DOOR_PROMPT,
            SPEED_WALL_PROMPT,
            SPEED_WIND_PROMPT,
            WALL_PROMPT,
            WIND_PROMPT,
        )

        # Speed prompts should be at least 50% shorter
        assert len(SPEED_WIND_PROMPT) < len(WIND_PROMPT) * 0.5
        assert len(SPEED_WALL_PROMPT) < len(WALL_PROMPT) * 0.5
        assert len(SPEED_DOOR_PROMPT) < len(DOOR_PROMPT) * 0.5


class TestSpeedIntegration:
    """Integration tests for Speed mode with run_debate tool.

    These tests verify that run_debate properly dispatches to Speed mode.
    They mock DebateOrchestrator to avoid invoking real CLI providers.
    """

    @pytest.mark.anyio
    async def test_run_debate_with_speed_mode(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate should support mode='speed' parameter."""
        from unittest.mock import MagicMock

        from debate_hall_mcp.orchestrator import DebateResult
        from debate_hall_mcp.tools.orchestrate import run_debate

        # Create mock debate result
        mock_result = DebateResult(
            thread_id="2026-02-08-speed-integration-test",
            topic="Speed integration test",
            status="synthesis",
            turn_count=3,
            synthesis="## Ratification\n\nDecision ratified.",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=speed_tier_config,
            ),
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run_speed = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(
                topic="Speed integration test",
                tier="standard",
                mode="speed",
                state_dir=temp_state_dir,
            )

        assert result["turn_count"] == 3
        assert result["status"] == "synthesis"
        # Verify run_speed was called (not run)
        mock_orchestrator.run_speed.assert_called_once()

    @pytest.mark.anyio
    async def test_run_debate_speed_initializes_with_speed_mode(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate with mode='speed' should initialize debate in Speed mode."""
        from unittest.mock import MagicMock

        from debate_hall_mcp.orchestrator import DebateResult
        from debate_hall_mcp.tools.orchestrate import run_debate

        # Initialize a real Speed debate first to verify mode is set correctly
        thread_id = "2026-02-08-speed-mode-init-test"
        debate_init(
            thread_id=thread_id,
            topic="Speed mode init test",
            mode="speed",
            state_dir=temp_state_dir,
        )

        # Create mock debate result with the same thread_id
        mock_result = DebateResult(
            thread_id=thread_id,
            topic="Speed mode init test",
            status="synthesis",
            turn_count=3,
            synthesis="## Ratification\n\nDecision ratified.",
        )

        with (
            patch(
                "debate_hall_mcp.tools.orchestrate.load_tier_config",
                return_value=speed_tier_config,
            ),
            patch(
                "debate_hall_mcp.tools.orchestrate.DebateOrchestrator"
            ) as mock_orchestrator_class,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run_speed = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator

            result = await run_debate(
                topic="Speed mode init test",
                tier="standard",
                mode="speed",
                thread_id=thread_id,
                state_dir=temp_state_dir,
            )

        # Verify run_speed was called with the correct thread_id
        mock_orchestrator.run_speed.assert_called_once_with(
            topic="Speed mode init test", thread_id=thread_id
        )

        # Load state and verify mode from the debate we initialized
        room = load_debate_state(result["thread_id"], temp_state_dir)
        assert room.mode == DebateMode.SPEED


class TestSpeedI3Compliance:
    """Tests for I3::FINITE_DIALECTIC_CLOSURE compliance in Speed mode."""

    def test_speed_max_turns_cannot_exceed_3(self, temp_state_dir: Path) -> None:
        """Speed mode should never allow more than 3 turns (I3 constraint)."""
        thread_id = "2026-02-08-speed-i3-test"
        debate_init(
            thread_id=thread_id,
            topic="I3 test",
            mode="speed",
            max_turns=100,  # Try to exceed
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.max_turns == 3

    def test_speed_max_rounds_cannot_exceed_1(self, temp_state_dir: Path) -> None:
        """Speed mode should never allow more than 1 round (I3 constraint)."""
        thread_id = "2026-02-08-speed-i3-rounds-test"
        debate_init(
            thread_id=thread_id,
            topic="I3 rounds test",
            mode="speed",
            max_rounds=10,  # Try to exceed
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.max_rounds == 1

    @pytest.mark.anyio
    async def test_speed_guarantees_termination(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Speed should guarantee termination within 3 turns (I3)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_speed(topic="Termination test")

        # Must terminate within resource bounds
        assert result.turn_count <= 3
        assert result.status in ["synthesis", "exhaustion"]


class TestSpeedResume:
    """Tests for Speed mode resume lifecycle (CRS blocking issue fix).

    CRS Review Finding: resume() ignores room.mode and treats all paused debates
    as standard mode. This causes Speed debates to:
    1. Use standard (heavy) prompts instead of Speed prompts
    2. Lose Proposer/Validator/Ratifier instructions
    3. Enter consensus loop, violating Speed's "no consensus" design
    """

    @pytest.mark.anyio
    async def test_resume_speed_uses_speed_prompts(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Resumed Speed debate should use Speed prompts, not standard prompts.

        This is the core test for the CRS blocking issue: ensuring that
        resume() dispatches to Speed-specific logic when room.mode is SPEED.
        """
        captured_user_prompts: list[str] = []
        captured_system_prompts: list[str] = []
        call_count = 0

        def mock_complete(
            system_prompt: str,
            user_prompt: str,
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            captured_user_prompts.append(user_prompt)
            captured_system_prompts.append(system_prompt)

            if call_count == 1:  # Wind
                return create_mock_provider_response("## PROPOSAL\n**Action**: Do X")
            elif call_count == 2:  # Wall
                return create_mock_provider_response("APPROVE\nNo objections.")
            else:  # Door
                return create_mock_provider_response("## RATIFICATION\n**Decision**: APPROVED")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        # First: Create a Speed debate and simulate a pause (e.g., timeout on Wind)
        from debate_hall_mcp.state import DebateStatus, save_debate_state

        thread_id = "2026-02-08-speed-resume-test"
        debate_init(
            thread_id=thread_id,
            topic="Speed resume test",
            mode="speed",
            state_dir=temp_state_dir,
        )

        # Simulate pause (what happens when provider times out during run_speed)
        room = load_debate_state(thread_id, temp_state_dir)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Verify room is in Speed mode and PAUSED
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.mode == DebateMode.SPEED
        assert room.status == DebateStatus.PAUSED

        # Resume the Speed debate
        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete successfully
        assert result.status == "synthesis"
        assert result.turn_count == 3

        # CRITICAL ASSERTION: Prompts should be Speed-specific
        # Speed prompts contain "Proposer", "Validator", "Ratifier"
        # Standard prompts contain "Wind (PATHOS) - The Ideator", etc.
        for user_prompt in captured_user_prompts:
            # Speed prompts should NOT contain standard identifiers
            assert (
                "Wind (PATHOS) - The Ideator" not in user_prompt
            ), "Resume used standard Wind prompt instead of Speed prompt"
            assert (
                "Wall (ETHOS) - The Validator" not in user_prompt
            ), "Resume used standard Wall prompt instead of Speed prompt"
            assert (
                "Door (LOGOS) - The Synthesizer" not in user_prompt
            ), "Resume used standard Door prompt instead of Speed prompt"

        # At least one prompt should contain Speed-specific language
        all_prompts = " ".join(captured_user_prompts)
        assert (
            "Speed" in all_prompts or "Proposer" in all_prompts or "Validator" in all_prompts
        ), "Resume prompts did not contain Speed-specific language"

    @pytest.mark.anyio
    async def test_resume_speed_skips_consensus_loop(self, temp_state_dir: Path) -> None:
        """Resumed Speed debate should skip consensus loop even if consensus_required=True."""
        # Create tier config with consensus_required=True
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=True,  # This should be ignored for Speed
                max_refinement_loops=3,
            ),
        )

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        # Create and pause a Speed debate
        from debate_hall_mcp.state import DebateStatus, save_debate_state

        thread_id = "2026-02-08-speed-no-consensus-test"
        debate_init(
            thread_id=thread_id,
            topic="Speed no consensus test",
            mode="speed",
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Resume
        orchestrator = DebateOrchestrator(
            tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete in exactly 3 turns (no consensus loop calls)
        assert result.turn_count == 3
        # Provider called exactly 3 times (Wind, Wall, Door - no approval prompts)
        assert mock_provider.complete.call_count == 3

    @pytest.mark.anyio
    async def test_resume_speed_with_partial_turns_completes(
        self, speed_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Resumed Speed debate with partial turns should complete remaining turns."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        # Create Speed debate with 1 turn already completed (Wind)
        from datetime import UTC, datetime

        from debate_hall_mcp.state import DebateStatus, Turn, save_debate_state

        thread_id = "2026-02-08-speed-partial-test"
        debate_init(
            thread_id=thread_id,
            topic="Speed partial test",
            mode="speed",
            state_dir=temp_state_dir,
        )

        # Add a Wind turn and pause
        room = load_debate_state(thread_id, temp_state_dir)
        wind_turn = Turn(
            role="Wind",
            content="## PROPOSAL\n**Action**: Test action",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(wind_turn)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Resume
        orchestrator = DebateOrchestrator(
            speed_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete with 3 turns total (1 existing + 2 new)
        assert result.turn_count == 3
        assert result.status == "synthesis"
        # Provider called 2 times (Wall, Door - Wind already done)
        assert mock_provider.complete.call_count == 2

    @pytest.mark.anyio
    async def test_resume_standard_mode_unchanged(self, temp_state_dir: Path) -> None:
        """Standard mode resume should continue to work as before (regression test)."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=False,
                max_refinement_loops=0,
            ),
        )

        captured_user_prompts: list[str] = []

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            captured_user_prompts.append(user_prompt)
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        # Create a STANDARD (mediated) debate and pause
        from debate_hall_mcp.state import DebateStatus, save_debate_state

        thread_id = "2026-02-08-standard-resume-test"
        debate_init(
            thread_id=thread_id,
            topic="Standard resume test",
            mode="mediated",  # Standard mode, not Speed
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Resume
        orchestrator = DebateOrchestrator(
            tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete
        assert result.status == "synthesis"

        # Standard prompts should be used (contain standard identifiers)
        all_prompts = " ".join(captured_user_prompts)
        assert (
            "Wind (PATHOS)" in all_prompts or "Wall (ETHOS)" in all_prompts
        ), "Standard resume did not use standard prompts"
