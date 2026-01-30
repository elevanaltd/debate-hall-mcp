"""CLI-based model provider for debate-hall-mcp auto-orchestration (ADR-0002).

This module implements CliProvider for executing external AI CLIs
in non-interactive mode.

Supported CLIs:
- claude: Anthropic Claude CLI (--print mode)
- codex: OpenAI Codex CLI (exec mode)
- gemini: Google Gemini CLI

Usage:
    provider = CliProvider(cli_name="claude", role="wind-agent")
    response = await provider.complete("System prompt", "User prompt")
"""

import asyncio

from debate_hall_mcp.providers import ProviderResponse

# Supported CLI names
CLI_NAMES = ("claude", "codex", "gemini")

# Default timeout for CLI subprocess execution (seconds)
# Set to 120s to accommodate model completion latency
DEFAULT_TIMEOUT_SECONDS = 120


class CliProviderError(Exception):
    """Error raised when CLI execution fails."""

    pass


class CliProvider:
    """Provider that uses external AI CLIs for completions.

    Executes CLI commands in non-interactive mode and parses responses.

    Attributes:
        cli_name: Which CLI to use (claude, codex, gemini)
        role: Optional role name for system prompt customization
        timeout: Timeout in seconds for CLI subprocess execution
    """

    def __init__(
        self,
        cli_name: str,
        role: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize CliProvider.

        Args:
            cli_name: CLI to use (claude, codex, gemini)
            role: Optional role name for system prompt
            timeout: Timeout in seconds for CLI execution (default: 120s)

        Raises:
            ValueError: If cli_name is not a supported CLI
        """
        if cli_name not in CLI_NAMES:
            raise ValueError(f"Unsupported CLI: {cli_name}. Supported: {CLI_NAMES}")
        self.cli_name = cli_name
        self.role = role
        self.timeout = timeout

    def _build_command(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
    ) -> list[str]:
        """Build CLI command based on provider type.

        Args:
            system_prompt: System context for the model
            user_prompt: User message to respond to
            model: Optional model override

        Returns:
            List of command arguments for subprocess
        """
        if self.cli_name == "claude":
            # Claude CLI: claude --print --system-prompt <prompt> --model <model> "<user>"
            cmd = ["claude", "--print", "--system-prompt", system_prompt]
            if model:
                cmd.extend(["--model", model])
            cmd.append(user_prompt)
            return cmd

        elif self.cli_name == "codex":
            # Codex CLI: codex exec --model <model> "<combined_prompt>"
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            cmd = ["codex", "exec"]
            if model:
                cmd.extend(["--model", model])
            cmd.append(combined_prompt)
            return cmd

        else:  # gemini
            # Gemini CLI: gemini --model <model> "<combined_prompt>"
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            cmd = ["gemini"]
            if model:
                cmd.extend(["--model", model])
            cmd.append(combined_prompt)
            return cmd

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> ProviderResponse:
        """Generate completion using CLI.

        Executes the CLI command and parses the response.

        Args:
            system_prompt: System context for the model
            user_prompt: User message to respond to
            model: Optional model override

        Returns:
            ProviderResponse with generated content

        Raises:
            CliProviderError: If CLI execution fails, times out, or returns empty
        """
        cmd = self._build_command(system_prompt, user_prompt, model)

        # Execute CLI command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
        except TimeoutError:
            # Kill the hanging process and clean up
            process.kill()
            await process.wait()
            raise CliProviderError(
                f"CLI {self.cli_name} timed out after {self.timeout} seconds"
            ) from None

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            raise CliProviderError(f"CLI {self.cli_name} failed: {error_msg}")

        content = stdout.decode("utf-8", errors="replace").strip()

        # Guard against empty responses
        if not content:
            raise CliProviderError(f"CLI {self.cli_name} returned empty response")

        # Use provided model or fall back to CLI name
        effective_model = model if model else self.cli_name

        return ProviderResponse(
            content=content,
            model=effective_model,
            token_input=None,  # CLI doesn't provide token counts
            token_output=None,
        )


__all__ = ["CliProvider", "CliProviderError", "DEFAULT_TIMEOUT_SECONDS"]
