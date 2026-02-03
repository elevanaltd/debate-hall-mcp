"""Tests for agent prompt loading with role-based resolution.

Tests the agent prompt resolution pattern:
1. ./agents/{role_name}.oct.md (debate-hall primary)
2. .hestai-sys/library/agents/{role_name}.oct.md (when HESTAI_INTEGRATION=true)
3. Return None (signal to use fallback prompt_file/embedded logic)

Role name normalization:
- Spaces converted to hyphens
- Lowercase
- "critical engineer" -> "critical-engineer"
"""

from pathlib import Path

from debate_hall_mcp.prompts.loader import get_agent_prompt


class TestGetAgentPromptLocalFound:
    """Test agent resolution from local ./agents/ directory."""

    def test_finds_agent_in_local_agents_dir(self, tmp_path: Path, monkeypatch):
        """Agent prompt found in ./agents/ directory returns content."""
        # Setup: create agent file in ./agents/
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "ideator.oct.md"
        agent_file.write_text("===IDEATOR_AGENT===\nLocal agent content\n===END===")

        # Mock PROJECT_AGENTS_DIR to use tmp_path
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("ideator")

        assert result is not None
        assert "IDEATOR_AGENT" in result
        assert "Local agent content" in result

    def test_local_agents_dir_takes_precedence_over_hestai(self, tmp_path: Path, monkeypatch):
        """Local ./agents/ directory takes precedence over .hestai-sys/library/agents/."""
        # Setup: create agent in both locations
        local_agents = tmp_path / "agents"
        local_agents.mkdir()
        (local_agents / "wind-agent.oct.md").write_text("===LOCAL_WIND===\n===END===")

        hestai_agents = tmp_path / ".hestai-sys" / "library" / "agents"
        hestai_agents.mkdir(parents=True)
        (hestai_agents / "wind-agent.oct.md").write_text("===HESTAI_WIND===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", local_agents)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR", hestai_agents)
        monkeypatch.setenv("HESTAI_INTEGRATION", "true")

        result = get_agent_prompt("wind-agent")

        assert result is not None
        assert "LOCAL_WIND" in result
        assert "HESTAI_WIND" not in result


class TestGetAgentPromptHestaiFound:
    """Test agent resolution from .hestai-sys/library/agents/ when enabled."""

    def test_finds_agent_in_hestai_when_enabled(self, tmp_path: Path, monkeypatch):
        """Agent found in .hestai-sys/library/agents/ when HESTAI_INTEGRATION=true."""
        # Setup: create agent in hestai directory only
        local_agents = tmp_path / "agents"  # Does not exist
        hestai_agents = tmp_path / ".hestai-sys" / "library" / "agents"
        hestai_agents.mkdir(parents=True)
        (hestai_agents / "critical-engineer.oct.md").write_text(
            "===CRITICAL_ENGINEER===\nHestAI agent\n===END==="
        )

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", local_agents)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR", hestai_agents)
        monkeypatch.setenv("HESTAI_INTEGRATION", "true")

        result = get_agent_prompt("critical-engineer")

        assert result is not None
        assert "CRITICAL_ENGINEER" in result
        assert "HestAI agent" in result

    def test_hestai_not_searched_when_integration_disabled(self, tmp_path: Path, monkeypatch):
        """Agent NOT found in .hestai-sys/ when HESTAI_INTEGRATION is not true."""
        # Setup: agent only in hestai directory
        local_agents = tmp_path / "agents"  # Does not exist
        hestai_agents = tmp_path / ".hestai-sys" / "library" / "agents"
        hestai_agents.mkdir(parents=True)
        (hestai_agents / "wall-agent.oct.md").write_text("===WALL===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", local_agents)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR", hestai_agents)
        # HESTAI_INTEGRATION not set or set to false
        monkeypatch.delenv("HESTAI_INTEGRATION", raising=False)

        result = get_agent_prompt("wall-agent")

        assert result is None

    def test_hestai_disabled_when_env_is_false(self, tmp_path: Path, monkeypatch):
        """Agent NOT found when HESTAI_INTEGRATION=false explicitly."""
        local_agents = tmp_path / "agents"
        hestai_agents = tmp_path / ".hestai-sys" / "library" / "agents"
        hestai_agents.mkdir(parents=True)
        (hestai_agents / "door-agent.oct.md").write_text("===DOOR===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", local_agents)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR", hestai_agents)
        monkeypatch.setenv("HESTAI_INTEGRATION", "false")

        result = get_agent_prompt("door-agent")

        assert result is None


