"""Unit tests for GitHub API client (Issue #15).

TDD Discipline: RED->GREEN->REFACTOR
Tests the GitHub client for posting comments to Discussions and Issues.
All tests use mocked HTTP responses - no actual GitHub API calls.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestGitHubClientInitialization:
    """Test GitHubClient initialization and configuration."""

    def test_github_client_requires_token(self) -> None:
        """GitHubClient requires GITHUB_TOKEN env var."""
        from debate_hall_mcp.github import GitHubClient, GitHubTokenError

        # Without GITHUB_TOKEN, should raise
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(GitHubTokenError, match="GITHUB_TOKEN"),
        ):
            GitHubClient()

    def test_github_client_uses_token_from_env(self) -> None:
        """GitHubClient uses GITHUB_TOKEN from environment."""
        from debate_hall_mcp.github import GitHubClient

        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test_token_123"}):
            client = GitHubClient()
            assert client._token == "ghp_test_token_123"

    def test_github_client_allows_custom_token(self) -> None:
        """GitHubClient accepts explicit token parameter."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_custom_token")
        assert client._token == "ghp_custom_token"


class TestGitHubClientDiscussionComments:
    """Test posting comments to GitHub Discussions via GraphQL API."""

    def test_post_discussion_comment_success(self) -> None:
        """Successfully post a comment to a GitHub Discussion."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        # Mock the GraphQL response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "addDiscussionComment": {
                    "comment": {
                        "id": "DC_kwDOtest123",
                        "url": "https://github.com/owner/repo/discussions/1#discussioncomment-123",
                    }
                }
            }
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.post_discussion_comment(
                discussion_id="D_kwDOdiscussion123",
                body="## Wind (PATHOS)\nTest comment content",
            )

        assert result["id"] == "DC_kwDOtest123"
        assert "url" in result

    def test_post_discussion_comment_formats_graphql_mutation(self) -> None:
        """Verify the GraphQL mutation structure for discussion comments."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "data": {
                    "addDiscussionComment": {
                        "comment": {"id": "DC_test", "url": "https://example.com"}
                    }
                }
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test body",
            )

        # Verify GraphQL mutation structure
        assert captured_request["method"] == "POST"
        assert "graphql" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert "query" in body
        assert "addDiscussionComment" in body["query"]
        assert "variables" in body
        assert body["variables"]["discussionId"] == "D_kwDO123"
        assert body["variables"]["body"] == "Test body"

    def test_post_discussion_comment_handles_graphql_errors(self) -> None:
        """Handle GraphQL errors gracefully."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Could not resolve to a node with ID D_invalid"}]
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Could not resolve"),
        ):
            client.post_discussion_comment(
                discussion_id="D_invalid",
                body="Test",
            )


class TestGitHubClientIssueComments:
    """Test posting comments to GitHub Issues via REST API."""

    def test_post_issue_comment_success(self) -> None:
        """Successfully post a comment to a GitHub Issue."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 123456789,
            "node_id": "IC_kwDOtest123",
            "html_url": "https://github.com/owner/repo/issues/42#issuecomment-123456789",
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.post_issue_comment(
                repo="owner/repo",
                issue_number=42,
                body="## Wall (ETHOS)\nTest issue comment",
            )

        assert result["node_id"] == "IC_kwDOtest123"
        assert result["html_url"].startswith("https://github.com")

    def test_post_issue_comment_uses_rest_api(self) -> None:
        """Verify the REST API call structure for issue comments."""
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
                "id": 123,
                "node_id": "IC_test",
                "html_url": "https://example.com",
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.post_issue_comment(
                repo="owner/repo",
                issue_number=42,
                body="Test body",
            )

        # Verify REST API structure
        assert captured_request["method"] == "POST"
        assert "/repos/owner/repo/issues/42/comments" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert body["body"] == "Test body"

    def test_post_issue_comment_handles_not_found(self) -> None:
        """Handle 404 errors for non-existent issues."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Not Found"),
        ):
            client.post_issue_comment(
                repo="owner/repo",
                issue_number=99999,
                body="Test",
            )


class TestGitHubClientRateLimiting:
    """Test rate limit handling with exponential backoff."""

    def test_rate_limit_retry_with_backoff(self) -> None:
        """Retry on rate limit with exponential backoff."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        call_count = 0

        def mock_request(_method: str, _url: str, **_kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1

            response = MagicMock()
            if call_count < 3:
                # First two calls hit rate limit
                response.status_code = 429
                response.headers = {"Retry-After": "0.01"}
                response.json.return_value = {"message": "rate limit exceeded"}
            else:
                # Third call succeeds
                response.status_code = 201
                response.json.return_value = {
                    "id": 123,
                    "node_id": "IC_success",
                    "html_url": "https://example.com",
                }
            return response

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = client.post_issue_comment(
                repo="owner/repo",
                issue_number=1,
                body="Test",
            )

        assert result["node_id"] == "IC_success"
        assert call_count == 3

    def test_rate_limit_max_retries_exceeded(self) -> None:
        """Raise error when max retries exceeded."""
        from debate_hall_mcp.github import GitHubClient, GitHubRateLimitError

        client = GitHubClient(token="ghp_test", max_retries=2)

        def always_rate_limited(_method: str, _url: str, **_kwargs: Any) -> MagicMock:
            response = MagicMock()
            response.status_code = 429
            response.headers = {"Retry-After": "0.01"}
            response.json.return_value = {"message": "rate limit exceeded"}
            return response

        with (
            patch.object(client, "_make_request", side_effect=always_rate_limited),
            pytest.raises(GitHubRateLimitError, match="rate limit"),
        ):
            client.post_issue_comment(
                repo="owner/repo",
                issue_number=1,
                body="Test",
            )


class TestGitHubClientAuthentication:
    """Test authentication header handling."""

    def test_auth_header_format(self) -> None:
        """Verify Authorization header format."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test_token")

        # Check that headers include proper auth
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer ghp_test_token"
        assert headers["Accept"] == "application/vnd.github+json"
        assert "X-GitHub-Api-Version" in headers


class TestCommentFormatting:
    """Test formatting debate turns as GitHub comments."""

    def test_format_turn_as_comment_wind(self) -> None:
        """Format Wind turn with PATHOS emoji and headers."""
        from debate_hall_mcp.github import format_turn_as_comment
        from debate_hall_mcp.state import Turn

        turn = Turn(
            role="Wind",
            content="This is the Wind's position.",
            timestamp="2025-01-02T10:00:00+00:00",
            previous_hash=None,
            model="claude-opus-4-5",
            cognition="PATHOS",
        )

        comment = format_turn_as_comment(turn, turn_number=1, max_turns=12)

        # Check formatting
        assert "Wind" in comment
        assert "PATHOS" in comment
        assert "claude-opus-4-5" in comment
        assert "Turn**: 1/12" in comment
        assert "This is the Wind's position." in comment
        assert "debate-hall-mcp" in comment  # Footer link

    def test_format_turn_as_comment_wall(self) -> None:
        """Format Wall turn with ETHOS styling."""
        from debate_hall_mcp.github import format_turn_as_comment
        from debate_hall_mcp.state import Turn

        turn = Turn(
            role="Wall",
            content="Counter-argument from Wall.",
            timestamp="2025-01-02T10:01:00+00:00",
            previous_hash="abc123",
            model="gemini-2.5-pro",
            cognition="ETHOS",
        )

        comment = format_turn_as_comment(turn, turn_number=2, max_turns=12)

        assert "Wall" in comment
        assert "ETHOS" in comment
        assert "gemini-2.5-pro" in comment

    def test_format_turn_as_comment_door(self) -> None:
        """Format Door turn with LOGOS styling."""
        from debate_hall_mcp.github import format_turn_as_comment
        from debate_hall_mcp.state import Turn

        turn = Turn(
            role="Door",
            content="Synthesis from Door.",
            timestamp="2025-01-02T10:02:00+00:00",
            previous_hash="def456",
            cognition="LOGOS",
        )

        comment = format_turn_as_comment(turn, turn_number=3, max_turns=12)

        assert "Door" in comment
        assert "LOGOS" in comment

    def test_format_turn_handles_missing_metadata(self) -> None:
        """Handle turns without optional metadata gracefully."""
        from debate_hall_mcp.github import format_turn_as_comment
        from debate_hall_mcp.state import Turn

        turn = Turn(
            role="Wind",
            content="Minimal turn content.",
            timestamp="2025-01-02T10:00:00+00:00",
            previous_hash=None,
            # No model or cognition
        )

        # Should not raise
        comment = format_turn_as_comment(turn, turn_number=1, max_turns=6)

        assert "Wind" in comment
        assert "Minimal turn content." in comment


class TestGitHubClientHTTPStatusValidation:
    """Test HTTP status code validation in GraphQL responses (Blocking Issue #2).

    GitHub may return 401/403 with JSON that lacks 'errors' field.
    The client must validate HTTP status codes, not just check for 'errors'.
    """

    def test_post_discussion_comment_raises_on_401_without_errors(self) -> None:
        """GraphQL 401 response without 'errors' field must raise GitHubAPIError.

        This catches auth failures where GitHub returns JSON like:
        {"message": "Bad credentials"} without a GraphQL errors array.
        """
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_invalid_token")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="401|Bad credentials"),
        ):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test",
            )

    def test_post_discussion_comment_raises_on_403_without_errors(self) -> None:
        """GraphQL 403 response without 'errors' field must raise GitHubAPIError."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Resource not accessible"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="403|Resource not accessible"),
        ):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test",
            )

    def test_post_discussion_comment_raises_on_500_server_error(self) -> None:
        """GraphQL 500 response must raise GitHubAPIError."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="500|Internal Server Error"),
        ):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test",
            )

    def test_post_discussion_comment_raises_on_missing_comment_id(self) -> None:
        """Response with empty/missing comment id must raise GitHubAPIError.

        Even with HTTP 200, if the response structure is wrong (no comment.id),
        we should fail rather than record an empty comment_id.
        """
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Missing nested 'comment' or 'id' field
        mock_response.json.return_value = {"data": {"addDiscussionComment": {}}}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="comment|id|missing"),
        ):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test",
            )

    def test_post_discussion_comment_raises_on_null_comment_id(self) -> None:
        """Response with null comment id must raise GitHubAPIError."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "addDiscussionComment": {"comment": {"id": None, "url": "https://example.com"}}
            }
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="comment|id|missing|null"),
        ):
            client.post_discussion_comment(
                discussion_id="D_kwDO123",
                body="Test",
            )


