"""GitHub API client for syncing debate turns to Discussions/Issues (Issue #15).

This module implements:
- GitHubClient for posting comments to Discussions (GraphQL) and Issues (REST)
- Branch/file creation and PR support for ratify_rfc (Issue #16)
- Rate limit handling with exponential backoff (429 and 403 responses)
- Comment formatting for debate turns

Immutables Compliance:
- I4 (VERIFIABLE_EVENT_LEDGER): Comment IDs stored for reference

Rate Limiting Notes:
- GitHub primary rate limit: 5000 requests/hour for authenticated users
- GitHub secondary rate limit: varies by endpoint (e.g., 80 content-creating requests/minute)
- Discussion comments: subject to secondary rate limits
- Issue comments: subject to secondary rate limits
- GitHub returns 429 (Too Many Requests) or 403 (Forbidden) for rate limiting

Feature Toggle:
- Set GITHUB_TOOLS_ENABLED=false to disable all GitHub integration tools
"""

import base64
import os
import time
from typing import Any

import httpx

from debate_hall_mcp.state import Turn


def is_github_tools_enabled() -> bool:
    """Check if GitHub integration tools are enabled.

    Returns:
        True if enabled (default), False if GITHUB_TOOLS_ENABLED=false
    """
    value = os.environ.get("GITHUB_TOOLS_ENABLED", "true").lower()
    return value not in ("false", "0", "no", "off", "disabled")


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

    def _is_rate_limit_response(self, response: httpx.Response) -> bool:
        """Check if response indicates rate limiting.

        GitHub rate limits can return:
        - 429 Too Many Requests (standard rate limit)
        - 403 Forbidden with rate limit headers (primary/secondary rate limit)
        - 403 with "rate limit" in message (GraphQL rate limit)

        Args:
            response: HTTP response to check

        Returns:
            True if this is a rate limit response that should be retried
        """
        # 429 is always rate limiting
        if response.status_code == 429:
            return True

        # 403 may or may not be rate limiting - check headers and body
        if response.status_code == 403:
            # Check for rate limit headers
            if response.headers.get("X-RateLimit-Remaining") == "0":
                return True

            # Check for rate limit message in response body
            try:
                data = response.json()
                message = data.get("message", "").lower()
                if "rate limit" in message or "secondary rate limit" in message:
                    return True
            except Exception:
                pass

        return False

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make request with retry logic for rate limits.

        Handles both 429 and 403 rate limit responses from GitHub.

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

            # Check if this is NOT a rate limit response - return immediately
            if not self._is_rate_limit_response(response):
                return response

            # Rate limited - check if we should retry
            if attempt >= self._max_retries:
                break

            # Get retry delay from headers or use exponential backoff
            # GitHub uses Retry-After for 429, X-RateLimit-Reset for 403
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                delay = float(retry_after)
            else:
                # Check X-RateLimit-Reset (Unix timestamp)
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    delay = max(0, int(reset_time) - int(time.time()) + 1)
                else:
                    # Fallback to exponential backoff
                    delay = self._base_delay * (2**attempt)

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

    def get_ref(self, repo: str, ref: str) -> dict[str, Any]:
        """Get a Git reference (branch/tag) from a repository.

        Args:
            repo: Repository in "owner/repo" format
            ref: Reference path (e.g., "heads/main" for main branch)

        Returns:
            Dictionary with reference details including 'sha' and 'ref'

        Raises:
            GitHubAPIError: If the API returns an error (e.g., 404 not found)
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/git/ref/{ref}"
        response = self._request_with_retry("GET", url)

        data = response.json()

        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message}")

        return {
            "ref": data.get("ref"),
            "sha": data.get("object", {}).get("sha"),
        }

    def create_ref(self, repo: str, ref: str, sha: str) -> dict[str, Any]:
        """Create a new Git reference (branch) in a repository.

        Args:
            repo: Repository in "owner/repo" format
            ref: Full reference path (e.g., "refs/heads/feature-branch")
            sha: The SHA1 value for this reference to point to

        Returns:
            Dictionary with the created reference details

        Raises:
            GitHubAPIError: If the API returns an error (e.g., 422 already exists)
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/git/refs"
        payload = {"ref": ref, "sha": sha}

        response = self._request_with_retry("POST", url, json=payload)

        data = response.json()

        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message}")

        return dict(data)

    def create_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> dict[str, Any]:
        """Create or update a file in a repository via Contents API.

        Args:
            repo: Repository in "owner/repo" format
            path: Path to the file (e.g., "docs/adr/ADR-001.md")
            content: The file content (will be Base64 encoded)
            message: Commit message
            branch: The branch to commit to

        Returns:
            Dictionary with commit and content details

        Raises:
            GitHubAPIError: If the API returns an error
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/contents/{path}"
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }

        response = self._request_with_retry("PUT", url, json=payload)

        data = response.json()

        if response.status_code >= 400:
            message_text = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message_text}")

        return dict(data)

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            repo: Repository in "owner/repo" format
            title: PR title
            body: PR body/description
            head: The head branch (branch with changes)
            base: The base branch (target branch)

        Returns:
            Dictionary with PR details including 'number' and 'html_url'

        Raises:
            GitHubAPIError: If the API returns an error
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        response = self._request_with_retry("POST", url, json=payload)

        data = response.json()

        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {response.status_code} - {message}")

        return dict(data)

    def get_discussion_number(self, node_id: str) -> int:
        """Get the human-readable discussion number from a node ID via GraphQL.

        This enables constructing deep links like /discussions/15 from the
        node ID (D_kwDO...) that is used internally by the GraphQL API.

        Args:
            node_id: The GraphQL node ID of the discussion (e.g., "D_kwDO...")

        Returns:
            The human-readable discussion number (e.g., 15 for discussions/15)

        Raises:
            GitHubAPIError: If the API returns an error, node doesn't exist,
                           or node is not a Discussion
            GitHubRateLimitError: If rate limit exceeded
        """
        query = """
        query GetDiscussionNumber($nodeId: ID!) {
            node(id: $nodeId) {
                ... on Discussion {
                    number
                }
            }
        }
        """

        payload = {
            "query": query,
            "variables": {
                "nodeId": node_id,
            },
        }

        response = self._request_with_retry("POST", GITHUB_GRAPHQL_URL, json=payload)

        # Validate HTTP status code first
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

        # Extract and validate node data
        node_data = data.get("data", {}).get("node")

        # Validate that we got a valid node
        if node_data is None:
            raise GitHubAPIError(
                "GraphQL response has null node - discussion may be deleted or inaccessible"
            )

        # Validate that node has a number field (is a Discussion)
        number = node_data.get("number")
        if number is None:
            raise GitHubAPIError(f"Node {node_id} is not a Discussion or is missing number field")

        return int(number)

    def get_default_branch(self, repo: str) -> str:
        """Get the default branch name for a repository.

        Args:
            repo: Repository in "owner/repo" format

        Returns:
            The default branch name (e.g., "main" or "master")

        Raises:
            GitHubAPIError: If the API returns an error
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}"
        response = self._request_with_retry("GET", url)

        data = response.json()

        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message}")

        return str(data.get("default_branch", "main"))

    def get_discussion_comment(self, node_id: str) -> dict[str, Any]:
        """Fetch a Discussion comment by node ID via GraphQL API (Issue #17).

        Args:
            node_id: The GraphQL node ID of the discussion comment (e.g., "DC_kwDO...")

        Returns:
            Dictionary with comment details:
            - body: The comment body text
            - author: Username of comment author
            - reply_to_id: Node ID of parent comment if this is a reply, else None
            - discussion_id: Node ID of the parent discussion (for source validation)

        Raises:
            GitHubAPIError: If the API returns an error or node doesn't exist
            GitHubRateLimitError: If rate limit exceeded
        """
        query = """
        query GetDiscussionComment($nodeId: ID!) {
            node(id: $nodeId) {
                ... on DiscussionComment {
                    body
                    author {
                        login
                    }
                    replyTo {
                        id
                    }
                    discussion {
                        id
                    }
                }
            }
        }
        """

        payload = {
            "query": query,
            "variables": {
                "nodeId": node_id,
            },
        }

        response = self._request_with_retry("POST", GITHUB_GRAPHQL_URL, json=payload)

        # Validate HTTP status code first
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

        # Extract and validate node data
        node_data = data.get("data", {}).get("node")

        if node_data is None:
            raise GitHubAPIError(
                "GraphQL response has null node - comment may be deleted or inaccessible"
            )

        # Extract fields
        body = node_data.get("body", "")
        author_data = node_data.get("author")
        author = author_data.get("login") if author_data else None
        reply_to_data = node_data.get("replyTo")
        reply_to_id = reply_to_data.get("id") if reply_to_data else None
        discussion_data = node_data.get("discussion")
        discussion_id = discussion_data.get("id") if discussion_data else None

        return {
            "body": body,
            "author": author,
            "reply_to_id": reply_to_id,
            "discussion_id": discussion_id,
        }

    def get_issue_comment(self, repo: str, comment_id: int) -> dict[str, Any]:
        """Fetch an Issue comment by ID via REST API (Issue #17).

        Args:
            repo: Repository in "owner/repo" format
            comment_id: The issue comment ID

        Returns:
            Dictionary with comment details:
            - body: The comment body text
            - author: Username of comment author
            - node_id: GraphQL node ID of the comment
            - issue_url: API URL of the parent issue (for source validation)

        Raises:
            GitHubAPIError: If the API returns an error (e.g., 404 not found)
            GitHubRateLimitError: If rate limit exceeded
        """
        url = f"{GITHUB_REST_BASE_URL}/repos/{repo}/issues/comments/{comment_id}"
        response = self._request_with_retry("GET", url)

        data = response.json()

        if response.status_code >= 400:
            message = data.get("message", f"HTTP {response.status_code}")
            raise GitHubAPIError(f"REST API error: {message}")

        # Extract fields
        user_data = data.get("user")
        author = user_data.get("login") if user_data else None

        return {
            "body": data.get("body", ""),
            "author": author,
            "node_id": data.get("node_id"),
            "issue_url": data.get("issue_url"),
        }

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
