"""Command-line interface for debate-hall-mcp.

This module provides CLI commands for managing debate-hall-mcp agents:
- sync: Sync agents from package to project's .github/agents/
- verify: Verify agent hashes match lockfile
- pin: Pin agents to specific git ref

Usage:
    debate-hall-mcp sync [--force]
    debate-hall-mcp verify
    debate-hall-mcp pin <ref>

Lockfile Schema (agents.lock.json):
    {
        "version": "1.0",
        "source": {
            "repo": "elevanaltd/debate-hall-mcp",
            "ref": "v0.1.0"
        },
        "agents": {
            "wind": {"file": ".github/agents/wind.agent.md", "sha256": "..."},
            "wall": {"file": ".github/agents/wall.agent.md", "sha256": "..."},
            "door": {"file": ".github/agents/door.agent.md", "sha256": "..."}
        }
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections.abc import Callable
from importlib.resources import as_file, files
from pathlib import Path

# CLI version - matches package version
CLI_VERSION = "0.1.0"

# Default values for lockfile
DEFAULT_REPO = "elevanaltd/debate-hall-mcp"
DEFAULT_REF = "v0.1.0"
LOCKFILE_VERSION = "1.0"
LOCKFILE_NAME = "agents.lock.json"

# Agent names to sync
AGENT_NAMES = ["wind", "wall", "door"]


def _get_package_agents_dir() -> Path:
    """Get the path to agent files bundled with this package.

    Uses importlib.resources to access agents bundled in the package,
    which works correctly after pip install (not just in development).

    Returns:
        Path to the agents directory within the installed package.
    """
    # Use importlib.resources to get the path to the agents subpackage
    # This works both in development (editable install) and after pip install
    agents_pkg = files("debate_hall_mcp.agents")

    # For filesystem-based packages (the typical case), we can get a direct path.
    # The as_file context manager extracts to a temp dir for zip-based packages,
    # but returns the actual path for filesystem packages.
    with as_file(agents_pkg) as agents_path:
        # Return a copy of the path that persists outside the context manager.
        # For filesystem packages, this is the actual package directory.
        # For zip packages, this will be a temporary extraction that may not
        # persist, but sync_agents copies the files immediately so this is OK.
        return Path(agents_path)


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal string of the SHA256 hash.
    """
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def _load_lockfile(project_dir: Path) -> dict[str, object] | None:
    """Load and parse the lockfile from project directory.

    Args:
        project_dir: Path to the project root.

    Returns:
        Parsed lockfile as dict, or None if not found/invalid.
    """
    lockfile_path = project_dir / LOCKFILE_NAME
    if not lockfile_path.exists():
        return None

    try:
        content = lockfile_path.read_text()
        return json.loads(content)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


def _save_lockfile(project_dir: Path, data: dict[str, object]) -> None:
    """Save lockfile to project directory.

    Args:
        project_dir: Path to the project root.
        data: Lockfile data to save.
    """
    lockfile_path = project_dir / LOCKFILE_NAME
    content = json.dumps(data, indent=2)
    try:
        lockfile_path.write_text(content + "\n")
    except OSError as e:
        print(f"Error: Failed to write lockfile {lockfile_path}: {e}")


