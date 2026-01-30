"""Tier configuration for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements:
- RoleConfig for Wind/Wall/Door provider configuration
- TierSettings for tier-specific debate settings
- TierConfig combining role configs with settings
- load_tier_config for configuration loading

Resolution order for tier configuration:
1. DEBATE_HALL_TIERS_FILE environment variable
2. ./tiers.yaml (project-local, for team/repo configs)
3. ~/.debate-hall/tiers.yaml (user-global)

No hardcoded defaults - configuration must exist in a tiers.yaml file.
"""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    """Configuration for a debate role (Wind, Wall, or Door).

    Supports two provider types:
    - cli: Use external AI CLI (claude, codex, gemini)
    - openrouter: Use OpenRouter API with specified model

    Fields:
    - provider: 'cli' or 'openrouter'
    - cli: For CLI provider, which CLI to use (claude, codex, gemini)
    - model: Model identifier (required for openrouter, optional for cli)
    - role: Optional system prompt role name override
    - prompt_file: Optional custom prompt file path or variant name
    - timeout: Provider-specific timeout in seconds (overrides tier default)
    - cli_args: Additional CLI arguments as key-value pairs

    Prompt Resolution (prompt_file):
    - Absolute path: Load from that file
    - Relative path (./...): Resolve from cwd
    - Variant name (e.g., "security"): Layered discovery:
      1. ./prompts/{role}-{name}.oct.md (project-local)
      2. ~/.debate-hall/prompts/{role}-{name}.oct.md (user-global)
    - None: Use embedded default (Ship ZERO principle)
    """

    provider: Literal["cli", "openrouter"] = Field(
        ..., description="Provider type: cli or openrouter"
    )
    cli: str | None = Field(
        default=None, description="CLI name for cli provider: claude, codex, gemini"
    )
    model: str | None = Field(
        default=None, description="Model identifier (required for openrouter, optional for cli)"
    )
    role: str | None = Field(default=None, description="System prompt role name override")
    prompt_file: str | None = Field(
        default=None,
        description="Custom prompt file path or variant name (e.g., 'security' -> wind-security.oct.md)",
    )
    timeout: int | None = Field(
        default=None, description="Provider timeout in seconds (overrides tier default)"
    )
    cli_args: dict[str, str | bool | int] | None = Field(
        default=None,
        description="Additional CLI arguments (e.g., {'temperature': 0.7, 'verbose': True})",
    )


class FallbackConfig(BaseModel):
    """Configuration for provider fallback on timeout/failure.

    When a primary provider times out or fails, the orchestrator can
    automatically retry with a fallback provider (typically faster/cheaper).

    Fields:
    - enabled: Whether fallback is enabled (default: False)
    - provider: Fallback provider type ('openrouter' recommended)
    - model: Model to use for fallback (should be fast/reliable)
    - timeout: Timeout for fallback provider in seconds
    """

    enabled: bool = Field(default=False, description="Enable fallback on timeout/failure")
    provider: Literal["cli", "openrouter"] = Field(
        default="openrouter", description="Fallback provider type"
    )
    model: str = Field(
        default="anthropic/claude-haiku-4",
        description="Fallback model (fast/cheap recommended)",
    )
    timeout: int = Field(default=60, description="Fallback provider timeout in seconds")


class TierSettings(BaseModel):
    """Settings for a tier configuration.

    Controls debate behavior for auto-orchestration.

    Fields:
    - consensus_required: Whether consensus is required for debate closure
    - max_turns: Maximum number of turns allowed in debate
    - max_refinement_loops: Maximum refinement iterations for auto-orchestration
    - provider_timeout: Default timeout in seconds for provider calls
    - fallback: Configuration for provider fallback on timeout/failure
    """

    consensus_required: bool = Field(
        default=True, description="Whether consensus is required for closure"
    )
    max_turns: int = Field(default=12, description="Maximum turns allowed")
    max_refinement_loops: int = Field(default=3, description="Maximum refinement iterations")
    provider_timeout: int = Field(
        default=120, description="Default provider timeout in seconds (default: 120)"
    )
    fallback: FallbackConfig = Field(
        default_factory=FallbackConfig,
        description="Fallback provider configuration for timeout recovery",
    )


