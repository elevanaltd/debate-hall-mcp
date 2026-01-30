"""Unit tests for debate_hall_mcp.config module.

Tests cover (ADR-0002 Foundation):
- RoleConfig model for Wind/Wall/Door provider configuration
- TierSettings model for tier-specific debate settings
- TierConfig model combining role configs with settings
- Tier configuration loader with file-based resolution
"""

from pathlib import Path
from textwrap import dedent

import pytest


class TestRoleConfig:
    """Test RoleConfig model for agent role provider configuration."""

    def test_role_config_with_cli_provider(self) -> None:
        """Create RoleConfig with CLI provider."""
        from debate_hall_mcp.config import RoleConfig

        config = RoleConfig(provider="cli", cli="claude")
        assert config.provider == "cli"
        assert config.cli == "claude"
        assert config.model is None
        assert config.role is None

    def test_role_config_with_openrouter_provider(self) -> None:
        """Create RoleConfig with OpenRouter provider."""
        from debate_hall_mcp.config import RoleConfig

        config = RoleConfig(
            provider="openrouter",
            model="anthropic/claude-3-opus",
            role="wind-agent",
        )
        assert config.provider == "openrouter"
        assert config.model == "anthropic/claude-3-opus"
        assert config.role == "wind-agent"
        assert config.cli is None

    def test_role_config_validates_provider_literal(self) -> None:
        """RoleConfig validates provider is 'cli' or 'openrouter'."""
        from pydantic import ValidationError

        from debate_hall_mcp.config import RoleConfig

        with pytest.raises(ValidationError, match="provider"):
            RoleConfig(provider="invalid")

    def test_role_config_cli_provider_options(self) -> None:
        """RoleConfig cli field accepts valid CLI names."""
        from debate_hall_mcp.config import RoleConfig

        for cli_name in ["claude", "codex", "gemini"]:
            config = RoleConfig(provider="cli", cli=cli_name)
            assert config.cli == cli_name


class TestTierSettings:
    """Test TierSettings model for tier-specific settings."""

    def test_tier_settings_defaults(self) -> None:
        """TierSettings has sensible defaults."""
        from debate_hall_mcp.config import TierSettings

        settings = TierSettings()
        assert settings.consensus_required is True
        assert settings.max_turns == 12
        assert settings.max_refinement_loops == 3

    def test_tier_settings_custom_values(self) -> None:
        """TierSettings accepts custom values."""
        from debate_hall_mcp.config import TierSettings

        settings = TierSettings(
            consensus_required=False,
            max_turns=8,
            max_refinement_loops=5,
        )
        assert settings.consensus_required is False
        assert settings.max_turns == 8
        assert settings.max_refinement_loops == 5


class TestTierConfig:
    """Test TierConfig model combining role configs with settings."""

    def test_tier_config_with_all_roles(self) -> None:
        """Create TierConfig with Wind, Wall, Door roles."""
        from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings

        config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        assert config.wind.cli == "claude"
        assert config.wall.cli == "codex"
        assert config.door.cli == "gemini"
        assert config.settings.consensus_required is True

    def test_tier_config_requires_wind_role(self) -> None:
        """TierConfig requires wind role."""
        from pydantic import ValidationError

        from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings

        with pytest.raises(ValidationError, match="wind"):
            TierConfig(
                wall=RoleConfig(provider="cli", cli="codex"),
                door=RoleConfig(provider="cli", cli="gemini"),
                settings=TierSettings(),
            )

    def test_tier_config_requires_wall_role(self) -> None:
        """TierConfig requires wall role."""
        from pydantic import ValidationError

        from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings

        with pytest.raises(ValidationError, match="wall"):
            TierConfig(
                wind=RoleConfig(provider="cli", cli="claude"),
                door=RoleConfig(provider="cli", cli="gemini"),
                settings=TierSettings(),
            )

    def test_tier_config_requires_door_role(self) -> None:
        """TierConfig requires door role."""
        from pydantic import ValidationError

        from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings

        with pytest.raises(ValidationError, match="door"):
            TierConfig(
                wind=RoleConfig(provider="cli", cli="claude"),
                wall=RoleConfig(provider="cli", cli="codex"),
                settings=TierSettings(),
            )

    def test_tier_config_settings_has_default(self) -> None:
        """TierConfig settings has a default factory."""
        from debate_hall_mcp.config import RoleConfig, TierConfig

        config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
        )
        # Settings should use defaults
        assert config.settings.consensus_required is True
        assert config.settings.max_turns == 12

    def test_tier_config_mixed_providers(self) -> None:
        """TierConfig can mix CLI and OpenRouter providers."""
        from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings

        config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="openrouter", model="openai/gpt-4"),
            door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
            settings=TierSettings(consensus_required=False),
        )
        assert config.wind.provider == "cli"
        assert config.wall.provider == "openrouter"
        assert config.door.provider == "cli"