def sync_agents(project_dir: Path, force: bool = False) -> int:
    """Sync agents from package to project's .github/agents/ directory.

    Creates the agents directory if it doesn't exist, copies agent files
    from the package, and creates/updates the lockfile with SHA256 hashes.

    Args:
        project_dir: Path to the project root where agents should be synced.
        force: If True, overwrite existing files even if they differ.

    Returns:
        0 on success, 1 on failure.
    """
    source_agents_dir = _get_package_agents_dir()

    # Verify source agents exist
    if not source_agents_dir.exists():
        print(f"Error: Source agents directory not found: {source_agents_dir}")
        return 1

    # Create target directory
    target_agents_dir = project_dir / ".github" / "agents"
    try:
        target_agents_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create directory {target_agents_dir}: {e}")
        return 1

    # Prepare lockfile data
    lockfile_data: dict[str, object] = {
        "version": LOCKFILE_VERSION,
        "source": {
            "repo": DEFAULT_REPO,
            "ref": DEFAULT_REF,
        },
        "agents": {},
    }

    # Copy each agent and compute hash
    synced_agents: list[str] = []
    skipped_agents: list[str] = []
    agents_dict: dict[str, dict[str, str]] = {}

    for agent_name in AGENT_NAMES:
        source_file = source_agents_dir / f"{agent_name}.agent.md"
        target_file = target_agents_dir / f"{agent_name}.agent.md"

        if not source_file.exists():
            print(f"Warning: Source agent file not found: {source_file}")
            continue

        should_copy = True

        # Check for existing file and potential conflict
        if target_file.exists():
            try:
                is_different = False
                # Optimization: Check size first
                if source_file.stat().st_size != target_file.stat().st_size:
                    is_different = True
                else:
                    # If sizes match, check hashes
                    src_hash = _compute_sha256(source_file)
                    tgt_hash = _compute_sha256(target_file)
                    if src_hash != tgt_hash:
                        is_different = True

                if is_different:
                    if not force:
                        print(
                            f"SKIP: {agent_name} - Local file differs from package. Use --force to overwrite."
                        )
                        skipped_agents.append(agent_name)
                        should_copy = False
                    else:
                        print(
                            f"OVERWRITE: {agent_name} - Local file differs, overwriting due to --force."
                        )
            except OSError as e:
                print(f"Error checking file {agent_name}: {e}")
                continue

        if should_copy:
            try:
                shutil.copy2(source_file, target_file)
                synced_agents.append(agent_name)
            except OSError as e:
                print(f"Error: Failed to copy {agent_name}: {e}")
                continue

        # Always calculate hash of the target file (whether copied or preserved)
        # so the lockfile matches what is actually on disk.
        try:
            if target_file.exists():
                file_hash = _compute_sha256(target_file)
                agents_dict[agent_name] = {
                    "file": f".github/agents/{agent_name}.agent.md",
                    "sha256": file_hash,
                }
        except OSError as e:
            print(f"Error hashing {agent_name}: {e}")

    lockfile_data["agents"] = agents_dict

    # Save lockfile
    _save_lockfile(project_dir, lockfile_data)

    # Print summary
    if synced_agents:
        print("Synced agents:")
        for agent_name in synced_agents:
            if agent_name in agents_dict:
                agent_info = agents_dict[agent_name]
                print(f"  - {agent_name}: {agent_info['file']}")
                print(f"    sha256: {agent_info['sha256'][:16]}...")

    if skipped_agents:
        print(f"\nSkipped {len(skipped_agents)} agent(s) (use --force to overwrite).")

    print(f"\nLockfile created: {LOCKFILE_NAME}")
    return 0


def verify_agents(project_dir: Path) -> int:
    """Verify that local agent files match the hashes in the lockfile.

    Args:
        project_dir: Path to the project root.

    Returns:
        0 if all hashes match, 1 if drift detected or error.
    """
    # Load lockfile
    lockfile_data = _load_lockfile(project_dir)
    if lockfile_data is None:
        print(f"Error: No {LOCKFILE_NAME} found in {project_dir}")
        return 1

    agents_data = lockfile_data.get("agents", {})
    if not isinstance(agents_data, dict):
        print("Error: Invalid lockfile format - 'agents' must be an object")
        return 1

    # Verify each agent
    all_ok = True
    drift_agents: list[str] = []

    for agent_name, agent_info in agents_data.items():
        if not isinstance(agent_info, dict):
            print(f"Error: Invalid agent entry for {agent_name}")
            all_ok = False
            continue

        file_path_str = agent_info.get("file", "")
        expected_hash = agent_info.get("sha256", "")

        if not file_path_str or not expected_hash:
            print(f"Error: Missing file or sha256 for agent {agent_name}")
            all_ok = False
            continue

        # Resolve file path relative to project dir
        try:
            agent_file = (project_dir / file_path_str).resolve()
        except OSError as e:
            print(f"Error: Invalid path {file_path_str}: {e}")
            all_ok = False
            continue

        # Security check: Path traversal
        # Ensure the resolved agent file path is within the resolved project directory
        if not agent_file.is_relative_to(project_dir.resolve()):
            print(f"SECURITY ERROR: Path traversal detected: {file_path_str}")
            print(f"  Resolved to: {agent_file}")
            print("  Agent file must be within project directory.")
            return 1

        if not agent_file.exists():
            print(f"MISSING: {agent_name} - file not found: {file_path_str}")
            all_ok = False
            drift_agents.append(agent_name)
            continue

        # Compute actual hash
        try:
            actual_hash = _compute_sha256(agent_file)
        except OSError as e:
            print(f"Error reading {agent_name}: {e}")
            all_ok = False
            continue

        if actual_hash == expected_hash:
            print(f"OK: {agent_name}")
        else:
            print(f"DRIFT: {agent_name}")
            print(f"  expected: {expected_hash[:16]}...")
            print(f"  actual:   {actual_hash[:16]}...")
            all_ok = False
            drift_agents.append(agent_name)

    # Summary
    if all_ok:
        print("\nAll agents match lockfile.")
        return 0
    else:
        print(f"\nDrift detected in {len(drift_agents)} agent(s): {', '.join(drift_agents)}")
        print("Run 'debate-hall-mcp sync' to reset agents from package.")
        return 1


