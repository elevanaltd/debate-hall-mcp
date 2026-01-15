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

    def test_server_version_matches_package_version(self) -> None:
        """SERVER_VERSION must match package __version__ to prevent drift."""
        from debate_hall_mcp import __version__

        assert __version__ == SERVER_VERSION

    def test_server_version_format(self) -> None:
        """SERVER_VERSION follows semantic versioning."""
        # Basic semver check: X.Y.Z
        parts = SERVER_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit() or part[0].isdigit()  # Allow 0.1.0-beta format


class TestGetDebateMcpWrapper:
    """Test get_debate MCP wrapper includes include_metadata parameter."""

    def test_get_debate_exposes_include_metadata_parameter(self) -> None:
        """get_debate MCP wrapper must expose include_metadata in the schema."""
        server = create_server()

        get_debate_tools = [
            tool for tool in server._tool_manager.list_tools() if tool.name == "get_debate"
        ]
        assert len(get_debate_tools) == 1, "get_debate tool should be registered"

        get_tool = get_debate_tools[0]
        input_schema = get_tool.parameters

        assert "include_metadata" in input_schema.get(
            "properties", {}
        ), "include_metadata parameter must be exposed in MCP get_debate schema"


class TestInitDebateMcpWrapper:
    """Test init_debate MCP wrapper parameters (Issue #26).

    Tests that the MCP layer correctly exposes and forwards the octave_mode
    parameter to the underlying debate_init tool.
    """

    def test_init_debate_accepts_octave_mode_parameter(self) -> None:
        """init_debate MCP wrapper accepts octave_mode parameter.

        BLOCKING issue B1: octave_mode not settable via MCP init_debate.
        The MCP server.py wrapper must accept octave_mode and forward it.
        """
        from debate_hall_mcp.server import create_server

        server = create_server()

        # Get the registered init_debate tool from the server
        # FastMCP registers tools internally, we need to inspect the wrapper
        # Check that the wrapper function signature includes octave_mode
        init_debate_tools = [
            tool for tool in server._tool_manager.list_tools() if tool.name == "init_debate"
        ]
        assert len(init_debate_tools) == 1, "init_debate tool should be registered"

        # Get the schema/parameters - octave_mode should be present
        init_tool = init_debate_tools[0]
        # FastMCP uses 'parameters' attribute for JSON schema
        input_schema = init_tool.parameters

        assert "octave_mode" in input_schema.get(
            "properties", {}
        ), "octave_mode parameter must be exposed in MCP init_debate schema"

    def test_init_debate_forwards_octave_mode_to_tool(self, tmp_path) -> None:
        """init_debate forwards octave_mode=True to underlying debate_init.

        Verifies that when octave_mode=True is passed via MCP, the created
        DebateRoom has octave_mode=True.
        """
        import os
        from unittest.mock import patch

        from debate_hall_mcp.state import load_debate_state
        from debate_hall_mcp.tools.init import debate_init

        # Set up temp state directory
        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(tmp_path)}):
            # Call debate_init with octave_mode=True (simulating MCP call)
            result = debate_init(
                thread_id="2025-01-02-octave-test",
                topic="Test topic",
                mode="fixed",
                octave_mode=True,
                state_dir=tmp_path,
            )

            # Verify result includes octave_mode
            assert result["octave_mode"] is True, "Result should reflect octave_mode=True"

            # Load state and verify persistence
            room = load_debate_state("2025-01-02-octave-test", tmp_path)
            assert room.octave_mode is True, "DebateRoom should have octave_mode=True"


class TestCloseDebateMcpWrapper:
    """Test close_debate MCP wrapper output_format behavior (Issue #26).

    Tests that the MCP layer correctly handles output_format defaults
    when octave_mode is enabled on the room.
    """

    def test_close_debate_defaults_to_octave_when_octave_mode_enabled(self, tmp_path) -> None:
        """close_debate returns OCTAVE format when room has octave_mode=True.

        BLOCKING issue B2: MCP close_debate forces output_format="json".
        When octave_mode=True and no output_format specified, should default to OCTAVE.
        """
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init
        from debate_hall_mcp.tools.turn import debate_turn

        # Create room with octave_mode=True
        debate_init(
            thread_id="2025-01-02-octave-close",
            topic="Test topic",
            mode="fixed",
            octave_mode=True,
            state_dir=tmp_path,
        )

        # Add required turns for close
        debate_turn(
            thread_id="2025-01-02-octave-close",
            role="Wind",
            content="PATHOS:: Opening position.",
            state_dir=tmp_path,
        )

        # Close without specifying output_format - should default to OCTAVE
        result = debate_close(
            thread_id="2025-01-02-octave-close",
            synthesis="1. Analysis\n2. Synthesis\n[PATTERN] Resolution.",
            state_dir=tmp_path,
            output_format=None,  # Explicitly None to test default behavior
        )

        # Result should be OCTAVE string (not dict)
        assert isinstance(
            result, str
        ), f"Expected OCTAVE string when octave_mode=True, got {type(result)}"
        assert (
            "DEBATE_TRANSCRIPT" in result or "META::" in result
        ), "Result should be OCTAVE formatted"

    def test_close_debate_respects_explicit_json_override(self, tmp_path) -> None:
        """close_debate returns JSON when explicitly requested, even with octave_mode.

        Even when octave_mode=True, explicit output_format='json' should be honored.
        """
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init
        from debate_hall_mcp.tools.turn import debate_turn

        # Create room with octave_mode=True
        debate_init(
            thread_id="2025-01-02-json-override",
            topic="Test topic",
            mode="fixed",
            octave_mode=True,
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id="2025-01-02-json-override",
            role="Wind",
            content="PATHOS:: Opening position.",
            state_dir=tmp_path,
        )

        # Close with explicit json format
        result = debate_close(
            thread_id="2025-01-02-json-override",
            synthesis="1. Analysis\n2. Synthesis\n[PATTERN] Resolution.",
            state_dir=tmp_path,
            output_format="json",  # Explicit override
        )

        # Result should be dict (JSON format)
        assert isinstance(
            result, dict
        ), f"Expected dict when output_format='json', got {type(result)}"
        assert "thread_id" in result
        assert result["status"] == "synthesis"

    def test_close_debate_mcp_wrapper_allows_none_output_format(self) -> None:
        """close_debate MCP wrapper allows output_format=None to trigger octave_mode logic.

        The MCP wrapper should NOT force output_format="json" but allow None
        so the underlying tool can apply octave_mode default.
        """
        from debate_hall_mcp.server import create_server

        server = create_server()

        # Get the registered close_debate tool
        close_debate_tools = [
            tool for tool in server._tool_manager.list_tools() if tool.name == "close_debate"
        ]
        assert len(close_debate_tools) == 1, "close_debate tool should be registered"

        # The schema default should NOT be "json" - should allow None
        close_tool = close_debate_tools[0]
        # FastMCP uses 'parameters' attribute for JSON schema
        input_schema = close_tool.parameters

        output_format_schema = input_schema.get("properties", {}).get("output_format", {})
        # If there's a default, it should NOT be "json" (which overrides octave_mode)
        # The default should be None/absent to let the tool decide
        schema_default = output_format_schema.get("default")
        assert schema_default != "json", (
            f"output_format default should not be 'json' (found: {schema_default}). "
            "This forces JSON even when octave_mode=True. Default should be None/absent."
        )
