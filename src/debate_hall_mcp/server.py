"""MCP server for debate-hall-mcp.

This module implements:
- FastMCP server initialization
- Tool registration for debate orchestration
- Server metadata and configuration
- Transport setup (stdio default)

B2 Phase Complete: All debate tools registered.

Environment Configuration:
    The server loads .env file from the project root at startup.
    This allows configuration without exposing secrets in MCP client configs.

    Supported variables:
    - GITHUB_TOKEN: GitHub personal access token for GitHub integration tools
    - GITHUB_TOOLS_ENABLED: Set to 'false' to disable GitHub tools (default: true)
    - DEBATE_HALL_STATE_DIR: Custom state directory (default: ./debates)
"""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# isort: off
# Load .env before other debate_hall imports that may need env vars
from debate_hall_mcp.utils import env as _env  # noqa: F401

# isort: on
from debate_hall_mcp.github import is_github_tools_enabled
from debate_hall_mcp.prompts import DOOR_PROMPT, WALL_PROMPT, WIND_PROMPT
from debate_hall_mcp.tools.admin import debate_force_close, debate_tombstone
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.github_sync import github_sync_debate as github_sync_debate_impl
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.interject import human_interject as human_interject_impl
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.ratify import ratify_rfc as ratify_rfc_impl
from debate_hall_mcp.tools.turn import debate_turn


class GitHubToolsDisabledError(Exception):
    """Raised when GitHub tools are disabled via GITHUB_TOOLS_ENABLED=false."""

    pass


# Server metadata
SERVER_NAME = "debate-hall-mcp"
SERVER_VERSION = "0.3.0"

# Default state directory
DEFAULT_STATE_DIR = Path("./debates")


