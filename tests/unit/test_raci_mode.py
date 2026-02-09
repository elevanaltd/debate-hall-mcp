"""Unit tests for RACI Dialogue Mode (Issue #139).

RACI Mode is a lightweight debate mode (550 tokens vs 90,000 full debate):
- Wind (Responsible): Proposes the action
- Wall (Consulted): Validates constraints/risks or yields
- Door (Accountable): Ratifies the decision

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
def raci_tier_config() -> TierConfig:
    """Create a test tier configuration for RACI mode."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=False,  # RACI never uses consensus loop
            max_turns=3,  # RACI hard limit
            max_refinement_loops=0,  # No refinement in RACI
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
    """Tests for RACI in DebateMode enum."""

    def test_debate_mode_has_raci_value(self) -> None:
        """DebateMode enum should include 'raci' as a valid mode."""
        assert DebateMode.RACI.value == "raci"

    def test_debate_mode_raci_is_str_enum(self) -> None:
        """DebateMode.RACI should be usable as a string."""
        assert str(DebateMode.RACI) == "raci"
        assert DebateMode.RACI.value == "raci"


class TestRaciDebateInit:
    """Tests for debate_init with RACI mode."""

    def test_init_raci_mode_succeeds(self, temp_state_dir: Path) -> None:
        """debate_init should accept mode='raci'."""
        result = debate_init(
            thread_id="2026-02-08-raci-test",
            topic="RACI test topic",
            mode="raci",
            state_dir=temp_state_dir,
        )
        assert result["mode"] == "raci"

    def test_init_raci_enforces_max_turns_3(self, temp_state_dir: Path) -> None:
        """RACI mode should enforce max_turns=3 regardless of input."""
        result = debate_init(
            thread_id="2026-02-08-raci-turns-test",
            topic="RACI turns test",
            mode="raci",
            max_turns=12,  # User tries to set higher limit
            state_dir=temp_state_dir,
        )
        # RACI enforces max_turns=3
        assert result["max_turns"] == 3

    def test_init_raci_enforces_max_rounds_1(self, temp_state_dir: Path) -> None:
        """RACI mode should enforce max_rounds=1 regardless of input."""
        result = debate_init(
            thread_id="2026-02-08-raci-rounds-test",
            topic="RACI rounds test",
            mode="raci",
            max_rounds=4,  # User tries to set higher limit
            state_dir=temp_state_dir,
        )
        # RACI enforces max_rounds=1
        assert result["max_rounds"] == 1

    def test_init_raci_persists_mode_in_state(self, temp_state_dir: Path) -> None:
        """RACI mode should be persisted in debate state."""
        thread_id = "2026-02-08-raci-persist-test"
        debate_init(
            thread_id=thread_id,
            topic="RACI persist test",
            mode="raci",
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.mode == DebateMode.RACI


class TestRaciPrompts:
    """Tests for RACI-specific prompts."""

    def test_raci_wind_prompt_exists(self) -> None:
        """RACI Wind prompt should exist and be distinct from standard."""
        from debate_hall_mcp.prompts import RACI_WIND_PROMPT, WIND_PROMPT

        assert RACI_WIND_PROMPT is not None
        assert len(RACI_WIND_PROMPT) > 0
        # RACI prompt should be more concise
        assert len(RACI_WIND_PROMPT) < len(WIND_PROMPT)

    def test_raci_wall_prompt_exists(self) -> None:
        """RACI Wall prompt should exist with YIELD option."""
        from debate_hall_mcp.prompts import RACI_WALL_PROMPT

        assert RACI_WALL_PROMPT is not None
        assert "YIELD" in RACI_WALL_PROMPT
        assert "APPROVE" in RACI_WALL_PROMPT or "VALIDATE" in RACI_WALL_PROMPT

    def test_raci_door_prompt_exists(self) -> None:
        """RACI Door prompt should exist and focus on ratification."""
        from debate_hall_mcp.prompts import DOOR_PROMPT, RACI_DOOR_PROMPT

        assert RACI_DOOR_PROMPT is not None
        assert len(RACI_DOOR_PROMPT) > 0
        # RACI prompt should be more concise
        assert len(RACI_DOOR_PROMPT) < len(DOOR_PROMPT)

    def test_format_raci_wind_user_prompt(self) -> None:
        """format_raci_wind_user_prompt should format RACI Wind prompt."""
        from debate_hall_mcp.prompts import format_raci_wind_user_prompt

        prompt = format_raci_wind_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "Responsible" in prompt or "propose" in prompt.lower()
        assert "Test action proposal" in prompt

    def test_format_raci_wall_user_prompt(self) -> None:
        """format_raci_wall_user_prompt should include YIELD option."""
        from debate_hall_mcp.prompts import format_raci_wall_user_prompt

        prompt = format_raci_wall_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "YIELD" in prompt
        assert "Test action proposal" in prompt

    def test_format_raci_door_user_prompt(self) -> None:
        """format_raci_door_user_prompt should focus on ratification."""
        from debate_hall_mcp.prompts import format_raci_door_user_prompt

        prompt = format_raci_door_user_prompt(
            topic="Test action proposal",
            thread_id="2026-02-08-test",
        )
        assert "ratif" in prompt.lower() or "Accountable" in prompt
        assert "Test action proposal" in prompt


class TestRaciOrchestrator:
    """Tests for RACI mode in DebateOrchestrator."""

    @pytest.mark.anyio
    async def test_run_raci_returns_debate_result(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_raci() should return a DebateResult."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response(
            "## RACI Response\n\nAction proposed."
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="RACI test topic")

        assert isinstance(result, DebateResult)
        assert result.thread_id is not None
        assert result.topic == "RACI test topic"

    @pytest.mark.anyio
    async def test_run_raci_completes_in_exactly_3_turns(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """RACI should complete in exactly 3 turns (Wind->Wall->Door)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response content")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="3-turn test")

        assert result.turn_count == 3
        assert result.status == "synthesis"

    @pytest.mark.anyio
    async def test_run_raci_calls_wind_wall_door_in_sequence(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """RACI should call Wind, Wall, Door in sequence."""
        call_order: list[str] = []

        def mock_complete(
            system_prompt: str,
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            # Check system_prompt for RACI role identifiers
            if "RACI_WIND" in system_prompt or "Responsible" in system_prompt:
                call_order.append("wind")
            elif "RACI_WALL" in system_prompt or "Consulted" in system_prompt:
                call_order.append("wall")
            elif "RACI_DOOR" in system_prompt or "Accountable" in system_prompt:
                call_order.append("door")
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.run_raci(topic="Sequence test")

        assert call_order == ["wind", "wall", "door"]

    @pytest.mark.anyio
    async def test_run_raci_skips_consensus_loop(self, temp_state_dir: Path) -> None:
        """RACI should skip consensus loop even if consensus_required=True."""
        # Create config with consensus_required=True
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=True,  # Even with this, RACI skips
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

        result = await orchestrator.run_raci(topic="Skip consensus test")

        # Should complete in 3 turns, not more (no consensus loop)
        assert result.turn_count == 3
        # Provider should be called exactly 3 times
        assert mock_provider.complete.call_count == 3

    @pytest.mark.anyio
    async def test_run_raci_uses_raci_prompts(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """RACI should use RACI-specific prompts, not standard prompts."""
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
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.run_raci(topic="Prompt test")

        # Wall prompt should include YIELD option (RACI-specific)
        wall_prompt = captured_prompts[1]  # Second call is Wall
        assert "YIELD" in wall_prompt


class TestRaciWallYield:
    """Tests for Wall YIELD functionality in RACI mode."""

    def test_wall_yield_counts_as_approval(self) -> None:
        """Wall responding with YIELD should count as implicit approval."""
        from debate_hall_mcp.consensus import parse_consensus_response

        # Test the parser directly
        result = parse_consensus_response("YIELD\n\nNo objections to proceed.")

        assert result.approved is True

    @pytest.mark.anyio
    async def test_wall_yield_completes_raci_successfully(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """RACI with Wall YIELD should complete with synthesis status."""
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
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Yield test")

        assert result.status == "synthesis"
        assert result.turn_count == 3


class TestRaciTokenEfficiency:
    """Tests for RACI token efficiency (target: <1000 tokens average)."""

    def test_raci_uses_concise_prompts(self) -> None:
        """RACI prompts should be significantly shorter than standard prompts."""
        from debate_hall_mcp.prompts import (
            DOOR_PROMPT,
            RACI_DOOR_PROMPT,
            RACI_WALL_PROMPT,
            RACI_WIND_PROMPT,
            WALL_PROMPT,
            WIND_PROMPT,
        )

        # RACI prompts should be at least 50% shorter
        assert len(RACI_WIND_PROMPT) < len(WIND_PROMPT) * 0.5
        assert len(RACI_WALL_PROMPT) < len(WALL_PROMPT) * 0.5
        assert len(RACI_DOOR_PROMPT) < len(DOOR_PROMPT) * 0.5


class TestRaciIntegration:
    """Integration tests for RACI mode with run_debate tool.

    These tests verify that run_debate properly dispatches to RACI mode.
    They mock DebateOrchestrator to avoid invoking real CLI providers.
    """

    @pytest.mark.anyio
    async def test_run_debate_with_raci_mode(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate should support mode='raci' parameter."""
        from unittest.mock import MagicMock

        from debate_hall_mcp.orchestrator import DebateResult
        from debate_hall_mcp.tools.orchestrate import run_debate

        # Create mock debate result
        mock_result = DebateResult(
            thread_id="2026-02-08-raci-integration-test",
            topic="RACI integration test",
            status="synthesis",
            turn_count=3,
            synthesis="## Ratification\n\nDecision ratified.",
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
                topic="RACI integration test",
                tier="standard",
                mode="raci",
                state_dir=temp_state_dir,
            )

        assert result["turn_count"] == 3
        assert result["status"] == "synthesis"
        # Verify run_raci was called (not run)
        mock_orchestrator.run_raci.assert_called_once()

    @pytest.mark.anyio
    async def test_run_debate_raci_initializes_with_raci_mode(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """run_debate with mode='raci' should initialize debate in RACI mode."""
        from unittest.mock import MagicMock

        from debate_hall_mcp.orchestrator import DebateResult
        from debate_hall_mcp.tools.orchestrate import run_debate

        # Initialize a real RACI debate first to verify mode is set correctly
        thread_id = "2026-02-08-raci-mode-init-test"
        debate_init(
            thread_id=thread_id,
            topic="RACI mode init test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        # Create mock debate result with the same thread_id
        mock_result = DebateResult(
            thread_id=thread_id,
            topic="RACI mode init test",
            status="synthesis",
            turn_count=3,
            synthesis="## Ratification\n\nDecision ratified.",
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
                topic="RACI mode init test",
                tier="standard",
                mode="raci",
                thread_id=thread_id,
                state_dir=temp_state_dir,
            )

        # Verify run_raci was called with the correct thread_id
        mock_orchestrator.run_raci.assert_called_once_with(
            topic="RACI mode init test", thread_id=thread_id
        )

        # Load state and verify mode from the debate we initialized
        room = load_debate_state(result["thread_id"], temp_state_dir)
        assert room.mode == DebateMode.RACI


class TestRaciI3Compliance:
    """Tests for I3::FINITE_DIALECTIC_CLOSURE compliance in RACI mode."""

    def test_raci_max_turns_cannot_exceed_3(self, temp_state_dir: Path) -> None:
        """RACI mode should never allow more than 3 turns (I3 constraint)."""
        thread_id = "2026-02-08-raci-i3-test"
        debate_init(
            thread_id=thread_id,
            topic="I3 test",
            mode="raci",
            max_turns=100,  # Try to exceed
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.max_turns == 3

    def test_raci_max_rounds_cannot_exceed_1(self, temp_state_dir: Path) -> None:
        """RACI mode should never allow more than 1 round (I3 constraint)."""
        thread_id = "2026-02-08-raci-i3-rounds-test"
        debate_init(
            thread_id=thread_id,
            topic="I3 rounds test",
            mode="raci",
            max_rounds=10,  # Try to exceed
            state_dir=temp_state_dir,
        )
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.max_rounds == 1

    @pytest.mark.anyio
    async def test_raci_guarantees_termination(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """RACI should guarantee termination within 3 turns (I3)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Termination test")

        # Must terminate within resource bounds
        assert result.turn_count <= 3
        assert result.status in ["synthesis", "exhaustion"]


class TestRaciResume:
    """Tests for RACI mode resume lifecycle (CRS blocking issue fix).

    CRS Review Finding: resume() ignores room.mode and treats all paused debates
    as standard mode. This causes RACI debates to:
    1. Use standard (heavy) prompts instead of RACI prompts
    2. Lose Responsible/Consulted/Accountable instructions
    3. Enter consensus loop, violating RACI's "no consensus" design
    """

    @pytest.mark.anyio
    async def test_resume_raci_uses_raci_prompts(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Resumed RACI debate should use RACI prompts, not standard prompts.

        This is the core test for the CRS blocking issue: ensuring that
        resume() dispatches to RACI-specific logic when room.mode is RACI.
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

        # First: Create a RACI debate and simulate a pause (e.g., timeout on Wind)
        from debate_hall_mcp.state import DebateStatus, save_debate_state

        thread_id = "2026-02-08-raci-resume-test"
        debate_init(
            thread_id=thread_id,
            topic="RACI resume test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        # Simulate pause (what happens when provider times out during run_raci)
        room = load_debate_state(thread_id, temp_state_dir)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Verify room is in RACI mode and PAUSED
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.mode == DebateMode.RACI
        assert room.status == DebateStatus.PAUSED

        # Resume the RACI debate
        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete successfully
        assert result.status == "synthesis"
        assert result.turn_count == 3

        # CRITICAL ASSERTION: Prompts should be RACI-specific
        # RACI prompts contain "Responsible", "Consulted", "Accountable"
        # Standard prompts contain "Wind (PATHOS) - The Ideator", etc.
        for user_prompt in captured_user_prompts:
            # RACI prompts should NOT contain standard identifiers
            assert (
                "Wind (PATHOS) - The Ideator" not in user_prompt
            ), "Resume used standard Wind prompt instead of RACI prompt"
            assert (
                "Wall (ETHOS) - The Validator" not in user_prompt
            ), "Resume used standard Wall prompt instead of RACI prompt"
            assert (
                "Door (LOGOS) - The Synthesizer" not in user_prompt
            ), "Resume used standard Door prompt instead of RACI prompt"

        # At least one prompt should contain RACI-specific language
        all_prompts = " ".join(captured_user_prompts)
        assert (
            "RACI" in all_prompts or "Responsible" in all_prompts or "Consulted" in all_prompts
        ), "Resume prompts did not contain RACI-specific language"

    @pytest.mark.anyio
    async def test_resume_raci_skips_consensus_loop(self, temp_state_dir: Path) -> None:
        """Resumed RACI debate should skip consensus loop even if consensus_required=True."""
        # Create tier config with consensus_required=True
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=True,  # This should be ignored for RACI
                max_refinement_loops=3,
            ),
        )

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        # Create and pause a RACI debate
        from debate_hall_mcp.state import DebateStatus, save_debate_state

        thread_id = "2026-02-08-raci-no-consensus-test"
        debate_init(
            thread_id=thread_id,
            topic="RACI no consensus test",
            mode="raci",
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
    async def test_resume_raci_with_partial_turns_completes(
        self, raci_tier_config: TierConfig, temp_state_dir: Path
    ) -> None:
        """Resumed RACI debate with partial turns should complete remaining turns."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        # Create RACI debate with 1 turn already completed (Wind)
        from datetime import UTC, datetime

        from debate_hall_mcp.state import DebateStatus, Turn, save_debate_state

        thread_id = "2026-02-08-raci-partial-test"
        debate_init(
            thread_id=thread_id,
            topic="RACI partial test",
            mode="raci",
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
            raci_tier_config,
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
            mode="mediated",  # Standard mode, not RACI
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
