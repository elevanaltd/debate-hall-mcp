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


# =============================================================================
# Test Error Handling - Paying Down TDD Debt
# =============================================================================


class TestErrorHandling:
    """Tests for error branches - paying down TDD debt.

    These tests cover OSError handling paths that were added defensively
    after initial implementation, violating TDD principles. This class
    systematically tests each error branch to restore coverage.
    """

    # -------------------------------------------------------------------------
    # _save_lockfile OSError (line 119-122)
    # -------------------------------------------------------------------------

    def test_save_lockfile_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _save_lockfile handles OSError gracefully."""
        from debate_hall_mcp.cli import _save_lockfile

        # Mock Path.write_text to raise OSError
        def mock_write_text(_self: Path, _content: str) -> None:
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        # Call _save_lockfile - should print error but not raise
        _save_lockfile(tmp_path, {"version": "1.0", "agents": {}})

        captured = capsys.readouterr()
        assert "Error: Failed to write lockfile" in captured.out
        assert "Permission denied" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents mkdir OSError (line 147-151)
    # -------------------------------------------------------------------------

    def test_sync_mkdir_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents handles mkdir failure."""
        from debate_hall_mcp.cli import sync_agents

        original_mkdir = Path.mkdir

        def mock_mkdir(self: Path, *args: object, **kwargs: object) -> None:
            # Only fail for the target .github/agents directory
            if ".github" in str(self) and "agents" in str(self):
                raise OSError("Permission denied")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        result = sync_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Failed to create directory" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents file check OSError (line 203-205)
    # -------------------------------------------------------------------------

    def test_sync_file_check_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents handles file stat/hash check failure."""
        from debate_hall_mcp.cli import sync_agents

        # Create target directory with agent files that will fail on stat
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        wind_file = agents_dir / "wind.agent.md"
        wind_file.write_text("# Wind Agent")

        original_stat = Path.stat

        def mock_stat(self: Path) -> object:
            # Fail on the target wind file during comparison
            if "wind.agent.md" in str(self) and ".github" in str(self):
                raise OSError("I/O error")
            return original_stat(self)

        monkeypatch.setattr(Path, "stat", mock_stat)

        result = sync_agents(tmp_path, force=False)

        # Should continue despite error
        assert result == 0
        captured = capsys.readouterr()
        assert "Error checking file wind" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents shutil.copy2 OSError (line 211-213)
    # -------------------------------------------------------------------------

    def test_sync_copy_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents handles shutil.copy2 failure."""
        import shutil as shutil_module

        from debate_hall_mcp.cli import sync_agents

        original_copy2 = shutil_module.copy2

        def mock_copy2(src: object, dst: object) -> None:
            # Fail on wind agent copy
            if "wind.agent.md" in str(src):
                raise OSError("Disk full")
            return original_copy2(src, dst)

        monkeypatch.setattr(shutil_module, "copy2", mock_copy2)

        result = sync_agents(tmp_path)

        # Should continue with other agents
        assert result == 0
        captured = capsys.readouterr()
        assert "Error: Failed to copy wind" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents hash OSError (line 224-225)
    # -------------------------------------------------------------------------

    def test_sync_hash_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents handles hash computation failure after copy."""
        from debate_hall_mcp.cli import sync_agents

        # Track which files have been copied
        copied_files: list[str] = []

        original_read_bytes = Path.read_bytes

        def mock_read_bytes(self: Path) -> bytes:
            # If this is a target file (in .github/agents) and has been copied,
            # fail the hash computation
            if ".github" in str(self) and "wind.agent.md" in str(self) and "wind" in copied_files:
                raise OSError("File locked")
            return original_read_bytes(self)

        # Track copies
        import shutil as shutil_module

        original_copy2 = shutil_module.copy2

        def tracking_copy2(src: object, dst: object) -> object:
            if "wind.agent.md" in str(src):
                copied_files.append("wind")
            return original_copy2(src, dst)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)
        monkeypatch.setattr(shutil_module, "copy2", tracking_copy2)

        result = sync_agents(tmp_path)

        # Should continue despite hash error
        assert result == 0
        captured = capsys.readouterr()
        assert "Error hashing wind" in captured.out

    # -------------------------------------------------------------------------
    # verify_agents path resolve OSError (line 286-289)
    # -------------------------------------------------------------------------

    def test_verify_path_resolve_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test verify_agents handles path resolution failure."""
        from debate_hall_mcp.cli import verify_agents

        # Create a lockfile with valid structure
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {
                "wind": {
                    "file": ".github/agents/wind.agent.md",
                    "sha256": "a" * 64,
                }
            },
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        # Create the agent file
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "wind.agent.md").write_text("# Wind")

        original_resolve = Path.resolve

        def mock_resolve(self: Path) -> Path:
            # Fail on resolving paths containing .github/agents
            if ".github" in str(self) and "agents" in str(self):
                raise OSError("Cannot resolve path")
            return original_resolve(self)

        monkeypatch.setattr(Path, "resolve", mock_resolve)

        result = verify_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Invalid path" in captured.out

    # -------------------------------------------------------------------------
    # verify_agents hash OSError (line 308-311)
    # -------------------------------------------------------------------------

    def test_verify_hash_oserror(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test verify_agents handles hash computation failure."""
        from debate_hall_mcp import cli
        from debate_hall_mcp.cli import verify_agents

        # Create agent file
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        wind_file = agents_dir / "wind.agent.md"
        wind_file.write_text("# Wind Agent")

        # Create lockfile with a hash (doesn't matter what value, we'll fail before comparing)
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {
                "wind": {
                    "file": ".github/agents/wind.agent.md",
                    "sha256": "a" * 64,
                }
            },
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        # Mock _compute_sha256 to raise OSError
        def mock_compute_sha256(_file_path: Path) -> str:
            raise OSError("File unreadable")

        monkeypatch.setattr(cli, "_compute_sha256", mock_compute_sha256)

        result = verify_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading wind" in captured.out

    # -------------------------------------------------------------------------
    # pin_agents empty ref validation (line 328-330)
    # -------------------------------------------------------------------------

    def test_pin_empty_ref(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test pin_agents rejects empty ref."""
        from debate_hall_mcp.cli import pin_agents

        # Create a lockfile
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {},
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        # Test empty string
        result = pin_agents(tmp_path, "")
        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Ref cannot be empty" in captured.out

    def test_pin_whitespace_only_ref(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pin_agents rejects whitespace-only ref."""
        from debate_hall_mcp.cli import pin_agents

        # Create a lockfile
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {},
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        # Test whitespace-only
        result = pin_agents(tmp_path, "   ")
        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Ref cannot be empty" in captured.out

    # -------------------------------------------------------------------------
    # verify_agents invalid lockfile format (line 265-266, 274-276)
    # -------------------------------------------------------------------------

    def test_verify_invalid_agents_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test verify_agents handles invalid agents format in lockfile."""
        from debate_hall_mcp.cli import verify_agents

        # Create lockfile with invalid agents (not a dict)
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": "not a dict",
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        result = verify_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Invalid lockfile format" in captured.out

    def test_verify_invalid_agent_entry_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test verify_agents handles invalid agent entry format."""
        from debate_hall_mcp.cli import verify_agents

        # Create lockfile with invalid agent entry (not a dict)
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {
                "wind": "not a dict",
            },
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        result = verify_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Invalid agent entry for wind" in captured.out

    def test_verify_missing_file_or_sha256(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test verify_agents handles missing file or sha256 in agent entry."""
        from debate_hall_mcp.cli import verify_agents

        # Create lockfile with missing sha256
        lockfile_data = {
            "version": "1.0",
            "source": {"repo": "test/repo", "ref": "v1.0.0"},
            "agents": {
                "wind": {
                    "file": ".github/agents/wind.agent.md",
                    # missing sha256
                },
            },
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        result = verify_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Missing file or sha256 for agent wind" in captured.out

    # -------------------------------------------------------------------------
    # pin_agents invalid source format (line 375-376)
    # -------------------------------------------------------------------------

    def test_pin_invalid_source_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pin_agents handles invalid source format in lockfile."""
        from debate_hall_mcp.cli import pin_agents

        # Create lockfile with invalid source (not a dict)
        lockfile_data = {
            "version": "1.0",
            "source": "not a dict",
            "agents": {},
        }
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(json.dumps(lockfile_data))

        result = pin_agents(tmp_path, "v2.0.0")

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Invalid lockfile format" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents source not found (line 142-143)
    # -------------------------------------------------------------------------

    def test_sync_source_not_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents handles missing source agents directory."""
        from debate_hall_mcp.cli import sync_agents

        # Mock _get_package_agents_dir to return a non-existent path
        def mock_get_package_agents_dir() -> Path:
            return tmp_path / "nonexistent" / "agents"

        from debate_hall_mcp import cli

        monkeypatch.setattr(cli, "_get_package_agents_dir", mock_get_package_agents_dir)

        result = sync_agents(tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Source agents directory not found" in captured.out

    # -------------------------------------------------------------------------
    # sync_agents missing source file warning (line 173-174)
    # -------------------------------------------------------------------------

    def test_sync_missing_source_file_warning(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync_agents prints warning when source agent file is missing."""
        from debate_hall_mcp.cli import sync_agents

        # Create a mock package agents dir with only some files
        mock_agents_dir = tmp_path / "mock_agents"
        mock_agents_dir.mkdir()
        (mock_agents_dir / "wall.agent.md").write_text("# Wall")
        (mock_agents_dir / "door.agent.md").write_text("# Door")
        # Intentionally missing wind.agent.md

        def mock_get_package_agents_dir() -> Path:
            return mock_agents_dir

        from debate_hall_mcp import cli

        monkeypatch.setattr(cli, "_get_package_agents_dir", mock_get_package_agents_dir)

        result = sync_agents(tmp_path)

        assert result == 0
        captured = capsys.readouterr()
        assert "Warning: Source agent file not found" in captured.out
        assert "wind.agent.md" in captured.out

    # -------------------------------------------------------------------------
    # _load_lockfile JSONDecodeError/OSError (line 106-107)
    # -------------------------------------------------------------------------

    def test_load_lockfile_json_decode_error(self, tmp_path: Path) -> None:
        """Test _load_lockfile handles invalid JSON gracefully."""
        from debate_hall_mcp.cli import _load_lockfile

        # Create an invalid JSON lockfile
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text("{ invalid json }")

        result = _load_lockfile(tmp_path)

        assert result is None

    def test_load_lockfile_oserror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _load_lockfile handles OSError gracefully."""
        from debate_hall_mcp.cli import _load_lockfile

        # Create a valid lockfile
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text('{"version": "1.0"}')

        original_read_text = Path.read_text

        def mock_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if "agents.lock.json" in str(self):
                raise OSError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        result = _load_lockfile(tmp_path)

        assert result is None

    # -------------------------------------------------------------------------
    # sync_agents same-size different-content (lines 187-190)
    # -------------------------------------------------------------------------

    def test_sync_same_size_different_content(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test sync detects different content when file sizes match."""
        from debate_hall_mcp.cli import sync_agents

        # Create a mock package agents dir
        mock_agents_dir = tmp_path / "mock_agents"
        mock_agents_dir.mkdir()
        # Content A: same size as target
        (mock_agents_dir / "wind.agent.md").write_text("ABC123")
        (mock_agents_dir / "wall.agent.md").write_text("# Wall")
        (mock_agents_dir / "door.agent.md").write_text("# Door")

        # Create target with same size but different content
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        # Content B: same size (6 chars) as source
        (agents_dir / "wind.agent.md").write_text("XYZ789")

        def mock_get_package_agents_dir() -> Path:
            return mock_agents_dir

        from debate_hall_mcp import cli

        monkeypatch.setattr(cli, "_get_package_agents_dir", mock_get_package_agents_dir)

        # Without force, should skip
        result = sync_agents(tmp_path, force=False)

        assert result == 0
        captured = capsys.readouterr()
        assert "SKIP: wind" in captured.out


# =============================================================================
# Test CLI Internal Functions - Direct Coverage
# =============================================================================


class TestCLIInternalFunctions:
    """Test internal CLI functions directly for coverage.

    The subprocess-based tests exercise CLI behavior but don't count
    toward coverage of the actual Python code. These tests call the
    internal functions directly.
    """

    def test_create_parser_returns_parser(self) -> None:
        """Test _create_parser returns a configured ArgumentParser."""
        from debate_hall_mcp.cli import _create_parser

        parser = _create_parser()

        assert parser is not None
        assert parser.prog == "debate-hall-mcp"

    def test_create_parser_has_subcommands(self) -> None:
        """Test _create_parser configures all subcommands."""
        from debate_hall_mcp.cli import _create_parser

        parser = _create_parser()

        # Parse each subcommand to verify they're configured
        sync_args = parser.parse_args(["sync"])
        assert sync_args.command == "sync"
        assert hasattr(sync_args, "func")

        verify_args = parser.parse_args(["verify"])
        assert verify_args.command == "verify"
        assert hasattr(verify_args, "func")

        pin_args = parser.parse_args(["pin", "v1.0.0"])
        assert pin_args.command == "pin"
        assert pin_args.ref == "v1.0.0"
        assert hasattr(pin_args, "func")

    def test_create_parser_sync_force_flag(self) -> None:
        """Test _create_parser configures --force flag for sync."""
        from debate_hall_mcp.cli import _create_parser

        parser = _create_parser()

        args_no_force = parser.parse_args(["sync"])
        assert args_no_force.force is False

        args_with_force = parser.parse_args(["sync", "--force"])
        assert args_with_force.force is True

        args_with_short_force = parser.parse_args(["sync", "-f"])
        assert args_with_short_force.force is True

    def test_cmd_sync_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _cmd_sync uses current working directory."""
        import argparse

        from debate_hall_mcp.cli import _cmd_sync

        # Mock Path.cwd to return tmp_path
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        args = argparse.Namespace(force=False)
        result = _cmd_sync(args)

        # Should succeed and create files
        assert result == 0
        assert (tmp_path / ".github" / "agents").exists()

    def test_cmd_verify_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _cmd_verify uses current working directory."""
        import argparse

        from debate_hall_mcp.cli import _cmd_verify

        # Mock Path.cwd to return tmp_path
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        args = argparse.Namespace()
        result = _cmd_verify(args)

        # Should fail because no lockfile exists
        assert result == 1

    def test_cmd_pin_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _cmd_pin uses current working directory."""
        import argparse

        from debate_hall_mcp.cli import _cmd_pin

        # Create a lockfile first
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(
            '{"version": "1.0", "source": {"repo": "test", "ref": "v1"}, "agents": {}}'
        )

        # Mock Path.cwd to return tmp_path
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        args = argparse.Namespace(ref="v2.0.0")
        result = _cmd_pin(args)

        assert result == 0

    def test_main_no_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main() with no command shows help."""
        import sys

        from debate_hall_mcp.cli import main

        # Mock sys.argv to have no command
        monkeypatch.setattr(sys, "argv", ["debate-hall-mcp"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "debate-hall-mcp" in captured.out

    def test_main_with_sync_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main() with sync command."""
        import sys

        from debate_hall_mcp.cli import main

        # Mock sys.argv and cwd
        monkeypatch.setattr(sys, "argv", ["debate-hall-mcp", "sync"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        result = main()

        assert result == 0
        assert (tmp_path / ".github" / "agents").exists()

    def test_main_with_verify_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main() with verify command."""
        import sys

        from debate_hall_mcp.cli import main

        # Mock sys.argv and cwd
        monkeypatch.setattr(sys, "argv", ["debate-hall-mcp", "verify"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        result = main()

        # Should fail - no lockfile
        assert result == 1

    def test_main_with_pin_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main() with pin command."""
        import sys

        from debate_hall_mcp.cli import main

        # Create a lockfile first
        lockfile = tmp_path / "agents.lock.json"
        lockfile.write_text(
            '{"version": "1.0", "source": {"repo": "test", "ref": "v1"}, "agents": {}}'
        )

        # Mock sys.argv and cwd
        monkeypatch.setattr(sys, "argv", ["debate-hall-mcp", "pin", "v2.0.0"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        result = main()

        assert result == 0
