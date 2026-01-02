"""Unit tests for human_interject tool (Issue #17).

TDD Discipline: RED->GREEN->REFACTOR
Tests the human_interject tool for injecting GitHub comments into debates.
All tests use mocked GitHub API - no actual GitHub API calls.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    DebateStatus,
    GitHubBinding,
    Turn,
    save_debate_state,
)


def create_test_room(
    thread_id: str,
    turns: list[Turn] | None = None,
    github_binding: GitHubBinding | None = None,
    status: DebateStatus = DebateStatus.ACTIVE,
) -> DebateRoom:
    """Helper to create a test DebateRoom."""
    return DebateRoom(
        thread_id=thread_id,
        topic="Test Topic",
        mode=DebateMode.FIXED,
        status=status,
        turns=turns or [],
        github_binding=github_binding,
    )


def create_turn(
    role: str, content: str, previous_hash: str | None = None, cognition: str | None = None
) -> Turn:
    """Helper to create a test Turn."""
    return Turn(
        role=role,
        content=content,
        timestamp=datetime.now(UTC),
        previous_hash=previous_hash,
        cognition=cognition,
    )


class TestHumanInterjectBasics:
    """Test basic human_interject functionality."""

    def test_interject_requires_existing_thread(self, tmp_path: Path) -> None:
        """Injecting into non-existent thread raises FileNotFoundError."""
        from debate_hall_mcp.tools.interject import human_interject

        with pytest.raises(FileNotFoundError, match="No state file found"):
            human_interject(
                thread_id="nonexistent-thread",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_kwDOtest",
                state_dir=tmp_path,
            )

    def test_interject_rejects_closed_debate(self, tmp_path: Path) -> None:
        """Injecting into closed debate raises ValueError."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-closed", status=DebateStatus.SYNTHESIS)
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="closed|not active"):
            human_interject(
                thread_id="2025-01-02-closed",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_kwDOtest",
                state_dir=tmp_path,
            )

    def test_interject_fetches_discussion_comment(self, tmp_path: Path) -> None:
        """Interject fetches comment from GitHub Discussion."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-fetch-discussion")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Human comment content",
                "author": "testuser",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            result = human_interject(
                thread_id="2025-01-02-fetch-discussion",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_kwDOtest123",
                state_dir=tmp_path,
            )

        mock_client.get_discussion_comment.assert_called_once_with("DC_kwDOtest123")
        assert result["status"] == "injected"
        assert result["comment_id"] == "DC_kwDOtest123"

    def test_interject_fetches_issue_comment(self, tmp_path: Path) -> None:
        """Interject fetches comment from GitHub Issue."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-fetch-issue")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_issue_comment.return_value = {
                "body": "Issue comment content",
                "author": "issueuser",
                "node_id": "IC_kwDOtest456",
                "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
            }

            result = human_interject(
                thread_id="2025-01-02-fetch-issue",
                repo="owner/repo",
                target_id="42",  # Issue number
                comment_id="12345678",  # Issue comment ID (numeric string)
                state_dir=tmp_path,
            )

        mock_client.get_issue_comment.assert_called_once_with("owner/repo", 12345678)
        assert result["status"] == "injected"


