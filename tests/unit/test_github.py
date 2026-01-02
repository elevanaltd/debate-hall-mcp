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
