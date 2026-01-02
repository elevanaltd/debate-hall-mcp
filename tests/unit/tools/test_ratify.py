"""Unit tests for ratify_rfc tool (Issue #16).

TDD Discipline: RED->GREEN->REFACTOR
Tests the ratify_rfc tool for generating ADRs from debate synthesis
and creating PRs on GitHub.

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
    topic: str = "Test Decision Topic",
    status: DebateStatus = DebateStatus.SYNTHESIS,
    synthesis: str | None = "This is the Door's synthesis of the decision.",
    turns: list[Turn] | None = None,
    github_binding: GitHubBinding | None = None,
) -> DebateRoom:
    """Helper to create a test DebateRoom."""
    return DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode.FIXED,
        status=status,
        synthesis=synthesis,
        turns=turns or [],
        github_binding=github_binding,
    )


def create_sample_turns() -> list[Turn]:
    """Create sample Wind/Wall/Door turns for testing."""
    turns: list[Turn] = []

    # Wind turn (PATHOS - opportunities)
    wind_turn = Turn(
        role="Wind",
        content="We should adopt this approach because it offers flexibility and innovation opportunities.",
        timestamp=datetime.now(UTC),
        previous_hash=None,
        cognition="PATHOS",
    )
    turns.append(wind_turn)

    # Wall turn (ETHOS - constraints)
    wall_turn = Turn(
        role="Wall",
        content="We must ensure security constraints are met and compliance is maintained.",
        timestamp=datetime.now(UTC),
        previous_hash=turns[-1].hash,
        cognition="ETHOS",
    )
    turns.append(wall_turn)

    # Door turn (LOGOS - synthesis)
    door_turn = Turn(
        role="Door",
        content="Synthesizing: adopt the approach with security guardrails.",
        timestamp=datetime.now(UTC),
        previous_hash=turns[-1].hash,
        cognition="LOGOS",
    )
    turns.append(door_turn)

    return turns


class TestADRGeneration:
    """Test ADR content generation from debate."""

    def test_generate_adr_content_basic_structure(self) -> None:
        """Generated ADR has correct basic structure."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        room = create_test_room(
            thread_id="2025-01-02-test-decision",
            topic="Use React for Frontend",
            synthesis="We will use React for the frontend due to team expertise.",
            turns=create_sample_turns(),
        )

        adr_content = generate_adr_content(room, adr_number=1)

        # Check required sections exist
        assert "# ADR-001: Use React for Frontend" in adr_content
        assert "## Status" in adr_content
        assert "Accepted" in adr_content
        assert "## Context" in adr_content
        assert "## Decision" in adr_content
        assert "## Consequences" in adr_content
        assert "## References" in adr_content

    def test_generate_adr_content_includes_synthesis(self) -> None:
        """ADR Decision section contains Door synthesis."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        synthesis = "We decided to use PostgreSQL for reliable ACID compliance."
        room = create_test_room(
            thread_id="2025-01-02-db-choice",
            topic="Database Selection",
            synthesis=synthesis,
            turns=create_sample_turns(),
        )

        adr_content = generate_adr_content(room, adr_number=42)

        assert synthesis in adr_content

    def test_generate_adr_content_extracts_wind_opportunities(self) -> None:
        """ADR extracts opportunities from Wind turns."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        turns: list[Turn] = []
        wind_turn = Turn(
            role="Wind",
            content="This opens opportunities for scalability and team growth.",
            timestamp=datetime.now(UTC),
            previous_hash=None,
            cognition="PATHOS",
        )
        turns.append(wind_turn)

        room = create_test_room(
            thread_id="2025-01-02-scaling",
            topic="Scaling Strategy",
            synthesis="Adopt horizontal scaling.",
            turns=turns,
        )

        adr_content = generate_adr_content(room, adr_number=1)

        # Should have Wind content in opportunities section
        assert (
            "opportunities for scalability" in adr_content.lower() or "scalability" in adr_content
        )

    def test_generate_adr_content_extracts_wall_constraints(self) -> None:
        """ADR extracts constraints from Wall turns."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        turns: list[Turn] = []
        wall_turn = Turn(
            role="Wall",
            content="Must maintain backward compatibility with v1 API.",
            timestamp=datetime.now(UTC),
            previous_hash=None,
            cognition="ETHOS",
        )
        turns.append(wall_turn)

        room = create_test_room(
            thread_id="2025-01-02-api-v2",
            topic="API Version 2 Design",
            synthesis="V2 API with v1 compatibility layer.",
            turns=turns,
        )

        adr_content = generate_adr_content(room, adr_number=2)

        # Should have Wall content in constraints section
        assert "backward compatibility" in adr_content.lower() or "compatibility" in adr_content

    def test_generate_adr_content_includes_thread_reference(self) -> None:
        """ADR includes debate thread_id in references."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        room = create_test_room(
            thread_id="2025-01-02-architecture-decision",
            topic="Architecture",
            synthesis="Microservices architecture.",
            turns=create_sample_turns(),
        )

        adr_content = generate_adr_content(room, adr_number=1)

        assert "2025-01-02-architecture-decision" in adr_content

    def test_generate_adr_content_includes_github_reference_if_bound(self) -> None:
        """ADR includes GitHub discussion URL if binding exists."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDO123",
            target_type="discussion",
            last_synced_turn=3,
        )
        room = create_test_room(
            thread_id="2025-01-02-design",
            topic="Design Decision",
            synthesis="Chosen design.",
            turns=create_sample_turns(),
            github_binding=binding,
        )

        adr_content = generate_adr_content(room, adr_number=1)

        # Should reference GitHub
        assert "github" in adr_content.lower() or "owner/repo" in adr_content


class TestRatifyRFCToolValidation:
    """Test ratify_rfc tool input validation."""

    def test_ratify_requires_existing_thread(self, tmp_path: Path) -> None:
        """Ratify raises FileNotFoundError for non-existent thread."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        with pytest.raises(FileNotFoundError, match="No state file found"):
            ratify_rfc(
                thread_id="nonexistent-thread",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

    def test_ratify_requires_closed_debate(self, tmp_path: Path) -> None:
        """Ratify raises ValueError if debate not closed."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-active-debate",
            topic="Active Debate",
            status=DebateStatus.ACTIVE,  # Not closed!
            synthesis=None,
        )
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="not closed|ACTIVE"):
            ratify_rfc(
                thread_id="2025-01-02-active-debate",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

    def test_ratify_requires_door_synthesis(self, tmp_path: Path) -> None:
        """Ratify raises ValueError if no Door synthesis."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-no-synthesis",
            topic="Missing Synthesis",
            status=DebateStatus.SYNTHESIS,
            synthesis=None,  # No synthesis!
        )
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="synthesis|Door"):
            ratify_rfc(
                thread_id="2025-01-02-no-synthesis",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )


