"""Unit tests for debate_hall_mcp.cli module.

Tests cover:
- CLI entry point (main function) is callable
- Help output works
- Subcommands are recognized (sync, verify, pin)
- Unknown commands show error
- Pin command accepts ref argument

TDD RED Phase: These tests were written BEFORE implementation.
"""

import subprocess
import sys


class TestCLIEntryPoint:
    """Test CLI entry point exists and is callable."""

    def test_main_is_callable(self) -> None:
        """main() function exists and is callable."""
        from debate_hall_mcp.cli import main

        assert callable(main)

    def test_main_function_has_docstring(self) -> None:
        """main() has a docstring for documentation."""
        from debate_hall_mcp.cli import main

        assert main.__doc__ is not None
        assert len(main.__doc__) > 0


class TestCLIHelpOutput:
    """Test --help flag works correctly."""

    def test_help_flag_shows_usage(self) -> None:
        """--help shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "debate-hall-mcp" in result.stdout.lower()

    def test_help_shows_available_commands(self) -> None:
        """--help shows available subcommands."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # All three subcommands should be listed
        assert "sync" in result.stdout.lower()
        assert "verify" in result.stdout.lower()
        assert "pin" in result.stdout.lower()


class TestSyncCommand:
    """Test sync subcommand."""

    def test_sync_command_recognized(self) -> None:
        """sync command is recognized and runs without error."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "sync"],
            capture_output=True,
            text=True,
        )
        # Command should be recognized (not return error for unknown command)
        # May return non-zero for "not implemented" but should not fail with
        # "unrecognized arguments" or similar
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_sync_stub_returns_nonzero(self) -> None:
        """sync stub returns non-zero exit code to signal not implemented."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "sync"],
            capture_output=True,
            text=True,
        )
        # Stub commands MUST return non-zero to signal failure to automation/CI
        assert result.returncode != 0, "Stub commands must return non-zero exit code"
        assert "not implemented" in result.stdout.lower()

    def test_sync_help_available(self) -> None:
        """sync --help shows help for sync command."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "sync", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "sync" in result.stdout.lower()


class TestVerifyCommand:
    """Test verify subcommand."""

    def test_verify_command_recognized(self) -> None:
        """verify command is recognized and runs without error."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "verify"],
            capture_output=True,
            text=True,
        )
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_verify_stub_returns_nonzero(self) -> None:
        """verify stub returns non-zero exit code to signal not implemented."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "verify"],
            capture_output=True,
            text=True,
        )
        # Stub commands MUST return non-zero to signal failure to automation/CI
        assert result.returncode != 0, "Stub commands must return non-zero exit code"
        assert "not implemented" in result.stdout.lower()

    def test_verify_help_available(self) -> None:
        """verify --help shows help for verify command."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "verify", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "verify" in result.stdout.lower()


class TestPinCommand:
    """Test pin subcommand."""

    def test_pin_command_recognized(self) -> None:
        """pin command is recognized."""
        # Pin requires a ref argument
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin", "v1.0.0"],
            capture_output=True,
            text=True,
        )
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_pin_stub_returns_nonzero(self) -> None:
        """pin stub returns non-zero exit code to signal not implemented."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin", "v1.0.0"],
            capture_output=True,
            text=True,
        )
        # Stub commands MUST return non-zero to signal failure to automation/CI
        assert result.returncode != 0, "Stub commands must return non-zero exit code"
        assert "not implemented" in result.stdout.lower()

    def test_pin_requires_ref_argument(self) -> None:
        """pin command requires a ref argument."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin"],
            capture_output=True,
            text=True,
        )
        # Should fail with error about missing argument
        assert result.returncode != 0
        # Should mention the required argument
        assert "ref" in result.stderr.lower() or "argument" in result.stderr.lower()

    def test_pin_help_available(self) -> None:
        """pin --help shows help for pin command."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "pin" in result.stdout.lower()
        assert "ref" in result.stdout.lower()


class TestUnknownCommands:
    """Test error handling for unknown commands."""

    def test_unknown_command_shows_error(self) -> None:
        """Unknown command shows appropriate error."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "unknown_command"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        # Should indicate invalid choice or similar
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_no_command_shows_help_or_usage(self) -> None:
        """Running without command shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli"],
            capture_output=True,
            text=True,
        )
        # Should either show help or indicate a command is required
        combined_output = result.stdout.lower() + result.stderr.lower()
        assert (
            "usage" in combined_output or "command" in combined_output or "help" in combined_output
        )


class TestCLIModuleStructure:
    """Test CLI module structure and conventions."""

    def test_cli_module_has_version(self) -> None:
        """CLI module exposes version information."""
        from debate_hall_mcp.cli import CLI_VERSION

        assert CLI_VERSION is not None
        assert len(CLI_VERSION) > 0

    def test_cli_can_run_as_module(self) -> None:
        """CLI can be run as python -m debate_hall_mcp.cli."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "--help"],
            capture_output=True,
            text=True,
        )
        # Should not fail with module not found error
        assert "No module named" not in result.stderr
        assert result.returncode == 0