def create_server() -> FastMCP:
    """Create debate-hall MCP server.

    Tools (10):
        init_debate, add_turn, get_debate, close_debate,
        pick_next_speaker, force_close_debate, tombstone_turn,
        github_sync_debate, ratify_rfc, human_interject
    """
    server = FastMCP(
        name=SERVER_NAME,
    )

    # Register debate prompts
    @server.prompt()
    def debate_agent(role: str) -> str:
        """Get the system prompt for a debate agent (Wind, Wall, Door)."""
        role_lower = role.lower()
        if role_lower == "wind":
            return WIND_PROMPT
        elif role_lower == "wall":
            return WALL_PROMPT
        elif role_lower == "door":
            return DOOR_PROMPT
        else:
            raise ValueError(f"Unknown role: {role}. Must be Wind, Wall, or Door.")

    # Register debate tools as MCP tools
    @server.tool()
    def init_debate(
        thread_id: str,
        topic: str,
        mode: str = "fixed",
        max_turns: int = 12,
        max_rounds: int = 4,
        strict_cognition: bool = False,
        octave_mode: bool = True,
    ) -> dict[str, Any]:
        """Create room. mode:fixed|mediated. strict_cognition->validate turns."""
        return debate_init(
            thread_id=thread_id,
            topic=topic,
            mode=mode,
            max_turns=max_turns,
            max_rounds=max_rounds,
            strict_cognition=strict_cognition,
            octave_mode=octave_mode,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def add_turn(
        thread_id: str,
        role: str,
        content: str,
        agent_role: str | None = None,
        model: str | None = None,
        cognition: str | None = None,
    ) -> dict[str, Any]:
        """Record turn. role:Wind|Wall|Door. cognition:PATHOS|ETHOS|LOGOS→validates content."""
        return debate_turn(
            thread_id=thread_id,
            role=role,
            content=content,
            state_dir=DEFAULT_STATE_DIR,
            agent_role=agent_role,
            model=model,
            cognition=cognition,
        )

    @server.tool()
    def get_debate(
        thread_id: str,
        include_transcript: bool = False,
        include_metadata: bool = False,
        context_lines: int | None = None,
    ) -> dict[str, Any]:
        """State+optional transcript. include_transcript→adds turn history. context_lines:limit depth."""
        return debate_get(
            thread_id=thread_id,
            include_transcript=include_transcript,
            include_metadata=include_metadata,
            context_lines=context_lines,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def close_debate(
        thread_id: str,
        synthesis: str,
        output_format: str | None = None,
    ) -> dict[str, Any] | str:
        """Finalize debate. synthesis:Door's final resolution->closes room.

        Args:
            output_format: 'json' (default), 'octave', or 'both'
        """
        return debate_close(
            thread_id=thread_id,
            synthesis=synthesis,
            state_dir=DEFAULT_STATE_DIR,
            output_format=output_format,  # type: ignore[arg-type]
        )

    @server.tool()
    def pick_next_speaker(thread_id: str, role: str) -> dict[str, Any]:
        """Mediated mode only. role:Wind|Wall|Door→sets next expected speaker."""
        return debate_pick(
            thread_id=thread_id,
            role=role,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def force_close_debate(thread_id: str, reason: str) -> dict[str, Any]:
        """I5:safety override. reason:logged→force closes any state."""
        return debate_force_close(
            thread_id=thread_id,
            reason=reason,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def tombstone_turn(thread_id: str, turn_index: int, reason: str) -> dict[str, Any]:
        """I4:redact content→hash chain preserved. turn_index:0-based."""
        return debate_tombstone(
            thread_id=thread_id,
            turn_index=turn_index,
            reason=reason,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def github_sync_debate(
        thread_id: str,
        repo: str,
        target_id: str,
        target_type: str = "discussion",
    ) -> dict[str, Any]:
        """Sync debate turns to GitHub Discussion/Issue comments.

        Posts new turns as formatted comments with cognition headers.
        Idempotent: tracks synced turns to avoid duplicates.

        Args:
            thread_id: The debate thread to sync
            repo: Repository in owner/repo format
            target_id: GitHub node ID (discussions) or issue number (issues)
            target_type: 'discussion' (GraphQL) or 'issue' (REST)

        Note: Can be disabled by setting GITHUB_TOOLS_ENABLED=false
        """
        if not is_github_tools_enabled():
            raise GitHubToolsDisabledError(
                "GitHub tools are disabled. Set GITHUB_TOOLS_ENABLED=true to enable."
            )
        return github_sync_debate_impl(
            thread_id=thread_id,
            repo=repo,
            target_id=target_id,
            target_type=target_type,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def ratify_rfc(
        thread_id: str,
        repo: str,
        adr_number: int,
        target_id: str | None = None,
        adr_path: str = "docs/adr/",
    ) -> dict[str, Any]:
        """Generate ADR from Door synthesis and create PR.

        Requires: Debate must be closed with synthesis.

        Args:
            thread_id: The debate thread to ratify
            repo: Repository in owner/repo format
            adr_number: Explicit ADR number (required to prevent collisions)
            target_id: Optional reference ID for linking (e.g., discussion node ID)
            adr_path: Path for ADR file in repo (default: docs/adr/)

        Returns:
            Dictionary with pr_url, pr_number, adr_path, branch_name

        Note: Can be disabled by setting GITHUB_TOOLS_ENABLED=false
        """
        if not is_github_tools_enabled():
            raise GitHubToolsDisabledError(
                "GitHub tools are disabled. Set GITHUB_TOOLS_ENABLED=true to enable."
            )
        return ratify_rfc_impl(
            thread_id=thread_id,
            repo=repo,
            adr_number=adr_number,
            target_id=target_id,
            adr_path=adr_path,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def human_interject(
        thread_id: str,
        repo: str,
        target_id: str,
        comment_id: str,
    ) -> dict[str, Any]:
        """Inject human GitHub comment into active debate as context.

        Fetches comment from GitHub and adds to debate context.
        Detects which role was replied to for injection typing.

        Args:
            thread_id: The debate thread to inject into
            repo: Repository in owner/repo format
            target_id: GitHub node ID (discussions) or issue number (issues)
            comment_id: Comment node ID (DC_...) or issue comment ID (numeric)

        Note: Can be disabled by setting GITHUB_TOOLS_ENABLED=false
        """
        if not is_github_tools_enabled():
            raise GitHubToolsDisabledError(
                "GitHub tools are disabled. Set GITHUB_TOOLS_ENABLED=true to enable."
            )
        return human_interject_impl(
            thread_id=thread_id,
            repo=repo,
            target_id=target_id,
            comment_id=comment_id,
            state_dir=DEFAULT_STATE_DIR,
        )

    return server


def main() -> None:
    """Entry point for running the MCP server.

    Runs server with stdio transport (default for MCP).
    """
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
