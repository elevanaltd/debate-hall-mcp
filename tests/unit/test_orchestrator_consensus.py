"""Unit tests for consensus loop in DebateOrchestrator (Phase 4: Consensus Implementation).

Tests the consensus loop flow:
- Both approve -> synthesis status
- Wind rejects -> refinement loop
- Wall rejects -> refinement loop
- Max loops exceeded -> stalemate status
- consensus_required=False skips loop
- CONSENSUS_VOTE events emitted
- Turn count reflects all turns including consensus
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.events import EventType, load_events
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import ProviderResponse


@pytest.fixture
def tier_config_consensus() -> TierConfig:
    """Create a tier configuration with consensus enabled."""
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


@pytest.fixture
def tier_config_no_consensus() -> TierConfig:
    """Create a tier configuration with consensus disabled."""
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
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "debates"
    state_dir.mkdir()
    return state_dir


def create_mock_response(content: str, model: str = "test-model") -> ProviderResponse:
    """Create a mock ProviderResponse."""
    return ProviderResponse(
        content=content,
        model=model,
        token_input=100,
        token_output=200,
    )


class TestConsensusLoopBothApprove:
    """Tests for when both Wind and Wall approve."""

    @pytest.mark.anyio
    async def test_both_approve_results_in_synthesis_status(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """When both Wind and Wall approve, debate should close with synthesis status."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            # Initial debate round
            create_mock_response("## WIND - Possibilities\nExpanding..."),
            create_mock_response("## WALL - Validation\nValidating..."),
            create_mock_response("## DOOR - Synthesis\nSynthesizing..."),
            # Consensus round
            create_mock_response("APPROVE\nThe synthesis is well-integrated."),  # Wind
            create_mock_response("APPROVE\nConstraints properly addressed."),  # Wall
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Consensus test")

        assert result.status == "synthesis"

    @pytest.mark.anyio
    async def test_both_approve_includes_synthesis_content(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """When both approve, synthesis should contain Door's synthesis."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)
        door_synthesis = "## DOOR - Final Synthesis\nThe integrated solution..."

        responses = [
            create_mock_response("Wind response"),
            create_mock_response("Wall response"),
            create_mock_response(door_synthesis),
            create_mock_response("APPROVE"),  # Wind
            create_mock_response("APPROVE"),  # Wall
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Synthesis content test")

        assert result.synthesis is not None
        assert "integrated solution" in result.synthesis.lower()


class TestConsensusLoopWindRejects:
    """Tests for when Wind rejects."""

    @pytest.mark.anyio
    async def test_wind_rejects_triggers_refinement(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """When Wind rejects, Door should refine and consensus repeats."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            # Initial round
            create_mock_response("Wind: Initial expansion"),
            create_mock_response("Wall: Initial validation"),
            create_mock_response("Door: Initial synthesis"),
            # First consensus - Wind rejects
            create_mock_response("REJECT\nMissing creative potential."),
            # No Wall vote needed - refinement triggered
            # Refinement
            create_mock_response("Door: Refined synthesis incorporating feedback"),
            # Second consensus - both approve
            create_mock_response("APPROVE\nNow captures possibilities."),
            create_mock_response("APPROVE\nConstraints still valid."),
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Wind rejection test")

        # Should eventually reach synthesis after refinement
        assert result.status == "synthesis"
        # Turn count should include refinement turns
        assert result.turn_count > 3


class TestConsensusLoopWallRejects:
    """Tests for when Wall rejects."""

    @pytest.mark.anyio
    async def test_wall_rejects_triggers_refinement(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """When Wall rejects, Door should refine and consensus repeats."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            # Initial round
            create_mock_response("Wind: Initial expansion"),
            create_mock_response("Wall: Initial validation"),
            create_mock_response("Door: Initial synthesis"),
            # First consensus - Wind approves, Wall rejects
            create_mock_response("APPROVE\nCaptures possibilities."),
            create_mock_response("REJECT\nMissing security constraints."),
            # Refinement
            create_mock_response("Door: Refined synthesis with security constraints"),
            # Second consensus - both approve
            create_mock_response("APPROVE\nStill expansive."),
            create_mock_response("APPROVE\nSecurity addressed."),
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Wall rejection test")

        assert result.status == "synthesis"
        assert result.turn_count > 3


class TestConsensusLoopMaxIterations:
    """Tests for max refinement loop behavior."""

    @pytest.mark.anyio
    async def test_max_loops_exceeded_results_in_stalemate(self, temp_state_dir: Path) -> None:
        """When max_refinement_loops exceeded, debate should end with stalemate."""
        # Use config with max_refinement_loops=2 for faster test
        config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
            wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
            door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
            settings=TierSettings(
                consensus_required=True,
                max_turns=20,
                max_refinement_loops=2,
            ),
        )
        orchestrator = DebateOrchestrator(config, temp_state_dir)

        responses = [
            # Initial round
            create_mock_response("Wind: Initial"),
            create_mock_response("Wall: Initial"),
            create_mock_response("Door: Initial"),
            # Loop 1: reject
            create_mock_response("REJECT"),
            create_mock_response("Door: Refinement 1"),
            # Loop 2: reject
            create_mock_response("REJECT"),
            create_mock_response("Door: Refinement 2"),
            # Loop 3 would exceed max_refinement_loops=2
            create_mock_response("REJECT"),
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Max loops test")

        assert result.status == "stalemate"


class TestConsensusDisabled:
    """Tests for consensus_required=False."""

    @pytest.mark.anyio
    async def test_consensus_disabled_skips_consensus_loop(
        self, tier_config_no_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """When consensus_required=False, should skip consensus loop."""
        orchestrator = DebateOrchestrator(tier_config_no_consensus, temp_state_dir)

        responses = [
            create_mock_response("Wind response"),
            create_mock_response("Wall response"),
            create_mock_response("Door synthesis"),
            # No consensus responses should be needed
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="No consensus test")

        # Should close immediately with synthesis
        assert result.status == "synthesis"
        # Should only have 3 turns (Wind, Wall, Door)
        assert result.turn_count == 3


class TestConsensusVoteEvents:
    """Tests for CONSENSUS_VOTE event emission."""

    @pytest.mark.anyio
    async def test_emits_consensus_vote_event_for_wind(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """Should emit CONSENSUS_VOTE event when Wind votes."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            create_mock_response("Wind"),
            create_mock_response("Wall"),
            create_mock_response("Door"),
            create_mock_response("APPROVE"),  # Wind vote
            create_mock_response("APPROVE"),  # Wall vote
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Wind vote event test")

        events = load_events(result.thread_id, temp_state_dir)
        consensus_events = [e for e in events if e.event_type == EventType.CONSENSUS_VOTE]

        # Should have at least one consensus vote event for Wind
        assert len(consensus_events) >= 1
        wind_votes = [e for e in consensus_events if e.payload.get("role") == "Wind"]
        assert len(wind_votes) >= 1

    @pytest.mark.anyio
    async def test_emits_consensus_vote_event_for_wall(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """Should emit CONSENSUS_VOTE event when Wall votes."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            create_mock_response("Wind"),
            create_mock_response("Wall"),
            create_mock_response("Door"),
            create_mock_response("APPROVE"),  # Wind vote
            create_mock_response("APPROVE"),  # Wall vote
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Wall vote event test")

        events = load_events(result.thread_id, temp_state_dir)
        consensus_events = [e for e in events if e.event_type == EventType.CONSENSUS_VOTE]

        # Should have consensus vote event for Wall
        wall_votes = [e for e in consensus_events if e.payload.get("role") == "Wall"]
        assert len(wall_votes) >= 1

    @pytest.mark.anyio
    async def test_consensus_vote_event_includes_approved_status(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """CONSENSUS_VOTE event should include approved status."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            create_mock_response("Wind"),
            create_mock_response("Wall"),
            create_mock_response("Door"),
            create_mock_response("APPROVE"),  # Wind approves
            create_mock_response("REJECT"),  # Wall rejects
            create_mock_response("Door: Refinement"),
            create_mock_response("APPROVE"),  # Wind
            create_mock_response("APPROVE"),  # Wall
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Vote status event test")

        events = load_events(result.thread_id, temp_state_dir)
        consensus_events = [e for e in events if e.event_type == EventType.CONSENSUS_VOTE]

        # Each vote event should have an 'approved' field
        for event in consensus_events:
            assert "approved" in event.payload


class TestTurnCountWithConsensus:
    """Tests for turn count including consensus turns."""

    @pytest.mark.anyio
    async def test_turn_count_includes_refinement_turns(
        self, tier_config_consensus: TierConfig, temp_state_dir: Path
    ) -> None:
        """Turn count should include Door's refinement turns."""
        orchestrator = DebateOrchestrator(tier_config_consensus, temp_state_dir)

        responses = [
            # Initial round (3 turns)
            create_mock_response("Wind"),
            create_mock_response("Wall"),
            create_mock_response("Door"),
            # Consensus 1: Wind rejects (vote doesn't count as turn)
            create_mock_response("REJECT"),
            # Refinement (1 turn)
            create_mock_response("Door: Refined"),
            # Consensus 2: both approve
            create_mock_response("APPROVE"),
            create_mock_response("APPROVE"),
        ]

        with patch("debate_hall_mcp.orchestrator.create_provider") as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.complete.side_effect = responses
            mock_create_provider.return_value = mock_provider

            result = await orchestrator.run(topic="Turn count test")

        # 3 initial turns + 1 refinement = 4 turns minimum
        assert result.turn_count >= 4