class TierConfig(BaseModel):
    """Complete configuration for a tier.

    Combines role configurations for Wind/Wall/Door with tier settings.

    Fields:
    - wind: Configuration for Wind role (PATHOS)
    - wall: Configuration for Wall role (ETHOS)
    - door: Configuration for Door role (LOGOS)
    - settings: Tier-specific settings
    """

    wind: RoleConfig = Field(..., description="Wind (PATHOS) role configuration")
    wall: RoleConfig = Field(..., description="Wall (ETHOS) role configuration")
    door: RoleConfig = Field(..., description="Door (LOGOS) role configuration")
    settings: TierSettings = Field(default_factory=TierSettings, description="Tier settings")


# Environment variable for tier configuration file
TIERS_FILE_ENV_VAR = "DEBATE_HALL_TIERS_FILE"


class TierConfigNotFoundError(Exception):
    """Raised when no tier configuration file is found."""

    pass


class TierConfigParseError(Exception):
    """Raised when tier configuration file cannot be parsed."""

    pass


def _load_tiers_from_yaml(file_path: Path) -> dict[str, TierConfig]:
    """Load tier configurations from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary of tier name to TierConfig

    Raises:
        FileNotFoundError: If file doesn't exist
        TierConfigParseError: If YAML is empty or invalid structure
        yaml.YAMLError: If YAML syntax is invalid
        pydantic.ValidationError: If config structure is invalid
    """
    with open(file_path) as f:
        data = yaml.safe_load(f)

    # Guard against empty file or non-mapping YAML
    if data is None:
        raise TierConfigParseError(f"Tier configuration file is empty: {file_path}")
    if not isinstance(data, dict):
        raise TierConfigParseError(
            f"Tier configuration must be a YAML mapping, got {type(data).__name__}: {file_path}"
        )

    tiers: dict[str, TierConfig] = {}
    for tier_name, tier_data in data.items():
        tiers[tier_name] = TierConfig.model_validate(tier_data)

    return tiers


def _get_tiers_file_path() -> Path | None:
    """Get the path to the tiers configuration file.

    Resolution order:
    1. DEBATE_HALL_TIERS_FILE environment variable
    2. ./tiers.yaml (project-local)
    3. ~/.debate-hall/tiers.yaml (user-global)

    Returns:
        Path to config file, or None if no file exists
    """
    # Priority 1: Environment variable
    env_value = os.environ.get(TIERS_FILE_ENV_VAR, "")
    if env_value:
        path = Path(env_value)
        if path.exists():
            return path

    # Priority 2: Project-local config
    project_config = Path("./tiers.yaml")
    if project_config.exists():
        return project_config.resolve()

    # Priority 3: User-global config
    home = Path(os.environ.get("HOME", "~")).expanduser()
    home_config = home / ".debate-hall" / "tiers.yaml"
    if home_config.exists():
        return home_config

    return None


def load_tier_config(tier_name: str) -> TierConfig:
    """Load configuration for a specific tier.

    Resolution order:
    1. DEBATE_HALL_TIERS_FILE environment variable
    2. ./tiers.yaml (project-local)
    3. ~/.debate-hall/tiers.yaml (user-global)

    Args:
        tier_name: Name of the tier to load (e.g., "standard", "premium")

    Returns:
        TierConfig for the requested tier

    Raises:
        TierConfigNotFoundError: If no configuration file is found
        KeyError: If tier_name is not found in the configuration file
    """
    config_file = _get_tiers_file_path()

    if config_file is None:
        raise TierConfigNotFoundError(
            "No tier configuration found. Create tiers.yaml in:\n"
            "  - ./tiers.yaml (project-local)\n"
            "  - ~/.debate-hall/tiers.yaml (user-global)\n"
            "  - Or set DEBATE_HALL_TIERS_FILE environment variable\n\n"
            "See https://github.com/elevanaltd/debate-hall-mcp#configuration for examples."
        )

    tiers = _load_tiers_from_yaml(config_file)

    if tier_name not in tiers:
        available = ", ".join(sorted(tiers.keys()))
        raise KeyError(
            f"Tier '{tier_name}' not found in {config_file}. " f"Available tiers: {available}"
        )

    return tiers[tier_name]
