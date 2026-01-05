"""Tests for debate_hall_mcp package initialization."""


def test_package_version() -> None:
    """Test that package version is defined."""
    from debate_hall_mcp import __version__

    assert __version__ == "0.3.0"


def test_package_author() -> None:
    """Test that package author is defined."""
    from debate_hall_mcp import __author__

    assert __author__ == "HestAI"
