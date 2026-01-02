"""Unit tests for GitHub API client PR/branch creation methods (Issue #16).

TDD Discipline: RED->GREEN->REFACTOR
Tests the GitHub client for creating branches, committing files, and PRs.
All tests use mocked HTTP responses - no actual GitHub API calls.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestGitHubClientGetRef:
    """Test getting branch reference from GitHub."""

    def test_get_ref_returns_sha(self) -> None:
        """Get reference returns the commit SHA."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ref": "refs/heads/main",
            "node_id": "REF_kwDO123",
            "object": {
                "sha": "abc123def456",
                "type": "commit",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_ref(
                repo="owner/repo",
                ref="heads/main",
            )

        assert result["sha"] == "abc123def456"
        assert result["ref"] == "refs/heads/main"

    def test_get_ref_uses_correct_endpoint(self) -> None:
        """Verify the REST API endpoint for getting reference."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **_kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "ref": "refs/heads/main",
                "object": {"sha": "abc123"},
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.get_ref(repo="owner/repo", ref="heads/main")

        assert captured_request["method"] == "GET"
        assert "/repos/owner/repo/git/ref/heads/main" in captured_request["url"]

    def test_get_ref_handles_not_found(self) -> None:
        """Handle 404 for non-existent reference."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Not Found"),
        ):
            client.get_ref(repo="owner/repo", ref="heads/nonexistent")


class TestGitHubClientCreateRef:
    """Test creating branch references on GitHub."""

    def test_create_ref_success(self) -> None:
        """Successfully create a new branch reference."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "ref": "refs/heads/adr/001-test-decision",
            "node_id": "REF_kwDO123",
            "object": {
                "sha": "abc123def456",
                "type": "commit",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_ref(
                repo="owner/repo",
                ref="refs/heads/adr/001-test-decision",
                sha="abc123def456",
            )

        assert result["ref"] == "refs/heads/adr/001-test-decision"
        assert result["object"]["sha"] == "abc123def456"

    def test_create_ref_uses_correct_endpoint_and_payload(self) -> None:
        """Verify the REST API call structure for creating refs."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {
                "ref": "refs/heads/test",
                "object": {"sha": "abc123"},
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_ref(
                repo="owner/repo",
                ref="refs/heads/adr/001-test",
                sha="abc123def456",
            )

        assert captured_request["method"] == "POST"
        assert "/repos/owner/repo/git/refs" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert body["ref"] == "refs/heads/adr/001-test"
        assert body["sha"] == "abc123def456"

    def test_create_ref_handles_already_exists(self) -> None:
        """Handle 422 when reference already exists."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "Reference already exists"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="already exists"),
        ):
            client.create_ref(
                repo="owner/repo",
                ref="refs/heads/existing-branch",
                sha="abc123",
            )


class TestGitHubClientCreateFile:
    """Test creating/updating files on GitHub via Contents API."""

    def test_create_file_success(self) -> None:
        """Successfully create a new file."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "content": {
                "name": "ADR-001-test-decision.md",
                "path": "docs/adr/ADR-001-test-decision.md",
                "sha": "file123sha",
            },
            "commit": {
                "sha": "commit123sha",
                "message": "Add ADR-001: Test Decision",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_file(
                repo="owner/repo",
                path="docs/adr/ADR-001-test-decision.md",
                content="# ADR-001: Test Decision\n\n## Status\nAccepted",
                message="Add ADR-001: Test Decision",
                branch="adr/001-test-decision",
            )

        assert result["content"]["path"] == "docs/adr/ADR-001-test-decision.md"
        assert result["commit"]["sha"] == "commit123sha"

    def test_create_file_uses_correct_endpoint_and_base64_content(self) -> None:
        """Verify the REST API call and Base64 encoding for file content."""
        import base64

        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {
                "content": {"path": "test.md"},
                "commit": {"sha": "abc123"},
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_file(
                repo="owner/repo",
                path="docs/adr/test.md",
                content="# Test Content",
                message="Add test file",
                branch="test-branch",
            )

        assert captured_request["method"] == "PUT"
        assert "/repos/owner/repo/contents/docs/adr/test.md" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert body["message"] == "Add test file"
        assert body["branch"] == "test-branch"
        # Content should be Base64 encoded
        decoded = base64.b64decode(body["content"]).decode("utf-8")
        assert decoded == "# Test Content"


class TestGitHubClientCreatePullRequest:
    """Test creating pull requests on GitHub."""

    def test_create_pull_request_success(self) -> None:
        """Successfully create a pull request."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
            "title": "ADR-001: Test Decision",
            "body": "## Summary\n\nThis ADR documents...",
            "state": "open",
            "head": {"ref": "adr/001-test-decision"},
            "base": {"ref": "main"},
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_pull_request(
                repo="owner/repo",
                title="ADR-001: Test Decision",
                body="## Summary\n\nThis ADR documents...",
                head="adr/001-test-decision",
                base="main",
            )

        assert result["number"] == 42
        assert result["html_url"] == "https://github.com/owner/repo/pull/42"

    def test_create_pull_request_uses_correct_endpoint_and_payload(self) -> None:
        """Verify the REST API call structure for creating PRs."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {
                "number": 1,
                "html_url": "https://github.com/test",
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_pull_request(
                repo="owner/repo",
                title="Test PR",
                body="PR body",
                head="feature-branch",
                base="main",
            )

        assert captured_request["method"] == "POST"
        assert "/repos/owner/repo/pulls" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert body["title"] == "Test PR"
        assert body["body"] == "PR body"
        assert body["head"] == "feature-branch"
        assert body["base"] == "main"

    def test_create_pull_request_handles_conflict(self) -> None:
        """Handle 422 when PR cannot be created (e.g., no commits to compare)."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "Validation Failed",
            "errors": [{"message": "No commits between main and feature-branch"}],
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="422|Validation Failed"),
        ):
            client.create_pull_request(
                repo="owner/repo",
                title="Test PR",
                body="PR body",
                head="feature-branch",
                base="main",
            )


class TestGitHubClientGetDefaultBranch:
    """Test getting repository default branch."""

    def test_get_default_branch_returns_branch_name(self) -> None:
        """Get repository default branch name."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "default_branch": "main",
            "name": "repo",
            "full_name": "owner/repo",
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_default_branch(repo="owner/repo")

        assert result == "main"

    def test_get_default_branch_uses_correct_endpoint(self) -> None:
        """Verify the REST API endpoint for getting repository info."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **_kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"default_branch": "main"}
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.get_default_branch(repo="owner/repo")

        assert captured_request["method"] == "GET"
        assert "/repos/owner/repo" in captured_request["url"]
        # Should NOT include /git/ref etc. - just the repo endpoint
        assert captured_request["url"].rstrip("/").endswith("/repos/owner/repo")
