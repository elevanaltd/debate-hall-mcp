"""Prompt loading with user customization support.

This module implements the Layered Discovery with Optional Naming pattern
decided in debate 2026-01-30-prompt-config-architecture.

Resolution order for named variants (e.g., prompt_file: "security"):
1. Project-local: ./prompts/{role}-{name}.oct.md
2. User-global: ~/.debate-hall/prompts/{role}-{name}.oct.md
3. Embedded default (Ship ZERO principle)

Resolution order for explicit paths:
1. Absolute path (/path/to/prompt.oct.md) -> load directly
2. Relative path (./local.oct.md) -> resolve from cwd
3. Named variant -> layered discovery above

Storage conventions:
    ./prompts/                           # Project-local (for teams/repos)
    ├── wind-security.oct.md
    └── wall-strict.oct.md

    ~/.debate-hall/prompts/              # User-global (personal customization)
    ├── wind-default.oct.md
    └── door-technical.oct.md
"""

import os
from pathlib import Path

from debate_hall_mcp.prompts import DOOR_PROMPT, WALL_PROMPT, WIND_PROMPT

# Directory names for prompt resolution
PROJECT_PROMPTS_DIR = Path("./prompts")  # Project-local prompts
USER_PROMPTS_DIR = Path(os.environ.get("HOME", "~")).expanduser() / ".debate-hall" / "prompts"

# Directory names for agent resolution
PROJECT_AGENTS_DIR = Path("./agents")  # Local agent prompts
HESTAI_AGENTS_DIR = Path(".hestai-sys/library/agents")  # HestAI system agents

# Legacy alias for backward compatibility
PROMPTS_DIR = USER_PROMPTS_DIR

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


def _normalize_role_name(role_name: str) -> str:
    """Normalize a role name for file lookup.

    Converts spaces to hyphens and lowercases the name.
    - "critical engineer" -> "critical-engineer"
    - "Technical Architect" -> "technical-architect"

    Args:
        role_name: Raw role name from configuration

    Returns:
        Normalized role name suitable for filename lookup
    """
    return role_name.lower().replace(" ", "-")


def _is_hestai_integration_enabled() -> bool:
    """Check if HestAI integration is enabled via environment variable.

    Returns:
        True if HESTAI_INTEGRATION env var is set to 'true' (case-insensitive)
    """
    return os.environ.get("HESTAI_INTEGRATION", "").lower() == "true"


def get_agent_prompt(role_name: str) -> str | None:
    """Get agent prompt by role name with layered resolution.

    Resolution order:
    1. ./agents/{role_name}.oct.md (debate-hall primary)
    2. .hestai-sys/library/agents/{role_name}.oct.md (if HESTAI_INTEGRATION=true)
    3. Return None (signal to use fallback prompt_file/embedded logic)

    Role name normalization:
    - Spaces converted to hyphens
    - Lowercased
    - "critical engineer" -> "critical-engineer"

    Args:
        role_name: The role name (e.g., "ideator", "critical engineer")

    Returns:
        Agent prompt content if found, None otherwise
    """
    normalized_name = _normalize_role_name(role_name)
    filename = f"{normalized_name}.oct.md"

    # 1. Check project-local ./agents/ directory first
    local_path = PROJECT_AGENTS_DIR / filename
    if local_path.exists():
        try:
            return local_path.read_text(encoding="utf-8")
        except OSError:
            pass  # Fall through to next resolution layer

    # 2. Check HestAI system agents if integration is enabled
    if _is_hestai_integration_enabled():
        hestai_path = HESTAI_AGENTS_DIR / filename
        if hestai_path.exists():
            try:
                return hestai_path.read_text(encoding="utf-8")
            except OSError:
                pass  # Fall through to return None

    # 3. Not found anywhere - return None to signal fallback
    return None


def _build_variant_filename(role: str, prompt_file: str) -> str:
    """Build the filename for a named variant.

    Args:
        role: The role (wind, wall, door)
        prompt_file: Variant name (e.g., "security" or "wind-security")

    Returns:
        Filename like "wind-security.oct.md"
    """
    # Support both "security" and "wind-security" formats
    if "-" in prompt_file and prompt_file.startswith(f"{role}-"):
        # Already has role prefix: "wind-security"
        return f"{prompt_file}.oct.md"
    else:
        # Just variant name: "security" -> "wind-security.oct.md"
        return f"{role}-{prompt_file}.oct.md"


