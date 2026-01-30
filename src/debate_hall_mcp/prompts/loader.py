"""Prompt loading with user customization support.

This module implements the Layered Discovery with Optional Naming pattern
decided in debate 2026-01-30-prompt-config-architecture.

Resolution order:
1. If prompt_file is absolute path -> load that file
2. If prompt_file is name (e.g., "security") -> resolve to ~/.debate-hall/prompts/{role}-{name}.oct.md
3. If prompt_file is null -> use embedded default (Ship ZERO principle)

Storage convention:
    ~/.debate-hall/prompts/
    ├── wind-default.oct.md      # User's default wind prompt
    ├── wind-security.oct.md     # Variant for security debates
    ├── wall-default.oct.md
    ├── door-legal.oct.md
    └── ...
"""

import os
from pathlib import Path

from debate_hall_mcp.prompts import DOOR_PROMPT, WALL_PROMPT, WIND_PROMPT

# Default prompts directory (XDG-like pattern)
PROMPTS_DIR = Path(os.environ.get("HOME", "~")).expanduser() / ".debate-hall" / "prompts"

# Embedded defaults map
EMBEDDED_PROMPTS: dict[str, str] = {
    "wind": WIND_PROMPT,
    "wall": WALL_PROMPT,
    "door": DOOR_PROMPT,
}

# Valid roles for validation
VALID_ROLES = frozenset({"wind", "wall", "door"})


class PromptLoadError(Exception):
    """Error raised when prompt loading fails."""

    pass


def _resolve_prompt_path(role: str, prompt_file: str) -> Path:
    """Resolve a prompt_file reference to an absolute path.

    Resolution logic:
    - If prompt_file is an absolute path -> return as-is
    - If prompt_file is a relative path starting with ./ or ../ -> resolve from cwd
    - Otherwise treat as variant name -> ~/.debate-hall/prompts/{role}-{name}.oct.md

    Args:
        role: The role (wind, wall, door) for named resolution
        prompt_file: Path or variant name

    Returns:
        Resolved absolute path
    """
    path = Path(prompt_file)

    # Absolute path
    if path.is_absolute():
        return path

    # Explicit relative path (./foo or ../foo)
    if prompt_file.startswith("./") or prompt_file.startswith("../"):
        return path.resolve()

    # Named variant -> resolve to prompts directory
    # Support both "security" and "wind-security" formats
    if "-" in prompt_file and prompt_file.startswith(f"{role}-"):
        # Already has role prefix: "wind-security"
        filename = f"{prompt_file}.oct.md"
    else:
        # Just variant name: "security" -> "wind-security.oct.md"
        filename = f"{role}-{prompt_file}.oct.md"

    return PROMPTS_DIR / filename


def get_prompt(role: str, prompt_file: str | None = None) -> str:
    """Get prompt for a debate role with optional custom file override.

    Implements the Layered Discovery pattern:
    1. If prompt_file is provided -> load from file
    2. If prompt_file is null/None -> use embedded default

    Args:
        role: The debate role (wind, wall, door)
        prompt_file: Optional path or variant name for custom prompt

    Returns:
        Prompt string (OCTAVE format)

    Raises:
        ValueError: If role is invalid
        PromptLoadError: If custom prompt file cannot be loaded
    """
    # Normalize role
    role_lower = role.lower()

    # Validate role
    if role_lower not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}")

    # If no custom file specified, return embedded default (Ship ZERO)
    if prompt_file is None:
        return EMBEDDED_PROMPTS[role_lower]

    # Resolve path
    path = _resolve_prompt_path(role_lower, prompt_file)

    # Load and return
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise PromptLoadError(f"Prompt file not found: {path}") from e
    except PermissionError as e:
        raise PromptLoadError(f"Permission denied reading prompt file: {path}") from e
    except OSError as e:
        raise PromptLoadError(f"Error reading prompt file {path}: {e}") from e


def list_available_prompts(prompts_dir: Path | None = None) -> dict[str, list[str]]:
    """List all available custom prompts organized by role.

    Scans the prompts directory for .oct.md files matching the
    naming convention {role}-{variant}.oct.md.

    Args:
        prompts_dir: Optional override for prompts directory (for testing)

    Returns:
        Dictionary mapping role to list of variant names:
        {
            "wind": ["default", "security", "creative"],
            "wall": ["default", "strict"],
            "door": ["default", "technical"]
        }

    Note:
        Returns empty dict if prompts directory doesn't exist.
        This is not an error - it means user hasn't created custom prompts.
    """
    directory = prompts_dir if prompts_dir is not None else PROMPTS_DIR

    # Return empty if directory doesn't exist (not an error)
    if not directory.exists():
        return {"wind": [], "wall": [], "door": []}

    result: dict[str, list[str]] = {"wind": [], "wall": [], "door": []}

    # Scan for .oct.md files
    for path in directory.glob("*.oct.md"):
        # path.stem for "wind-security.oct.md" gives "wind-security.oct"
        # We need to remove the ".oct" suffix to get "wind-security"
        filename = path.stem
        if filename.endswith(".oct"):
            filename = filename[:-4]  # Remove ".oct" suffix

        # Parse role and variant from filename
        for role in VALID_ROLES:
            if filename.startswith(f"{role}-"):
                variant = filename[len(f"{role}-") :]  # e.g., "security"
                if variant:  # Ensure there's actually a variant name
                    result[role].append(variant)
                break

    # Sort variants alphabetically for consistent output
    for role in result:
        result[role].sort()

    return result


def get_prompts_dir() -> Path:
    """Get the prompts directory path.

    Returns:
        Path to ~/.debate-hall/prompts/
    """
    return PROMPTS_DIR


def ensure_prompts_dir() -> Path:
    """Ensure the prompts directory exists, creating if necessary.

    Returns:
        Path to the created/existing prompts directory
    """
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROMPTS_DIR


__all__ = [
    "get_prompt",
    "list_available_prompts",
    "get_prompts_dir",
    "ensure_prompts_dir",
    "PromptLoadError",
    "PROMPTS_DIR",
    "VALID_ROLES",
]
