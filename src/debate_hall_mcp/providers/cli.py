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
        default_model: Default model to use (can be overridden per-call)
        cli_args: Additional CLI arguments to pass
    """

    def __init__(
        self,
        cli_name: str,
        role: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        model: str | None = None,
        cli_args: dict[str, str | bool | int] | None = None,
    ) -> None:
        """Initialize CliProvider.

        Args:
            cli_name: CLI to use (claude, codex, gemini)
            role: Optional role name for system prompt
            timeout: Timeout in seconds for CLI execution (default: 120s)
            model: Default model to use for this provider
            cli_args: Additional CLI arguments (e.g., {'temperature': 0.7})

        Raises:
            ValueError: If cli_name is not a supported CLI
        """
        if cli_name not in CLI_NAMES:
            raise ValueError(f"Unsupported CLI: {cli_name}. Supported: {CLI_NAMES}")
        self.cli_name = cli_name
        self.role = role
        self.timeout = timeout
        self.default_model = model
        self.cli_args = cli_args or {}

    def _build_cli_args(self) -> list[str]:
        """Build additional CLI arguments from cli_args dict.

        Converts the cli_args dictionary into command line arguments:
        - Boolean True: --flag
        - Boolean False: omitted
        - String/int values: --key value

        Returns:
            List of CLI argument strings
        """
        args: list[str] = []
        for key, value in self.cli_args.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            else:
                args.extend([f"--{key}", str(value)])
        return args

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
        # Use provided model, or fall back to default_model, or None
        effective_model = model if model else self.default_model
        extra_args = self._build_cli_args()

        if self.cli_name == "claude":
            # Claude CLI: claude --print --system-prompt <prompt> --model <model> "<user>"
            cmd = ["claude", "--print", "--system-prompt", system_prompt]
            if effective_model:
                cmd.extend(["--model", effective_model])
            cmd.extend(extra_args)
            cmd.append(user_prompt)
            return cmd

        elif self.cli_name == "codex":
            # Codex CLI: codex exec --model <model> "<combined_prompt>"
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            cmd = ["codex", "exec"]
            if effective_model:
                cmd.extend(["--model", effective_model])
            cmd.extend(extra_args)
            cmd.append(combined_prompt)
            return cmd

        else:  # gemini
            # Gemini CLI: gemini --model <model> "<combined_prompt>"
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            cmd = ["gemini"]
            if effective_model:
                cmd.extend(["--model", effective_model])
            cmd.extend(extra_args)
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