class TestRatifyRFCToolExecution:
    """Test ratify_rfc tool GitHub integration."""

    def test_ratify_creates_branch_from_default(self, tmp_path: Path) -> None:
        """Ratify creates branch from repo default branch."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-test-decision",
            topic="Test Decision",
            status=DebateStatus.SYNTHESIS,
            synthesis="The decision is made.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock the GitHub API calls
            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123def456", "ref": "refs/heads/main"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001-test-decision"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-001-test-decision.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 42,
                "html_url": "https://github.com/owner/repo/pull/42",
            }

            ratify_rfc(
                thread_id="2025-01-02-test-decision",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify branch creation
        mock_client.get_default_branch.assert_called_once_with(repo="owner/repo")
        mock_client.get_ref.assert_called_once_with(repo="owner/repo", ref="heads/main")
        mock_client.create_ref.assert_called_once()

        # Verify branch name format
        create_ref_call = mock_client.create_ref.call_args
        assert "adr/" in create_ref_call.kwargs.get("ref", "")

    def test_ratify_commits_adr_file(self, tmp_path: Path) -> None:
        """Ratify commits ADR file to the created branch."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-commit-test",
            topic="Commit Test Decision",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision content here.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001-commit-test"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-001-commit-test-decision.md"},
                "commit": {"sha": "commit456"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/owner/repo/pull/1",
            }

            ratify_rfc(
                thread_id="2025-01-02-commit-test",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                adr_path="docs/adr/",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify file creation call
        mock_client.create_file.assert_called_once()
        create_file_call = mock_client.create_file.call_args

        # Check path includes adr_path
        assert create_file_call.kwargs.get("path", "").startswith("docs/adr/")
        # Check content includes ADR structure
        content = create_file_call.kwargs.get("content", "")
        assert "ADR" in content
        assert "Status" in content

    def test_ratify_creates_pr(self, tmp_path: Path) -> None:
        """Ratify creates PR linking to debate."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-pr-test",
            topic="PR Test Decision",
            status=DebateStatus.SYNTHESIS,
            synthesis="Final decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001-pr-test"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-001-pr-test-decision.md"},
                "commit": {"sha": "commit789"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 99,
                "html_url": "https://github.com/owner/repo/pull/99",
            }

            ratify_rfc(
                thread_id="2025-01-02-pr-test",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify PR creation
        mock_client.create_pull_request.assert_called_once()
        pr_call = mock_client.create_pull_request.call_args

        # Check PR links to debate
        pr_body = pr_call.kwargs.get("body", "")
        assert "2025-01-02-pr-test" in pr_body or "debate" in pr_body.lower()

    def test_ratify_returns_pr_url(self, tmp_path: Path) -> None:
        """Ratify returns the created PR URL."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-url-test",
            topic="URL Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001-url-test"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-001.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 42,
                "html_url": "https://github.com/owner/repo/pull/42",
            }

            result = ratify_rfc(
                thread_id="2025-01-02-url-test",
                repo="owner/repo",
                adr_number=1,
                target_id="D_kwDO123",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        assert result["pr_url"] == "https://github.com/owner/repo/pull/42"
        assert result["pr_number"] == 42


class TestRatifyRFCADRNumbering:
    """Test ADR numbering in ratify_rfc."""

    def test_ratify_uses_provided_adr_number(self, tmp_path: Path) -> None:
        """Ratify uses explicit adr_number parameter for ADR number."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-numbered",
            topic="Numbered ADR",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/042-numbered"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-042-numbered-adr.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/owner/repo/pull/1",
            }

            # Explicit adr_number parameter determines ADR number
            ratify_rfc(
                thread_id="2025-01-02-numbered",
                repo="owner/repo",
                adr_number=42,  # Explicit ADR number
                target_id="D_kwDO123",  # target_id is now for reference only
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify ADR number in file path
        create_file_call = mock_client.create_file.call_args
        path = create_file_call.kwargs.get("path", "")
        assert "042" in path or "42" in path  # ADR-042 format


class TestRatifyRFCWithoutGitHubBinding:
    """Test ratify without prior GitHub binding."""

    def test_ratify_works_without_prior_binding(self, tmp_path: Path) -> None:
        """Ratify can create ADR PR without prior github_sync binding."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        # Room without GitHub binding (debate wasn't synced first)
        room = create_test_room(
            thread_id="2025-01-02-no-binding",
            topic="No Prior Binding",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision without prior sync.",
            turns=create_sample_turns(),
            github_binding=None,  # No binding!
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-001.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/owner/repo/pull/1",
            }

            # Should work without prior binding
            result = ratify_rfc(
                thread_id="2025-01-02-no-binding",
                repo="owner/repo",
                adr_number=1,
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        assert "pr_url" in result
        assert result["pr_number"] == 1


class TestRatifyRFCBranchNaming:
    """Test branch naming conventions."""

    def test_branch_name_uses_slugified_topic(self, tmp_path: Path) -> None:
        """Branch name is derived from topic slugified."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-complex-topic",
            topic="Use PostgreSQL for User Data Storage",
            status=DebateStatus.SYNTHESIS,
            synthesis="PostgreSQL is the choice.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/003-use-postgresql"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-003.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 5,
                "html_url": "https://github.com/owner/repo/pull/5",
            }

            ratify_rfc(
                thread_id="2025-01-02-complex-topic",
                repo="owner/repo",
                adr_number=3,
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify branch naming
        create_ref_call = mock_client.create_ref.call_args
        ref = create_ref_call.kwargs.get("ref", "")
        # Should be lowercase, hyphenated slug
        assert "adr/" in ref
        assert "003" in ref or "3" in ref


class TestRatifyRFCExplicitADRNumber:
    """Test explicit adr_number requirement (Issue: ADR number collision fix)."""

    def test_ratify_requires_explicit_adr_number(self, tmp_path: Path) -> None:
        """Ratify requires explicit adr_number parameter - no silent fallback to 1.

        This prevents ADR number collisions when GraphQL node IDs (D_kwDO...)
        are passed as target_id.
        """
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-explicit-number",
            topic="Explicit ADR Number Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision made.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/042-explicit-number"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/adr/ADR-042.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/owner/repo/pull/1",
            }

            # Should pass explicit adr_number, not derive from target_id
            result = ratify_rfc(
                thread_id="2025-01-02-explicit-number",
                repo="owner/repo",
                adr_number=42,  # Explicit ADR number
                target_id="D_kwDONcTest",  # GraphQL node ID (non-numeric)
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        # Verify correct ADR number was used
        assert result["adr_number"] == 42
        # Check file path contains correct number
        create_file_call = mock_client.create_file.call_args
        path = create_file_call.kwargs.get("path", "")
        assert "042" in path  # ADR-042 format

    def test_ratify_adr_number_is_required_parameter(self) -> None:
        """Verify adr_number is a required parameter in function signature."""
        import inspect

        from debate_hall_mcp.tools.ratify import ratify_rfc

        sig = inspect.signature(ratify_rfc)
        params = sig.parameters

        # adr_number must exist as a parameter
        assert "adr_number" in params, "adr_number must be a parameter"

        # adr_number must NOT have a default value (required)
        param = params["adr_number"]
        assert (
            param.default is inspect.Parameter.empty
        ), "adr_number must be required (no default value)"

    def test_ratify_target_id_is_optional(self) -> None:
        """Verify target_id is optional (for reference linking only)."""
        import inspect

        from debate_hall_mcp.tools.ratify import ratify_rfc

        sig = inspect.signature(ratify_rfc)
        params = sig.parameters

        # target_id should be optional
        if "target_id" in params:
            param = params["target_id"]
            assert param.default is not inspect.Parameter.empty or "None" in str(
                param.annotation
            ), "target_id should be optional"


class TestRatifyRFCDiscussionDeepLink:
    """Test discussion deep-link URL generation (Issue: Discussion deep-link broken)."""

    def test_adr_content_includes_discussion_number_in_url(self) -> None:
        """ADR content should include deep-link to specific discussion, not just index."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        # Binding with discussion_number for deep linking
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDONcTest",  # GraphQL node ID
            target_type="discussion",
            last_synced_turn=3,
            discussion_number=15,  # Discussion number for deep linking
        )
        room = create_test_room(
            thread_id="2025-01-02-discussion-link",
            topic="Discussion Deep Link Test",
            synthesis="Decision from discussion.",
            turns=create_sample_turns(),
            github_binding=binding,
        )

        adr_content = generate_adr_content(room, adr_number=1)

        # Should have deep link to specific discussion, NOT just the index
        assert "https://github.com/owner/repo/discussions/15" in adr_content
        # Should NOT just link to discussions index
        assert "discussions (ID:" not in adr_content

    def test_adr_content_issue_url_links_to_specific_issue(self) -> None:
        """ADR content should include deep-link to specific issue."""
        from debate_hall_mcp.tools.ratify import generate_adr_content

        binding = GitHubBinding(
            repo="owner/repo",
            target_id="42",  # Issue number
            target_type="issue",
            last_synced_turn=3,
        )
        room = create_test_room(
            thread_id="2025-01-02-issue-link",
            topic="Issue Deep Link Test",
            synthesis="Decision from issue.",
            turns=create_sample_turns(),
            github_binding=binding,
        )

        adr_content = generate_adr_content(room, adr_number=1)

        # Should link to specific issue
        assert "https://github.com/owner/repo/issues/42" in adr_content

    def test_github_binding_supports_discussion_number(self) -> None:
        """GitHubBinding model should support optional discussion_number field."""
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDONcTest",
            target_type="discussion",
            last_synced_turn=0,
            discussion_number=25,  # New field
        )

        assert binding.discussion_number == 25

    def test_github_binding_discussion_number_is_optional(self) -> None:
        """GitHubBinding discussion_number should be optional for backwards compat."""
        binding = GitHubBinding(
            repo="owner/repo",
            target_id="D_kwDONcTest",
            target_type="discussion",
            last_synced_turn=0,
            # No discussion_number provided
        )

        assert binding.discussion_number is None


