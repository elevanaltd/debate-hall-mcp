"""Unit tests for RACI orchestrator integration.

Tests for run_raci() and _resume_raci() methods on DebateOrchestrator.

TDD: These tests are written first (RED phase) before implementation.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator, DebateResult
from debate_hall_mcp.providers import ProviderResponse
from debate_hall_mcp.raci import RACIConfig
from debate_hall_mcp.state import (
    DebateStatus,
    Turn,
    load_debate_state,
    save_debate_state,
)


@pytest.fixture
def raci_tier_config() -> TierConfig:
    """Create a test tier configuration for RACI mode."""
    return TierConfig(
        wind=RoleConfig(provider="cli", cli="claude"),
        wall=RoleConfig(provider="cli", cli="codex"),
        door=RoleConfig(provider="cli", cli="gemini"),
        settings=TierSettings(
            consensus_required=False,
            max_turns=12,
            max_refinement_loops=0,
        ),
    )


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def simple_raci_config() -> RACIConfig:
    """Create a simple RACI config with one consulted agent."""
    return RACIConfig(
        responsible="architect",
        accountable="tech-lead",
        consulted=["security-reviewer"],
        informed=["pm"],
    )


@pytest.fixture
def minimal_raci_config() -> RACIConfig:
    """Create a minimal RACI config with no consulted agents."""
    return RACIConfig(
        responsible="architect",
        accountable="tech-lead",
    )


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


class TestRunRACIBasic:
    """Tests for run_raci() basic functionality."""

    @pytest.mark.anyio
    async def test_run_raci_returns_debate_result(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        simple_raci_config: RACIConfig,
    ) -> None:
        """run_raci() should return a DebateResult."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response content")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(
            topic="RACI test topic",
            raci_config=simple_raci_config,
        )

        assert isinstance(result, DebateResult)
        assert result.thread_id is not None
        assert result.topic == "RACI test topic"

    @pytest.mark.anyio
    async def test_run_raci_completes_in_manifest_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        simple_raci_config: RACIConfig,
    ) -> None:
        """RACI should complete in exactly manifest.specs turns (R+C+R+A+I = 5)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(
            topic="Turn count test",
            raci_config=simple_raci_config,
        )

        # R(proposal) + C(advice) + R(rebuttal) + A(verdict) + I(observation) = 5 turns
        assert result.turn_count == 5
        assert result.status == "synthesis"

    @pytest.mark.anyio
    async def test_run_raci_minimal_config_two_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        minimal_raci_config: RACIConfig,
    ) -> None:
        """RACI with no consulted agents should complete in 2 turns (R+A)."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(
            topic="Minimal RACI test",
            raci_config=minimal_raci_config,
        )

        # R(proposal) + A(verdict) = 2 turns
        assert result.turn_count == 2
        assert result.status == "synthesis"

    @pytest.mark.anyio
    async def test_run_raci_closes_with_verdict_as_synthesis(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        minimal_raci_config: RACIConfig,
    ) -> None:
        """RACI should close the debate with A's verdict as synthesis."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # R proposal
                return create_mock_provider_response("## PROPOSAL\nI propose we deploy the API.")
            else:  # A verdict
                return create_mock_provider_response(
                    "## VERDICT: GO\n**Decision**: GO\n**Reasons**: Proposal is sound."
                )

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(
            topic="Verdict synthesis test",
            raci_config=minimal_raci_config,
        )

        assert result.synthesis is not None
        assert "VERDICT" in result.synthesis or "GO" in result.synthesis

    @pytest.mark.anyio
    async def test_run_raci_no_consensus_loop(
        self,
        temp_state_dir: Path,
        simple_raci_config: RACIConfig,
    ) -> None:
        """RACI should have no consensus loop (A-verdict IS the decision)."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(
                consensus_required=True,  # Even if true, RACI skips consensus
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

        result = await orchestrator.run_raci(
            topic="No consensus test",
            raci_config=simple_raci_config,
        )

        # Should complete in exactly manifest turns, no extra consensus calls
        # R + C + R(rebuttal) + A + I(observation) = 5
        assert result.turn_count == 5
        assert mock_provider.complete.call_count == 5

    @pytest.mark.anyio
    async def test_run_raci_with_custom_thread_id(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        minimal_raci_config: RACIConfig,
    ) -> None:
        """run_raci() should accept optional custom thread_id."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(
            topic="Custom thread test",
            raci_config=minimal_raci_config,
            thread_id="2026-02-13-custom-raci-test",
        )

        assert result.thread_id == "2026-02-13-custom-raci-test"


class TestRunRACISequence:
    """Tests for RACI turn sequence execution."""

    @pytest.mark.anyio
    async def test_raci_follows_manifest_sequence(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """RACI should follow the manifest sequence exactly."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["security", "ux"],
        )

        call_order: list[str] = []

        def mock_complete(
            system_prompt: str,
            user_prompt: str,
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            # Detect turn type from system prompt (more reliable than user prompt)
            if "RACI_ACCOUNTABLE" in system_prompt or "Decision Maker" in system_prompt:
                call_order.append("A-verdict")
            elif "RACI_CONSULTED" in system_prompt or "Advisor" in system_prompt:
                call_order.append("C-advice")
            elif "RACI_RESPONSIBLE" in system_prompt or "Responsible" in system_prompt:
                # Distinguish proposal from rebuttal via user prompt
                if "rebuttal" in user_prompt.lower() or "synthesize" in user_prompt.lower():
                    call_order.append("R-rebuttal")
                else:
                    call_order.append("R-proposal")
            else:
                call_order.append("unknown")
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.run_raci(topic="Sequence test", raci_config=config)

        # R(proposal) -> C1(advice) -> C2(advice) -> R(rebuttal) -> A(verdict)
        assert len(call_order) == 5
        assert call_order[0] == "R-proposal"
        assert call_order[1] == "C-advice"
        assert call_order[2] == "C-advice"
        assert call_order[3] == "R-rebuttal"
        assert call_order[4] == "A-verdict"


class TestRunRACIPauseRecovery:
    """Tests for RACI pause/resume lifecycle."""

    @pytest.mark.anyio
    async def test_run_raci_pauses_on_failure(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
        minimal_raci_config: RACIConfig,
    ) -> None:
        """RACI should mark debate as PAUSED on provider failure."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("Proposal content")
            raise RuntimeError("Provider failed")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        with pytest.raises(RuntimeError, match="Provider failed"):
            await orchestrator.run_raci(
                topic="Failure test",
                raci_config=minimal_raci_config,
            )

        # Debate should be paused, not lost
        # (we need to find the thread_id from the state dir)
        import os

        state_files = [f for f in os.listdir(temp_state_dir) if f.endswith(".json")]
        assert len(state_files) == 1
        thread_id = state_files[0].replace(".json", "")
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.status == DebateStatus.PAUSED


class TestResumeRACIBasic:
    """Tests for resume support with RACI mode."""

    @pytest.mark.anyio
    async def test_resume_raci_completes_remaining_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Resuming a paused RACI debate should complete remaining turns."""
        from debate_hall_mcp.raci import compile_raci_manifest
        from debate_hall_mcp.tools.init import debate_init

        raci_config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["reviewer"],
        )
        manifest = compile_raci_manifest(raci_config)

        # Create RACI debate and add first turn (R proposal), then pause
        thread_id = "2026-02-13-resume-raci-test"
        debate_init(
            thread_id=thread_id,
            topic="Resume RACI test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.turn_manifest = manifest

        # Add first turn (R proposal)
        wind_turn = Turn(
            role="architect",
            content="## PROPOSAL\nI propose we deploy the new API.",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(wind_turn)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Should complete: 1 existing + 3 new = 4 total (R+C+R(rebuttal)+A)
        assert result.turn_count == 4
        assert result.status == "synthesis"
        # Provider called 3 times for remaining turns
        assert mock_provider.complete.call_count == 3

    @pytest.mark.anyio
    async def test_resume_raci_uses_raci_prompts(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Resumed RACI debate should use RACI-specific prompts."""
        from debate_hall_mcp.raci import compile_raci_manifest
        from debate_hall_mcp.tools.init import debate_init

        raci_config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
        )
        manifest = compile_raci_manifest(raci_config)

        thread_id = "2026-02-13-resume-prompts-test"
        debate_init(
            thread_id=thread_id,
            topic="Resume prompts test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.turn_manifest = manifest
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

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

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        await orchestrator.resume(thread_id)

        # Verify RACI prompts are used (not standard Wind/Wall/Door)
        all_prompts = " ".join(captured_user_prompts)
        assert "Wind (PATHOS)" not in all_prompts, "Resume used standard prompts"
        # Should contain RACI-specific language
        all_prompts_lower = all_prompts.lower()
        assert (
            "raci" in all_prompts_lower
            or "proposal" in all_prompts_lower
            or "verdict" in all_prompts_lower
        )


class TestRACIManifestAutoMaxTurns:
    """Tests for automatic max_turns from manifest (I3 compliance)."""

    @pytest.mark.anyio
    async def test_max_turns_set_from_manifest_length(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """RACI should auto-set max_turns from manifest.specs length (I3)."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["c1", "c2", "c3"],
        )

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Max turns test", raci_config=config)

        # Load state and verify max_turns matches manifest
        room = load_debate_state(result.thread_id, temp_state_dir)
        # R + C1 + C2 + C3 + R(rebuttal) + A = 6
        assert room.max_turns == 6


class TestRACIObservationTurns:
    """Tests for RACI Informed agent OBSERVATION turns."""

    @pytest.mark.anyio
    async def test_run_raci_with_informed_agents_gets_observation_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """RACI with informed agents should execute OBSERVATION turns after verdict."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["ops", "security"],
        )

        call_order: list[str] = []

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            # Detect based on "Your Role:" line in user prompt
            if "Your Role: Informed Observer" in user_prompt:
                call_order.append("I-observation")
            elif "Your Role: Accountable" in user_prompt:
                call_order.append("A-verdict")
            elif "Your Role: Responsible" in user_prompt:
                call_order.append("R-proposal")
            else:
                call_order.append("unknown")
            return create_mock_provider_response("Response")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Observation test", raci_config=config)

        # R(proposal) + A(verdict) + I1(observation) + I2(observation) = 4
        assert result.turn_count == 4
        assert call_order == ["R-proposal", "A-verdict", "I-observation", "I-observation"]

    @pytest.mark.anyio
    async def test_verdict_used_as_synthesis_not_last_observation(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Debate synthesis should be the A-verdict, not the last I-observation."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy API")
            elif call_count == 2:
                return create_mock_provider_response("## VERDICT: GO\nDecision is GO. Proceed.")
            else:
                return create_mock_provider_response("OBSERVATION: Impact on my domain noted.")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Synthesis test", raci_config=config)

        # Synthesis should be the verdict, not the observation
        assert result.synthesis is not None
        assert "VERDICT" in result.synthesis
        assert "OBSERVATION" not in result.synthesis

    @pytest.mark.anyio
    async def test_max_turns_includes_observation_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """max_turns should include I-observation turns in count."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["reviewer"],
            informed=["pm", "ops"],
        )

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response("Response")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Max turns I test", raci_config=config)

        room = load_debate_state(result.thread_id, temp_state_dir)
        # R + C + R(rebuttal) + A + I1 + I2 = 6
        assert room.max_turns == 6
        assert result.turn_count == 6

    @pytest.mark.anyio
    async def test_resume_raci_with_observation_turns(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Resuming a paused RACI debate should complete remaining I-observation turns."""
        from debate_hall_mcp.raci import compile_raci_manifest
        from debate_hall_mcp.tools.init import debate_init

        raci_config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm"],
        )
        manifest = compile_raci_manifest(raci_config)

        # Create RACI debate, add R-proposal and A-verdict, then pause before I-observation
        thread_id = "2026-02-14-resume-observation-test"
        debate_init(
            thread_id=thread_id,
            topic="Resume observation test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.turn_manifest = manifest
        room.max_turns = len(manifest.specs)

        # Add R and A turns
        r_turn = Turn(
            role="dev",
            content="PROPOSAL: Deploy now.",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(r_turn)
        a_turn = Turn(
            role="lead",
            content="VERDICT: GO. Proceed with deployment.",
            timestamp=datetime.now(UTC),
            previous_hash=r_turn.hash,
        )
        room.turns.append(a_turn)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = create_mock_provider_response(
            "OBSERVATION: Impact noted for PM domain."
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # 2 existing + 1 new I-observation = 3 total
        assert result.turn_count == 3
        assert result.status == "synthesis"
        # Provider called once for the remaining I-observation turn
        assert mock_provider.complete.call_count == 1
        # Synthesis should be the verdict, not the observation
        assert "VERDICT" in result.synthesis or "GO" in result.synthesis


class TestITurnFailureDegradation:
    """Tests for W2: Graceful I-turn failure degradation.

    When an Informed agent's OBSERVATION turn fails, the debate should:
    1. Record a sentinel turn in the transcript (gapless hash chain - I4)
    2. Log the failure
    3. Continue executing other I-turns
    4. Close the debate normally with the verdict as synthesis
    """

    @pytest.mark.anyio
    async def test_i_turn_failure_records_sentinel_content(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Failed I-turn should record sentinel content in transcript."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy API")
            elif call_count == 2:
                return create_mock_provider_response("VERDICT: GO")
            else:
                # I-turn fails
                raise RuntimeError("Provider timeout")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["ops"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Sentinel test", raci_config=config)

        # Debate should still close successfully
        assert result.status == "synthesis"

        # Verify sentinel turn was recorded
        room = load_debate_state(result.thread_id, temp_state_dir)
        sentinel_turns = [t for t in room.turns if "[OBSERVATION FAILED]" in t.content]
        assert len(sentinel_turns) == 1
        assert "ops" in sentinel_turns[0].content
        assert "RuntimeError" in sentinel_turns[0].content

    @pytest.mark.anyio
    async def test_i_turn_failure_does_not_prevent_debate_closure(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Failed I-turn should not prevent debate from closing with verdict."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy API")
            elif call_count == 2:
                return create_mock_provider_response("VERDICT: GO. Approved.")
            else:
                raise RuntimeError("I-turn failure")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Closure test", raci_config=config)

        assert result.status == "synthesis"
        assert "VERDICT" in result.synthesis
        assert "GO" in result.synthesis

    @pytest.mark.anyio
    async def test_multiple_i_turns_partial_failure(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Multiple I-turns where one fails but others succeed."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy")
            elif call_count == 2:
                return create_mock_provider_response("VERDICT: GO")
            elif call_count == 3:
                # First I-turn (ops) succeeds
                return create_mock_provider_response("OBSERVATION: Ops impact noted.")
            elif call_count == 4:
                # Second I-turn (security) fails
                raise RuntimeError("Security provider down")
            else:
                return create_mock_provider_response("OBSERVATION: PM impact noted.")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["ops", "security", "pm"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="Partial failure test", raci_config=config)

        assert result.status == "synthesis"

        # Load transcript
        room = load_debate_state(result.thread_id, temp_state_dir)
        # Should have 5 turns: R + A + I(ok) + I(sentinel) + I(ok)
        assert len(room.turns) == 5

        # One sentinel turn
        sentinel_turns = [t for t in room.turns if "[OBSERVATION FAILED]" in t.content]
        assert len(sentinel_turns) == 1
        assert "security" in sentinel_turns[0].content

        # Two successful observation turns
        obs_turns = [
            t
            for t in room.turns
            if "OBSERVATION:" in t.content and "[OBSERVATION FAILED]" not in t.content
        ]
        assert len(obs_turns) == 2

    @pytest.mark.anyio
    async def test_all_i_turns_fail_debate_still_closes(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """All I-turns fail -- debate still closes with verdict as synthesis."""
        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy")
            elif call_count == 2:
                return create_mock_provider_response("VERDICT: GO. Approved.")
            else:
                # All I-turns fail
                raise RuntimeError("All providers down")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["ops", "pm"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.run_raci(topic="All fail test", raci_config=config)

        # Debate still closes successfully
        assert result.status == "synthesis"
        assert "VERDICT" in result.synthesis
        assert "GO" in result.synthesis

        # Both I-turns should have sentinel content
        room = load_debate_state(result.thread_id, temp_state_dir)
        sentinel_turns = [t for t in room.turns if "[OBSERVATION FAILED]" in t.content]
        assert len(sentinel_turns) == 2

    @pytest.mark.anyio
    async def test_r_a_turn_failure_still_pauses(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """R/C/A turn failure should still cause PAUSED state (unchanged behavior)."""
        import os

        call_count = 0

        def mock_complete(
            system_prompt: str,  # noqa: ARG001
            user_prompt: str,  # noqa: ARG001
            **kwargs: Any,  # noqa: ARG001
        ) -> ProviderResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_provider_response("PROPOSAL: Deploy")
            else:
                # A-turn (verdict) fails -- this should NOT be gracefully degraded
                raise RuntimeError("Accountable provider failed")

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = mock_complete

        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm"],
        )

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        with pytest.raises(RuntimeError, match="Accountable provider failed"):
            await orchestrator.run_raci(topic="A-fail test", raci_config=config)

        # Debate should be PAUSED (not closed)
        state_files = [f for f in os.listdir(temp_state_dir) if f.endswith(".json")]
        assert len(state_files) == 1
        thread_id = state_files[0].replace(".json", "")
        room = load_debate_state(thread_id, temp_state_dir)
        assert room.status == DebateStatus.PAUSED

    @pytest.mark.anyio
    async def test_resume_raci_i_turn_failure_degradation(
        self,
        raci_tier_config: TierConfig,
        temp_state_dir: Path,
    ) -> None:
        """Resumed RACI debate should also gracefully degrade I-turn failures."""
        from debate_hall_mcp.raci import compile_raci_manifest
        from debate_hall_mcp.tools.init import debate_init

        raci_config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["ops"],
        )
        manifest = compile_raci_manifest(raci_config)

        # Set up paused debate with R + A turns already done
        thread_id = "2026-02-14-resume-i-fail-test"
        debate_init(
            thread_id=thread_id,
            topic="Resume I-fail test",
            mode="raci",
            state_dir=temp_state_dir,
        )

        room = load_debate_state(thread_id, temp_state_dir)
        room.turn_manifest = manifest
        room.max_turns = len(manifest.specs)

        # Add R and A turns
        r_turn = Turn(
            role="dev",
            content="PROPOSAL: Deploy now.",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(r_turn)
        a_turn = Turn(
            role="lead",
            content="VERDICT: GO.",
            timestamp=datetime.now(UTC),
            previous_hash=r_turn.hash,
        )
        room.turns.append(a_turn)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, temp_state_dir)

        # Mock provider that fails for I-turn
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("Provider down")

        orchestrator = DebateOrchestrator(
            raci_tier_config,
            temp_state_dir,
            provider_factory=create_mock_provider_factory(mock_provider),
        )

        result = await orchestrator.resume(thread_id)

        # Debate should still close successfully
        assert result.status == "synthesis"
        assert "VERDICT" in result.synthesis or "GO" in result.synthesis

        # Sentinel turn should be recorded
        room = load_debate_state(thread_id, temp_state_dir)
        sentinel_turns = [t for t in room.turns if "[OBSERVATION FAILED]" in t.content]
        assert len(sentinel_turns) == 1
        assert "ops" in sentinel_turns[0].content