def _resolve_prompt_path(role: str, prompt_file: str) -> Path:
    """Resolve a prompt_file reference using layered discovery.

    Resolution logic:
    - If prompt_file is an absolute path -> return as-is
    - If prompt_file is a relative path starting with ./ or ../ -> resolve from cwd
    - Otherwise treat as variant name with layered discovery:
      1. ./prompts/{role}-{name}.oct.md (project-local)
      2. ~/.debate-hall/prompts/{role}-{name}.oct.md (user-global)

    Args:
        role: The role (wind, wall, door) for named resolution
        prompt_file: Path or variant name

    Returns:
        Resolved path (may not exist - caller handles FileNotFoundError)
    """
    path = Path(prompt_file)

    # Absolute path - return as-is (caller handles FileNotFoundError)
    if path.is_absolute():
        return path

    # Explicit relative path (./foo or ../foo) - resolve from cwd
    if prompt_file.startswith("./") or prompt_file.startswith("../"):
        return path.resolve()

    # Named variant -> layered discovery
    filename = _build_variant_filename(role, prompt_file)

    # 1. Check project-local first
    project_path = PROJECT_PROMPTS_DIR / filename
    if project_path.exists():
        return project_path.resolve()

    # 2. Check user-global
    user_path = USER_PROMPTS_DIR / filename
    if user_path.exists():
        return user_path

    # 3. Variant not found - return user path for error message clarity
    # (The error will say "not found at ~/.debate-hall/prompts/...")
    return user_path


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


def _scan_prompts_dir(directory: Path) -> dict[str, set[str]]:
    """Scan a single directory for prompt files.

    Args:
        directory: Directory to scan

    Returns:
        Dictionary mapping role to set of variant names found
    """
    result: dict[str, set[str]] = {"wind": set(), "wall": set(), "door": set()}

    if not directory.exists():
        return result

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
                    result[role].add(variant)
                break

    return result


def list_available_prompts(prompts_dir: Path | None = None) -> dict[str, list[str]]:
    """List all available custom prompts organized by role.

    Scans both project-local (./prompts/) and user-global (~/.debate-hall/prompts/)
    directories for .oct.md files matching the naming convention {role}-{variant}.oct.md.

    Args:
        prompts_dir: Optional override for prompts directory (for testing).
                     If provided, only scans this single directory.

    Returns:
        Dictionary mapping role to list of variant names:
        {
            "wind": ["default", "security", "creative"],
            "wall": ["default", "strict"],
            "door": ["default", "technical"]
        }

    Note:
        Returns empty lists if no prompts directories exist.
        This is not an error - it means no custom prompts are configured.
    """
    # If explicit directory provided (for testing), only scan that
    if prompts_dir is not None:
        variants = _scan_prompts_dir(prompts_dir)
        return {role: sorted(variants[role]) for role in VALID_ROLES}

    # Merge variants from both directories (project-local takes precedence in resolution,
    # but we list all available variants from both)
    result: dict[str, set[str]] = {"wind": set(), "wall": set(), "door": set()}

    # Scan project-local
    project_variants = _scan_prompts_dir(PROJECT_PROMPTS_DIR)
    for role in VALID_ROLES:
        result[role].update(project_variants[role])

    # Scan user-global
    user_variants = _scan_prompts_dir(USER_PROMPTS_DIR)
    for role in VALID_ROLES:
        result[role].update(user_variants[role])

    # Convert to sorted lists
    return {role: sorted(result[role]) for role in VALID_ROLES}


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
    "get_agent_prompt",
    "list_available_prompts",
    "get_prompts_dir",
    "ensure_prompts_dir",
    "PromptLoadError",
    "PROJECT_PROMPTS_DIR",
    "USER_PROMPTS_DIR",
    "PROJECT_AGENTS_DIR",
    "HESTAI_AGENTS_DIR",
    "PROMPTS_DIR",  # Legacy alias for USER_PROMPTS_DIR
    "VALID_ROLES",
]
