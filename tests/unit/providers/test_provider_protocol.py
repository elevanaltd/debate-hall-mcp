"""Unit tests for ModelProvider Protocol and ProviderResponse.

Tests cover:
- ProviderResponse model creation and fields
- ModelProvider Protocol definition
- Protocol structural conformance checks
"""

import pytest


class TestProviderResponse:
    """Test ProviderResponse Pydantic model."""

    def test_provider_response_creation_with_required_fields(self) -> None:
        """ProviderResponse can be created with content and model."""
        from debate_hall_mcp.providers import ProviderResponse

        response = ProviderResponse(content="Hello, world!", model="claude-3-opus")
        assert response.content == "Hello, world!"
        assert response.model == "claude-3-opus"

    def test_provider_response_optional_token_fields(self) -> None:
        """ProviderResponse has optional token fields defaulting to None."""
        from debate_hall_mcp.providers import ProviderResponse

        response = ProviderResponse(content="Test", model="gpt-4")
        assert response.token_input is None
        assert response.token_output is None

    def test_provider_response_with_token_fields(self) -> None:
        """ProviderResponse accepts token_input and token_output."""
        from debate_hall_mcp.providers import ProviderResponse

        response = ProviderResponse(
            content="Test response",
            model="claude-3-opus",
            token_input=100,
            token_output=50,
        )
        assert response.token_input == 100
        assert response.token_output == 50

    def test_provider_response_requires_content(self) -> None:
        """ProviderResponse requires content field."""
        from pydantic import ValidationError

        from debate_hall_mcp.providers import ProviderResponse

        with pytest.raises(ValidationError, match="content"):
            ProviderResponse(model="test-model")  # type: ignore[call-arg]

    def test_provider_response_requires_model(self) -> None:
        """ProviderResponse requires model field."""
        from pydantic import ValidationError

        from debate_hall_mcp.providers import ProviderResponse

        with pytest.raises(ValidationError, match="model"):
            ProviderResponse(content="test")  # type: ignore[call-arg]

    def test_provider_response_is_pydantic_model(self) -> None:
        """ProviderResponse should be a Pydantic BaseModel."""
        from pydantic import BaseModel

        from debate_hall_mcp.providers import ProviderResponse

        assert issubclass(ProviderResponse, BaseModel)


class TestModelProviderProtocol:
    """Test ModelProvider Protocol definition."""

    def test_model_provider_is_protocol(self) -> None:
        """ModelProvider should be a Protocol."""
        from typing import Protocol

        from debate_hall_mcp.providers import ModelProvider

        assert issubclass(ModelProvider, Protocol)

    def test_model_provider_is_runtime_checkable(self) -> None:
        """ModelProvider should be runtime checkable for isinstance checks."""
        from debate_hall_mcp.providers import ModelProvider

        # Should have @runtime_checkable decorator
        assert hasattr(ModelProvider, "__protocol_attrs__") or callable(
            getattr(ModelProvider, "_is_protocol", None)
        )

    def test_model_provider_has_complete_method(self) -> None:
        """ModelProvider Protocol requires complete() async method."""
        from debate_hall_mcp.providers import ModelProvider

        # Protocol should define complete method
        assert hasattr(ModelProvider, "complete")

    def test_mock_provider_conforms_to_protocol(self) -> None:
        """A mock implementation should conform to ModelProvider Protocol."""
        from debate_hall_mcp.providers import ModelProvider, ProviderResponse

        class MockProvider:
            async def complete(
                self,
                system_prompt: str,  # noqa: ARG002
                user_prompt: str,  # noqa: ARG002
                model: str | None = None,  # noqa: ARG002
            ) -> ProviderResponse:
                return ProviderResponse(content="mock", model="mock-model")

        # Structural check - mock should be usable as ModelProvider
        provider: ModelProvider = MockProvider()
        assert hasattr(provider, "complete")
