"""Unit tests for provider factory function.

Tests cover:
- Factory routing to CliProvider
- Factory routing to OpenRouterProvider
- Error handling for invalid configurations
"""

import pytest


class TestCreateProviderFactory:
    """Test create_provider factory function."""

    def test_factory_creates_cli_provider_for_cli_config(self) -> None:
        """Factory creates CliProvider when provider='cli'."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import create_provider
        from debate_hall_mcp.providers.cli import CliProvider

        config = RoleConfig(provider="cli", cli="claude", role="wind-agent")
        provider = create_provider(config)

        assert isinstance(provider, CliProvider)
        assert provider.cli_name == "claude"
        assert provider.role == "wind-agent"

    def test_factory_creates_cli_provider_for_codex(self) -> None:
        """Factory creates CliProvider for codex CLI."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import create_provider
        from debate_hall_mcp.providers.cli import CliProvider

        config = RoleConfig(provider="cli", cli="codex", role="wall-agent")
        provider = create_provider(config)

        assert isinstance(provider, CliProvider)
        assert provider.cli_name == "codex"

    def test_factory_creates_cli_provider_for_gemini(self) -> None:
        """Factory creates CliProvider for gemini CLI."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import create_provider
        from debate_hall_mcp.providers.cli import CliProvider

        config = RoleConfig(provider="cli", cli="gemini", role="door-agent")
        provider = create_provider(config)

        assert isinstance(provider, CliProvider)
        assert provider.cli_name == "gemini"

    def test_factory_creates_openrouter_provider(self) -> None:
        """Factory creates OpenRouterProvider when provider='openrouter'."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import create_provider
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        config = RoleConfig(provider="openrouter", model="anthropic/claude-3-opus")
        provider = create_provider(config)

        assert isinstance(provider, OpenRouterProvider)
        assert provider.model == "anthropic/claude-3-opus"

    def test_factory_raises_for_cli_without_cli_name(self) -> None:
        """Factory raises error if provider='cli' but cli is None."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import ProviderConfigError, create_provider

        config = RoleConfig(provider="cli", cli=None)
        with pytest.raises(ProviderConfigError, match="cli"):
            create_provider(config)

    def test_factory_raises_for_openrouter_without_model(self) -> None:
        """Factory raises error if provider='openrouter' but model is None."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import ProviderConfigError, create_provider

        config = RoleConfig(provider="openrouter", model=None)
        with pytest.raises(ProviderConfigError, match="model"):
            create_provider(config)

    def test_factory_returns_model_provider_type(self) -> None:
        """Factory returns object conforming to ModelProvider Protocol."""
        from debate_hall_mcp.config import RoleConfig
        from debate_hall_mcp.providers import ModelProvider, create_provider

        config = RoleConfig(provider="cli", cli="claude")
        provider = create_provider(config)

        # Should be usable as ModelProvider
        model_provider: ModelProvider = provider
        assert hasattr(model_provider, "complete")