class TestRatifyRFCBranchConflict:
    """Test 422 branch conflict handling in ratify_rfc (CE Blocking Issue #2)."""

    def test_ratify_raises_user_friendly_error_on_branch_conflict(self, tmp_path: Path) -> None:
        """Ratify raises user-friendly error when branch already exists (422).

        GitHub returns 422 when create_ref is called for an existing branch.
        The error should be user-friendly, not a raw GitHubAPIError.
        """
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.ratify import BranchConflictError, ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-branch-conflict",
            topic="Branch Conflict Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            # Simulate 422 "Reference already exists"
            mock_client.create_ref.side_effect = GitHubAPIError(
                "REST API error: Reference already exists"
            )

            with pytest.raises(
                BranchConflictError,
                match="Branch.*already exists|delete.*different ADR number",
            ):
                ratify_rfc(
                    thread_id="2025-01-02-branch-conflict",
                    repo="owner/repo",
                    adr_number=1,
                    state_dir=tmp_path,
                    github_token="ghp_test",
                )

    def test_ratify_error_message_includes_branch_name(self, tmp_path: Path) -> None:
        """Branch conflict error includes the conflicting branch name."""
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.ratify import BranchConflictError, ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-branch-name-test",
            topic="Specific Branch",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.side_effect = GitHubAPIError(
                "REST API error: Reference already exists"
            )

            with pytest.raises(BranchConflictError) as exc_info:
                ratify_rfc(
                    thread_id="2025-01-02-branch-name-test",
                    repo="owner/repo",
                    adr_number=42,
                    state_dir=tmp_path,
                    github_token="ghp_test",
                )

            # Error should mention the branch name
            error_msg = str(exc_info.value)
            assert "adr/042" in error_msg or "042" in error_msg

    def test_ratify_propagates_other_github_errors(self, tmp_path: Path) -> None:
        """Non-422 GitHub errors are propagated as GitHubAPIError."""
        from debate_hall_mcp.github import GitHubAPIError
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-other-error",
            topic="Other Error Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            # Different error - not 422
            mock_client.create_ref.side_effect = GitHubAPIError("REST API error: Not Found")

            with pytest.raises(GitHubAPIError, match="Not Found"):
                ratify_rfc(
                    thread_id="2025-01-02-other-error",
                    repo="owner/repo",
                    adr_number=1,
                    state_dir=tmp_path,
                    github_token="ghp_test",
                )


