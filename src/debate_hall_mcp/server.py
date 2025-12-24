"""MCP server for debate-hall-mcp.

This module implements:
- FastMCP server initialization
- Tool registration scaffold (tools implemented in B2)
- Server metadata and configuration
- Transport setup (stdio default)

B1 Phase: Foundation scaffold only
B2 Phase: Will add actual debate tools (debate_init, debate_turn, etc.)
"""

from mcp.server.fastmcp import FastMCP

# Server metadata
SERVER_NAME = "debate-hall-mcp"
SERVER_VERSION = "0.1.0"


def create_server() -> FastMCP:
    """Create and configure the debate-hall MCP server.

    Returns:
        Configured FastMCP instance ready for tool registration

    Note:
        B1 phase provides scaffold only.
        B2 phase will register actual debate tools.
    """
    server = FastMCP(
        name=SERVER_NAME,
    )

    # B2: Tool registration will happen here
    # Examples:
    # - debate_init: Create new debate room
    # - debate_turn: Record agent turn
    # - debate_next: Get prompt for next speaker
    # - debate_status: View debate state
    # - debate_close: Finalize debate
    # - debate_pick: Set next speaker (mediated mode)
    # - debate_force_close: Admin kill switch (I5)
    # - debate_tombstone: Redact turn (I4)

    return server


def main() -> None:
    """Entry point for running the MCP server.

    Runs server with stdio transport (default for MCP).
    """
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
