"""human_interject tool - Inject human GitHub comments into debates (Issue #17).

Fetches human comments from GitHub Discussions/Issues and injects them
as context for active debates. Supports parent detection for role-aware
injection typing.

Immutables Compliance:
- I3 (HUMAN_PRIMACY): Enables human-in-the-loop participation
- I4 (VERIFIABLE_EVENT_LEDGER): Comment IDs stored for idempotency

Security:
- Validates target_id matches debate's github_binding.target_id
- Validates fetched comment belongs to expected discussion/issue
- Uses atomic locking for read-modify-write operations
"""

import contextlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from debate_hall_mcp.github import GitHubClient
from debate_hall_mcp.state import (
    DebateRoom,
    DebateStatus,
    InjectedContext,
)

# Environment variable for state directory
STATE_DIR_ENV_VAR = "DEBATE_HALL_STATE_DIR"
DEFAULT_STATE_DIR = Path("./debates")

# Role to injection type mapping
ROLE_TO_INJECTION_TYPE = {
    "Wind": "pathos",
    "Wall": "ethos",
    "Door": "logos",
}


def get_state_dir() -> Path:
    """Get state directory from environment or use default."""
    env_value = os.environ.get(STATE_DIR_ENV_VAR, "")
    if env_value:
        return Path(env_value)
    return DEFAULT_STATE_DIR


# Security: Patterns that indicate path traversal or directory injection
PATH_UNSAFE_PATTERNS = ["..", "/", "\\"]


def _validate_thread_id_for_filesystem(thread_id: str) -> None:
    """Validate thread_id is safe for filesystem operations.

    Security: Rejects path traversal sequences and directory separators.

    Raises:
        ValueError: If thread_id contains path-unsafe characters
    """
    for pattern in PATH_UNSAFE_PATTERNS:
        if pattern in thread_id:
            raise ValueError(f"Invalid thread_id '{thread_id}': contains path-unsafe characters")


