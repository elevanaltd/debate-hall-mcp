"""Tests for DEBATE_HALL_STATE_DIR environment variable support (Issue #33).

TDD Discipline: RED -> GREEN -> REFACTOR
This test file verifies that all tools respect the DEBATE_HALL_STATE_DIR
environment variable for consistent persistence location.

Acceptance Criteria:
- DEBATE_HALL_STATE_DIR env var respected by all tools
- Fallback to ./debates when env var unset (backwards compatible)
- All tools use consistent state_dir resolution
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from debate_hall_mcp.state import find_project_root, get_state_dir
from debate_hall_mcp.tools.admin import debate_force_close, debate_tombstone
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn


class TestFindProjectRoot:
    """Test find_project_root function for project-relative detection."""

    def test_finds_git_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that find_project_root finds .git directory."""
        project_root = tmp_path / "my_project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        # Start from subdirectory
        subdir = project_root / "src" / "debate_hall_mcp"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        assert find_project_root() == project_root

    def test_finds_pyproject_toml_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that find_project_root finds pyproject.toml."""
        project_root = tmp_path / "my_project"
        project_root.mkdir()
        (project_root / "pyproject.toml").touch()

        # Start from subdirectory
        subdir = project_root / "src" / "debate_hall_mcp"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        assert find_project_root() == project_root

    def test_returns_cwd_when_no_markers_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that find_project_root returns cwd when no markers found."""
        no_markers_dir = tmp_path / "no_markers"
        no_markers_dir.mkdir()
        monkeypatch.chdir(no_markers_dir)

        assert find_project_root() == no_markers_dir


class TestGetStateDirFunction:
    """Test get_state_dir helper function across all tool modules."""

    def test_get_state_dir_returns_env_var_when_set(self, tmp_path: Path) -> None:
        """Test that get_state_dir respects DEBATE_HALL_STATE_DIR env var."""
        env_path = str(tmp_path / "custom_debates")
        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": env_path}):
            assert get_state_dir() == Path(env_path)

    def test_get_state_dir_uses_project_relative_when_env_unset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_state_dir uses project root when env var unset."""
        # Create a fake project with .git marker
        project_root = tmp_path / "my_project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        # Change to project directory
        monkeypatch.chdir(project_root)

        # Ensure env var is NOT set
        monkeypatch.delenv("DEBATE_HALL_STATE_DIR", raising=False)

        # Should return project_root/debates
        assert get_state_dir() == project_root / "debates"

    def test_get_state_dir_handles_empty_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty env var falls back to project-relative detection."""
        # Create a fake project with pyproject.toml marker
        project_root = tmp_path / "my_project"
        project_root.mkdir()
        (project_root / "pyproject.toml").touch()

        # Change to project directory
        monkeypatch.chdir(project_root)

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": ""}):
            # Empty string should fall back to project-relative
            assert get_state_dir() == project_root / "debates"


class TestDebateInitEnvVar:
    """Test debate_init respects DEBATE_HALL_STATE_DIR."""

    def test_init_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_init creates state in env var location when set."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_init(
                thread_id="2025-01-01-env-test",
                topic="Env var test",
            )

        # Verify state file created in custom location
        state_file = custom_dir / "2025-01-01-env-test.json"
        assert state_file.exists(), f"Expected state file at {state_file}"
        assert result["thread_id"] == "2025-01-01-env-test"

    def test_init_explicit_state_dir_overrides_env_var(self, tmp_path: Path) -> None:
        """Test explicit state_dir parameter takes precedence over env var."""
        env_dir = tmp_path / "env_dir"
        explicit_dir = tmp_path / "explicit_dir"
        env_dir.mkdir()
        explicit_dir.mkdir()

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(env_dir)}):
            debate_init(
                thread_id="2025-01-01-override-test",
                topic="Override test",
                state_dir=explicit_dir,
            )

        # Should use explicit, not env var
        assert (explicit_dir / "2025-01-01-override-test.json").exists()
        assert not (env_dir / "2025-01-01-override-test.json").exists()


