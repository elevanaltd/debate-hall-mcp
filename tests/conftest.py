"""Pytest configuration and fixtures for debate-hall-mcp tests."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_state_dir_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent local developer env vars from affecting test persistence paths.

    Some E2E tests assume persistence under ./debates and clean that directory.
    If a developer has DEBATE_HALL_STATE_DIR set globally, tests can become flaky
    due to state leakage outside the repo.
    """
    monkeypatch.delenv("DEBATE_HALL_STATE_DIR", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"
