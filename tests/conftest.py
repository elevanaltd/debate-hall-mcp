"""Pytest configuration and fixtures for debate-hall-mcp tests."""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"