class TestHumanInterjectIdempotency:
    """Test idempotent injection (no duplicate processing)."""

    def test_interject_skips_already_processed(self, tmp_path: Path) -> None:
        """Interject skips comment if already processed (idempotent)."""
        from debate_hall_mcp.state import InjectedContext, load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        # Create room with already-processed comment
        room = create_test_room("2025-01-02-idempotent")
        room.injected_context.append(
            InjectedContext(
                source="github_comment",
                comment_id="DC_already_processed",
                content="Already processed",
                injection_type="general",
                processed_at=datetime.now(UTC),
            )
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = human_interject(
                thread_id="2025-01-02-idempotent",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_already_processed",
                state_dir=tmp_path,
            )

        # Should not call GitHub API for already-processed comment
        mock_client.get_discussion_comment.assert_not_called()
        assert result["status"] == "already_processed"

        # Should not add duplicate
        loaded_room = load_debate_state("2025-01-02-idempotent", tmp_path)
        assert len(loaded_room.injected_context) == 1


class TestHumanInterjectParentDetection:
    """Test parent comment detection and injection type assignment."""

    def test_interject_detects_wind_reply_as_pathos(self, tmp_path: Path) -> None:
        """Reply to Wind comment injects as PATHOS."""
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        # Create room with turns that have synced comment IDs
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_wind_turn", "DC_wall_turn"],
        )
        room = create_test_room("2025-01-02-wind-reply", github_binding=binding)
        room.turns.append(create_turn("Wind", "Wind content", cognition="PATHOS"))
        room.turns.append(
            create_turn("Wall", "Wall content", room.turns[0].hash, cognition="ETHOS")
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Replying to Wind",
                "author": "human",
                "reply_to_id": "DC_wind_turn",  # Reply to Wind's turn
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-wind-reply",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_reply_to_wind",
                state_dir=tmp_path,
            )

        loaded_room = load_debate_state("2025-01-02-wind-reply", tmp_path)
        assert len(loaded_room.injected_context) == 1
        assert loaded_room.injected_context[0].injection_type == "pathos"
        assert loaded_room.injected_context[0].replied_to_turn == 0

    def test_interject_detects_wall_reply_as_ethos(self, tmp_path: Path) -> None:
        """Reply to Wall comment injects as ETHOS."""
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=2,
            comment_ids=["DC_wind_turn", "DC_wall_turn"],
        )
        room = create_test_room("2025-01-02-wall-reply", github_binding=binding)
        room.turns.append(create_turn("Wind", "Wind content", cognition="PATHOS"))
        room.turns.append(
            create_turn("Wall", "Wall content", room.turns[0].hash, cognition="ETHOS")
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Replying to Wall",
                "author": "human",
                "reply_to_id": "DC_wall_turn",  # Reply to Wall's turn
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-wall-reply",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_reply_to_wall",
                state_dir=tmp_path,
            )

        loaded_room = load_debate_state("2025-01-02-wall-reply", tmp_path)
        assert loaded_room.injected_context[0].injection_type == "ethos"
        assert loaded_room.injected_context[0].replied_to_turn == 1

    def test_interject_detects_door_reply_as_logos(self, tmp_path: Path) -> None:
        """Reply to Door comment injects as LOGOS."""
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=3,
            comment_ids=["DC_wind", "DC_wall", "DC_door"],
        )
        room = create_test_room("2025-01-02-door-reply", github_binding=binding)
        room.turns.append(create_turn("Wind", "Wind", cognition="PATHOS"))
        room.turns.append(create_turn("Wall", "Wall", room.turns[0].hash, cognition="ETHOS"))
        room.turns.append(create_turn("Door", "Door", room.turns[1].hash, cognition="LOGOS"))
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Replying to Door",
                "author": "human",
                "reply_to_id": "DC_door",
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-door-reply",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_reply_to_door",
                state_dir=tmp_path,
            )

        loaded_room = load_debate_state("2025-01-02-door-reply", tmp_path)
        assert loaded_room.injected_context[0].injection_type == "logos"
        assert loaded_room.injected_context[0].replied_to_turn == 2

    def test_interject_no_reply_is_general(self, tmp_path: Path) -> None:
        """Top-level comment (not a reply) injects as GENERAL."""
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-general")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Top-level comment",
                "author": "human",
                "reply_to_id": None,  # Not a reply
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-general",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_top_level",
                state_dir=tmp_path,
            )

        loaded_room = load_debate_state("2025-01-02-general", tmp_path)
        assert loaded_room.injected_context[0].injection_type == "general"
        assert loaded_room.injected_context[0].replied_to_turn is None


class TestHumanInterjectStateUpdates:
    """Test that interject properly updates room state."""

    def test_interject_stores_context_with_all_fields(self, tmp_path: Path) -> None:
        """Interject stores complete InjectedContext."""
        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-full-context")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Complete comment body",
                "author": "fulluser",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-full-context",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_full_test",
                state_dir=tmp_path,
            )

        loaded_room = load_debate_state("2025-01-02-full-context", tmp_path)
        ctx = loaded_room.injected_context[0]
        assert ctx.source == "github_comment"
        assert ctx.comment_id == "DC_full_test"
        assert ctx.content == "Complete comment body"
        assert ctx.author == "fulluser"
        assert ctx.processed_at is not None