class TestDebateCloseEnvVar:
    """Test debate_close respects DEBATE_HALL_STATE_DIR."""

    def test_close_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_close finds state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        # Create debate with explicit path
        debate_init(
            thread_id="2025-01-01-close-env-test",
            topic="Close env test",
            octave_mode=False,  # Use JSON output for this test
            state_dir=custom_dir,
        )

        # Close using env var (no explicit state_dir)
        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_close(
                thread_id="2025-01-01-close-env-test",
                synthesis="1. Step one\n2. Step two\n3. SYNTHESIS: Done",
            )

        assert result["status"] == "synthesis"


class TestDebateGetEnvVar:
    """Test debate_get respects DEBATE_HALL_STATE_DIR."""

    def test_get_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_get finds state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        debate_init(
            thread_id="2025-01-01-get-env-test",
            topic="Get env test",
            state_dir=custom_dir,
        )

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_get(thread_id="2025-01-01-get-env-test")

        assert result["thread_id"] == "2025-01-01-get-env-test"


class TestDebateTurnEnvVar:
    """Test debate_turn respects DEBATE_HALL_STATE_DIR."""

    def test_turn_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_turn finds and updates state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        debate_init(
            thread_id="2025-01-01-turn-env-test",
            topic="Turn env test",
            state_dir=custom_dir,
        )

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_turn(
                thread_id="2025-01-01-turn-env-test",
                role="Wind",
                content="PATHOS content for env test",
            )

        assert result["turn_count"] == 1


class TestDebatePickEnvVar:
    """Test debate_pick respects DEBATE_HALL_STATE_DIR."""

    def test_pick_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_pick finds state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        debate_init(
            thread_id="2025-01-01-pick-env-test",
            topic="Pick env test",
            mode="mediated",
            state_dir=custom_dir,
        )

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_pick(
                thread_id="2025-01-01-pick-env-test",
                role="Wind",
            )

        assert result["next_role"] == "Wind"


class TestDebateAdminEnvVar:
    """Test admin tools respect DEBATE_HALL_STATE_DIR."""

    def test_force_close_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_force_close finds state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        debate_init(
            thread_id="2025-01-01-force-env-test",
            topic="Force close env test",
            state_dir=custom_dir,
        )

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_force_close(
                thread_id="2025-01-01-force-env-test",
                reason="Env var test",
            )

        assert result["status"] == "force_closed"

    def test_tombstone_uses_env_var_state_dir(self, tmp_path: Path) -> None:
        """Test debate_tombstone finds state in env var location."""
        custom_dir = tmp_path / "custom_debates"
        custom_dir.mkdir(parents=True)

        debate_init(
            thread_id="2025-01-01-tomb-env-test",
            topic="Tombstone env test",
            state_dir=custom_dir,
        )
        # Add a turn to tombstone
        from debate_hall_mcp.tools.turn import debate_turn

        debate_turn(
            thread_id="2025-01-01-tomb-env-test",
            role="Wind",
            content="Content to redact",
            state_dir=custom_dir,
        )

        with patch.dict(os.environ, {"DEBATE_HALL_STATE_DIR": str(custom_dir)}):
            result = debate_tombstone(
                thread_id="2025-01-01-tomb-env-test",
                turn_index=0,
                reason="Env var test redaction",
            )

        assert result["turn_index"] == 0


class TestBackwardsCompatibility:
    """Test backwards compatibility when env var is not set."""

    def test_all_tools_use_default_debates_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test tools fall back to ./debates when env var not set.

        This ensures backwards compatibility with existing deployments.
        """
        # Ensure env var is NOT set
        monkeypatch.delenv("DEBATE_HALL_STATE_DIR", raising=False)

        # Create a controlled cwd with debates directory
        debates_dir = tmp_path / "debates"
        debates_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        # Create debate without explicit state_dir
        result = debate_init(
            thread_id="2025-01-01-backwards-compat",
            topic="Backwards compatibility test",
        )

        assert result["thread_id"] == "2025-01-01-backwards-compat"
        # State file should be in ./debates relative to cwd
        assert (debates_dir / "2025-01-01-backwards-compat.json").exists()
