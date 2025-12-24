"""Tests for debate_hall_mcp.tools package initialization."""


def test_tools_package_importable() -> None:
    """Test that tools package is importable."""
    from debate_hall_mcp import tools

    assert tools is not None
