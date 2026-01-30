"""OpenRouter API provider for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements OpenRouterProvider for accessing models via
the OpenRouter API.

API Documentation: https://openrouter.ai/docs

Usage:
    provider = OpenRouterProvider(model="anthropic/claude-3-opus")
    response = await provider.complete("System prompt", "User prompt")

Environment:
    OPENROUTER_API_KEY: Required API key for authentication
"""

import asyncio
import json
import os
from typing import Any

import httpx

from debate_hall_mcp.providers import ProviderResponse

# Default timeout values (seconds)
DEFAULT_CONNECT_TIMEOUT = 10  # Connection establishment timeout
DEFAULT_READ_TIMEOUT = 120  # Response read timeout (model completion)

# Retry configuration
MAX_RETRIES = 3  # Maximum number of retry attempts
INITIAL_BACKOFF = 1.0  # Initial backoff in seconds
BACKOFF_MULTIPLIER = 2.0  # Exponential backoff multiplier

# HTTP status codes that trigger retry
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


class OpenRouterConfigError(Exception):
    """Error raised for OpenRouter configuration issues."""

    pass


class OpenRouterApiError(Exception):
    """Error raised when OpenRouter API call fails."""

    pass


class OpenRouterProvider:
    """Provider that uses OpenRouter API for completions.

    Sends requests to the OpenRouter API endpoint and parses responses.

    Attributes:
        model: Default model identifier to use
        api_url: OpenRouter API endpoint URL
    """

    def __init__(self, model: str) -> None:
        """Initialize OpenRouterProvider.

        Args:
            model: Model identifier (e.g., "anthropic/claude-3-opus")
        """
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _get_api_key(self) -> str:
        """Get API key from environment.

        Returns:
            API key string

        Raises:
            OpenRouterConfigError: If OPENROUTER_API_KEY is not set
        """
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise OpenRouterConfigError("OPENROUTER_API_KEY environment variable is required")
        return api_key

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for API request.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

    def _build_request_body(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
    ) -> dict[str, Any]:
        """Build request body for API call.

        Args:
            system_prompt: System context for the model
            user_prompt: User message to respond to
            model: Optional model override

        Returns:
            Dictionary representing JSON request body
        """
        effective_model = model if model else self.model

        return {
            "model": effective_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

    def _is_retryable_status(self, status_code: int) -> bool:
        """Check if HTTP status code is retryable.

        Args:
            status_code: HTTP status code to check

        Returns:
            True if the status code indicates a transient error
        """
        return status_code in RETRYABLE_STATUS_CODES

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> ProviderResponse:
        """Generate completion using OpenRouter API.

        Sends a request to the OpenRouter API and parses the response.
        Implements retry logic with exponential backoff for transient errors.

        Args:
            system_prompt: System context for the model
            user_prompt: User message to respond to
            model: Optional model override

        Returns:
            ProviderResponse with generated content and token usage

        Raises:
            OpenRouterApiError: If API call fails, times out, or response is malformed
        """
        headers = self._build_headers()
        body = self._build_request_body(system_prompt, user_prompt, model)

        # Configure timeout with explicit connect and read timeouts
        timeout = httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=DEFAULT_CONNECT_TIMEOUT,
            pool=DEFAULT_CONNECT_TIMEOUT,
        )

        last_exception: httpx.HTTPStatusError | None = None
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=body,
                    )
                    response.raise_for_status()

                    # Parse JSON with error handling
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        raise OpenRouterApiError(
                            f"OpenRouter returned invalid JSON: {response.text[:200]}"
                        ) from e

                    # Success - extract and return response
                    break

                except httpx.TimeoutException as e:
                    raise OpenRouterApiError(
                        f"OpenRouter request timed out after "
                        f"{DEFAULT_CONNECT_TIMEOUT}s connect/{DEFAULT_READ_TIMEOUT}s read"
                    ) from e

                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code
                    if self._is_retryable_status(status_code) and attempt < MAX_RETRIES:
                        last_exception = e
                        await asyncio.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                        continue
                    raise OpenRouterApiError(
                        f"OpenRouter API error: {status_code} - {e.response.text}"
                    ) from e

                except httpx.RequestError as e:
                    raise OpenRouterApiError(f"OpenRouter request failed: {e}") from e
        else:
            # All retries exhausted
            if last_exception:
                raise OpenRouterApiError(
                    f"OpenRouter API error after {MAX_RETRIES} retries: "
                    f"{last_exception.response.status_code} - {last_exception.response.text}"
                ) from last_exception

        # Extract content from response
        choices = data.get("choices", [])
        if not choices or "message" not in choices[0]:
            raise OpenRouterApiError("No content in OpenRouter response")

        content = choices[0]["message"].get("content", "")
        if not content:
            raise OpenRouterApiError("No content in OpenRouter response")

        # Extract model and token usage
        response_model = data.get("model", model if model else self.model)
        usage = data.get("usage", {})
        token_input = usage.get("prompt_tokens")
        token_output = usage.get("completion_tokens")

        return ProviderResponse(
            content=content,
            model=response_model,
            token_input=token_input,
            token_output=token_output,
        )


__all__ = [
    "OpenRouterProvider",
    "OpenRouterConfigError",
    "OpenRouterApiError",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_READ_TIMEOUT",
    "MAX_RETRIES",
]