class TestGitHubClientGetDiscussionNumber:
    """Test fetching discussion number from node ID via GraphQL API."""

    def test_get_discussion_number_success(self) -> None:
        """Successfully fetch discussion number from node ID."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        # Mock the GraphQL response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "node": {
                    "number": 42,
                }
            }
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_discussion_number(node_id="D_kwDO123abc")

        assert result == 42

    def test_get_discussion_number_formats_graphql_query(self) -> None:
        """Verify the GraphQL query structure for fetching discussion number."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": {"node": {"number": 15}}}
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.get_discussion_number(node_id="D_kwDO456def")

        # Verify GraphQL query structure
        assert captured_request["method"] == "POST"
        assert "graphql" in captured_request["url"]
        body = captured_request["kwargs"].get("json", {})
        assert "query" in body
        assert "node" in body["query"]
        assert "Discussion" in body["query"]
        assert "number" in body["query"]
        assert body["variables"]["nodeId"] == "D_kwDO456def"

    def test_get_discussion_number_handles_invalid_node(self) -> None:
        """Handle error when node ID doesn't exist or isn't a discussion."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Could not resolve to a node with the global id of 'D_invalid'"}]
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Could not resolve"),
        ):
            client.get_discussion_number(node_id="D_invalid")

    def test_get_discussion_number_handles_null_node(self) -> None:
        """Handle case where node is null (deleted or inaccessible)."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"node": None}}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="node|null|missing"),
        ):
            client.get_discussion_number(node_id="D_kwDO_deleted")

    def test_get_discussion_number_handles_missing_number_field(self) -> None:
        """Handle case where node exists but has no number field (not a discussion)."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Node exists but isn't a Discussion (no number field)
        mock_response.json.return_value = {"data": {"node": {}}}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="number|missing|Discussion"),
        ):
            client.get_discussion_number(node_id="D_kwDO_not_discussion")


class TestGitHubClientRepositoryOperations:
    """Test GitHubClient repository operations for Issue #16 ratify_rfc support.

    Tests the methods: get_ref, create_ref, create_file, create_pull_request,
    get_default_branch. These were previously only tested at tool-level with mocks,
    leaving implementation bugs (URL construction, Base64 encoding) uncaught.
    """

    def test_get_ref_success(self) -> None:
        """Test fetching ref SHA from repository."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ref": "refs/heads/main",
            "object": {
                "sha": "abc123def456",
                "type": "commit",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_ref(repo="owner/repo", ref="heads/main")

        assert result["sha"] == "abc123def456"
        assert result["ref"] == "refs/heads/main"

    def test_get_ref_url_construction(self) -> None:
        """Verify correct URL construction for get_ref."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
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

    def test_get_ref_not_found(self) -> None:
        """Test 404 handling when ref doesn't exist."""
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

    def test_create_ref_success(self) -> None:
        """Test branch creation via create_ref."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "ref": "refs/heads/feature-branch",
            "object": {
                "sha": "abc123",
                "type": "commit",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_ref(
                repo="owner/repo",
                ref="refs/heads/feature-branch",
                sha="abc123",
            )

        assert result["ref"] == "refs/heads/feature-branch"

    def test_create_ref_url_and_payload(self) -> None:
        """Verify correct URL and payload for create_ref."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {"ref": "refs/heads/test", "object": {"sha": "xyz"}}
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_ref(
                repo="owner/repo",
                ref="refs/heads/test-branch",
                sha="abc123def",
            )

        assert captured_request["method"] == "POST"
        assert "/repos/owner/repo/git/refs" in captured_request["url"]
        payload = captured_request["kwargs"].get("json", {})
        assert payload["ref"] == "refs/heads/test-branch"
        assert payload["sha"] == "abc123def"

    def test_create_ref_already_exists_422(self) -> None:
        """Test 422 handling when branch already exists."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "Reference already exists",
            "documentation_url": "https://docs.github.com/rest/git/refs#create-a-reference",
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Reference already exists"),
        ):
            client.create_ref(
                repo="owner/repo",
                ref="refs/heads/existing-branch",
                sha="abc123",
            )

    def test_create_file_success(self) -> None:
        """Test file commit via create_file."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "content": {
                "name": "test.md",
                "path": "docs/test.md",
                "sha": "file_sha_123",
            },
            "commit": {
                "sha": "commit_sha_456",
                "message": "Add test file",
            },
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_file(
                repo="owner/repo",
                path="docs/test.md",
                content="# Test Content",
                message="Add test file",
                branch="feature-branch",
            )

        assert result["content"]["path"] == "docs/test.md"
        assert result["commit"]["sha"] == "commit_sha_456"

    def test_create_file_base64_encoding(self) -> None:
        """Verify content is properly base64 encoded."""
        import base64

        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}
        test_content = "# Hello World\n\nThis is test content with unicode: cafe"

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:
            captured_request["method"] = method
            captured_request["url"] = url
            captured_request["kwargs"] = kwargs
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {
                "content": {"path": "test.md", "sha": "abc"},
                "commit": {"sha": "xyz"},
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_file(
                repo="owner/repo",
                path="test.md",
                content=test_content,
                message="Test commit",
                branch="main",
            )

        assert captured_request["method"] == "PUT"
        assert "/repos/owner/repo/contents/test.md" in captured_request["url"]
        payload = captured_request["kwargs"].get("json", {})

        # Verify base64 encoding
        encoded_content = payload["content"]
        decoded_content = base64.b64decode(encoded_content).decode("utf-8")
        assert decoded_content == test_content

        # Verify other payload fields
        assert payload["message"] == "Test commit"
        assert payload["branch"] == "main"

    def test_create_file_url_construction(self) -> None:
        """Verify correct URL construction for create_file with path."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:  # noqa: ARG001
            captured_request["url"] = url
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {
                "content": {"path": "docs/adr/ADR-001.md"},
                "commit": {"sha": "abc"},
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_file(
                repo="owner/repo",
                path="docs/adr/ADR-001.md",
                content="content",
                message="msg",
                branch="branch",
            )

        # Verify nested path is preserved in URL
        assert "/repos/owner/repo/contents/docs/adr/ADR-001.md" in captured_request["url"]

    def test_create_pull_request_success(self) -> None:
        """Test PR creation."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
            "state": "open",
            "title": "Test PR",
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.create_pull_request(
                repo="owner/repo",
                title="Test PR",
                body="PR description",
                head="feature-branch",
                base="main",
            )

        assert result["number"] == 42
        assert result["html_url"] == "https://github.com/owner/repo/pull/42"

    def test_create_pull_request_payload(self) -> None:
        """Verify correct payload structure for create_pull_request."""
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
                "html_url": "https://example.com/pull/1",
            }
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.create_pull_request(
                repo="owner/repo",
                title="ADR-001: Test Decision",
                body="This is the PR body",
                head="adr/001-test",
                base="main",
            )

        assert captured_request["method"] == "POST"
        assert "/repos/owner/repo/pulls" in captured_request["url"]
        payload = captured_request["kwargs"].get("json", {})
        assert payload["title"] == "ADR-001: Test Decision"
        assert payload["body"] == "This is the PR body"
        assert payload["head"] == "adr/001-test"
        assert payload["base"] == "main"

    def test_create_pull_request_handles_errors(self) -> None:
        """Test error handling for PR creation failures."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "Validation Failed",
            "errors": [{"message": "A pull request already exists"}],
        }

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="422.*Validation Failed"),
        ):
            client.create_pull_request(
                repo="owner/repo",
                title="Duplicate PR",
                body="Body",
                head="branch",
                base="main",
            )

    def test_get_default_branch_success(self) -> None:
        """Test fetching default branch name."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "full_name": "owner/repo",
            "default_branch": "main",
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_default_branch(repo="owner/repo")

        assert result == "main"

    def test_get_default_branch_master(self) -> None:
        """Test fetching default branch when it's master (not main)."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "old-repo",
            "default_branch": "master",
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            result = client.get_default_branch(repo="owner/old-repo")

        assert result == "master"

    def test_get_default_branch_url_construction(self) -> None:
        """Verify correct URL for get_default_branch."""
        from debate_hall_mcp.github import GitHubClient

        client = GitHubClient(token="ghp_test")

        captured_request: dict[str, Any] = {}

        def capture_request(method: str, url: str, **kwargs: Any) -> MagicMock:  # noqa: ARG001
            captured_request["method"] = method
            captured_request["url"] = url
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"default_branch": "main"}
            return response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.get_default_branch(repo="owner/repo")

        assert captured_request["method"] == "GET"
        assert captured_request["url"].endswith("/repos/owner/repo")

    def test_get_default_branch_not_found(self) -> None:
        """Test error handling when repository doesn't exist."""
        from debate_hall_mcp.github import GitHubAPIError, GitHubClient

        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        with (
            patch.object(client, "_make_request", return_value=mock_response),
            pytest.raises(GitHubAPIError, match="Not Found"),
        ):
            client.get_default_branch(repo="nonexistent/repo")