class TestHumanInterjectReturn:
    """Test return value format."""

    def test_interject_returns_full_summary(self, tmp_path: Path) -> None:
        """Interject returns complete summary dictionary."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-summary")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Summary test",
                "author": "summaryuser",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            result = human_interject(
                thread_id="2025-01-02-summary",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_summary",
                state_dir=tmp_path,
            )

        assert result["thread_id"] == "2025-01-02-summary"
        assert result["status"] == "injected"
        assert result["comment_id"] == "DC_summary"
        assert result["injection_type"] == "general"
        assert result["author"] == "summaryuser"


class TestHumanInterjectCommentTypeDetection:
    """Test automatic detection of comment type (Discussion vs Issue)."""

    def test_interject_detects_discussion_comment_by_prefix(self, tmp_path: Path) -> None:
        """DC_ prefix indicates Discussion comment."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-dc-prefix")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "DC comment",
                "author": "user",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-dc-prefix",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_kwDOtest",  # DC_ prefix
                state_dir=tmp_path,
            )

        mock_client.get_discussion_comment.assert_called_once()
        mock_client.get_issue_comment.assert_not_called()

    def test_interject_detects_issue_comment_by_numeric_id(self, tmp_path: Path) -> None:
        """Numeric comment_id indicates Issue comment."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-numeric-id")
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_issue_comment.return_value = {
                "body": "Issue comment",
                "author": "user",
                "node_id": "IC_test",
                "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
            }

            human_interject(
                thread_id="2025-01-02-numeric-id",
                repo="owner/repo",
                target_id="42",
                comment_id="12345678",  # Numeric = Issue comment
                state_dir=tmp_path,
            )

        mock_client.get_issue_comment.assert_called_once()
        mock_client.get_discussion_comment.assert_not_called()


class TestHumanInterjectSecurity:
    """Test security validations for human_interject (CRS blocking issues)."""

    def test_interject_rejects_repo_mismatch(self, tmp_path: Path) -> None:
        """Security: Reject comment when repo parameter doesn't match binding's repo.

        Attack vector: Inject comments from different repo's issue with same number.
        The repo must be validated BEFORE any API calls are made.
        """
        from debate_hall_mcp.tools.interject import human_interject

        # Create room bound to owner/repo
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="42",
            target_type="issue",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-repo-mismatch", github_binding=binding)
        save_debate_state(room, tmp_path)

        # Attack: Pass different repo to access comment from other-owner/other-repo
        with pytest.raises(ValueError, match="repo.*mismatch|does not match"):
            human_interject(
                thread_id="2025-01-02-repo-mismatch",
                repo="other-owner/other-repo",  # Different repo!
                target_id="42",  # Same issue number as in binding
                comment_id="12345678",
                state_dir=tmp_path,
            )

    def test_interject_validates_repo_before_api_call(self, tmp_path: Path) -> None:
        """Security: Repo validation must happen BEFORE any GitHub API calls.

        If repo is validated after API calls, an attacker could still trigger
        fetches to arbitrary repos (information disclosure, rate limit attacks).
        """
        from debate_hall_mcp.tools.interject import human_interject

        # Create room bound to owner/repo
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="42",
            target_type="issue",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-repo-before-api", github_binding=binding)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Should raise BEFORE making any API calls
            with pytest.raises(ValueError, match="repo.*mismatch"):
                human_interject(
                    thread_id="2025-01-02-repo-before-api",
                    repo="attacker/malicious-repo",
                    target_id="42",
                    comment_id="12345678",
                    state_dir=tmp_path,
                )

            # CRITICAL: No API methods should have been called
            mock_client.get_issue_comment.assert_not_called()
            mock_client.get_discussion_comment.assert_not_called()

    def test_interject_rejects_discussion_comment_from_wrong_discussion(
        self, tmp_path: Path
    ) -> None:
        """Security: Reject comment from different discussion than debate's target_id.

        Attack vector: Inject/exfiltrate any accessible DiscussionComment by passing
        a DC_ comment_id from a different Discussion.
        """
        from debate_hall_mcp.tools.interject import human_interject

        # Create room bound to Discussion D_kwDODebate123
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDODebate123",
            target_type="discussion",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-security-discussion", github_binding=binding)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            # Comment is from a DIFFERENT discussion (D_kwDOEvil456)
            mock_client.get_discussion_comment.return_value = {
                "body": "Malicious content from wrong discussion",
                "author": "attacker",
                "reply_to_id": None,
                "discussion_id": "D_kwDOEvil456",  # Wrong discussion!
            }

            with pytest.raises(ValueError, match="target_id mismatch|different discussion"):
                human_interject(
                    thread_id="2025-01-02-security-discussion",
                    repo="owner/repo",
                    target_id="D_kwDODebate123",  # Expects this discussion
                    comment_id="DC_kwDOEvilComment",  # Comment from different discussion
                    state_dir=tmp_path,
                )

    def test_interject_rejects_issue_comment_from_wrong_issue(self, tmp_path: Path) -> None:
        """Security: Reject comment from different issue than debate's target_id.

        Attack vector: Inject comment from any accessible issue.
        """
        from debate_hall_mcp.tools.interject import human_interject

        # Create room bound to Issue #42
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="42",
            target_type="issue",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-security-issue", github_binding=binding)
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            # Comment metadata shows it's from Issue #99, not #42
            mock_client.get_issue_comment.return_value = {
                "body": "Malicious content from wrong issue",
                "author": "attacker",
                "node_id": "IC_kwDOEvilComment",
                "issue_url": "https://api.github.com/repos/owner/repo/issues/99",  # Wrong!
            }

            with pytest.raises(ValueError, match="target_id mismatch|different issue"):
                human_interject(
                    thread_id="2025-01-02-security-issue",
                    repo="owner/repo",
                    target_id="42",  # Expects issue #42
                    comment_id="12345678",  # Comment from issue #99
                    state_dir=tmp_path,
                )

    def test_interject_validates_target_id_matches_binding(self, tmp_path: Path) -> None:
        """Security: Validate target_id parameter matches debate's github_binding.target_id."""
        from debate_hall_mcp.tools.interject import human_interject

        # Create room bound to Discussion D_kwDOBound123
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDOBound123",
            target_type="discussion",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-binding-check", github_binding=binding)
        save_debate_state(room, tmp_path)

        # Attacker passes mismatched target_id to bypass binding
        with pytest.raises(ValueError, match="target_id.*mismatch|does not match"):
            human_interject(
                thread_id="2025-01-02-binding-check",
                repo="owner/repo",
                target_id="D_kwDOEvil456",  # Doesn't match binding's D_kwDOBound123
                comment_id="DC_kwDOAnyComment",
                state_dir=tmp_path,
            )


