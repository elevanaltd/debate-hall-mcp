"""Startup utilities for debate-hall-mcp server.

This module provides dependency synchronization for development environments.
When running the MCP server from a git checkout (not pip-installed), this
ensures the venv stays in sync with uv.lock to prevent missing dependency errors.

The sync is:
- Only triggered in development mode (detected by uv.lock presence)
- Fast when already synced (~12ms overhead)
- Graceful on failure (logs warning, doesn't crash)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_dependencies(project_root: Path | None = None) -> bool:
    """Ensure dependencies are synced from uv.lock.

    This function checks if we're in a development environment (uv.lock exists)
    and runs `uv sync --frozen --quiet` to ensure dependencies match the lockfile.

    Args:
        project_root: Path to project root containing uv.lock.
                     If None, auto-detects from this file's location.

    Returns:
        True if sync was performed successfully.
        False if sync was skipped (production mode) or failed.

    Note:
        This function never raises exceptions - it's designed for startup
        where we want graceful degradation, not crashes.
    """
    # Auto-detect project root if not specified
    if project_root is None:
        # Navigate from src/debate_hall_mcp/startup.py to project root
        project_root = Path(__file__).resolve().parent.parent.parent

    # Check for development mode (uv.lock exists)
    uv_lock = project_root / "uv.lock"
    if not uv_lock.exists():
        # Production mode - dependencies managed by pip/package manager
        logger.debug("No uv.lock found, skipping dependency sync (production mode)")
        return False

    # Development mode - sync dependencies
    try:
        subprocess.run(
            ["uv", "sync", "--frozen", "--quiet"],
            cwd=project_root,
            check=True,
        )
        logger.debug("Dependency sync completed successfully")
        return True

    except FileNotFoundError:
        # uv command not available
        logger.warning(
            "uv command not found - cannot sync dependencies. "
            "Install uv or run 'pip install -e .' manually if you encounter import errors."
        )
        return False

    except subprocess.CalledProcessError as e:
        # uv sync failed
        logger.warning(
            f"uv sync failed with exit code {e.returncode}. " "Dependencies may be out of sync."
        )
        return False

    except OSError as e:
        # Other OS-level errors
        logger.warning(f"Failed to run uv sync: {e}")
        return False
