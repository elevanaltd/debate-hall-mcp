"""Command-line interface for debate-hall-mcp.

This module provides CLI commands for managing debate-hall-mcp agents:
- sync: Sync agents from upstream repository
- verify: Verify agent hashes match lockfile
- pin: Pin agents to specific git ref

Usage:
    debate-hall-mcp sync
    debate-hall-mcp verify
    debate-hall-mcp pin <ref>
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

# CLI version - matches package version
CLI_VERSION = "0.1.0"


def _create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser with all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="debate-hall-mcp",
        description="Manage debate-hall-mcp agents for Wind/Wall/Door debates.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {CLI_VERSION}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
    )

    # sync command
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync agents from upstream repository",
        description="Sync Wind/Wall/Door agents from the upstream repository.",
    )
    sync_parser.set_defaults(func=_cmd_sync)

    # verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify agent hashes match lockfile",
        description="Verify that local agent files match the hashes in the lockfile.",
    )
    verify_parser.set_defaults(func=_cmd_verify)

    # pin command
    pin_parser = subparsers.add_parser(
        "pin",
        help="Pin agents to specific git ref",
        description="Pin agents to a specific git ref (tag, branch, or commit).",
    )
    pin_parser.add_argument(
        "ref",
        help="Git ref to pin agents to (e.g., v1.0.0, main, abc1234)",
    )
    pin_parser.set_defaults(func=_cmd_pin)

    return parser


def _cmd_sync(_args: argparse.Namespace) -> int:
    """Execute sync command.

    Args:
        _args: Parsed command-line arguments (unused in stub).

    Returns:
        Exit code (1 for stub/not implemented).
    """
    print("sync: Not implemented yet")
    return 1


def _cmd_verify(_args: argparse.Namespace) -> int:
    """Execute verify command.

    Args:
        _args: Parsed command-line arguments (unused in stub).

    Returns:
        Exit code (1 for stub/not implemented).
    """
    print("verify: Not implemented yet")
    return 1


def _cmd_pin(args: argparse.Namespace) -> int:
    """Execute pin command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (1 for stub/not implemented).
    """
    print(f"pin: Not implemented yet (ref: {args.ref})")
    return 1


def main() -> int:
    """Entry point for debate-hall-mcp CLI.

    Parses command-line arguments and dispatches to the appropriate handler.

    Returns:
        Exit code from the executed command.
    """
    parser = _create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    # Type assertion: func is set by subparser defaults to command handlers
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
