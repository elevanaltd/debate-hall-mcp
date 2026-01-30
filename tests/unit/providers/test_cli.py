"""Unit tests for CliProvider implementation.

Tests cover:
- CliProvider initialization
- CLI command generation for claude, codex, gemini
- Subprocess execution mocking
- Response parsing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCliProviderInit:
    """Test CliProvider initialization."""

    def test_cli_provider_init_with_claude(self) -> None:
        """CliProvider initializes with claude CLI."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")
        assert provider.cli_name == "claude"
        assert provider.role is None

    def test_cli_provider_init_with_codex(self) -> None:
        """CliProvider initializes with codex CLI."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="codex")
        assert provider.cli_name == "codex"

    def test_cli_provider_init_with_gemini(self) -> None:
        """CliProvider initializes with gemini CLI."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="gemini")
        assert provider.cli_name == "gemini"

    def test_cli_provider_init_with_role(self) -> None:
        """CliProvider accepts optional role parameter."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude", role="wind-agent")
        assert provider.role == "wind-agent"

    def test_cli_provider_rejects_invalid_cli(self) -> None:
        """CliProvider raises ValueError for unsupported CLI names."""
        from debate_hall_mcp.providers.cli import CliProvider

        with pytest.raises(ValueError, match="Unsupported CLI"):
            CliProvider(cli_name="invalid-cli")


class TestCliProviderCommandGeneration:
    """Test CLI command generation for different providers."""

    def test_claude_command_generation(self) -> None:
        """Claude CLI command should use --print and --system-prompt."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")
        cmd = provider._build_command(
            system_prompt="You are Wind.",
            user_prompt="Analyze this.",
            model="claude-3-opus",
        )

        assert "claude" in cmd
        assert "--print" in cmd
        assert "--system-prompt" in cmd
        assert "You are Wind." in cmd
        assert "--model" in cmd
        assert "claude-3-opus" in cmd
        assert "Analyze this." in cmd

    def test_codex_command_generation(self) -> None:
        """Codex CLI command should use exec and combine prompts."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="codex")
        cmd = provider._build_command(
            system_prompt="You are Wall.",
            user_prompt="Review this.",
            model="gpt-4",
        )

        assert "codex" in cmd
        assert "exec" in cmd
        assert "--model" in cmd
        assert "gpt-4" in cmd
        # Combined prompt should be in command
        assert "You are Wall." in " ".join(cmd)
        assert "Review this." in " ".join(cmd)

    def test_gemini_command_generation(self) -> None:
        """Gemini CLI command should combine prompts."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="gemini")
        cmd = provider._build_command(
            system_prompt="You are Door.",
            user_prompt="Synthesize this.",
            model="gemini-pro",
        )

        assert "gemini" in cmd
        assert "--model" in cmd
        assert "gemini-pro" in cmd
        # Combined prompt should be in command
        assert "You are Door." in " ".join(cmd)
        assert "Synthesize this." in " ".join(cmd)

    def test_command_without_model_uses_default(self) -> None:
        """Command generation without model should not include --model flag."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")
        cmd = provider._build_command(
            system_prompt="System",
            user_prompt="User",
            model=None,
        )

        # Without model, --model flag should not be present
        assert "--model" not in cmd


class TestCliProviderComplete:
    """Test CliProvider.complete() method."""

    @pytest.mark.asyncio
    async def test_complete_returns_provider_response(self) -> None:
        """complete() should return ProviderResponse."""
        from debate_hall_mcp.providers import ProviderResponse
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"Test output", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            response = await provider.complete(
                system_prompt="System",
                user_prompt="User",
                model="claude-3-opus",
            )

            assert isinstance(response, ProviderResponse)
            assert response.content == "Test output"
            assert response.model == "claude-3-opus"

    @pytest.mark.asyncio
    async def test_complete_handles_subprocess_error(self) -> None:
        """complete() should raise on subprocess failure."""
        from debate_hall_mcp.providers.cli import CliProvider, CliProviderError

        provider = CliProvider(cli_name="claude")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            with pytest.raises(CliProviderError, match="Error message"):
                await provider.complete(
                    system_prompt="System",
                    user_prompt="User",
                )

    @pytest.mark.asyncio
    async def test_complete_uses_cli_default_model(self) -> None:
        """complete() without model uses CLI name as model identifier."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"Output", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            response = await provider.complete(
                system_prompt="System",
                user_prompt="User",
            )

            # Model should default to CLI name
            assert response.model == "claude"


class TestCliProviderProtocolConformance:
    """Test that CliProvider conforms to ModelProvider Protocol."""

    def test_cli_provider_conforms_to_protocol(self) -> None:
        """CliProvider should conform to ModelProvider Protocol."""
        from debate_hall_mcp.providers import ModelProvider
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude")
        # Should be usable as ModelProvider type
        model_provider: ModelProvider = provider
        assert hasattr(model_provider, "complete")


class TestCliProviderTimeout:
    """Test CliProvider timeout handling."""

    def test_default_timeout_is_set(self) -> None:
        """CliProvider should have a default timeout constant."""
        from debate_hall_mcp.providers.cli import DEFAULT_TIMEOUT_SECONDS

        assert DEFAULT_TIMEOUT_SECONDS == 120

    @pytest.mark.asyncio
    async def test_timeout_raises_error_and_kills_process(self) -> None:
        """complete() should raise CliProviderError on timeout and kill process."""
        from debate_hall_mcp.providers.cli import CliProvider, CliProviderError

        provider = CliProvider(cli_name="claude", timeout=0.01)  # Very short timeout

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            # Simulate a hanging process - use TimeoutError (builtin)
            mock_process.communicate = AsyncMock(
                side_effect=TimeoutError("Process timed out")
            )
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            with pytest.raises(CliProviderError, match="timed out"):
                await provider.complete(
                    system_prompt="System",
                    user_prompt="User",
                )

            # Ensure process was killed
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_timeout_is_used(self) -> None:
        """Custom timeout value should be respected."""
        from debate_hall_mcp.providers.cli import CliProvider

        provider = CliProvider(cli_name="claude", timeout=60)
        assert provider.timeout == 60


class TestCliProviderEmptyResponse:
    """Test CliProvider empty response handling."""

    @pytest.mark.asyncio
    async def test_empty_stdout_raises_error(self) -> None:
        """complete() should raise CliProviderError when stdout is empty."""
        from debate_hall_mcp.providers.cli import CliProvider, CliProviderError

        provider = CliProvider(cli_name="claude")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with pytest.raises(CliProviderError, match="empty response"):
                await provider.complete(
                    system_prompt="System",
                    user_prompt="User",
                )

    @pytest.mark.asyncio
    async def test_whitespace_only_stdout_raises_error(self) -> None:
        """complete() should raise CliProviderError when stdout is whitespace only."""
        from debate_hall_mcp.providers.cli import CliProvider, CliProviderError

        provider = CliProvider(cli_name="claude")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"   \n\t  ", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with pytest.raises(CliProviderError, match="empty response"):
                await provider.complete(
                    system_prompt="System",
                    user_prompt="User",
                )
