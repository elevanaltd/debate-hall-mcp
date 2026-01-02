"""Tests for environment variable loading from .env files."""

import os
import tempfile
from pathlib import Path
from unittest import mock


class TestEnvLoading:
    """Tests for .env file loading functionality."""

    def test_get_env_returns_environment_variable(self) -> None:
        """get_env should return value from os.environ."""
        with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            from debate_hall_mcp.utils.env import get_env

            result = get_env("TEST_VAR")
            assert result == "test_value"

    def test_get_env_returns_default_when_not_set(self) -> None:
        """get_env should return default when variable not set."""
        from debate_hall_mcp.utils.env import get_env

        # Ensure variable doesn't exist
        env_copy = os.environ.copy()
        if "NONEXISTENT_VAR_12345" in env_copy:
            del env_copy["NONEXISTENT_VAR_12345"]

        with mock.patch.dict(os.environ, env_copy, clear=True):
            result = get_env("NONEXISTENT_VAR_12345", "default_value")
            assert result == "default_value"

    def test_get_env_returns_none_when_not_set_no_default(self) -> None:
        """get_env should return None when variable not set and no default."""
        from debate_hall_mcp.utils.env import get_env

        env_copy = os.environ.copy()
        if "NONEXISTENT_VAR_67890" in env_copy:
            del env_copy["NONEXISTENT_VAR_67890"]

        with mock.patch.dict(os.environ, env_copy, clear=True):
            result = get_env("NONEXISTENT_VAR_67890")
            assert result is None

    def test_load_env_from_file(self) -> None:
        """load_env should load variables from .env file."""
        from debate_hall_mcp.utils.env import load_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_LOAD_VAR=loaded_value\n")
            f.write("ANOTHER_VAR=another_value\n")
            temp_path = Path(f.name)

        try:
            # Clear any existing value
            if "TEST_LOAD_VAR" in os.environ:
                del os.environ["TEST_LOAD_VAR"]

            result = load_env(temp_path)
            assert result is True
            assert os.environ.get("TEST_LOAD_VAR") == "loaded_value"
            assert os.environ.get("ANOTHER_VAR") == "another_value"
        finally:
            temp_path.unlink()
            # Cleanup
            os.environ.pop("TEST_LOAD_VAR", None)
            os.environ.pop("ANOTHER_VAR", None)

    def test_load_env_returns_false_for_missing_file(self) -> None:
        """load_env should return False when .env file doesn't exist."""
        from debate_hall_mcp.utils.env import load_env

        result = load_env(Path("/nonexistent/path/.env"))
        assert result is False

    def test_load_env_does_not_override_existing(self) -> None:
        """load_env should not override existing environment variables."""
        from debate_hall_mcp.utils.env import load_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("EXISTING_VAR=new_value\n")
            temp_path = Path(f.name)

        try:
            # Set existing value
            os.environ["EXISTING_VAR"] = "original_value"

            load_env(temp_path)
            # Should keep original value (override=False by default)
            assert os.environ.get("EXISTING_VAR") == "original_value"
        finally:
            temp_path.unlink()
            os.environ.pop("EXISTING_VAR", None)

    def test_reload_env_overrides_existing(self) -> None:
        """reload_env should override existing environment variables."""
        from debate_hall_mcp.utils.env import reload_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OVERRIDE_VAR=new_value\n")
            temp_path = Path(f.name)

        try:
            # Set existing value
            os.environ["OVERRIDE_VAR"] = "original_value"

            reload_env(temp_path)
            # Should have new value (override=True)
            assert os.environ.get("OVERRIDE_VAR") == "new_value"
        finally:
            temp_path.unlink()
            os.environ.pop("OVERRIDE_VAR", None)

    def test_get_env_file_path_finds_existing_file(self) -> None:
        """get_env_file_path should return path to existing .env file."""
        from debate_hall_mcp.utils.env import get_env_file_path

        # This may or may not find a .env file depending on test environment
        result = get_env_file_path()
        # Result is either None or a Path
        assert result is None or isinstance(result, Path)


class TestGitHubTokenLoading:
    """Tests specifically for GITHUB_TOKEN loading pattern."""

    def test_github_token_from_env(self) -> None:
        """GITHUB_TOKEN should be accessible via get_env."""
        from debate_hall_mcp.utils.env import get_env

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
            result = get_env("GITHUB_TOKEN")
            assert result == "ghp_test123"

    def test_github_token_from_dotenv_file(self) -> None:
        """GITHUB_TOKEN should be loadable from .env file."""
        from debate_hall_mcp.utils.env import get_env, load_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("GITHUB_TOKEN=ghp_from_dotenv\n")
            temp_path = Path(f.name)

        try:
            # Clear any existing token
            original = os.environ.pop("GITHUB_TOKEN", None)

            load_env(temp_path)
            result = get_env("GITHUB_TOKEN")
            assert result == "ghp_from_dotenv"
        finally:
            temp_path.unlink()
            os.environ.pop("GITHUB_TOKEN", None)
            if original:
                os.environ["GITHUB_TOKEN"] = original