class TestTierConfigLoader:
    """Test tier configuration loader with file-based resolution."""

    def test_load_tier_config_from_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config reads from DEBATE_HALL_TIERS_FILE env var first."""
        from debate_hall_mcp.config import load_tier_config

        # Create config file
        config_file = tmp_path / "tiers.yaml"
        config_file.write_text(dedent("""
            standard:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: cli
                cli: codex
              door:
                provider: cli
                cli: gemini
              settings:
                consensus_required: true
                max_turns: 12
                max_refinement_loops: 3
        """))

        monkeypatch.setenv("DEBATE_HALL_TIERS_FILE", str(config_file))

        config = load_tier_config("standard")
        assert config.wind.cli == "claude"
        assert config.wall.cli == "codex"
        assert config.door.cli == "gemini"

    def test_load_tier_config_from_home_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config reads from ~/.debate-hall/tiers.yaml if no env var."""
        from debate_hall_mcp.config import load_tier_config

        # Create mock home directory with config
        mock_home = tmp_path / "home"
        mock_debate_hall = mock_home / ".debate-hall"
        mock_debate_hall.mkdir(parents=True)

        config_file = mock_debate_hall / "tiers.yaml"
        config_file.write_text(dedent("""
            premium:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: openrouter
                model: anthropic/claude-3-opus
              door:
                provider: cli
                cli: gemini
              settings:
                consensus_required: false
                max_turns: 20
                max_refinement_loops: 5
        """))

        # Unset env var and mock home directory
        monkeypatch.delenv("DEBATE_HALL_TIERS_FILE", raising=False)
        monkeypatch.setenv("HOME", str(mock_home))
        # Change to temp dir so ./tiers.yaml isn't found
        monkeypatch.chdir(tmp_path)

        config = load_tier_config("premium")
        assert config.wall.provider == "openrouter"
        assert config.settings.max_turns == 20

    def test_load_tier_config_no_config_raises_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """load_tier_config raises TierConfigNotFoundError if no config files exist."""
        from debate_hall_mcp.config import TierConfigNotFoundError, load_tier_config

        # Point to non-existent locations
        monkeypatch.delenv("DEBATE_HALL_TIERS_FILE", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "nonexistent"))
        monkeypatch.chdir(tmp_path / "also_nonexistent" if False else tmp_path)

        # Create empty tmp_path with no tiers.yaml
        with pytest.raises(TierConfigNotFoundError, match="No tier configuration found"):
            load_tier_config("standard")

    def test_load_tier_config_tier_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config raises error for unknown tier name."""
        from debate_hall_mcp.config import load_tier_config

        # Create config without the requested tier
        config_file = tmp_path / "tiers.yaml"
        config_file.write_text(dedent("""
            standard:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: cli
                cli: codex
              door:
                provider: cli
                cli: gemini
              settings:
                consensus_required: true
                max_turns: 12
                max_refinement_loops: 3
        """))

        monkeypatch.setenv("DEBATE_HALL_TIERS_FILE", str(config_file))

        with pytest.raises(KeyError, match="nonexistent"):
            load_tier_config("nonexistent")

    def test_load_tier_config_empty_file_raises_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config raises TierConfigParseError for empty YAML file."""
        from debate_hall_mcp.config import TierConfigParseError, load_tier_config

        # Create empty config file
        config_file = tmp_path / "tiers.yaml"
        config_file.write_text("")

        monkeypatch.setenv("DEBATE_HALL_TIERS_FILE", str(config_file))

        with pytest.raises(TierConfigParseError, match="empty"):
            load_tier_config("standard")

    def test_load_tier_config_non_mapping_raises_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config raises TierConfigParseError for non-mapping YAML."""
        from debate_hall_mcp.config import TierConfigParseError, load_tier_config

        # Create config file with list instead of mapping
        config_file = tmp_path / "tiers.yaml"
        config_file.write_text("- item1\n- item2\n")

        monkeypatch.setenv("DEBATE_HALL_TIERS_FILE", str(config_file))

        with pytest.raises(TierConfigParseError, match="must be a YAML mapping"):
            load_tier_config("standard")

    def test_load_tier_config_env_var_priority(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env var takes priority over home directory config."""
        from debate_hall_mcp.config import load_tier_config

        # Create env var config
        env_config = tmp_path / "env_tiers.yaml"
        env_config.write_text(dedent("""
            standard:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: cli
                cli: codex
              door:
                provider: cli
                cli: gemini
              settings:
                consensus_required: true
                max_turns: 100
                max_refinement_loops: 3
        """))

        # Create home dir config with different values
        mock_home = tmp_path / "home"
        mock_debate_hall = mock_home / ".debate-hall"
        mock_debate_hall.mkdir(parents=True)
        home_config = mock_debate_hall / "tiers.yaml"
        home_config.write_text(dedent("""
            standard:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: cli
                cli: codex
              door:
                provider: cli
                cli: gemini
              settings:
                consensus_required: true
                max_turns: 50
                max_refinement_loops: 3
        """))

        monkeypatch.setenv("DEBATE_HALL_TIERS_FILE", str(env_config))
        monkeypatch.setenv("HOME", str(mock_home))

        config = load_tier_config("standard")
        # Should use env var config (max_turns=100) not home config (max_turns=50)
        assert config.settings.max_turns == 100

    def test_load_tier_config_from_project_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tier_config reads from ./tiers.yaml (project-local)."""
        from debate_hall_mcp.config import load_tier_config

        # Create project-local config
        config_file = tmp_path / "tiers.yaml"
        config_file.write_text(dedent("""
            standard:
              wind:
                provider: openrouter
                model: anthropic/claude-sonnet-4
              wall:
                provider: openrouter
                model: anthropic/claude-sonnet-4
              door:
                provider: openrouter
                model: anthropic/claude-sonnet-4
        """))

        # Unset env var and point home to non-existent
        monkeypatch.delenv("DEBATE_HALL_TIERS_FILE", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "nonexistent"))
        monkeypatch.chdir(tmp_path)

        config = load_tier_config("standard")
        assert config.wind.provider == "openrouter"
        assert config.wind.model == "anthropic/claude-sonnet-4"

    def test_load_tier_config_project_local_priority_over_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project-local ./tiers.yaml takes priority over ~/.debate-hall/tiers.yaml."""
        from debate_hall_mcp.config import load_tier_config

        # Create project-local config
        project_config = tmp_path / "tiers.yaml"
        project_config.write_text(dedent("""
            standard:
              wind:
                provider: openrouter
                model: project-model
              wall:
                provider: openrouter
                model: project-model
              door:
                provider: openrouter
                model: project-model
              settings:
                max_turns: 999
        """))

        # Create home dir config
        mock_home = tmp_path / "home"
        mock_debate_hall = mock_home / ".debate-hall"
        mock_debate_hall.mkdir(parents=True)
        home_config = mock_debate_hall / "tiers.yaml"
        home_config.write_text(dedent("""
            standard:
              wind:
                provider: cli
                cli: claude
              wall:
                provider: cli
                cli: codex
              door:
                provider: cli
                cli: gemini
              settings:
                max_turns: 1
        """))

        monkeypatch.delenv("DEBATE_HALL_TIERS_FILE", raising=False)
        monkeypatch.setenv("HOME", str(mock_home))
        monkeypatch.chdir(tmp_path)

        config = load_tier_config("standard")
        # Should use project-local (max_turns=999), not home (max_turns=1)
        assert config.settings.max_turns == 999
        assert config.wind.model == "project-model"
