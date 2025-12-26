"""Unit tests for debate_hall_mcp.cli module.

Tests cover:
- CLI entry point (main function) is callable
- Help output works
- Subcommands are recognized (sync, verify, pin)
- Unknown commands show error
- Pin command accepts ref argument
- sync: copies agents to .github/agents/, creates lockfile with hashes
- verify: compares local file hashes against lockfile
- pin: updates lockfile with specified ref

TDD RED Phase: These tests define expected behavior BEFORE implementation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory with no lockfile."""
    yield tmp_path


@pytest.fixture
def temp_project_with_agents(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory with agent files already present."""
    agents_dir = tmp_path / ".github" / "agents"
    agents_dir.mkdir(parents=True)

    # Create sample agent files
    (agents_dir / "wind.agent.md").write_text("# Wind Agent\nTest content for wind")
    (agents_dir / "wall.agent.md").write_text("# Wall Agent\nTest content for wall")
    (agents_dir / "door.agent.md").write_text("# Door Agent\nTest content for door")

    yield tmp_path


@pytest.fixture
def temp_project_with_lockfile(temp_project_with_agents: Path) -> Generator[Path, None, None]:
    """Create a project with agents and a valid lockfile."""
    agents_dir = temp_project_with_agents / ".github" / "agents"

    # Compute hashes for the test agent files
    lockfile_data = {
        "version": "1.0",
        "source": {
            "repo": "elevanaltd/debate-hall-mcp",
            "ref": "v0.1.0",
        },
        "agents": {},
    }

    for agent_name in ["wind", "wall", "door"]:
        file_path = agents_dir / f"{agent_name}.agent.md"
        content = file_path.read_bytes()
        sha256 = hashlib.sha256(content).hexdigest()
        lockfile_data["agents"][agent_name] = {
            "file": f".github/agents/{agent_name}.agent.md",
            "sha256": sha256,
        }

    lockfile_path = temp_project_with_agents / "agents.lock.json"
    lockfile_path.write_text(json.dumps(lockfile_data, indent=2))

    yield temp_project_with_agents


@pytest.fixture
def temp_project_with_drifted_agents(
    temp_project_with_lockfile: Path,
) -> Generator[Path, None, None]:
    """Create a project where agent files have drifted from lockfile hashes."""
    # Modify one agent file to cause drift
    agents_dir = temp_project_with_lockfile / ".github" / "agents"
    wind_file = agents_dir / "wind.agent.md"
    wind_file.write_text("# Wind Agent\nMODIFIED content that differs from lockfile hash")

    yield temp_project_with_lockfile


# =============================================================================
# Test CLI Entry Point
# =============================================================================


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


# =============================================================================
# Test Sync Command - Real Implementation
# =============================================================================


class TestSyncCommand:
    """Test sync subcommand creates agents and lockfile."""

    def test_sync_command_recognized(self) -> None:
        """sync command is recognized and runs without error."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "sync"],
            capture_output=True,
            text=True,
        )
        # Command should be recognized (not return error for unknown command)
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_sync_help_available(self) -> None:
        """sync --help shows help for sync command."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "sync", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "sync" in result.stdout.lower()

    def test_sync_creates_agents_directory(self, temp_project_dir: Path) -> None:
        """sync creates .github/agents/ directory if it doesn't exist."""
        from debate_hall_mcp.cli import sync_agents

        result = sync_agents(temp_project_dir)

        assert result == 0
        agents_dir = temp_project_dir / ".github" / "agents"
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_sync_creates_agent_files(self, temp_project_dir: Path) -> None:
        """sync creates wind.agent.md, wall.agent.md, door.agent.md files."""
        from debate_hall_mcp.cli import sync_agents

        result = sync_agents(temp_project_dir)

        assert result == 0
        agents_dir = temp_project_dir / ".github" / "agents"
        assert (agents_dir / "wind.agent.md").exists()
        assert (agents_dir / "wall.agent.md").exists()
        assert (agents_dir / "door.agent.md").exists()

    def test_sync_creates_lockfile(self, temp_project_dir: Path) -> None:
        """sync creates agents.lock.json in project root."""
        from debate_hall_mcp.cli import sync_agents

        result = sync_agents(temp_project_dir)

        assert result == 0
        lockfile = temp_project_dir / "agents.lock.json"
        assert lockfile.exists()

    def test_sync_lockfile_has_valid_schema(self, temp_project_dir: Path) -> None:
        """sync creates lockfile with correct schema structure."""
        from debate_hall_mcp.cli import sync_agents

        sync_agents(temp_project_dir)

        lockfile = temp_project_dir / "agents.lock.json"
        data = json.loads(lockfile.read_text())

        # Check top-level keys
        assert "version" in data
        assert "source" in data
        assert "agents" in data

        # Check source structure
        assert "repo" in data["source"]
        assert "ref" in data["source"]

        # Check agents structure
        for agent_name in ["wind", "wall", "door"]:
            assert agent_name in data["agents"]
            assert "file" in data["agents"][agent_name]
            assert "sha256" in data["agents"][agent_name]

    def test_sync_lockfile_has_correct_hashes(self, temp_project_dir: Path) -> None:
        """sync lockfile contains SHA256 hashes matching actual file content."""
        from debate_hall_mcp.cli import sync_agents

        sync_agents(temp_project_dir)

        lockfile = temp_project_dir / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        agents_dir = temp_project_dir / ".github" / "agents"

        for agent_name in ["wind", "wall", "door"]:
            agent_file = agents_dir / f"{agent_name}.agent.md"
            content = agent_file.read_bytes()
            expected_hash = hashlib.sha256(content).hexdigest()
            actual_hash = data["agents"][agent_name]["sha256"]
            assert actual_hash == expected_hash, f"Hash mismatch for {agent_name}"

    def test_sync_returns_zero_on_success(self, temp_project_dir: Path) -> None:
        """sync returns 0 exit code on success."""
        from debate_hall_mcp.cli import sync_agents

        result = sync_agents(temp_project_dir)
        assert result == 0

    def test_sync_prints_synced_agents(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """sync prints what was synced."""
        from debate_hall_mcp.cli import sync_agents

        sync_agents(temp_project_dir)

        captured = capsys.readouterr()
        assert "wind" in captured.out.lower()
        assert "wall" in captured.out.lower()
        assert "door" in captured.out.lower()

    def test_sync_skips_modified_files_without_force(
        self, temp_project_with_agents: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """sync skips files that differ from package without --force."""
        from debate_hall_mcp.cli import sync_agents

        # Modify a file locally
        wind_file = temp_project_with_agents / ".github" / "agents" / "wind.agent.md"
        wind_file.write_text("Modified content")

        # Run sync without force
        result = sync_agents(temp_project_with_agents, force=False)

        assert result == 0

        # Check output
        captured = capsys.readouterr()
        assert "SKIP: wind" in captured.out

        # Check content is preserved
        assert wind_file.read_text() == "Modified content"

    def test_sync_overwrites_with_force(
        self, temp_project_with_agents: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """sync overwrites files with --force."""
        from debate_hall_mcp.cli import sync_agents

        # Modify a file locally
        wind_file = temp_project_with_agents / ".github" / "agents" / "wind.agent.md"
        wind_file.write_text("Modified content")

        # Run sync WITH force
        result = sync_agents(temp_project_with_agents, force=True)

        assert result == 0

        # Check output
        captured = capsys.readouterr()
        assert "OVERWRITE: wind" in captured.out

        # Check content is reverted (it should differ from "Modified content")
        assert wind_file.read_text() != "Modified content"


# =============================================================================
# Test Verify Command - Real Implementation
# =============================================================================


class TestVerifyCommand:
    """Test verify subcommand checks agent hashes against lockfile."""

    def test_verify_command_recognized(self) -> None:
        """verify command is recognized and runs without error."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "verify"],
            capture_output=True,
            text=True,
        )
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_verify_help_available(self) -> None:
        """verify --help shows help for verify command."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "verify", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "verify" in result.stdout.lower()

    def test_verify_returns_zero_when_hashes_match(self, temp_project_with_lockfile: Path) -> None:
        """verify returns 0 when all agent hashes match lockfile."""
        from debate_hall_mcp.cli import verify_agents

        result = verify_agents(temp_project_with_lockfile)
        assert result == 0

    def test_verify_returns_one_when_drift_detected(
        self, temp_project_with_drifted_agents: Path
    ) -> None:
        """verify returns 1 when agent hash doesn't match lockfile."""
        from debate_hall_mcp.cli import verify_agents

        result = verify_agents(temp_project_with_drifted_agents)
        assert result == 1

    def test_verify_prints_drift_details(
        self,
        temp_project_with_drifted_agents: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """verify prints which agent has drifted."""
        from debate_hall_mcp.cli import verify_agents

        verify_agents(temp_project_with_drifted_agents)

        captured = capsys.readouterr()
        # Should mention the drifted agent
        assert "wind" in captured.out.lower() or "drift" in captured.out.lower()

    def test_verify_returns_one_when_no_lockfile(self, temp_project_dir: Path) -> None:
        """verify returns 1 when no lockfile exists."""
        from debate_hall_mcp.cli import verify_agents

        result = verify_agents(temp_project_dir)
        assert result == 1

    def test_verify_prints_success_message(
        self,
        temp_project_with_lockfile: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """verify prints success message when all hashes match."""
        from debate_hall_mcp.cli import verify_agents

        verify_agents(temp_project_with_lockfile)

        captured = capsys.readouterr()
        # Should indicate success
        assert "ok" in captured.out.lower() or "match" in captured.out.lower()

    def test_verify_returns_one_when_agent_file_missing(
        self, temp_project_with_lockfile: Path
    ) -> None:
        """verify returns 1 when an agent file in lockfile is missing."""
        from debate_hall_mcp.cli import verify_agents

        # Remove one agent file
        agents_dir = temp_project_with_lockfile / ".github" / "agents"
        (agents_dir / "wind.agent.md").unlink()

        result = verify_agents(temp_project_with_lockfile)
        assert result == 1

    def test_verify_detects_path_traversal(
        self, temp_project_with_lockfile: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """verify detects and blocks path traversal in lockfile."""
        from debate_hall_mcp.cli import verify_agents

        # Create a malicious lockfile entry
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())

        # Point to a file outside project root (using ..)
        data["agents"]["wind"]["file"] = "../outside.txt"
        lockfile.write_text(json.dumps(data))

        # Run verify
        result = verify_agents(temp_project_with_lockfile)

        assert result == 1
        captured = capsys.readouterr()
        assert "SECURITY ERROR" in captured.out
        assert "Path traversal detected" in captured.out


# =============================================================================
# Test Pin Command - Real Implementation
# =============================================================================


class TestPinCommand:
    """Test pin subcommand updates lockfile with specified ref."""

    def test_pin_command_recognized(self) -> None:
        """pin command is recognized."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin", "v1.0.0"],
            capture_output=True,
            text=True,
        )
        assert "unrecognized" not in result.stderr.lower()
        assert "invalid choice" not in result.stderr.lower()

    def test_pin_requires_ref_argument(self) -> None:
        """pin command requires a ref argument."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli", "pin"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
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

    def test_pin_updates_lockfile_ref(self, temp_project_with_lockfile: Path) -> None:
        """pin updates the ref in existing lockfile."""
        from debate_hall_mcp.cli import pin_agents

        result = pin_agents(temp_project_with_lockfile, "v2.0.0")

        assert result == 0
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        assert data["source"]["ref"] == "v2.0.0"

    def test_pin_preserves_agent_entries(self, temp_project_with_lockfile: Path) -> None:
        """pin preserves existing agent entries in lockfile."""
        from debate_hall_mcp.cli import pin_agents

        # Get original agents data
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        original_data = json.loads(lockfile.read_text())
        original_agents = original_data["agents"]

        pin_agents(temp_project_with_lockfile, "v2.0.0")

        data = json.loads(lockfile.read_text())
        assert data["agents"] == original_agents

    def test_pin_returns_zero_on_success(self, temp_project_with_lockfile: Path) -> None:
        """pin returns 0 exit code on success."""
        from debate_hall_mcp.cli import pin_agents

        result = pin_agents(temp_project_with_lockfile, "v2.0.0")
        assert result == 0

    def test_pin_returns_one_when_no_lockfile(self, temp_project_dir: Path) -> None:
        """pin returns 1 when no lockfile exists."""
        from debate_hall_mcp.cli import pin_agents

        result = pin_agents(temp_project_dir, "v2.0.0")
        assert result == 1

    def test_pin_prints_confirmation(
        self,
        temp_project_with_lockfile: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """pin prints confirmation of the new ref."""
        from debate_hall_mcp.cli import pin_agents

        pin_agents(temp_project_with_lockfile, "v2.0.0")

        captured = capsys.readouterr()
        assert "v2.0.0" in captured.out

    def test_pin_accepts_git_sha(self, temp_project_with_lockfile: Path) -> None:
        """pin accepts a git SHA as ref."""
        from debate_hall_mcp.cli import pin_agents

        sha = "abc1234567890"
        result = pin_agents(temp_project_with_lockfile, sha)

        assert result == 0
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        assert data["source"]["ref"] == sha

    def test_pin_rejects_invalid_ref(self, temp_project_with_lockfile: Path) -> None:
        """pin rejects invalid git refs."""
        from debate_hall_mcp.cli import pin_agents

        # Space
        result = pin_agents(temp_project_with_lockfile, "invalid ref")
        assert result == 1

        # Double dot
        result = pin_agents(temp_project_with_lockfile, "v1..2")
        assert result == 1

        # ASCII control char
        result = pin_agents(temp_project_with_lockfile, "v1\t2")
        assert result == 1

        # .lock ending
        result = pin_agents(temp_project_with_lockfile, "feature/branch.lock")
        assert result == 1

        # .lock component
        result = pin_agents(temp_project_with_lockfile, "feature/branch.lock/sub")
        assert result == 1

        # Consecutive slashes
        result = pin_agents(temp_project_with_lockfile, "feature//branch")
        assert result == 1

        # Start with slash
        result = pin_agents(temp_project_with_lockfile, "/feature/branch")
        assert result == 1

        # End with dot
        result = pin_agents(temp_project_with_lockfile, "feature/branch.")
        assert result == 1

        # Start with dot
        result = pin_agents(temp_project_with_lockfile, ".feature")
        assert result == 1

        # Component start with dot
        result = pin_agents(temp_project_with_lockfile, "feature/.branch")
        assert result == 1

        # Valid ref with dot in middle
        result = pin_agents(temp_project_with_lockfile, "v1.0.0")
        assert result == 0


# =============================================================================
# Test Unknown Commands
# =============================================================================


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
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_no_command_shows_help_or_usage(self) -> None:
        """Running without command shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "debate_hall_mcp.cli"],
            capture_output=True,
            text=True,
        )
        combined_output = result.stdout.lower() + result.stderr.lower()
        assert (
            "usage" in combined_output or "command" in combined_output or "help" in combined_output
        )


# =============================================================================
# Test CLI Module Structure
# =============================================================================


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
        assert "No module named" not in result.stderr
        assert result.returncode == 0


# =============================================================================
# Test Lockfile Schema
# =============================================================================


# =============================================================================
# Test Package Agent Resources (pip install compatibility)
# =============================================================================


class TestPackageAgentResources:
    """Test that agent files are accessible as package resources after pip install.

    This ensures the CLI works when installed via pip, not just in development.
    The agents must be bundled inside the package, not read from .github/.
    """

    def test_agents_subpackage_importable(self) -> None:
        """debate_hall_mcp.agents subpackage can be imported."""
        import debate_hall_mcp.agents

        assert debate_hall_mcp.agents is not None

    def test_agents_subpackage_has_init(self) -> None:
        """agents subpackage has __init__.py (is a proper package)."""
        from importlib.resources import files

        agents_pkg = files("debate_hall_mcp.agents")
        # Check that we can access it - if it's not a package this will fail
        assert agents_pkg is not None

    def test_wind_agent_accessible_via_importlib(self) -> None:
        """wind.agent.md is accessible via importlib.resources."""
        from importlib.resources import files

        agents_pkg = files("debate_hall_mcp.agents")
        wind_content = (agents_pkg / "wind.agent.md").read_text()

        assert "WIND" in wind_content or "Wind" in wind_content
        assert "PATHOS" in wind_content

    def test_wall_agent_accessible_via_importlib(self) -> None:
        """wall.agent.md is accessible via importlib.resources."""
        from importlib.resources import files

        agents_pkg = files("debate_hall_mcp.agents")
        wall_content = (agents_pkg / "wall.agent.md").read_text()

        assert "WALL" in wall_content or "Wall" in wall_content
        assert "ETHOS" in wall_content

    def test_door_agent_accessible_via_importlib(self) -> None:
        """door.agent.md is accessible via importlib.resources."""
        from importlib.resources import files

        agents_pkg = files("debate_hall_mcp.agents")
        door_content = (agents_pkg / "door.agent.md").read_text()

        assert "DOOR" in door_content or "Door" in door_content
        assert "LOGOS" in door_content

    def test_all_three_agents_present(self) -> None:
        """All three agent files (wind, wall, door) are present in package."""
        from importlib.resources import files

        agents_pkg = files("debate_hall_mcp.agents")
        expected_files = ["wind.agent.md", "wall.agent.md", "door.agent.md"]

        for filename in expected_files:
            resource = agents_pkg / filename
            # Attempting to read should not raise
            content = resource.read_text()
            assert len(content) > 0, f"{filename} is empty"

    def test_get_package_agents_dir_returns_valid_path(self) -> None:
        """_get_package_agents_dir returns path with agent files."""
        from debate_hall_mcp.cli import _get_package_agents_dir

        agents_dir = _get_package_agents_dir()

        # Path should exist
        assert agents_dir.exists(), f"Agents dir does not exist: {agents_dir}"

        # Should contain all three agents
        assert (agents_dir / "wind.agent.md").exists()
        assert (agents_dir / "wall.agent.md").exists()
        assert (agents_dir / "door.agent.md").exists()


class TestLockfileSchema:
    """Test agents.lock.json schema and structure."""

    def test_lockfile_version_is_string(self, temp_project_with_lockfile: Path) -> None:
        """Lockfile version field is a string."""
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        assert isinstance(data["version"], str)

    def test_lockfile_source_has_repo(self, temp_project_with_lockfile: Path) -> None:
        """Lockfile source contains repo field."""
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        assert "repo" in data["source"]
        assert isinstance(data["source"]["repo"], str)

    def test_lockfile_source_has_ref(self, temp_project_with_lockfile: Path) -> None:
        """Lockfile source contains ref field."""
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        assert "ref" in data["source"]
        assert isinstance(data["source"]["ref"], str)

    def test_lockfile_agents_have_file_paths(self, temp_project_with_lockfile: Path) -> None:
        """Each agent entry has a file path."""
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        for _agent_name, agent_data in data["agents"].items():
            assert "file" in agent_data
            assert agent_data["file"].endswith(".agent.md")

    def test_lockfile_agents_have_sha256(self, temp_project_with_lockfile: Path) -> None:
        """Each agent entry has a SHA256 hash."""
        lockfile = temp_project_with_lockfile / "agents.lock.json"
        data = json.loads(lockfile.read_text())
        for _agent_name, agent_data in data["agents"].items():
            assert "sha256" in agent_data
            # SHA256 is 64 hex characters
            assert len(agent_data["sha256"]) == 64
            assert all(c in "0123456789abcdef" for c in agent_data["sha256"])
