"""MCP server for debate-hall-mcp.

This module implements:
- FastMCP server initialization
- Tool registration for debate orchestration
- Server metadata and configuration
- Transport setup (stdio default)

B2 Phase Complete: All debate tools registered.
"""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from debate_hall_mcp.tools.admin import debate_force_close, debate_tombstone
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn

# Server metadata
SERVER_NAME = "debate-hall-mcp"
SERVER_VERSION = "0.1.0"

# Default state directory
DEFAULT_STATE_DIR = Path("./debates")


def create_server() -> FastMCP:
    """Create debate-hall MCP server.

    Tools (7):
        init_debate, add_turn, get_debate, close_debate,
        pick_next_speaker, force_close_debate, tombstone_turn
    """
    server = FastMCP(
        name=SERVER_NAME,
    )

    # Register debate tools as MCP tools
    @server.tool()
    def init_debate(
        thread_id: str,
        topic: str,
        mode: str = "fixed",
        max_turns: int = 12,
        max_rounds: int = 4,
        strict_cognition: bool = False,
    ) -> dict[str, Any]:
        """Create room. mode:fixed|mediated. strict_cognition→validate turns."""
        return debate_init(
            thread_id=thread_id,
            topic=topic,
            mode=mode,
            max_turns=max_turns,
            max_rounds=max_rounds,
            strict_cognition=strict_cognition,
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
        context_lines: int | None = None,
    ) -> dict[str, Any]:
        """State+optional transcript. include_transcript→adds turn history. context_lines:limit depth."""
        return debate_get(
            thread_id=thread_id,
            include_transcript=include_transcript,
            context_lines=context_lines,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def close_debate(thread_id: str, synthesis: str) -> dict[str, Any]:
        """Finalize debate. synthesis:Door's final resolution→closes room."""
        return debate_close(
            thread_id=thread_id,
            synthesis=synthesis,
            state_dir=DEFAULT_STATE_DIR,
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

    return server


def main() -> None:
    """Entry point for running the MCP server.

    Runs server with stdio transport (default for MCP).
    """
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