def pin_agents(project_dir: Path, ref: str) -> int:
    """Pin agents to a specific git ref in the lockfile.

    Updates the ref in the lockfile's source section. Does not fetch
    or update agent files (that's future work).

    Args:
        project_dir: Path to the project root.
        ref: Git ref to pin (tag, branch, or commit SHA).

    Returns:
        0 on success, 1 on failure.
    """
    # Validation
    if not ref or not ref.strip():
        print("Error: Ref cannot be empty.")
        return 1

    # Regex validation for git ref safety
    # Disallow control chars, spaces, tilde, caret, colon, question mark, asterisk, open bracket
    # Disallow starts/ends with slash, consecutive slashes, dot-sequences, @{, \
    # Disallow components ending with .lock
    # Disallow consecutive slashes, starting with slash, ending with dot, starting with dot
    ref_pattern = re.compile(
        r"^(?!@$|^\.|.*/\.|.*\.\.|.*@{|.*/$|.*\.lock(/|$)|^/|.*//|.*\.$)(?!.*[\\ \00-\037\177 ~^:?*[\]]).+$"
    )
    if not ref_pattern.match(ref):
        print(f"Error: Invalid git ref format: '{ref}'")
        return 1

    # Load existing lockfile
    lockfile_data = _load_lockfile(project_dir)
    if lockfile_data is None:
        print(f"Error: No {LOCKFILE_NAME} found in {project_dir}")
        print("Run 'debate-hall-mcp sync' first to create a lockfile.")
        return 1

    # Update the ref
    source = lockfile_data.get("source", {})
    if not isinstance(source, dict):
        print("Error: Invalid lockfile format - 'source' must be an object")
        return 1

    old_ref = source.get("ref", "unknown")
    source["ref"] = ref
    lockfile_data["source"] = source

    # Save updated lockfile
    _save_lockfile(project_dir, lockfile_data)

    print(f"Pinned agents to ref: {ref}")
    print(f"  Previous ref: {old_ref}")
    print(f"  Updated: {LOCKFILE_NAME}")
    print("\nNote: This updates the lockfile metadata only.")
    print("To fetch agents from a specific version, manually update the agent files")
    print("and run 'debate-hall-mcp sync' to update hashes.")

    return 0


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
        help="Sync agents from package to .github/agents/",
        description="Sync Wind/Wall/Door agents from the package to your project.",
    )
    sync_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite of local agent files even if they have been modified.",
    )
    sync_parser.set_defaults(func=_cmd_sync)

    # verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify agent hashes match lockfile",
        description="Verify that local agent files match the hashes in agents.lock.json.",
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


def _cmd_sync(args: argparse.Namespace) -> int:
    """Execute sync command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code from sync_agents.
    """
    project_dir = Path.cwd()
    return sync_agents(project_dir, force=args.force)


def _cmd_verify(_args: argparse.Namespace) -> int:
    """Execute verify command.

    Args:
        _args: Parsed command-line arguments.

    Returns:
        Exit code from verify_agents.
    """
    project_dir = Path.cwd()
    return verify_agents(project_dir)


def _cmd_pin(args: argparse.Namespace) -> int:
    """Execute pin command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code from pin_agents.
    """
    project_dir = Path.cwd()
    return pin_agents(project_dir, args.ref)


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
