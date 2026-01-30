"""Tests for prompt loading with user customization support.

Tests the Layered Discovery with Optional Naming pattern:
1. Embedded defaults (Ship ZERO)
2. Custom file loading (absolute path)
3. Named variant resolution with layered discovery:
   - Project-local: ./prompts/{role}-{variant}.oct.md
   - User-global: ~/.debate-hall/prompts/{role}-{variant}.oct.md
4. Discovery/listing of available prompts
"""

from pathlib import Path

import pytest

from debate_hall_mcp.prompts import DOOR_PROMPT, WALL_PROMPT, WIND_PROMPT
from debate_hall_mcp.prompts.loader import (
    PROJECT_PROMPTS_DIR,
    PROMPTS_DIR,
    USER_PROMPTS_DIR,
    VALID_ROLES,
    PromptLoadError,
    _resolve_prompt_path,
    ensure_prompts_dir,
    get_prompt,
    get_prompts_dir,
    list_available_prompts,
)


class TestGetPromptEmbeddedDefaults:
    """Test Ship ZERO principle: embedded prompts work without configuration."""

    def test_wind_returns_embedded_when_no_file(self):
        """Wind role returns embedded WIND_PROMPT when prompt_file is None."""
        result = get_prompt("wind")
        assert result == WIND_PROMPT

    def test_wall_returns_embedded_when_no_file(self):
        """Wall role returns embedded WALL_PROMPT when prompt_file is None."""
        result = get_prompt("wall")
        assert result == WALL_PROMPT

    def test_door_returns_embedded_when_no_file(self):
        """Door role returns embedded DOOR_PROMPT when prompt_file is None."""
        result = get_prompt("door")
        assert result == DOOR_PROMPT

    def test_role_is_case_insensitive(self):
        """Role parameter is case-insensitive."""
        assert get_prompt("WIND") == WIND_PROMPT
        assert get_prompt("Wind") == WIND_PROMPT
        assert get_prompt("wInD") == WIND_PROMPT

    def test_invalid_role_raises_valueerror(self):
        """Invalid role raises ValueError with helpful message."""
        with pytest.raises(ValueError, match="Invalid role 'scout'"):
            get_prompt("scout")


class TestGetPromptCustomFile:
    """Test loading custom prompts from files."""

    def test_absolute_path_loads_file(self, tmp_path: Path):
        """Absolute path loads content from that file."""
        prompt_file = tmp_path / "custom-wind.oct.md"
        prompt_file.write_text("===CUSTOM_WIND===\nMy custom prompt\n===END===")

        result = get_prompt("wind", str(prompt_file))
        assert "CUSTOM_WIND" in result
        assert "My custom prompt" in result

    def test_missing_file_raises_promptloaderror(self, tmp_path: Path):
        """Non-existent file raises PromptLoadError."""
        missing = tmp_path / "nonexistent.oct.md"

        with pytest.raises(PromptLoadError, match="not found"):
            get_prompt("wind", str(missing))

    def test_relative_path_with_dot_prefix_resolves(self, tmp_path: Path, monkeypatch):
        """Relative paths starting with ./ resolve from cwd."""
        monkeypatch.chdir(tmp_path)
        prompt_file = tmp_path / "local-prompt.oct.md"
        prompt_file.write_text("===LOCAL===\n===END===")

        result = get_prompt("wind", "./local-prompt.oct.md")
        assert "LOCAL" in result