class TestGetAgentPromptNotFound:
    """Test behavior when agent is not found anywhere."""

    def test_returns_none_when_agent_not_found(self, tmp_path: Path, monkeypatch):
        """Returns None when agent file doesn't exist in any location."""
        local_agents = tmp_path / "agents"
        hestai_agents = tmp_path / ".hestai-sys" / "library" / "agents"

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", local_agents)
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR", hestai_agents)
        monkeypatch.setenv("HESTAI_INTEGRATION", "true")

        result = get_agent_prompt("nonexistent-agent")

        assert result is None

    def test_returns_none_gracefully_no_exceptions(self, tmp_path: Path, monkeypatch):
        """File not found is handled gracefully, no exceptions raised."""
        monkeypatch.setattr(
            "debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", tmp_path / "agents"
        )
        monkeypatch.setattr(
            "debate_hall_mcp.prompts.loader.HESTAI_AGENTS_DIR",
            tmp_path / ".hestai-sys" / "library" / "agents",
        )

        # Should not raise any exception
        result = get_agent_prompt("missing-agent")
        assert result is None


class TestGetAgentPromptNormalization:
    """Test role name normalization (spaces to hyphens, lowercase)."""

    def test_spaces_converted_to_hyphens(self, tmp_path: Path, monkeypatch):
        """'critical engineer' finds 'critical-engineer.oct.md'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "critical-engineer.oct.md").write_text("===CRITICAL_ENGINEER===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("critical engineer")

        assert result is not None
        assert "CRITICAL_ENGINEER" in result

    def test_uppercase_converted_to_lowercase(self, tmp_path: Path, monkeypatch):
        """'Technical Architect' finds 'technical-architect.oct.md'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "technical-architect.oct.md").write_text(
            "===TECHNICAL_ARCHITECT===\n===END==="
        )

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("Technical Architect")

        assert result is not None
        assert "TECHNICAL_ARCHITECT" in result

    def test_mixed_normalization(self, tmp_path: Path, monkeypatch):
        """'CRITICAL ENGINEER' finds 'critical-engineer.oct.md'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "critical-engineer.oct.md").write_text("===CRITICAL_ENGINEER===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("CRITICAL ENGINEER")

        assert result is not None
        assert "CRITICAL_ENGINEER" in result

    def test_already_normalized_name_works(self, tmp_path: Path, monkeypatch):
        """'implementation-lead' (already normalized) finds correct file."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "implementation-lead.oct.md").write_text(
            "===IMPLEMENTATION_LEAD===\n===END==="
        )

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("implementation-lead")

        assert result is not None
        assert "IMPLEMENTATION_LEAD" in result


class TestGetAgentPromptSecurity:
    """Test security: path traversal and invalid character prevention."""

    def test_get_agent_prompt_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Path traversal attempts should be blocked even if file exists at traversed path.

        This test creates a file structure where path traversal WOULD succeed
        if not blocked, proving the security fix actually prevents it.
        """
        # Create the structure: agents/ and private/ at same level
        agents_dir = tmp_path / "project" / "agents"
        agents_dir.mkdir(parents=True)

        # Create a "secret" file that path traversal would try to access
        private_dir = tmp_path / "private"
        private_dir.mkdir()
        secret_file = private_dir / "secret.oct.md"
        secret_file.write_text("===SECRET_DATA===\nThis should not be accessible\n===END===")

        # Point PROJECT_AGENTS_DIR to agents dir
        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        # Attempt path traversal: ../../private/secret would resolve to private/secret.oct.md
        result = get_agent_prompt("../../private/secret")

        # Should be None because path traversal is blocked, NOT because file doesn't exist
        assert result is None

    def test_get_agent_prompt_invalid_characters_blocked(self, tmp_path, monkeypatch):
        """Invalid characters in role name should be blocked even if file exists."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create nested structure that slash would navigate to
        nested = agents_dir / "role" / "with"
        nested.mkdir(parents=True)
        (nested / "slashes.oct.md").write_text("===NESTED===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("role/with/slashes")
        assert result is None

    def test_get_agent_prompt_dots_blocked(self):
        """Role names with dots should be blocked."""
        result = get_agent_prompt("role.with.dots")
        assert result is None

    def test_get_agent_prompt_underscores_blocked(self):
        """Role names with underscores should be blocked (use hyphens)."""
        result = get_agent_prompt("role_with_underscores")
        assert result is None

    def test_get_agent_prompt_backslash_blocked(self):
        """Windows-style path traversal should be blocked."""
        result = get_agent_prompt("..\\..\\private\\secret")
        assert result is None

    def test_get_agent_prompt_valid_hyphenated_role_allowed(self, tmp_path, monkeypatch):
        """Valid hyphenated role names should still work."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "valid-role-name.oct.md").write_text("===VALID===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("valid-role-name")

        assert result is not None
        assert "VALID" in result

    def test_get_agent_prompt_numeric_suffix_allowed(self, tmp_path, monkeypatch):
        """Role names with numbers should work."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent-v2.oct.md").write_text("===AGENT_V2===\n===END===")

        monkeypatch.setattr("debate_hall_mcp.prompts.loader.PROJECT_AGENTS_DIR", agents_dir)

        result = get_agent_prompt("agent-v2")

        assert result is not None
        assert "AGENT_V2" in result
