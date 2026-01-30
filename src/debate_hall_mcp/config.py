"""Tier configuration for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements:
- RoleConfig for Wind/Wall/Door provider configuration
- TierSettings for tier-specific debate settings
- TierConfig combining role configs with settings
- load_tier_config for configuration loading with resolution order

Resolution order for tier configuration:
1. DEBATE_HALL_TIERS_FILE environment variable
2. ~/.debate-hall/tiers.yaml
3. Built-in DEFAULT_TIERS
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
    - model: For OpenRouter provider, the model identifier
    - role: Optional system prompt role name override
    - prompt_file: Optional custom prompt file path or variant name

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
    model: str | None = Field(default=None, description="Model identifier for openrouter provider")
    role: str | None = Field(default=None, description="System prompt role name override")
    prompt_file: str | None = Field(
        default=None,
        description="Custom prompt file path or variant name (e.g., 'security' -> wind-security.oct.md)",
    )


class TierSettings(BaseModel):
    """Settings for a tier configuration.

    Controls debate behavior for auto-orchestration.

    Fields:
    - consensus_required: Whether consensus is required for debate closure
    - max_turns: Maximum number of turns allowed in debate
    - max_refinement_loops: Maximum refinement iterations for auto-orchestration
    - provider_timeout: Timeout in seconds for provider calls (default: 300)
    """

    consensus_required: bool = Field(
        default=True, description="Whether consensus is required for closure"
    )
    max_turns: int = Field(default=12, description="Maximum turns allowed")
    max_refinement_loops: int = Field(default=3, description="Maximum refinement iterations")
    provider_timeout: int = Field(
        default=300, description="Provider call timeout in seconds (default: 300)"
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
    settings: TierSettings = Field(..., description="Tier settings")


# Built-in default tiers
DEFAULT_TIERS: dict[str, TierConfig] = {
    "standard": TierConfig(
        wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
        wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
        door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
        settings=TierSettings(
            consensus_required=True,
            max_turns=12,
            max_refinement_loops=3,
        ),
    ),
}

# Environment variable for tier configuration file
TIERS_FILE_ENV_VAR = "DEBATE_HALL_TIERS_FILE"


def _load_tiers_from_yaml(file_path: Path) -> dict[str, TierConfig]:
    """Load tier configurations from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary of tier name to TierConfig

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
        pydantic.ValidationError: If config structure is invalid
    """
    with open(file_path) as f:
        data = yaml.safe_load(f)

    tiers: dict[str, TierConfig] = {}
    for tier_name, tier_data in data.items():
        tiers[tier_name] = TierConfig.model_validate(tier_data)

    return tiers


def _get_tiers_file_path() -> Path | None:
    """Get the path to the tiers configuration file.

    Resolution order:
    1. DEBATE_HALL_TIERS_FILE environment variable
    2. ~/.debate-hall/tiers.yaml

    Returns:
        Path to config file, or None if no file exists
    """
    # Priority 1: Environment variable
    env_value = os.environ.get(TIERS_FILE_ENV_VAR, "")
    if env_value:
        path = Path(env_value)
        if path.exists():
            return path

    # Priority 2: Home directory config
    home = Path(os.environ.get("HOME", "~")).expanduser()
    home_config = home / ".debate-hall" / "tiers.yaml"
    if home_config.exists():
        return home_config

    return None


def load_tier_config(tier_name: str) -> TierConfig:
    """Load configuration for a specific tier.

    Resolution order:
    1. DEBATE_HALL_TIERS_FILE environment variable
    2. ~/.debate-hall/tiers.yaml
    3. Built-in DEFAULT_TIERS

    Args:
        tier_name: Name of the tier to load (e.g., "standard", "premium")

    Returns:
        TierConfig for the requested tier

    Raises:
        KeyError: If tier_name is not found in available configurations
    """
    # Try to load from file
    config_file = _get_tiers_file_path()
    if config_file is not None:
        tiers = _load_tiers_from_yaml(config_file)
        if tier_name in tiers:
            return tiers[tier_name]
        else:
            raise KeyError(f"Tier '{tier_name}' not found in {config_file}")

    # Fall back to built-in defaults
    if tier_name in DEFAULT_TIERS:
        return DEFAULT_TIERS[tier_name]

    raise KeyError(f"Tier '{tier_name}' not found in default tiers")