class TestGetPromptNamedVariants:
    """Test named variant resolution with layered discovery."""

    def test_variant_resolves_from_user_global(self, tmp_path: Path, monkeypatch):
        """Variant name resolves to user-global dir when project-local doesn't exist."""
        # Mock both directories
        project_dir = tmp_path / "project" / "prompts"
        user_dir = tmp_path / "user" / ".debate-hall" / "prompts"
        user_dir.mkdir(parents=True)

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Create variant in user-global only
        variant_file = user_dir / "wind-security.oct.md"
        variant_file.write_text("===WIND_SECURITY_USER===\nFrom user dir\n===END===")

        result = get_prompt("wind", "security")
        assert "WIND_SECURITY_USER" in result

    def test_project_local_takes_precedence(self, tmp_path: Path, monkeypatch):
        """Project-local prompts take precedence over user-global."""
        # Mock both directories
        project_dir = tmp_path / "project" / "prompts"
        user_dir = tmp_path / "user" / ".debate-hall" / "prompts"
        project_dir.mkdir(parents=True)
        user_dir.mkdir(parents=True)

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Create variant in both locations
        (project_dir / "wind-security.oct.md").write_text("===PROJECT_LOCAL===\n===END===")
        (user_dir / "wind-security.oct.md").write_text("===USER_GLOBAL===\n===END===")

        result = get_prompt("wind", "security")
        assert "PROJECT_LOCAL" in result
        assert "USER_GLOBAL" not in result

    def test_variant_with_role_prefix_works(self, tmp_path: Path, monkeypatch):
        """Variant name with role prefix (wind-security) also works."""
        user_dir = tmp_path / ".debate-hall" / "prompts"
        user_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", tmp_path / "nonexistent"
        )
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        variant_file = user_dir / "wall-strict.oct.md"
        variant_file.write_text("===WALL_STRICT===\nExtra strict validation\n===END===")

        result = get_prompt("wall", "wall-strict")
        assert "WALL_STRICT" in result

    def test_missing_variant_raises_promptloaderror(self, tmp_path: Path, monkeypatch):
        """Missing variant file raises PromptLoadError."""
        monkeypatch.setattr(
            "debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", tmp_path / "project"
        )
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", tmp_path / "user")

        with pytest.raises(PromptLoadError, match="not found"):
            get_prompt("door", "nonexistent-variant")


class TestResolvePromptPath:
    """Test path resolution logic."""

    def test_absolute_path_returned_unchanged(self):
        """Absolute paths are returned as-is."""
        path = _resolve_prompt_path("wind", "/absolute/path/to/prompt.oct.md")
        assert path == Path("/absolute/path/to/prompt.oct.md")

    def test_relative_with_dot_resolves_from_cwd(self, tmp_path: Path, monkeypatch):
        """Paths starting with ./ resolve relative to cwd."""
        monkeypatch.chdir(tmp_path)
        path = _resolve_prompt_path("wind", "./local/prompt.oct.md")
        assert path == tmp_path / "local" / "prompt.oct.md"

    def test_variant_prefers_project_local_when_exists(self, tmp_path: Path, monkeypatch):
        """Variant resolves to project-local when file exists there."""
        project_dir = tmp_path / "prompts"
        user_dir = tmp_path / "user"
        project_dir.mkdir()

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Create file in project-local
        (project_dir / "wind-security.oct.md").write_text("project")

        path = _resolve_prompt_path("wind", "security")
        assert path == (project_dir / "wind-security.oct.md").resolve()

    def test_variant_falls_back_to_user_global(self, tmp_path: Path, monkeypatch):
        """Variant falls back to user-global when project-local doesn't exist."""
        project_dir = tmp_path / "project"  # Doesn't exist
        user_dir = tmp_path / "user"
        user_dir.mkdir()

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Create file in user-global only
        (user_dir / "wind-security.oct.md").write_text("user")

        path = _resolve_prompt_path("wind", "security")
        assert path == user_dir / "wind-security.oct.md"

    def test_variant_with_role_prefix_not_duplicated(self, tmp_path: Path, monkeypatch):
        """Variant 'wind-security' doesn't become 'wind-wind-security'."""
        project_dir = tmp_path / "prompts"
        project_dir.mkdir()
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", tmp_path / "user")

        (project_dir / "wind-security.oct.md").write_text("test")

        path = _resolve_prompt_path("wind", "wind-security")
        assert "wind-wind-security" not in str(path)
        assert path == (project_dir / "wind-security.oct.md").resolve()


