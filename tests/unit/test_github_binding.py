"""Unit tests for GitHubBinding state extension (Issue #15).

TDD Discipline: RED->GREEN->REFACTOR
Tests the GitHubBinding model and its integration with DebateRoom.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    Turn,
    load_debate_state,
    save_debate_state,
)


class TestGitHubBindingModel:
    """Test GitHubBinding model structure."""

    def test_github_binding_has_required_fields(self) -> None:
        """GitHubBinding model has repo, target_id, target_type fields."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDOtest123",
            target_type="discussion",
        )

        assert binding.repo == "owner/repo"
        assert binding.target_id == "D_kwDOtest123"
        assert binding.target_type == "discussion"

    def test_github_binding_defaults(self) -> None:
        """GitHubBinding has sensible defaults for tracking fields."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="123",
            target_type="issue",
        )

        # Default: no turns synced yet
        assert binding.last_synced_turn == 0
        # Default: empty list of comment IDs
        assert binding.comment_ids == []

    def test_github_binding_tracks_synced_turns(self) -> None:
        """GitHubBinding tracks last synced turn index."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=3,
        )

        assert binding.last_synced_turn == 3

    def test_github_binding_stores_comment_ids(self) -> None:
        """GitHubBinding stores list of posted comment node IDs."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            comment_ids=["DC_kwDO1", "DC_kwDO2", "DC_kwDO3"],
        )

        assert len(binding.comment_ids) == 3
        assert binding.comment_ids[0] == "DC_kwDO1"

    def test_github_binding_validates_target_type(self) -> None:
        """GitHubBinding only accepts 'discussion' or 'issue' as target_type."""
        from debate_hall_mcp.state import GitHubBinding

        # Valid types
        GitHubBinding(repo="o/r", target_id="1", target_type="discussion")
        GitHubBinding(repo="o/r", target_id="1", target_type="issue")

        # Invalid type should raise
        with pytest.raises(ValueError, match="target_type"):
            GitHubBinding(repo="o/r", target_id="1", target_type="pull_request")


class TestDebateRoomWithGitHubBinding:
    """Test DebateRoom integration with GitHubBinding."""

    def test_debate_room_has_optional_github_binding(self) -> None:
        """DebateRoom has optional github_binding field."""
        room = DebateRoom(
            thread_id="2025-01-02-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
        )

        # Default: no GitHub binding
        assert room.github_binding is None

    def test_debate_room_with_github_binding(self) -> None:
        """DebateRoom can have GitHubBinding attached."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="elevanaltd/debate-hall-mcp",
            target_id="D_kwDO123abc",
            target_type="discussion",
        )

        room = DebateRoom(
            thread_id="2025-01-02-github-test",
            topic="GitHub integration test",
            mode=DebateMode.FIXED,
            github_binding=binding,
        )

        assert room.github_binding is not None
        assert room.github_binding.repo == "elevanaltd/debate-hall-mcp"
        assert room.github_binding.target_type == "discussion"


class TestGitHubBindingPersistence:
    """Test GitHubBinding persistence via JSON."""

    def test_github_binding_persists_through_save_load(self, tmp_path: Path) -> None:
        """GitHubBinding is preserved through save/load cycle."""
        from debate_hall_mcp.state import GitHubBinding

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_kwDO1", "DC_kwDO2"],
        )

        room = DebateRoom(
            thread_id="2025-01-02-persist-test",
            topic="Persistence test",
            mode=DebateMode.FIXED,
            github_binding=binding,
        )

        # Add a turn to make it more realistic
        turn = Turn(
            role="Wind",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)

        # Save and reload
        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded_room = load_debate_state("2025-01-02-persist-test", state_dir)

        # Verify GitHubBinding persisted
        assert loaded_room.github_binding is not None
        assert loaded_room.github_binding.repo == "owner/repo"
        assert loaded_room.github_binding.target_id == "D_kwDO123"
        assert loaded_room.github_binding.target_type == "discussion"
        assert loaded_room.github_binding.last_synced_turn == 2
        assert loaded_room.github_binding.comment_ids == ["DC_kwDO1", "DC_kwDO2"]

    def test_room_without_binding_still_works(self, tmp_path: Path) -> None:
        """Rooms without GitHubBinding persist normally."""
        room = DebateRoom(
            thread_id="2025-01-02-no-binding",
            topic="No binding test",
            mode=DebateMode.FIXED,
        )

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)
        loaded_room = load_debate_state("2025-01-02-no-binding", state_dir)

        assert loaded_room.github_binding is None
