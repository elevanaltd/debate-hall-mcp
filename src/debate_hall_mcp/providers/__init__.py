"""Model providers for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements:
- ModelProvider Protocol for provider abstraction
- ProviderResponse for standardized completion responses
- create_provider factory for creating providers from RoleConfig

Provider Types:
- CliProvider: External AI CLIs (claude, codex, gemini)
- OpenRouterProvider: OpenRouter API for model access

Usage:
    from debate_hall_mcp.config import RoleConfig
    from debate_hall_mcp.providers import create_provider

    config = RoleConfig(provider="cli", cli="claude", role="wind-agent")
    provider = create_provider(config)
    response = await provider.complete("You are Wind.", "Analyze this topic.")
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from debate_hall_mcp.config import RoleConfig


class ProviderResponse(BaseModel):
    """Response from a model provider completion.

    Standardizes the response format across different providers.

    Fields:
    - content: The generated text response
    - model: The model that generated the response
    - token_input: Number of input tokens (optional)
    - token_output: Number of output tokens (optional)
    """

    content: str = Field(..., description="Generated text response")
    model: str = Field(..., description="Model identifier that generated response")
    token_input: int | None = Field(default=None, description="Input token count")
    token_output: int | None = Field(default=None, description="Output token count")


@runtime_checkable
class ModelProvider(Protocol):
    """Protocol for model providers.

    Defines the interface that all model providers must implement.
    Uses structural subtyping - any class with a matching complete()
    method signature conforms to this protocol.

    Methods:
        complete: Generate a completion from system and user prompts.
    """

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> ProviderResponse:
        """Generate a completion from the model.

        Args:
            system_prompt: System context for the model
            user_prompt: User message to respond to
            model: Optional model override (uses provider default if None)

        Returns:
            ProviderResponse with generated content and metadata
        """
        ...


class ProviderConfigError(Exception):
    """Error raised for invalid provider configuration."""

    pass


def create_provider(
    role_config: "RoleConfig",
    timeout_override: float | None = None,
) -> ModelProvider:
    """Create a model provider from role configuration.

    Factory function that instantiates the appropriate provider
    based on the RoleConfig settings.

    Args:
        role_config: Configuration specifying provider type and settings
        timeout_override: Optional timeout to use instead of role_config.timeout

    Returns:
        ModelProvider instance for the configured provider

    Raises:
        ProviderConfigError: If configuration is invalid
    """
    # Determine effective timeout: override > role_config > provider default
    effective_timeout = timeout_override if timeout_override is not None else role_config.timeout

    if role_config.provider == "cli":
        if role_config.cli is None:
            raise ProviderConfigError("CLI provider requires 'cli' field (claude, codex, gemini)")
        from .cli import DEFAULT_TIMEOUT_SECONDS, CliProvider

        # Use effective_timeout or provider default
        timeout = effective_timeout if effective_timeout is not None else DEFAULT_TIMEOUT_SECONDS

        return CliProvider(
            cli_name=role_config.cli,
            role=role_config.role,
            timeout=timeout,
            model=role_config.model,
            cli_args=role_config.cli_args,
        )

    elif role_config.provider == "openrouter":
        if role_config.model is None:
            raise ProviderConfigError("OpenRouter provider requires 'model' field")
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(model=role_config.model)

    else:
        # This should not happen with Literal type, but handle defensively
        raise ProviderConfigError(f"Unknown provider type: {role_config.provider}")


__all__ = [
    "ModelProvider",
    "ProviderResponse",
    "ProviderConfigError",
    "create_provider",
]