class TestListAvailablePrompts:
    """Test discovery of available custom prompts."""

    def test_empty_when_dir_not_exists(self, tmp_path: Path):
        """Returns empty lists when prompts directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        result = list_available_prompts(nonexistent)
        assert result == {"wind": [], "wall": [], "door": []}

    def test_discovers_prompts_by_role(self, tmp_path: Path):
        """Discovers prompts and organizes by role."""
        # Create sample prompt files
        (tmp_path / "wind-default.oct.md").write_text("wind default")
        (tmp_path / "wind-security.oct.md").write_text("wind security")
        (tmp_path / "wall-strict.oct.md").write_text("wall strict")
        (tmp_path / "door-technical.oct.md").write_text("door technical")

        result = list_available_prompts(tmp_path)

        assert "default" in result["wind"]
        assert "security" in result["wind"]
        assert "strict" in result["wall"]
        assert "technical" in result["door"]

    def test_merges_project_and_user_directories(self, tmp_path: Path, monkeypatch):
        """Lists prompts from both project-local and user-global directories."""
        project_dir = tmp_path / "prompts"
        user_dir = tmp_path / "user" / ".debate-hall" / "prompts"
        project_dir.mkdir()
        user_dir.mkdir(parents=True)

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Create variants in different locations
        (project_dir / "wind-security.oct.md").write_text("project")
        (user_dir / "wind-creative.oct.md").write_text("user")
        (user_dir / "wall-strict.oct.md").write_text("user")

        result = list_available_prompts()  # No explicit dir = merge both

        assert "security" in result["wind"]
        assert "creative" in result["wind"]
        assert "strict" in result["wall"]

    def test_deduplicates_variants_from_both_dirs(self, tmp_path: Path, monkeypatch):
        """Same variant in both directories appears only once."""
        project_dir = tmp_path / "prompts"
        user_dir = tmp_path / "user"
        project_dir.mkdir()
        user_dir.mkdir()

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_PROMPTS_DIR", project_dir)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.USER_PROMPTS_DIR", user_dir)

        # Same variant in both
        (project_dir / "wind-security.oct.md").write_text("project")
        (user_dir / "wind-security.oct.md").write_text("user")

        result = list_available_prompts()

        assert result["wind"].count("security") == 1

    def test_ignores_non_octmd_files(self, tmp_path: Path):
        """Only discovers .oct.md files."""
        (tmp_path / "wind-valid.oct.md").write_text("valid")
        (tmp_path / "wind-invalid.md").write_text("invalid")
        (tmp_path / "wind-also-invalid.txt").write_text("also invalid")

        result = list_available_prompts(tmp_path)

        assert result["wind"] == ["valid"]

    def test_ignores_files_without_role_prefix(self, tmp_path: Path):
        """Files without valid role prefix are ignored."""
        (tmp_path / "wind-valid.oct.md").write_text("valid")
        (tmp_path / "random-file.oct.md").write_text("no role prefix")
        (tmp_path / "scout-future.oct.md").write_text("invalid role")

        result = list_available_prompts(tmp_path)

        assert result["wind"] == ["valid"]
        assert result["wall"] == []
        assert result["door"] == []

    def test_variants_sorted_alphabetically(self, tmp_path: Path):
        """Variants are sorted alphabetically for consistent output."""
        (tmp_path / "wind-zebra.oct.md").write_text("z")
        (tmp_path / "wind-alpha.oct.md").write_text("a")
        (tmp_path / "wind-middle.oct.md").write_text("m")

        result = list_available_prompts(tmp_path)

        assert result["wind"] == ["alpha", "middle", "zebra"]


class TestHelperFunctions:
    """Test utility functions."""

    def test_get_prompts_dir_returns_user_global_path(self):
        """get_prompts_dir returns the user-global prompts directory."""
        result = get_prompts_dir()
        assert isinstance(result, Path)
        assert result == USER_PROMPTS_DIR
        assert result == PROMPTS_DIR  # Legacy alias

    def test_ensure_prompts_dir_creates_directory(self, tmp_path: Path, monkeypatch):
        """ensure_prompts_dir creates the directory if it doesn't exist."""
        new_dir = tmp_path / ".debate-hall" / "prompts"
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROMPTS_DIR", new_dir)

        assert not new_dir.exists()
        result = ensure_prompts_dir()
        assert new_dir.exists()
        assert result == new_dir

    def test_ensure_prompts_dir_idempotent(self, tmp_path: Path, monkeypatch):
        """ensure_prompts_dir is idempotent - doesn't fail if dir exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROMPTS_DIR", existing_dir)

        result = ensure_prompts_dir()
        assert result == existing_dir


class TestConstants:
    """Test module constants."""

    def test_valid_roles_contains_expected(self):
        """VALID_ROLES contains wind, wall, door."""
        assert "wind" in VALID_ROLES
        assert "wall" in VALID_ROLES
        assert "door" in VALID_ROLES

    def test_valid_roles_is_frozen(self):
        """VALID_ROLES is immutable."""
        assert isinstance(VALID_ROLES, frozenset)

    def test_project_prompts_dir_is_relative(self):
        """PROJECT_PROMPTS_DIR is relative ./prompts."""
        assert Path("./prompts") == PROJECT_PROMPTS_DIR

    def test_user_prompts_dir_is_in_home(self):
        """USER_PROMPTS_DIR is in home directory."""
        assert ".debate-hall" in str(USER_PROMPTS_DIR)
        assert "prompts" in str(USER_PROMPTS_DIR)

    def test_prompts_dir_is_alias_for_user(self):
        """PROMPTS_DIR is legacy alias for USER_PROMPTS_DIR."""
        assert PROMPTS_DIR == USER_PROMPTS_DIR
