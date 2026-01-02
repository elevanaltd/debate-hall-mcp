"""GitHub API client for syncing debate turns to Discussions/Issues (Issue #15).

This module implements:
- GitHubClient for posting comments to Discussions (GraphQL) and Issues (REST)
- Rate limit handling with exponential backoff
- Comment formatting for debate turns

Immutables Compliance:
- I4 (VERIFIABLE_EVENT_LEDGER): Comment IDs stored for reference
"""

import os
import time
from typing import Any

import httpx

from debate_hall_mcp.state import Turn

# GitHub API endpoints
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_BASE_URL = "https://api.github.com"

# API version header
GITHUB_API_VERSION = "2022-11-28"

# Default retry settings
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 1.0  # seconds


class GitHubTokenError(Exception):
    """Raised when GITHUB_TOKEN is not available."""

    pass


class GitHubAPIError(Exception):
    """Raised when GitHub API returns an error."""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when rate limit is exceeded and max retries reached."""

    pass


# Emoji and styling for each role
ROLE_STYLING = {
    "Wind": {"emoji": "wind_face", "header_emoji": "wind"},
    "Wall": {"emoji": "brick", "header_emoji": "wall"},
    "Door": {"emoji": "door", "header_emoji": "door"},
}

# Cognition labels with styling - using safe ASCII alternatives
COGNITION_STYLING = {
    "PATHOS": {"label": "PATHOS", "description": "emotion/intuition"},
    "ETHOS": {"label": "ETHOS", "description": "ethics/credibility"},
    "LOGOS": {"label": "LOGOS", "description": "logic/reason"},
}


def format_turn_as_comment(turn: Turn, turn_number: int, max_turns: int) -> str:
    """Format a debate turn as a GitHub comment.

    Args:
        turn: The Turn object to format
        turn_number: The 1-indexed turn number
        max_turns: Maximum turns allowed in the debate

    Returns:
        Formatted markdown string for the comment
    """
    role = turn.role
    cognition = turn.cognition

    # Build header line
    role_style = ROLE_STYLING.get(role, {"emoji": "speech_balloon", "header_emoji": "speech"})
    header_emoji = role_style["header_emoji"]

    # Format cognition if present
    cognition_display = ""
    if cognition and cognition in COGNITION_STYLING:
        cognition_info = COGNITION_STYLING[cognition]
        cognition_display = f" ({cognition_info['label']})"

    # Build metadata line
    metadata_parts = []
    if turn.model:
        metadata_parts.append(f"**Model**: {turn.model}")
    metadata_parts.append(f"**Turn**: {turn_number}/{max_turns}")
    metadata_line = " | ".join(metadata_parts)

    # Build the comment
    lines = [
        f"## :{header_emoji}: {role}{cognition_display}",
        metadata_line,
        "",
        turn.content,
        "",
        "---",
        "*Posted via [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp)*",
    ]

    return "\n".join(lines)


class GitHubClient:
    """GitHub API client for posting comments to Discussions and Issues.

    Supports both GraphQL API (for Discussions) and REST API (for Issues).
    Includes rate limit handling with exponential backoff.

    Example:
        >>> client = GitHubClient()  # Uses GITHUB_TOKEN env var
        >>> result = client.post_discussion_comment(
        ...     discussion_id="D_kwDO123",
        ...     body="## Wind (PATHOS)\\nContent here"
        ... )
        >>> print(result["id"])  # Comment node ID
    """

    def __init__(
        self,
        token: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
    ) -> None:
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token. If not provided,
                   reads from GITHUB_TOKEN environment variable.
            max_retries: Maximum number of retries for rate-limited requests.
            base_delay: Base delay in seconds for exponential backoff.

        Raises:
            GitHubTokenError: If no token provided and GITHUB_TOKEN not set.
        """
        if token is None:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise GitHubTokenError(
                    "GITHUB_TOKEN environment variable is required. "
                    "Set it to a GitHub personal access token with appropriate permissions."
                )

        self._token = token
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        """Get standard headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request to GitHub API.

        This is the low-level request method that can be mocked in tests.
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())
        return self._client.request(method, url, headers=headers, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make request with retry logic for rate limits.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            httpx.Response on success

        Raises:
            GitHubRateLimitError: If max retries exceeded for rate limiting
        """
        for attempt in range(self._max_retries + 1):
            response = self._make_request(method, url, **kwargs)

            if response.status_code != 429:
                return response

            # Rate limited - check if we should retry
            if attempt >= self._max_retries:
                break

            # Get retry delay from header or use exponential backoff
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else self._base_delay * (2**attempt)

            time.sleep(delay)

        # Max retries exceeded
        raise GitHubRateLimitError(f"GitHub rate limit exceeded after {self._max_retries} retries")

    def post_discussion_comment(self, discussion_id: str, body: str) -> dict[str, Any]:
        """Post a comment to a GitHub Discussion using GraphQL API.

        Args:
            discussion_id: The GraphQL node ID of the discussion (e.g., "D_kwDO...")
            body: The markdown body of the comment

        Returns:
            Dictionary with comment details including 'id' (node ID) and 'url'

        Raises:
            GitHubAPIError: If the API returns an error or response is malformed
            GitHubRateLimitError: If rate limit exceeded
        """
        mutation = """
        mutation AddDiscussionComment($discussionId: ID!, $body: String!) {
            addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
                comment {
                    id
                    url
                }
            }
        }
        """

        payload = {
            "query": mutation,
            "variables": {
                "discussionId": discussion_id,
                "body": body,
            },
        }

        response = self._request_with_retry("POST", GITHUB_GRAPHQL_URL, json=payload)

        # Validate HTTP status code first (GitHub may return 401/403 without 'errors')
        if response.status_code >= 400:
            try:
                data = response.json()
                message = data.get("message", f"HTTP {response.status_code}")
            except Exception:
                message = f"HTTP {response.status_code}"
            raise GitHubAPIError(f"GraphQL API error: {response.status_code} - {message}")

        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            error_messages = [e.get("message", str(e)) for e in data["errors"]]
            raise GitHubAPIError(f"GraphQL error: {'; '.join(error_messages)}")

        # Extract and validate comment data
        comment_data = data.get("data", {}).get("addDiscussionComment", {}).get("comment")

        # Validate that we got a valid comment with an id
        if not comment_data or not comment_data.get("id"):
            raise GitHubAPIError(
                "GraphQL response missing expected comment id - response may be malformed"
            )

        return dict(comment_data)

    def post_issue_comment(self, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        """Post a comment to a GitHub Issue using REST API.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: The issue number
            body: The markdown body of the comment

        Returns:
            Dictionary with comment details including 'node_id' and 'html_url'

        Raises:
            GitHubAPIError: If the API returns an error
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/issues/{issue_number}/comments"
        payload = {"body": body}

        response = self._request_with_retry("POST", url, json=payload)

        data = response.json()

        # Check for errors
        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message}")

        return dict(data)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
