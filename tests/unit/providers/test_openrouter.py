"""Unit tests for OpenRouterProvider implementation.

Tests cover:
- OpenRouterProvider initialization
- API key handling from environment
- HTTP request construction
- Response parsing
- Error handling
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOpenRouterProviderInit:
    """Test OpenRouterProvider initialization."""

    def test_openrouter_provider_init_with_model(self) -> None:
        """OpenRouterProvider initializes with model."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model="anthropic/claude-3-opus")
        assert provider.model == "anthropic/claude-3-opus"

    def test_openrouter_provider_default_api_url(self) -> None:
        """OpenRouterProvider has correct default API URL."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model="test-model")
        assert provider.api_url == "https://openrouter.ai/api/v1/chat/completions"


class TestOpenRouterProviderApiKey:
    """Test API key handling."""

    def test_api_key_read_from_environment(self) -> None:
        """OpenRouterProvider reads API key from OPENROUTER_API_KEY env var."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"}):
            provider = OpenRouterProvider(model="test-model")
            assert provider._get_api_key() == "test-key-123"

    def test_missing_api_key_raises_error(self) -> None:
        """OpenRouterProvider raises error if API key is missing."""
        from debate_hall_mcp.providers.openrouter import (
            OpenRouterConfigError,
            OpenRouterProvider,
        )

        with patch.dict(os.environ, {}, clear=True):
            # Ensure OPENROUTER_API_KEY is not set
            os.environ.pop("OPENROUTER_API_KEY", None)
            provider = OpenRouterProvider(model="test-model")

            with pytest.raises(OpenRouterConfigError, match="OPENROUTER_API_KEY"):
                provider._get_api_key()


class TestOpenRouterProviderRequestConstruction:
    """Test HTTP request construction."""

    def test_request_headers_include_auth(self) -> None:
        """Request headers should include Authorization bearer token."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")
            headers = provider._build_headers()

            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test-key"
            assert headers["Content-Type"] == "application/json"

    def test_request_body_construction(self) -> None:
        """Request body should follow OpenRouter API format."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model="anthropic/claude-3-opus")
        body = provider._build_request_body(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello!",
            model=None,  # Use default model
        )

        assert body["model"] == "anthropic/claude-3-opus"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][0]["content"] == "You are a helpful assistant."
        assert body["messages"][1]["role"] == "user"
        assert body["messages"][1]["content"] == "Hello!"

    def test_request_body_with_override_model(self) -> None:
        """Request body should use override model when provided."""
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model="default-model")
        body = provider._build_request_body(
            system_prompt="System",
            user_prompt="User",
            model="override-model",
        )

        assert body["model"] == "override-model"


class TestOpenRouterProviderComplete:
    """Test OpenRouterProvider.complete() method."""

    @pytest.mark.asyncio
    async def test_complete_returns_provider_response(self) -> None:
        """complete() should return ProviderResponse on success."""
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        mock_response_data = {
            "choices": [{"message": {"content": "Hello, I am Claude!"}}],
            "model": "anthropic/claude-3-opus",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="anthropic/claude-3-opus")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                response = await provider.complete(
                    system_prompt="You are helpful.",
                    user_prompt="Hello!",
                )

                assert isinstance(response, ProviderResponse)
                assert response.content == "Hello, I am Claude!"
                assert response.model == "anthropic/claude-3-opus"
                assert response.token_input == 10
                assert response.token_output == 5

    @pytest.mark.asyncio
    async def test_complete_handles_api_error(self) -> None:
        """complete() should raise on API error response."""
        import httpx

        from debate_hall_mcp.providers.openrouter import (
            OpenRouterApiError,
            OpenRouterProvider,
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "401 Unauthorized",
                        request=MagicMock(),
                        response=mock_response,
                    )
                )
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(OpenRouterApiError):
                    await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )

    @pytest.mark.asyncio
    async def test_complete_handles_missing_content(self) -> None:
        """complete() should handle malformed API response gracefully."""
        from debate_hall_mcp.providers.openrouter import (
            OpenRouterApiError,
            OpenRouterProvider,
        )

        mock_response_data = {"choices": []}  # Empty choices

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(OpenRouterApiError, match="No content"):
                    await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )


class TestOpenRouterProviderProtocolConformance:
    """Test that OpenRouterProvider conforms to ModelProvider Protocol."""

    def test_openrouter_provider_conforms_to_protocol(self) -> None:
        """OpenRouterProvider should conform to ModelProvider Protocol."""
        from debate_hall_mcp.providers import ModelProvider
        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model="test-model")
        # Should be usable as ModelProvider type
        model_provider: ModelProvider = provider
        assert hasattr(model_provider, "complete")


