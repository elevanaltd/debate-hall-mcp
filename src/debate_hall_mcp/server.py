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
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.next import debate_next
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.status import debate_status
from debate_hall_mcp.tools.turn import debate_turn

# Server metadata
SERVER_NAME = "debate-hall-mcp"
SERVER_VERSION = "0.1.0"

# Default state directory
DEFAULT_STATE_DIR = Path("./debates")


def create_server() -> FastMCP:
    """Create and configure the debate-hall MCP server.

    Returns:
        Configured FastMCP instance with all tools registered

    Tools registered:
        - debate_init: Create new debate room
        - debate_turn: Record agent turn
        - debate_next: Get prompt for next speaker
        - debate_status: View debate state
        - debate_close: Finalize debate
        - debate_pick: Set next speaker (mediated mode)
        - debate_force_close: Admin kill switch (I5)
        - debate_tombstone: Redact turn (I4)
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
        """Create debate room. Returns: thread_id, topic, mode, status, limits."""
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
        """Record agent turn. role: Wind|Wall|Door. cognition: PATHOS|ETHOS|LOGOS. Returns: turn_count, status."""
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
    def get_next_prompt(thread_id: str, context_lines: int | None = None) -> dict[str, Any]:
        """Get next speaker prompt with transcript. context_lines limits history."""
        return debate_next(
            thread_id=thread_id,
            context_lines=context_lines,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def get_status(thread_id: str) -> dict[str, Any]:
        """View debate state. Returns: topic, mode, status, turn_count, limits."""
        return debate_status(
            thread_id=thread_id,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def close_debate(thread_id: str, synthesis: str) -> dict[str, Any]:
        """Close debate with Door synthesis. Returns: thread_id, status, synthesis."""
        return debate_close(
            thread_id=thread_id,
            synthesis=synthesis,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def pick_next_speaker(thread_id: str, role: str) -> dict[str, Any]:
        """Set next speaker in mediated mode. role: Wind|Wall|Door."""
        return debate_pick(
            thread_id=thread_id,
            role=role,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def force_close_debate(thread_id: str, reason: str) -> dict[str, Any]:
        """Admin kill switch. Force close regardless of state."""
        return debate_force_close(
            thread_id=thread_id,
            reason=reason,
            state_dir=DEFAULT_STATE_DIR,
        )

    @server.tool()
    def tombstone_turn(thread_id: str, turn_index: int, reason: str) -> dict[str, Any]:
        """Redact turn content, preserve hash chain. turn_index is 0-based."""
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
