"""Centralized environment variable access for debate-hall-mcp.

Loads .env file from the project root (same directory as server.py) at import time.
This allows configuration via .env file without exposing secrets in MCP client configs.

Usage:
    from debate_hall_mcp.utils.env import get_env

    token = get_env("GITHUB_TOKEN")
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import dotenv_values, load_dotenv
except ImportError:  # pragma: no cover - optional in minimal installs
    dotenv_values = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]

# Project root is the directory containing server.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

# Also check parent directories (for worktree support)
_REPO_ROOT = _PROJECT_ROOT.parent.parent.parent  # src/debate_hall_mcp -> repo root
_REPO_ENV_PATH = _REPO_ROOT / ".env"

_DOTENV_VALUES: dict[str, str | None] = {}
_LOADED = False


def _find_env_file() -> Path | None:
    """Find .env file, checking multiple locations."""
    # Priority: package directory -> repo root -> worktree main repo
    for path in [_ENV_PATH, _REPO_ENV_PATH]:
        if path.exists():
            return path
    return None


def _read_dotenv_values(env_path: Path) -> dict[str, str | None]:
    """Read .env file values without modifying os.environ."""
    if dotenv_values is not None and env_path.exists():
        loaded = dotenv_values(env_path)
        return dict(loaded)
    return {}


def load_env(env_path: Path | None = None) -> bool:
    """Load .env file into os.environ.

    Args:
        env_path: Optional explicit path to .env file. If not provided,
                  searches standard locations.

    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    global _DOTENV_VALUES, _LOADED

    if env_path is None:
        env_path = _find_env_file()

    if env_path is None or not env_path.exists():
        return False

    if load_dotenv is not None:
        # Load into os.environ (override=False means don't overwrite existing)
        load_dotenv(dotenv_path=env_path, override=False)
        _DOTENV_VALUES = _read_dotenv_values(env_path)
        _LOADED = True
        return True

    return False


def reload_env(env_path: Path | None = None) -> bool:
    """Force reload of .env file, overwriting existing values.

    Args:
        env_path: Optional explicit path to .env file.

    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    global _DOTENV_VALUES, _LOADED

    if env_path is None:
        env_path = _find_env_file()

    if env_path is None or not env_path.exists():
        return False

    if load_dotenv is not None:
        # Load into os.environ with override=True
        load_dotenv(dotenv_path=env_path, override=True)
        _DOTENV_VALUES = _read_dotenv_values(env_path)
        _LOADED = True
        return True

    return False


def get_env(key: str, default: str | None = None) -> str | None:
    """Get environment variable value.

    Args:
        key: Environment variable name.
        default: Default value if not found.

    Returns:
        Value from environment or default.
    """
    return os.getenv(key, default)


def is_loaded() -> bool:
    """Check if .env file has been loaded."""
    return _LOADED


def get_env_file_path() -> Path | None:
    """Get the path to the .env file that was loaded, or would be loaded."""
    return _find_env_file()


# Auto-load on import
load_env()