class TestOpenRouterProviderTimeout:
    """Test OpenRouterProvider timeout handling."""

    def test_default_timeouts_are_set(self) -> None:
        """OpenRouterProvider should have default timeout constants."""
        from debate_hall_mcp.providers.openrouter import (
            DEFAULT_CONNECT_TIMEOUT,
            DEFAULT_READ_TIMEOUT,
        )

        assert DEFAULT_CONNECT_TIMEOUT == 10
        assert DEFAULT_READ_TIMEOUT == 120

    @pytest.mark.asyncio
    async def test_timeout_raises_api_error(self) -> None:
        """complete() should raise OpenRouterApiError on timeout."""
        import httpx

        from debate_hall_mcp.providers.openrouter import (
            OpenRouterApiError,
            OpenRouterProvider,
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=httpx.TimeoutException("Connection timed out")
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(OpenRouterApiError, match="timed out"):
                    await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )


class TestOpenRouterProviderRetry:
    """Test OpenRouterProvider retry logic for transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_429_rate_limit(self) -> None:
        """complete() should retry on 429 rate limit errors."""
        import httpx

        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        mock_response_data = {
            "choices": [{"message": {"content": "Success after retry!"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                # First call fails with 429, second succeeds
                mock_response_429 = MagicMock()
                mock_response_429.status_code = 429
                mock_response_429.text = "Rate limited"
                mock_response_429.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=MagicMock(),
                        response=mock_response_429,
                    )
                )

                mock_response_success = MagicMock()
                mock_response_success.status_code = 200
                mock_response_success.json.return_value = mock_response_data
                mock_response_success.raise_for_status = MagicMock()

                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_success])
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                # Patch sleep to avoid actual waiting
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    response = await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )

                    assert response.content == "Success after retry!"
                    assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_5xx_server_error(self) -> None:
        """complete() should retry on 5xx server errors."""
        import httpx

        from debate_hall_mcp.providers.openrouter import OpenRouterProvider

        mock_response_data = {
            "choices": [{"message": {"content": "Success!"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response_503 = MagicMock()
                mock_response_503.status_code = 503
                mock_response_503.text = "Service Unavailable"
                mock_response_503.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Service Unavailable",
                        request=MagicMock(),
                        response=mock_response_503,
                    )
                )

                mock_response_success = MagicMock()
                mock_response_success.status_code = 200
                mock_response_success.json.return_value = mock_response_data
                mock_response_success.raise_for_status = MagicMock()

                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=[mock_response_503, mock_response_success])
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with patch("asyncio.sleep", new_callable=AsyncMock):
                    response = await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )

                    assert response.content == "Success!"
                    assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        """complete() should raise after max retries exhausted."""
        import httpx

        from debate_hall_mcp.providers.openrouter import (
            MAX_RETRIES,
            OpenRouterApiError,
            OpenRouterProvider,
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response_429 = MagicMock()
                mock_response_429.status_code = 429
                mock_response_429.text = "Rate limited"
                mock_response_429.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=MagicMock(),
                        response=mock_response_429,
                    )
                )

                mock_client = AsyncMock()
                # Return 429 for all attempts (initial + retries)
                mock_client.post = AsyncMock(return_value=mock_response_429)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with patch("asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(OpenRouterApiError, match="429"):
                        await provider.complete(
                            system_prompt="System",
                            user_prompt="User",
                        )

                    # Initial attempt + MAX_RETRIES
                    assert mock_client.post.call_count == MAX_RETRIES + 1


class TestOpenRouterProviderJsonParsing:
    """Test OpenRouterProvider JSON parsing error handling."""

    @pytest.mark.asyncio
    async def test_json_decode_error_raises_api_error(self) -> None:
        """complete() should raise OpenRouterApiError on JSON decode failure."""
        import json

        from debate_hall_mcp.providers.openrouter import (
            OpenRouterApiError,
            OpenRouterProvider,
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = OpenRouterProvider(model="test-model")

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "Not valid JSON {{"
                mock_response.json.side_effect = json.JSONDecodeError(
                    "Expecting value", "Not valid JSON {{", 0
                )
                mock_response.raise_for_status = MagicMock()

                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(OpenRouterApiError, match="JSON"):
                    await provider.complete(
                        system_prompt="System",
                        user_prompt="User",
                    )