def _get_interject_lock(lock_file: Path) -> FileLock:
    """Get a file lock for atomic interject operations.

    This lock ensures the entire read-modify-write cycle is atomic,
    preventing concurrent interjections from dropping updates or
    bypassing idempotency checks.

    Args:
        lock_file: Path to the lock file

    Returns:
        FileLock instance for use as context manager
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_file))


def _validate_comment_id_format(comment_id: str) -> None:
    """Validate comment_id format before processing.

    Args:
        comment_id: The comment ID to validate

    Raises:
        ValueError: If comment_id is empty or has invalid format
    """
    if not comment_id:
        raise ValueError("Invalid comment_id format: comment_id cannot be empty")

    # Valid formats: DC_* (Discussion comment) or numeric (Issue comment)
    if comment_id.startswith("DC_"):
        return  # Valid discussion comment format

    # Must be numeric for issue comments
    if not comment_id.isdigit():
        raise ValueError(
            f"Invalid comment_id format: '{comment_id}' must be either "
            f"'DC_*' (Discussion comment) or numeric (Issue comment)"
        )


def _is_discussion_comment(comment_id: str) -> bool:
    """Determine if comment_id is for a Discussion (DC_ prefix) or Issue (numeric)."""
    return comment_id.startswith("DC_")


def _detect_injection_type(
    reply_to_id: str | None,
    comment_ids: list[str],
    turns: list[Any],
) -> tuple[str, int | None]:
    """Detect injection type based on which turn was replied to.

    Args:
        reply_to_id: Node ID of parent comment (None if top-level)
        comment_ids: List of synced comment IDs matching turn indices
        turns: List of Turn objects

    Returns:
        Tuple of (injection_type, replied_to_turn_index)
    """
    if reply_to_id is None:
        return "general", None

    # Find which turn this is a reply to
    try:
        turn_index = comment_ids.index(reply_to_id)
        if turn_index < len(turns):
            role = turns[turn_index].role
            injection_type = ROLE_TO_INJECTION_TYPE.get(role, "general")
            return injection_type, turn_index
    except ValueError:
        pass  # reply_to_id not in our tracked comments

    return "general", None


def _load_room_state_unlocked(thread_id: str, state_dir: Path) -> DebateRoom:
    """Load room state without locking (caller must hold lock).

    For use within atomic operations where caller holds the lock.
    """
    state_file = state_dir / f"{thread_id}.json"
    if not state_file.exists():
        raise FileNotFoundError(f"No state file found for thread {thread_id}")

    with open(state_file) as f:
        data = json.load(f)

    return DebateRoom.model_validate(data)


def _save_room_state_unlocked(room: DebateRoom, state_dir: Path) -> None:
    """Save room state without locking (caller must hold lock).

    Uses atomic write pattern for crash safety.
    """
    state_file = state_dir / f"{room.thread_id}.json"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Atomic write: temp file -> fsync -> rename
    fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(room.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(state_file))
    except Exception:
        # Clean up temp file on failure
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _validate_target_id(target_id: str, room: DebateRoom) -> None:
    """Validate target_id matches debate's github_binding.

    Security: Prevents injection of comments from arbitrary discussions/issues.

    Raises:
        ValueError: If target_id doesn't match binding or no binding exists
    """
    if room.github_binding is None:
        # No binding - target_id validation not possible
        # This is acceptable for debates without GitHub sync
        return

    if room.github_binding.target_id != target_id:
        raise ValueError(
            f"target_id mismatch: provided '{target_id}' does not match "
            f"debate binding '{room.github_binding.target_id}'"
        )


def _validate_repo(repo: str, room: DebateRoom) -> None:
    """Validate repo matches debate's github_binding.repo.

    Security: Prevents injection of comments from different repos with same issue number.
    This validation MUST happen BEFORE any GitHub API calls.

    Raises:
        ValueError: If repo doesn't match binding or no binding exists
    """
    if room.github_binding is None:
        # No binding - repo validation not possible
        # This is acceptable for debates without GitHub sync
        return

    if room.github_binding.repo != repo:
        raise ValueError(
            f"repo mismatch: provided '{repo}' does not match "
            f"debate binding '{room.github_binding.repo}'"
        )


def _validate_discussion_comment_source(
    comment_data: dict[str, Any], expected_target_id: str
) -> None:
    """Validate Discussion comment belongs to expected discussion.

    Security: Prevents injection of comments from different discussions.

    Raises:
        ValueError: If comment is from a different discussion or missing discussion_id
    """
    # Get discussion_id from comment data - now returned by get_discussion_comment()
    actual_discussion_id = comment_data.get("discussion_id")

    if actual_discussion_id is None:
        # SECURITY: Cannot validate source without discussion_id - fail safe
        raise ValueError("Cannot validate comment source: discussion_id missing from response")

    if actual_discussion_id != expected_target_id:
        raise ValueError(
            f"target_id mismatch: comment belongs to different discussion "
            f"'{actual_discussion_id}', expected '{expected_target_id}'"
        )


def _validate_issue_comment_source(
    comment_data: dict[str, Any], expected_issue_number: str
) -> None:
    """Validate Issue comment belongs to expected issue.

    Security: Prevents injection of comments from different issues.

    Raises:
        ValueError: If comment is from a different issue or missing issue_url
    """
    issue_url = comment_data.get("issue_url")
    if issue_url is None:
        # SECURITY: Cannot validate source without issue_url - fail safe
        raise ValueError("Cannot validate comment source: issue_url missing from response")

    # Extract issue number from URL like:
    # https://api.github.com/repos/owner/repo/issues/42
    match = re.search(r"/issues/(\d+)$", issue_url)
    if not match:
        raise ValueError(
            f"Cannot validate comment source: unable to parse issue number from '{issue_url}'"
        )

    actual_issue_number = match.group(1)
    if actual_issue_number != expected_issue_number:
        raise ValueError(
            f"target_id mismatch: comment belongs to different issue "
            f"#{actual_issue_number}, expected #{expected_issue_number}"
        )


def human_interject(
    thread_id: str,
    repo: str,
    target_id: str,
    comment_id: str,
    state_dir: Path | None = None,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Inject human GitHub comment into active debate as context.

    Fetches the specified comment from GitHub and adds it to the debate's
    injected_context list. Detects which role was replied to and assigns
    appropriate injection type.

    Security:
    - Validates comment_id format before processing
    - Validates repo matches debate's github_binding.repo (BEFORE API calls)
    - Validates target_id matches debate's github_binding.target_id
    - Validates fetched comment belongs to expected discussion/issue
    - Uses atomic locking with canonical {thread_id}.lock file

    Args:
        thread_id: Thread identifier for the debate
        repo: GitHub repository in "owner/repo" format
        target_id: GitHub node ID (for discussions) or issue number (for issues)
        comment_id: GitHub comment node ID (DC_...) or issue comment ID (numeric)
        state_dir: Optional state directory override
        github_token: Optional GitHub token override (defaults to GITHUB_TOKEN env)

    Returns:
        Dictionary with injection result:
        - thread_id: Thread identifier
        - status: "injected" or "already_processed"
        - comment_id: The comment ID processed
        - injection_type: Type assigned (pathos, ethos, logos, general)
        - author: Comment author (if available)

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate is not active, target_id mismatch, or invalid format
    """
    if state_dir is None:
        state_dir = get_state_dir()

    # Security: Validate inputs BEFORE any file/network operations
    _validate_thread_id_for_filesystem(thread_id)
    _validate_comment_id_format(comment_id)

    state_dir.mkdir(parents=True, exist_ok=True)
    # Use canonical lock file (same as save_debate_state uses) to prevent races
    lock_file = state_dir / f"{thread_id}.lock"

    # Atomic operation: acquire lock for entire read-modify-write cycle
    with _get_interject_lock(lock_file):
        # Load room state (under lock)
        room = _load_room_state_unlocked(thread_id, state_dir)

        # Security: Validate repo and target_id match binding BEFORE any API calls
        _validate_repo(repo, room)
        _validate_target_id(target_id, room)

        # Reject if debate is not active
        if room.status != DebateStatus.ACTIVE:
            raise ValueError(
                f"Cannot inject into debate '{thread_id}': debate is not active "
                f"(status: {room.status.value})"
            )

        # Idempotency check (under lock - prevents race condition)
        processed_ids = {ctx.comment_id for ctx in room.injected_context}
        if comment_id in processed_ids:
            return {
                "thread_id": thread_id,
                "status": "already_processed",
                "comment_id": comment_id,
                "injection_type": None,
                "author": None,
            }

        # Initialize GitHub client and fetch comment
        client = GitHubClient(token=github_token)
        try:
            if _is_discussion_comment(comment_id):
                comment_data = client.get_discussion_comment(comment_id)
                reply_to_id = comment_data.get("reply_to_id")

                # Security: Validate comment source
                _validate_discussion_comment_source(comment_data, target_id)
            else:
                comment_data = client.get_issue_comment(repo, int(comment_id))
                reply_to_id = None  # Issue comments don't have nested replies

                # Security: Validate comment source
                _validate_issue_comment_source(comment_data, target_id)
        finally:
            client.close()

        body = comment_data.get("body", "")
        author = comment_data.get("author")

        # Detect injection type based on parent comment
        comment_ids = []
        if room.github_binding:
            comment_ids = room.github_binding.comment_ids

        injection_type, replied_to_turn = _detect_injection_type(
            reply_to_id, comment_ids, room.turns
        )

        # Create and add InjectedContext
        injected = InjectedContext(
            source="github_comment",
            comment_id=comment_id,
            content=body,
            injection_type=injection_type,
            processed_at=datetime.now(UTC),
            author=author,
            replied_to_turn=replied_to_turn,
        )
        room.injected_context.append(injected)

        # Save room state (under lock)
        _save_room_state_unlocked(room, state_dir)

    return {
        "thread_id": thread_id,
        "status": "injected",
        "comment_id": comment_id,
        "injection_type": injection_type,
        "author": author,
    }