class TestHumanInterjectAtomicity:
    """Test atomic read-modify-write operations (CRS blocking issue)."""

    def test_interject_uses_canonical_lock_file(self, tmp_path: Path) -> None:
        """Reliability: Must use canonical {thread_id}.lock file.

        The interject operation must use the SAME lock file as save_debate_state()
        uses: {thread_id}.lock. Using a separate lock file like {thread_id}.interject.lock
        would allow interject to race with other state writers (add_turn, close_debate).
        """
        from debate_hall_mcp.tools.interject import human_interject

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-canonical-lock", github_binding=binding)
        save_debate_state(room, tmp_path)

        lock_files_accessed: list[str] = []

        def track_lock_files(lock_file):
            """Track which lock files are accessed."""
            from filelock import FileLock

            lock_files_accessed.append(str(lock_file))
            return FileLock(str(lock_file))

        with (
            patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class,
            patch(
                "debate_hall_mcp.tools.interject._get_interject_lock",
                side_effect=track_lock_files,
            ),
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Test comment",
                "author": "user",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-canonical-lock",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_canonical_test",
                state_dir=tmp_path,
            )

        # CRITICAL: Must use canonical lock file, not interject-specific one
        assert (
            len(lock_files_accessed) == 1
        ), f"Expected exactly 1 lock file access, got {len(lock_files_accessed)}"
        lock_file_used = lock_files_accessed[0]
        # Must be {thread_id}.lock, NOT {thread_id}.interject.lock
        assert lock_file_used.endswith(
            "2025-01-02-canonical-lock.lock"
        ), f"Expected canonical lock file '{{thread_id}}.lock', got '{lock_file_used}'"
        assert (
            ".interject.lock" not in lock_file_used
        ), f"Must NOT use interject-specific lock file, got '{lock_file_used}'"

    def test_interject_uses_single_atomic_lock_cycle(self, tmp_path: Path) -> None:
        """Reliability: Must use SINGLE lock cycle for read-modify-write.

        The interject operation must:
        1. Acquire lock ONCE
        2. Load state (read)
        3. Check idempotency
        4. Append context
        5. Save state (write)
        6. Release lock ONCE

        Multiple acquire/release cycles allow:
        - Concurrent interjections dropping updates
        - Bypassed idempotency checks
        """
        from debate_hall_mcp.tools.interject import human_interject

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=0,
            comment_ids=[],
        )
        room = create_test_room("2025-01-02-atomicity", github_binding=binding)
        save_debate_state(room, tmp_path)

        # Track lock acquisition/release with timestamps to detect interleaving
        lock_events: list[tuple[str, str]] = []  # (event, lock_file)

        def track_lock_factory(lock_file):
            """Factory that creates tracking locks."""
            from filelock import FileLock

            real_lock = FileLock(str(lock_file))
            lock_path = str(lock_file)

            class TrackingLock:
                def __enter__(self):
                    lock_events.append(("acquire", lock_path))
                    return real_lock.__enter__()

                def __exit__(self, *args):
                    lock_events.append(("release", lock_path))
                    return real_lock.__exit__(*args)

            return TrackingLock()

        with (
            patch("debate_hall_mcp.tools.interject.GitHubClient") as mock_client_class,
            patch(
                "debate_hall_mcp.tools.interject._get_interject_lock",
                side_effect=track_lock_factory,
            ),
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_discussion_comment.return_value = {
                "body": "Test comment",
                "author": "user",
                "reply_to_id": None,
                "discussion_id": "D_kwDO123",
            }

            human_interject(
                thread_id="2025-01-02-atomicity",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="DC_atomicity_test",
                state_dir=tmp_path,
            )

        # Extract events for the interject lock (not save/load internal locks)
        interject_events = [e[0] for e in lock_events]

        # CRITICAL: Must have exactly ONE acquire-release cycle for atomicity
        assert interject_events.count("acquire") == 1, (
            f"Expected exactly 1 lock acquisition for atomic operation, "
            f"got {interject_events.count('acquire')}: {lock_events}"
        )
        assert interject_events.count("release") == 1, (
            f"Expected exactly 1 lock release for atomic operation, "
            f"got {interject_events.count('release')}: {lock_events}"
        )
        assert interject_events == [
            "acquire",
            "release",
        ], f"Lock pattern must be acquire-release, got: {interject_events}"


class TestHumanInterjectValidation:
    """Test input validation for human_interject (CRS advisory issue)."""

    def test_interject_rejects_invalid_comment_id_format(self, tmp_path: Path) -> None:
        """Advisory: Invalid comment_id format should raise clear error.

        Non-DC_, non-numeric comment_id should raise domain-specific error,
        not raw ValueError from int() conversion.
        """
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-validation")
        save_debate_state(room, tmp_path)

        # Invalid format: not DC_ prefix and not numeric
        with pytest.raises(ValueError, match="Invalid comment_id format"):
            human_interject(
                thread_id="2025-01-02-validation",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="INVALID_FORMAT_XYZ",  # Not DC_ and not numeric
                state_dir=tmp_path,
            )

    def test_interject_rejects_empty_comment_id(self, tmp_path: Path) -> None:
        """Advisory: Empty comment_id should raise clear error."""
        from debate_hall_mcp.tools.interject import human_interject

        room = create_test_room("2025-01-02-empty")
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="Invalid comment_id|empty"):
            human_interject(
                thread_id="2025-01-02-empty",
                repo="owner/repo",
                target_id="D_kwDO123",
                comment_id="",
                state_dir=tmp_path,
            )