class TestRatifyRFCPathTraversal:
    """Test path traversal validation in ratify_rfc (CE Blocking Issue #3)."""

    def test_ratify_rejects_path_traversal_in_adr_path(self, tmp_path: Path) -> None:
        """Ratify rejects adr_path containing '..' path traversal sequences."""
        from debate_hall_mcp.tools.ratify import PathTraversalError, ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-path-traversal",
            topic="Path Traversal Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with pytest.raises(PathTraversalError, match="path traversal|\\.\\."):
            ratify_rfc(
                thread_id="2025-01-02-path-traversal",
                repo="owner/repo",
                adr_number=1,
                adr_path="../../../etc/passwd",  # Path traversal attempt
                state_dir=tmp_path,
                github_token="ghp_test",
            )

    def test_ratify_rejects_encoded_path_traversal(self, tmp_path: Path) -> None:
        """Ratify rejects various forms of path traversal."""
        from debate_hall_mcp.tools.ratify import PathTraversalError, ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-encoded-traversal",
            topic="Encoded Traversal Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        # Test with embedded ..
        with pytest.raises(PathTraversalError):
            ratify_rfc(
                thread_id="2025-01-02-encoded-traversal",
                repo="owner/repo",
                adr_number=1,
                adr_path="docs/../../../secrets/",
                state_dir=tmp_path,
                github_token="ghp_test",
            )

    def test_ratify_allows_valid_nested_paths(self, tmp_path: Path) -> None:
        """Ratify allows valid nested paths without traversal."""
        from debate_hall_mcp.tools.ratify import ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-valid-path",
            topic="Valid Path Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with patch("debate_hall_mcp.tools.ratify.GitHubClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.get_default_branch.return_value = "main"
            mock_client.get_ref.return_value = {"sha": "abc123"}
            mock_client.create_ref.return_value = {"ref": "refs/heads/adr/001-valid-path"}
            mock_client.create_file.return_value = {
                "content": {"path": "docs/decisions/adr/ADR-001.md"},
                "commit": {"sha": "commit123"},
            }
            mock_client.create_pull_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/owner/repo/pull/1",
            }

            # Valid nested path should work
            result = ratify_rfc(
                thread_id="2025-01-02-valid-path",
                repo="owner/repo",
                adr_number=1,
                adr_path="docs/decisions/adr/",  # Valid nested path
                state_dir=tmp_path,
                github_token="ghp_test",
            )

        assert "pr_url" in result

    def test_ratify_rejects_absolute_paths(self, tmp_path: Path) -> None:
        """Ratify rejects absolute paths that could escape repo root."""
        from debate_hall_mcp.tools.ratify import PathTraversalError, ratify_rfc

        room = create_test_room(
            thread_id="2025-01-02-absolute-path",
            topic="Absolute Path Test",
            status=DebateStatus.SYNTHESIS,
            synthesis="Decision.",
            turns=create_sample_turns(),
        )
        save_debate_state(room, tmp_path)

        with pytest.raises(PathTraversalError, match="path traversal|absolute"):
            ratify_rfc(
                thread_id="2025-01-02-absolute-path",
                repo="owner/repo",
                adr_number=1,
                adr_path="/etc/passwd",  # Absolute path
                state_dir=tmp_path,
                github_token="ghp_test",
            )
