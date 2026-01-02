"""github_sync_debate tool - Sync debate turns to GitHub (Issue #15).

Syncs debate turns to GitHub Discussion or Issue comments.
Idempotent: tracks synced turns to avoid duplicates.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I4 (VERIFIABLE_EVENT_LEDGER): Comment IDs stored for reference

Robustness:
- Persists state after EACH successful post (not just at end of loop)
- Validates comment IDs are non-empty before advancing state
- Detects repo mismatch in binding conflict checks
"""

import os
from pathlib import Path
from typing import Any

from debate_hall_mcp.github import GitHubAPIError, GitHubClient, format_turn_as_comment
from debate_hall_mcp.state import (
    GitHubBinding,
    GitHubTargetType,
    load_debate_state,
    save_debate_state,
)

# Environment variable for state directory
STATE_DIR_ENV_VAR = "DEBATE_HALL_STATE_DIR"
DEFAULT_STATE_DIR = Path("./debates")


def get_state_dir() -> Path:
    """Get state directory from environment or use default."""
    env_value = os.environ.get(STATE_DIR_ENV_VAR, "")
    if env_value:
        return Path(env_value)
    return DEFAULT_STATE_DIR


def github_sync_debate(
    thread_id: str,
    repo: str,
    target_id: str,
    target_type: str = "discussion",
    state_dir: Path | None = None,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Sync debate turns to GitHub Discussion/Issue comments.

    Posts new turns as formatted comments with cognition headers.
    Idempotent: tracks synced turns to avoid duplicates.

    Args:
        thread_id: Thread identifier for the debate
        repo: GitHub repository in "owner/repo" format
        target_id: GitHub node ID (for discussions) or issue number (for issues)
        target_type: Target type - "discussion" or "issue"
        state_dir: Optional state directory override
        github_token: Optional GitHub token override (defaults to GITHUB_TOKEN env)

    Returns:
        Dictionary with sync summary:
        - thread_id: Thread identifier
        - synced_count: Number of turns synced in this call
        - comment_ids: List of all comment IDs (including previously synced)
        - target_type: The target type used
        - target_id: The target ID used

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If target_type is invalid or there's a binding conflict
        GitHubAPIError: If GitHub API call fails
        GitHubRateLimitError: If rate limit exceeded after retries
    """
    if state_dir is None:
        state_dir = get_state_dir()

    # Validate target_type
    valid_types = {t.value for t in GitHubTargetType}
    if target_type not in valid_types:
        raise ValueError(
            f"Invalid target_type '{target_type}': must be one of {sorted(valid_types)}"
        )

    # Load existing room state
    room = load_debate_state(thread_id, state_dir)

    # Check for binding conflict (including repo mismatch)
    if room.github_binding is not None:
        existing = room.github_binding
        # Check all binding fields: repo, target_id, and target_type
        if (
            existing.target_id != target_id
            or existing.target_type != target_type
            or existing.repo != repo
        ):
            raise ValueError(
                f"Debate '{thread_id}' is already bound to "
                f"{existing.repo}:{existing.target_type}:{existing.target_id}. "
                f"Cannot sync to {repo}:{target_type}:{target_id}"
            )

    # Determine which turns need syncing
    last_synced = 0
    existing_comment_ids: list[str] = []

    if room.github_binding is not None:
        last_synced = room.github_binding.last_synced_turn
        existing_comment_ids = list(room.github_binding.comment_ids)

    # Get turns to sync (0-indexed, last_synced is count of synced turns)
    turns_to_sync = room.turns[last_synced:]

    # If no new turns, return early
    if not turns_to_sync:
        return {
            "thread_id": thread_id,
            "synced_count": 0,
            "comment_ids": existing_comment_ids,
            "target_type": target_type,
            "target_id": target_id,
        }

    # Initialize GitHub client
    client = GitHubClient(token=github_token)

    # Create or update binding
    if room.github_binding is None:
        # Fetch discussion_number for discussions (enables deep-linking)
        discussion_number: int | None = None
        if target_type == "discussion":
            discussion_number = client.get_discussion_number(target_id)

        room.github_binding = GitHubBinding(
            repo=repo,
            target_id=target_id,
            target_type=target_type,
            last_synced_turn=0,
            comment_ids=[],
            discussion_number=discussion_number,
        )

    synced_count = 0

    try:
        for i, turn in enumerate(turns_to_sync):
            # Calculate turn number (1-indexed)
            turn_number = last_synced + i + 1

            # Format the turn as a comment
            body = format_turn_as_comment(turn, turn_number, room.max_turns)

            # Post to appropriate API
            if target_type == "discussion":
                result = client.post_discussion_comment(
                    discussion_id=target_id,
                    body=body,
                )
                comment_id = result.get("id", "")
            else:
                # Issue - target_id is the issue number
                result = client.post_issue_comment(
                    repo=repo,
                    issue_number=int(target_id),
                    body=body,
                )
                comment_id = result.get("node_id", "")

            # Validate comment_id is non-empty before advancing state
            if not comment_id:
                raise GitHubAPIError(f"GitHub API returned empty comment id for turn {turn_number}")

            # CRITICAL: Persist state after EACH successful post
            # This ensures idempotency - if a later turn fails, we don't
            # duplicate already-posted comments on retry
            room.github_binding.last_synced_turn = last_synced + i + 1
            room.github_binding.comment_ids.append(comment_id)
            save_debate_state(room, state_dir)

            synced_count += 1

    finally:
        client.close()

    return {
        "thread_id": thread_id,
        "synced_count": synced_count,
        "comment_ids": room.github_binding.comment_ids,
        "target_type": target_type,
        "target_id": target_id,
        "discussion_number": room.github_binding.discussion_number,
    }
