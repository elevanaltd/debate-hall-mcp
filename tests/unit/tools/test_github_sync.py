"""Unit tests for github_sync_debate tool (Issue #15).

TDD Discipline: RED->GREEN->REFACTOR
Tests the github_sync_debate tool for syncing debate turns to GitHub.
All tests use mocked GitHub API - no actual GitHub API calls.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    GitHubBinding,
    Turn,
    save_debate_state,
)


def create_test_room(
    thread_id: str,
    turns: list[Turn] | None = None,
    github_binding: GitHubBinding | None = None,
    max_turns: int = 12,
) -> DebateRoom:
    """Helper to create a test DebateRoom."""
    return DebateRoom(
        thread_id=thread_id,
        topic="Test Topic",
        mode=DebateMode.FIXED,
        max_turns=max_turns,
        turns=turns or [],
        github_binding=github_binding,
    )


class TestGitHubSyncDebateBasics:
    """Test basic github_sync_debate functionality."""

    def test_sync_debate_requires_existing_thread(self, tmp_path: Path) -> None:
        """Syncing non-existent thread raises FileNotFoundError."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        with pytest.raises(FileNotFoundError, match="No state file found"):
            github_sync_debate(
                thread_id="nonexistent-thread",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

    def test_sync_debate_creates_binding_if_not_exists(self, tmp_path: Path) -> None:
        """First sync creates GitHubBinding in room state."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Create room without binding
        room = create_test_room("2025-01-02-test-sync")
        turn = Turn(
            role="Wind",
            content="Test content",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)
        save_debate_state(room, tmp_path)

        # Mock GitHub client
        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.return_value = {
                "id": "DC_kwDO123",
                "url": "https://github.com/test",
            }

            github_sync_debate(
                thread_id="2025-01-02-test-sync",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        # Check binding was created
        from debate_hall_mcp.state import load_debate_state

        updated_room = load_debate_state("2025-01-02-test-sync", tmp_path)
        assert updated_room.github_binding is not None
        assert updated_room.github_binding.repo == "owner/repo"
        assert updated_room.github_binding.target_id == "D_kwDO123"

    def test_sync_debate_returns_sync_summary(self, tmp_path: Path) -> None:
        """Sync returns summary with synced turn count."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Create room with turns
        room = create_test_room("2025-01-02-summary-test")
        for i in range(3):
            turn = Turn(
                role=["Wind", "Wall", "Door"][i % 3],
                content=f"Turn {i + 1} content",
                timestamp=datetime.now(UTC),
                previous_hash=room.turns[-1].hash if room.turns else None,
            )
            room.turns.append(turn)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.return_value = {
                "id": "DC_test",
                "url": "https://github.com/test",
            }

            result = github_sync_debate(
                thread_id="2025-01-02-summary-test",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        assert result["thread_id"] == "2025-01-02-summary-test"
        assert result["synced_count"] == 3
        assert "comment_ids" in result
        assert len(result["comment_ids"]) == 3


class TestGitHubSyncIdempotency:
    """Test idempotent sync behavior (no duplicate comments)."""

    def test_sync_only_posts_new_turns(self, tmp_path: Path) -> None:
        """Sync skips already-synced turns (idempotent)."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Create room with binding showing 2 turns already synced
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_1", "DC_2"],
        )

        room = create_test_room("2025-01-02-idempotent", github_binding=binding)
        for i in range(4):  # 4 total turns, 2 already synced
            turn = Turn(
                role=["Wind", "Wall", "Door", "Wind"][i],
                content=f"Turn {i + 1}",
                timestamp=datetime.now(UTC),
                previous_hash=room.turns[-1].hash if room.turns else None,
            )
            room.turns.append(turn)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.return_value = {
                "id": "DC_new",
                "url": "https://github.com/test",
            }

            result = github_sync_debate(
                thread_id="2025-01-02-idempotent",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        # Should only sync 2 new turns (turns 3 and 4)
        assert result["synced_count"] == 2
        assert mock_client.post_discussion_comment.call_count == 2

    def test_sync_no_turns_to_sync(self, tmp_path: Path) -> None:
        """Sync returns 0 when all turns already synced."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_1", "DC_2"],
        )

        room = create_test_room("2025-01-02-all-synced", github_binding=binding)
        for i in range(2):  # 2 turns, both synced
            turn = Turn(
                role=["Wind", "Wall"][i],
                content=f"Turn {i + 1}",
                timestamp=datetime.now(UTC),
                previous_hash=room.turns[-1].hash if room.turns else None,
            )
            room.turns.append(turn)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = github_sync_debate(
                thread_id="2025-01-02-all-synced",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        assert result["synced_count"] == 0
        mock_client.post_discussion_comment.assert_not_called()


class TestGitHubSyncDiscussion:
    """Test syncing to GitHub Discussions (GraphQL API)."""

    def test_sync_to_discussion_uses_graphql(self, tmp_path: Path) -> None:
        """Syncing to discussion uses GraphQL API."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-discussion")
        room.turns.append(
            Turn(
                role="Wind",
                content="Discussion content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.return_value = {
                "id": "DC_discussion",
                "url": "https://github.com/test",
            }

            github_sync_debate(
                thread_id="2025-01-02-discussion",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        # Verify discussion-specific API was called
        mock_client.post_discussion_comment.assert_called_once()
        mock_client.post_issue_comment.assert_not_called()


class TestGitHubSyncIssue:
    """Test syncing to GitHub Issues (REST API)."""

    def test_sync_to_issue_uses_rest(self, tmp_path: Path) -> None:
        """Syncing to issue uses REST API."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-issue")
        room.turns.append(
            Turn(
                role="Wind",
                content="Issue content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_issue_comment.return_value = {
                "node_id": "IC_issue",
                "html_url": "https://github.com/test",
            }

            github_sync_debate(
                thread_id="2025-01-02-issue",
                repo="owner/repo",
                target_id="42",  # Issue number as string
                target_type="issue",
                state_dir=tmp_path,
            )

        # Verify issue-specific API was called
        mock_client.post_issue_comment.assert_called_once()
        mock_client.post_discussion_comment.assert_not_called()

    def test_sync_to_issue_extracts_comment_node_id(self, tmp_path: Path) -> None:
        """Issue sync stores node_id in comment_ids list."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-issue-nodeid")
        room.turns.append(
            Turn(
                role="Wind",
                content="Content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_issue_comment.return_value = {
                "node_id": "IC_kwDO123abc",
                "html_url": "https://github.com/test",
            }

            result = github_sync_debate(
                thread_id="2025-01-02-issue-nodeid",
                repo="owner/repo",
                target_id="42",
                target_type="issue",
                state_dir=tmp_path,
            )

        assert "IC_kwDO123abc" in result["comment_ids"]


class TestGitHubSyncStateUpdates:
    """Test that sync properly updates room state."""

    def test_sync_updates_last_synced_turn(self, tmp_path: Path) -> None:
        """Sync updates last_synced_turn in binding."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-update-last")
        for i in range(3):
            room.turns.append(
                Turn(
                    role=["Wind", "Wall", "Door"][i],
                    content=f"Turn {i + 1}",
                    timestamp=datetime.now(UTC),
                    previous_hash=room.turns[-1].hash if room.turns else None,
                )
            )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.return_value = {
                "id": "DC_test",
                "url": "https://github.com/test",
            }

            github_sync_debate(
                thread_id="2025-01-02-update-last",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        from debate_hall_mcp.state import load_debate_state

        updated_room = load_debate_state("2025-01-02-update-last", tmp_path)
        assert updated_room.github_binding is not None
        assert updated_room.github_binding.last_synced_turn == 3

    def test_sync_accumulates_comment_ids(self, tmp_path: Path) -> None:
        """Sync appends new comment IDs to existing list."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Start with 2 synced turns
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_1", "DC_2"],
        )

        room = create_test_room("2025-01-02-accumulate", github_binding=binding)
        for i in range(4):
            room.turns.append(
                Turn(
                    role=["Wind", "Wall", "Door", "Wind"][i],
                    content=f"Turn {i + 1}",
                    timestamp=datetime.now(UTC),
                    previous_hash=room.turns[-1].hash if room.turns else None,
                )
            )
        save_debate_state(room, tmp_path)

        comment_counter = 3

        def mock_post(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            nonlocal comment_counter
            result = {"id": f"DC_{comment_counter}", "url": "https://github.com/test"}
            comment_counter += 1
            return result

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.side_effect = mock_post

            github_sync_debate(
                thread_id="2025-01-02-accumulate",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        from debate_hall_mcp.state import load_debate_state

        updated_room = load_debate_state("2025-01-02-accumulate", tmp_path)
        assert updated_room.github_binding is not None
        assert updated_room.github_binding.comment_ids == ["DC_1", "DC_2", "DC_3", "DC_4"]


class TestGitHubSyncValidation:
    """Test input validation for github_sync_debate."""

    def test_sync_validates_target_type(self, tmp_path: Path) -> None:
        """Sync rejects invalid target_type."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-invalid-type")
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="target_type"):
            github_sync_debate(
                thread_id="2025-01-02-invalid-type",
                repo="owner/repo",
                target_id="123",
                target_type="pull_request",  # Invalid
                state_dir=tmp_path,
            )

    def test_sync_detects_binding_conflict(self, tmp_path: Path) -> None:
        """Sync detects when trying to sync to different target."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Room already bound to different target
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO_original",
            target_type="discussion",
            last_synced_turn=1,
        )
        room = create_test_room("2025-01-02-conflict", github_binding=binding)
        room.turns.append(
            Turn(
                role="Wind",
                content="Content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        # Try to sync to different target
        with pytest.raises(ValueError, match="already bound"):
            github_sync_debate(
                thread_id="2025-01-02-conflict",
                repo="owner/repo",
                target_id="D_kwDO_different",  # Different target
                target_type="discussion",
                state_dir=tmp_path,
            )


class TestGitHubSyncEmptyDebate:
    """Test syncing debates with no turns."""

    def test_sync_empty_debate_returns_zero(self, tmp_path: Path) -> None:
        """Syncing debate with no turns returns 0 synced."""
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-empty")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = github_sync_debate(
                thread_id="2025-01-02-empty",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        assert result["synced_count"] == 0
        assert result["comment_ids"] == []


class TestGitHubSyncPartialFailureRecovery:
    """Test partial failure recovery (Blocking Issue #3).

    When posting multiple turns, if turn N succeeds but turn N+1 fails,
    the state must be persisted after EACH successful post.
    This prevents duplicate comments on retry.
    """

    def test_sync_persists_state_after_each_successful_post(self, tmp_path: Path) -> None:
        """State is persisted after each successful post, not just at the end.

        If turn 1 posts successfully and turn 2 fails, turn 1's comment_id
        must be persisted so retrying doesn't duplicate turn 1.
        """
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Create room with 3 turns
        room = create_test_room("2025-01-02-partial-fail")
        for i in range(3):
            room.turns.append(
                Turn(
                    role=["Wind", "Wall", "Door"][i],
                    content=f"Turn {i + 1}",
                    timestamp=datetime.now(UTC),
                    previous_hash=room.turns[-1].hash if room.turns else None,
                )
            )
        save_debate_state(room, tmp_path)

        call_count = 0

        def mock_post_fail_on_second(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"id": "DC_turn1", "url": "https://github.com/test"}
            else:
                raise GitHubAPIError("Simulated failure on turn 2")

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.side_effect = mock_post_fail_on_second

            # Should raise on the second turn
            with pytest.raises(GitHubAPIError, match="Simulated failure"):
                github_sync_debate(
                    thread_id="2025-01-02-partial-fail",
                    repo="owner/repo",
                    target_id="D_kwDO123",
                    target_type="discussion",
                    state_dir=tmp_path,
                )

        # Critical: Despite failure, the first turn's progress MUST be saved
        recovered_room = load_debate_state("2025-01-02-partial-fail", tmp_path)
        assert recovered_room.github_binding is not None
        assert recovered_room.github_binding.last_synced_turn == 1  # First turn was saved
        assert recovered_room.github_binding.comment_ids == ["DC_turn1"]

    def test_sync_retry_after_partial_failure_no_duplicates(self, tmp_path: Path) -> None:
        """Retrying after partial failure must not duplicate already-posted turns."""
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Create room with 2 turns
        room = create_test_room("2025-01-02-retry-test")
        for i in range(2):
            room.turns.append(
                Turn(
                    role=["Wind", "Wall"][i],
                    content=f"Turn {i + 1}",
                    timestamp=datetime.now(UTC),
                    previous_hash=room.turns[-1].hash if room.turns else None,
                )
            )
        save_debate_state(room, tmp_path)

        attempt = 0
        posted_turns: list[int] = []

        def mock_post_with_tracking(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            nonlocal attempt, posted_turns
            attempt += 1
            posted_turns.append(attempt)
            if attempt == 2:
                raise GitHubAPIError("First attempt at turn 2 fails")
            return {"id": f"DC_turn{attempt}", "url": "https://github.com/test"}

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.side_effect = mock_post_with_tracking

            # First attempt: turn 1 succeeds, turn 2 fails
            with pytest.raises(GitHubAPIError):
                github_sync_debate(
                    thread_id="2025-01-02-retry-test",
                    repo="owner/repo",
                    target_id="D_kwDO123",
                    target_type="discussion",
                    state_dir=tmp_path,
                )

        # Reset for retry: turn 2 should now succeed
        def mock_post_success(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            nonlocal attempt
            attempt += 1
            return {"id": f"DC_turn{attempt}", "url": "https://github.com/test"}

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_discussion_comment.side_effect = mock_post_success

            result = github_sync_debate(
                thread_id="2025-01-02-retry-test",
                repo="owner/repo",
                target_id="D_kwDO123",
                target_type="discussion",
                state_dir=tmp_path,
            )

        # Should only sync 1 turn on retry (turn 2), NOT turn 1 again
        assert result["synced_count"] == 1
        # Turn 1 was posted once (attempt 1), turn 2 was posted twice (attempts 2 failed, 3 success)
        # But we only want turn 2 to be synced on retry
        assert mock_client.post_discussion_comment.call_count == 1


class TestGitHubSyncEmptyCommentIdHandling:
    """Test handling of empty or invalid comment IDs."""

    def test_sync_raises_on_empty_comment_id_from_discussion(self, tmp_path: Path) -> None:
        """Empty comment_id from discussion API must raise error, not advance state."""
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-empty-id")
        room.turns.append(
            Turn(
                role="Wind",
                content="Content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            # Return empty string for id (the problematic case)
            mock_client.post_discussion_comment.return_value = {
                "id": "",  # Empty!
                "url": "https://github.com/test",
            }

            # Should raise because we got an empty comment_id
            with pytest.raises(GitHubAPIError, match="comment.*id|empty"):
                github_sync_debate(
                    thread_id="2025-01-02-empty-id",
                    repo="owner/repo",
                    target_id="D_kwDO123",
                    target_type="discussion",
                    state_dir=tmp_path,
                )

    def test_sync_raises_on_empty_node_id_from_issue(self, tmp_path: Path) -> None:
        """Empty node_id from issue API must raise error, not advance state."""
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        room = create_test_room("2025-01-02-empty-nodeid")
        room.turns.append(
            Turn(
                role="Wind",
                content="Content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.github_sync.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post_issue_comment.return_value = {
                "node_id": "",  # Empty!
                "html_url": "https://github.com/test",
            }

            with pytest.raises(GitHubAPIError, match="comment.*id|empty|node_id"):
                github_sync_debate(
                    thread_id="2025-01-02-empty-nodeid",
                    repo="owner/repo",
                    target_id="42",
                    target_type="issue",
                    state_dir=tmp_path,
                )


class TestGitHubSyncRepoMismatchDetection:
    """Test repo validation in binding conflict detection (Advisory Issue)."""

    def test_sync_detects_repo_mismatch_conflict(self, tmp_path: Path) -> None:
        """Binding conflict check must include repo validation.

        If debate is bound to owner/repo-a but caller tries to sync to
        owner/repo-b (same target_id), it should fail.
        """
        from debate_hall_mcp.tools.github_sync import github_sync_debate

        # Room bound to different repo
        binding = GitHubBinding(
            repo="owner/repo-original",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=1,
            comment_ids=["DC_1"],
        )
        room = create_test_room("2025-01-02-repo-mismatch", github_binding=binding)
        room.turns.append(
            Turn(
                role="Wind",
                content="Content",
                timestamp=datetime.now(UTC),
                previous_hash=None,
            )
        )
        save_debate_state(room, tmp_path)

        # Try to sync to same target_id but different repo
        with pytest.raises(ValueError, match="already bound|repo"):
            github_sync_debate(
                thread_id="2025-01-02-repo-mismatch",
                repo="owner/repo-different",  # Different repo!
                target_id="D_kwDO123",  # Same target
                target_type="discussion",
                state_dir=tmp_path,
            )
