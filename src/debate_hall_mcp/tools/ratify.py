"""ratify_rfc tool - Generate ADR from Door synthesis and create PR (Issue #16).

Generates an Architecture Decision Record (ADR) from a closed debate's
Door synthesis, then creates a GitHub PR with the ADR file.

Immutables Compliance:
- I4 (VERIFIABLE_EVENT_LEDGER): ADR creation tracked via PR
- I5 (QUALITY_VERIFICATION): Requires closed debate with synthesis
"""

import os
import re
from pathlib import Path
from typing import Any

from debate_hall_mcp.github import GitHubAPIError, GitHubClient
from debate_hall_mcp.state import (
    DebateRoom,
    DebateStatus,
    load_debate_state,
)


class BranchConflictError(Exception):
    """Raised when branch already exists during ratify_rfc (422 from GitHub)."""

    pass


class PathTraversalError(Exception):
    """Raised when adr_path contains path traversal sequences."""

    pass


def validate_adr_path(adr_path: str) -> None:
    """Validate adr_path for path traversal attacks.

    Args:
        adr_path: The path to validate

    Raises:
        PathTraversalError: If path contains traversal sequences or is absolute
    """
    # Check for absolute paths (Unix and Windows)
    if adr_path.startswith("/") or (len(adr_path) > 1 and adr_path[1] == ":"):
        raise PathTraversalError(
            f"Invalid adr_path: absolute paths not allowed (got '{adr_path}'). "
            "Use a relative path like 'docs/adr/'."
        )

    # Check for path traversal sequences
    if ".." in adr_path:
        raise PathTraversalError(
            f"Invalid adr_path: path traversal sequences (..) not allowed (got '{adr_path}'). "
            "Use a safe relative path like 'docs/adr/'."
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


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to slugify
        max_length: Maximum length of the slug

    Returns:
        Lowercase, hyphenated slug
    """
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def generate_adr_content(room: DebateRoom, adr_number: int) -> str:
    """Generate ADR markdown content from debate room.

    Args:
        room: The closed debate room with synthesis
        adr_number: The ADR number to use

    Returns:
        Formatted ADR markdown content
    """
    # Format ADR number with leading zeros
    adr_num_str = f"{adr_number:03d}"

    # Extract topic from debate
    topic = room.topic

    # Extract Wind (PATHOS/opportunities) content
    wind_content: list[str] = []
    for turn in room.turns:
        if turn.role == "Wind":
            wind_content.append(turn.content)

    # Extract Wall (ETHOS/constraints) content
    wall_content: list[str] = []
    for turn in room.turns:
        if turn.role == "Wall":
            wall_content.append(turn.content)

    # Format opportunities section
    opportunities_section = ""
    if wind_content:
        opportunities_section = "\n\n".join(wind_content)
    else:
        opportunities_section = "No opportunities identified during debate."

    # Format constraints section
    constraints_section = ""
    if wall_content:
        constraints_section = "\n\n".join(wall_content)
    else:
        constraints_section = "No constraints identified during debate."

    # Build references section
    references_lines = [f"- Debate transcript: `{room.thread_id}`"]
    if room.github_binding:
        repo = room.github_binding.repo
        target_id = room.github_binding.target_id
        target_type = room.github_binding.target_type

        if target_type == "discussion":
            # For discussions, use discussion_number for deep linking if available
            discussion_number = room.github_binding.discussion_number
            if discussion_number is not None:
                references_lines.append(
                    f"- GitHub Discussion: https://github.com/{repo}/discussions/{discussion_number}"
                )
            else:
                # Fallback to node ID if discussion_number not available
                references_lines.append(
                    f"- GitHub Discussion: https://github.com/{repo}/discussions (ID: {target_id})"
                )
        else:
            # For issues
            references_lines.append(f"- GitHub Issue: https://github.com/{repo}/issues/{target_id}")

    references_section = "\n".join(references_lines)

    # Build the ADR
    adr = f"""# ADR-{adr_num_str}: {topic}

## Status

Accepted

## Context

This decision was reached through structured debate using the Wind-Wall-Door dialectic
methodology. The debate topic was: "{topic}"

## Decision

{room.synthesis}

## Consequences

### Opportunities (from Wind/PATHOS)

{opportunities_section}

### Constraints (from Wall/ETHOS)

{constraints_section}

## References

{references_section}

---
*Generated by [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp)*
"""

    return adr


def ratify_rfc(
    thread_id: str,
    repo: str,
    adr_number: int,
    target_id: str | None = None,  # noqa: ARG001 - Reserved for future reference linking
    adr_path: str = "docs/adr/",
    state_dir: Path | None = None,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Generate ADR from Door synthesis and create PR on GitHub.

    Args:
        thread_id: Thread identifier for the debate
        repo: GitHub repository in "owner/repo" format
        adr_number: Explicit ADR number (required to prevent collisions)
        target_id: Optional reference ID for linking (reserved for future use)
        adr_path: Path for ADR files in repo (default: "docs/adr/")
        state_dir: Optional state directory override
        github_token: Optional GitHub token override (defaults to GITHUB_TOKEN env)

    Returns:
        Dictionary with:
        - thread_id: Debate thread ID
        - adr_number: The ADR number used
        - adr_path: Path to the ADR file in the PR
        - branch_name: The created branch name
        - pr_number: The created PR number
        - pr_url: URL to the created PR

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate not closed or no synthesis
        PathTraversalError: If adr_path contains path traversal sequences
        BranchConflictError: If branch already exists (422 from GitHub)
        GitHubAPIError: If GitHub API call fails
    """
    # Validate adr_path for security (path traversal prevention)
    validate_adr_path(adr_path)

    if state_dir is None:
        state_dir = get_state_dir()

    # Load debate room
    room = load_debate_state(thread_id, state_dir)

    # Validate debate is closed
    if room.status == DebateStatus.ACTIVE:
        raise ValueError(
            f"Debate '{thread_id}' is not closed (status: ACTIVE). "
            f"Close the debate with close_debate before ratifying."
        )

    # Validate synthesis exists
    if not room.synthesis:
        raise ValueError(
            f"Debate '{thread_id}' has no Door synthesis. "
            f"A synthesis is required to generate an ADR."
        )

    # adr_number is now a required parameter - no fallback logic needed

    # Generate ADR content
    adr_content = generate_adr_content(room, adr_number)

    # Format ADR number with leading zeros for filenames
    adr_num_str = f"{adr_number:03d}"

    # Generate branch name and file path
    topic_slug = slugify(room.topic)
    branch_name = f"adr/{adr_num_str}-{topic_slug}"
    adr_filename = f"ADR-{adr_num_str}-{topic_slug}.md"
    full_adr_path = f"{adr_path.rstrip('/')}/{adr_filename}"

    # Initialize GitHub client
    client = GitHubClient(token=github_token)

    try:
        # Get default branch and its SHA
        default_branch = client.get_default_branch(repo=repo)
        base_ref = client.get_ref(repo=repo, ref=f"heads/{default_branch}")
        base_sha = base_ref["sha"]

        # Create the ADR branch with user-friendly error handling for conflicts
        try:
            client.create_ref(
                repo=repo,
                ref=f"refs/heads/{branch_name}",
                sha=base_sha,
            )
        except GitHubAPIError as e:
            # Check for 422 "Reference already exists" error
            error_msg = str(e).lower()
            if "reference already exists" in error_msg or "422" in error_msg:
                raise BranchConflictError(
                    f"Branch '{branch_name}' already exists. "
                    f"Please delete the branch or use a different ADR number."
                ) from e
            # Re-raise other GitHub errors
            raise

        # Commit the ADR file
        commit_message = f"Add ADR-{adr_num_str}: {room.topic}"
        client.create_file(
            repo=repo,
            path=full_adr_path,
            content=adr_content,
            message=commit_message,
            branch=branch_name,
        )

        # Create the PR
        pr_title = f"ADR-{adr_num_str}: {room.topic}"
        pr_body = f"""## Summary

This PR adds ADR-{adr_num_str}, generated from debate-hall-mcp debate `{thread_id}`.

## ADR Details

- **Topic**: {room.topic}
- **Status**: Accepted
- **Debate Thread**: `{thread_id}`

## Decision (Door Synthesis)

{room.synthesis}

---
*Generated by [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp)*
"""

        pr_result = client.create_pull_request(
            repo=repo,
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch,
        )

        return {
            "thread_id": thread_id,
            "adr_number": adr_number,
            "adr_path": full_adr_path,
            "branch_name": branch_name,
            "pr_number": pr_result["number"],
            "pr_url": pr_result["html_url"],
        }

    finally:
        client.close()
