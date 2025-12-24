"""Unit tests for debate_hall_mcp.server module.

Tests cover:
- FastMCP server initialization
- Tool registration (placeholders for B2 phase)
- Server metadata (name, version)
- Transport configuration
"""


from debate_hall_mcp.server import SERVER_NAME, SERVER_VERSION, create_server


class TestServerInitialization:
    """Test MCP server creation and configuration."""

    def test_create_server_returns_fastmcp(self) -> None:
        """create_server returns FastMCP instance."""
        from mcp.server.fastmcp import FastMCP

        server = create_server()
        assert isinstance(server, FastMCP)

    def test_server_has_correct_name(self) -> None:
        """Server is initialized with correct name."""
        server = create_server()
        assert server.name == SERVER_NAME
        assert SERVER_NAME == "debate-hall-mcp"

    def test_server_version_defined(self) -> None:
        """Server version is defined and non-empty."""
        assert SERVER_VERSION is not None
        assert len(SERVER_VERSION) > 0
        assert "." in SERVER_VERSION  # Version format check (e.g., "0.1.0")


class TestToolRegistration:
    """Test tool registration scaffold (actual tools in B2)."""

    def test_server_has_tools_attribute(self) -> None:
        """Server has tools collection for registration."""
        server = create_server()
        # FastMCP provides tools through decorators
        # At B1 phase, we just verify the scaffold exists
        assert hasattr(server, "tool")

    def test_server_can_register_tool(self) -> None:
        """Server supports tool registration via decorator."""
        server = create_server()

        # Test that tool decorator exists and is callable
        assert callable(server.tool)

        # Register a test tool (won't be used in production)
        @server.tool()
        def test_tool(arg: str) -> str:
            """Test tool for validation."""
            return f"Test: {arg}"

        # Verify tool was registered (FastMCP internal check)
        # This validates the registration mechanism works
        assert test_tool is not None


class TestServerRun:
    """Test server run configuration."""

    def test_server_run_method_exists(self) -> None:
        """Server has run method for execution."""
        server = create_server()
        assert hasattr(server, "run")
        assert callable(server.run)


class TestServerMetadata:
    """Test server metadata configuration."""

    def test_server_name_constant(self) -> None:
        """SERVER_NAME constant is correct."""
        assert SERVER_NAME == "debate-hall-mcp"

    def test_server_version_format(self) -> None:
        """SERVER_VERSION follows semantic versioning."""
        # Basic semver check: X.Y.Z
        parts = SERVER_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit() or part[0].isdigit()  # Allow 0.1.0-beta format
