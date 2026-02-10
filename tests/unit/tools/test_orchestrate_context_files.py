"""Unit tests for context_files parameter in run_debate (Issue #133).

Tests cover:
- File injection into debate prompts (CODEBASE_CONTEXT block)
- Path validation (security - no path traversal, must be absolute)
- Root directory restriction (no arbitrary file read)
- Symlink escape prevention
- Graceful handling of missing files (warns, doesn't crash)
- Max chars per file truncation (bounded memory read)
- Aggregate limits (MAX_CONTEXT_FILES, MAX_TOTAL_CONTEXT_CHARS)
- XML attribute escaping in FILE path tag
- Empty context_files list (no-op)
- Integration: context appears in agent prompts during debate
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator, DebateResult
from debate_hall_mcp.tools.orchestrate import (
    MAX_CHARS_PER_FILE,
    MAX_CONTEXT_FILES,
    MAX_TOTAL_CONTEXT_CHARS,
    _read_context_files,
    _validate_context_file_path,
    run_debate,
)

# =============================================================================
# Path Validation Tests
# =============================================================================


class TestValidateContextFilePath:
    """Tests for _validate_context_file_path security validation."""

    def test_rejects_path_traversal_double_dot(self) -> None:
        """Paths with .. must be rejected to prevent directory traversal."""
        with pytest.raises(ValueError, match="path traversal"):
            _validate_context_file_path("../../etc/passwd")

    def test_rejects_path_traversal_in_middle(self) -> None:
        """Paths with .. in the middle must be rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            _validate_context_file_path("/home/user/../etc/passwd")

    def test_rejects_relative_path(self) -> None:
        """Relative paths must be rejected (must be absolute)."""
        with pytest.raises(ValueError, match="must be an absolute path"):
            _validate_context_file_path("src/main.py")

    def test_rejects_relative_path_with_dot(self) -> None:
        """Relative paths starting with ./ must be rejected."""
        with pytest.raises(ValueError, match="must be an absolute path"):
            _validate_context_file_path("./src/main.py")

    def test_accepts_valid_absolute_path(self, tmp_path: Path) -> None:
        """Valid absolute paths should be accepted."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        result = _validate_context_file_path(str(test_file))
        assert result == test_file.resolve()

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        """Return value should be a resolved Path object."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        result = _validate_context_file_path(str(test_file))
        assert isinstance(result, Path)
        assert result.is_absolute()


# =============================================================================
# Root Directory Restriction Tests (Fix #1 - Security Hardening)
# =============================================================================


class TestRootDirectoryRestriction:
    """Tests for root_dir parameter restricting file access scope."""

    def test_rejects_path_outside_root_dir(self, tmp_path: Path) -> None:
        """Paths outside the root directory must be rejected."""
        root = tmp_path / "project"
        root.mkdir()
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret data")

        with pytest.raises(ValueError, match="outside allowed root"):
            _validate_context_file_path(str(outside_file), root_dir=root)

    def test_accepts_path_inside_root_dir(self, tmp_path: Path) -> None:
        """Paths inside the root directory should be accepted."""
        root = tmp_path / "project"
        root.mkdir()
        inside_file = root / "src" / "main.py"
        inside_file.parent.mkdir(parents=True, exist_ok=True)
        inside_file.write_text("# main")

        result = _validate_context_file_path(str(inside_file), root_dir=root)
        assert result == inside_file.resolve()

    def test_accepts_path_at_root_dir(self, tmp_path: Path) -> None:
        """Files directly in the root directory should be accepted."""
        root = tmp_path / "project"
        root.mkdir()
        file_at_root = root / "README.md"
        file_at_root.write_text("# readme")

        result = _validate_context_file_path(str(file_at_root), root_dir=root)
        assert result == file_at_root.resolve()

    def test_rejects_symlink_escaping_root(self, tmp_path: Path) -> None:
        """Symlinks that resolve outside root must be rejected."""
        root = tmp_path / "project"
        root.mkdir()
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret data")

        # Create symlink inside root pointing outside
        symlink = root / "escape.txt"
        symlink.symlink_to(outside_file)

        with pytest.raises(ValueError, match="outside allowed root"):
            _validate_context_file_path(str(symlink), root_dir=root)

    def test_accepts_symlink_within_root(self, tmp_path: Path) -> None:
        """Symlinks that resolve within root should be accepted."""
        root = tmp_path / "project"
        root.mkdir()
        real_file = root / "real.py"
        real_file.write_text("# real")
        symlink = root / "link.py"
        symlink.symlink_to(real_file)

        result = _validate_context_file_path(str(symlink), root_dir=root)
        assert result == real_file.resolve()

    def test_root_dir_none_allows_any_absolute_path(self, tmp_path: Path) -> None:
        """When root_dir is None, any valid absolute path should be accepted."""
        test_file = tmp_path / "anywhere.py"
        test_file.write_text("# anywhere")

        result = _validate_context_file_path(str(test_file), root_dir=None)
        assert result == test_file.resolve()

    def test_root_dir_defaults_to_none(self, tmp_path: Path) -> None:
        """Default root_dir should be None (backward compatible)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        # Should work without root_dir parameter (backward compat)
        result = _validate_context_file_path(str(test_file))
        assert result == test_file.resolve()

    def test_read_context_files_uses_root_dir(self, tmp_path: Path) -> None:
        """_read_context_files should pass root_dir to path validation."""
        root = tmp_path / "project"
        root.mkdir()
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("# outside")

        # File exists but is outside root - should be skipped
        result = _read_context_files([str(outside_file)], root_dir=root)
        assert result == ""

    def test_read_context_files_root_dir_allows_valid(self, tmp_path: Path) -> None:
        """_read_context_files with root_dir should allow files inside root."""
        root = tmp_path / "project"
        root.mkdir()
        inside_file = root / "module.py"
        inside_file.write_text("# inside module")

        result = _read_context_files([str(inside_file)], root_dir=root)
        assert "<CODEBASE_CONTEXT>" in result
        assert "# inside module" in result


# =============================================================================
# Aggregate Limits Tests (Fix #3 - Security Hardening)
# =============================================================================


class TestAggregateLimits:
    """Tests for MAX_CONTEXT_FILES and MAX_TOTAL_CONTEXT_CHARS limits."""

    def test_max_context_files_constant_value(self) -> None:
        """MAX_CONTEXT_FILES should be 20."""
        assert MAX_CONTEXT_FILES == 20

    def test_max_total_context_chars_constant_value(self) -> None:
        """MAX_TOTAL_CONTEXT_CHARS should be 100000."""
        assert MAX_TOTAL_CONTEXT_CHARS == 100_000

    def test_rejects_too_many_files(self, tmp_path: Path) -> None:
        """More than MAX_CONTEXT_FILES should raise ValueError."""
        files = []
        for i in range(MAX_CONTEXT_FILES + 1):
            f = tmp_path / f"file_{i}.py"
            f.write_text(f"# file {i}")
            files.append(str(f))

        with pytest.raises(ValueError, match="exceeds maximum"):
            _read_context_files(files)

    def test_accepts_exactly_max_files(self, tmp_path: Path) -> None:
        """Exactly MAX_CONTEXT_FILES should be accepted."""
        files = []
        for i in range(MAX_CONTEXT_FILES):
            f = tmp_path / f"file_{i}.py"
            f.write_text(f"# file {i}")
            files.append(str(f))

        result = _read_context_files(files)
        assert "<CODEBASE_CONTEXT>" in result
        assert result.count("<FILE") == MAX_CONTEXT_FILES

    def test_aggregate_chars_limit_stops_reading(self, tmp_path: Path) -> None:
        """Reading should stop when aggregate content exceeds MAX_TOTAL_CONTEXT_CHARS."""
        # Create files that together exceed the aggregate limit
        chars_per_file = MAX_TOTAL_CONTEXT_CHARS // 2 + 1000
        files = []
        for i in range(3):
            f = tmp_path / f"big_{i}.py"
            f.write_text("x" * chars_per_file)
            files.append(str(f))

        result = _read_context_files(files, max_chars_per_file=chars_per_file)

        # Should not include all 3 files because aggregate would exceed limit
        file_count = result.count("<FILE")
        assert (
            file_count < 3
        ), f"Expected fewer than 3 files due to aggregate limit, got {file_count}"
        assert "AGGREGATE_LIMIT" in result or file_count < 3


# =============================================================================
# XML Attribute Escaping Tests (Fix #4 - Security Hardening)
# =============================================================================


class TestXmlAttributeEscaping:
    """Tests for proper escaping of file paths in XML attributes."""

    def test_path_with_quotes_is_escaped(self, tmp_path: Path) -> None:
        """Paths containing double quotes must be escaped in XML attributes."""
        # Create a directory with quotes in its name
        quoted_dir = tmp_path / 'has"quote'
        try:
            quoted_dir.mkdir()
            quoted_file = quoted_dir / "test.py"
            quoted_file.write_text("# test")

            result = _read_context_files([str(quoted_file)])

            # The raw quote should NOT appear unescaped in the path attribute
            assert '="' + str(quoted_file) + '"' not in result or "&quot;" in result
            assert "&quot;" in result
        except OSError:
            pytest.skip("Filesystem does not support quotes in filenames")

    def test_path_with_ampersand_is_escaped(self, tmp_path: Path) -> None:
        """Paths containing & must be escaped in XML attributes."""
        amp_dir = tmp_path / "a&b"
        try:
            amp_dir.mkdir()
            amp_file = amp_dir / "test.py"
            amp_file.write_text("# test")

            result = _read_context_files([str(amp_file)])

            assert "&amp;" in result
        except OSError:
            pytest.skip("Filesystem does not support & in filenames")

    def test_path_with_angle_brackets_is_escaped(self) -> None:
        """Paths containing < or > must be escaped in XML attributes."""
        # Angle brackets are typically not allowed in filenames on most OSes.
        # Test the _escape_xml_attr function directly to verify escaping.
        from debate_hall_mcp.tools.orchestrate import _escape_xml_attr

        escaped = _escape_xml_attr("/tmp/test<file>.py")
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "<" not in escaped.replace("&lt;", "").replace("&gt;", "")

    def test_normal_path_not_over_escaped(self, tmp_path: Path) -> None:
        """Normal paths without special chars should not be modified."""
        test_file = tmp_path / "normal.py"
        test_file.write_text("# normal")

        result = _read_context_files([str(test_file)])

        # Path should appear as-is (no unnecessary escaping)
        assert f'path="{test_file}"' in result
        assert "&amp;" not in result
        assert "&quot;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result


# =============================================================================
# Bounded Memory Read Tests (Fix #2 - Security Hardening)
# =============================================================================


class TestBoundedMemoryRead:
    """Tests for chunked/bounded file reading (no full file load)."""

    def test_large_file_only_reads_needed_bytes(self, tmp_path: Path) -> None:
        """Reading should not load entire file into memory when truncating."""
        test_file = tmp_path / "huge.py"
        # Write a large file
        large_content = "x" * 50000
        test_file.write_text(large_content)

        # With max_chars_per_file=100, only ~101 chars should be read
        result = _read_context_files([str(test_file)], max_chars_per_file=100)

        assert "TRUNCATED at 100 chars" in result
        # The content between the FILE open tag and TRUNCATED notice should be
        # exactly 100 x characters (bounded read, not full 50000)
        # Format: <FILE path="...">\nXXX...\n... [TRUNCATED ...]
        file_tag_end = result.find(">\n", result.find("<FILE"))
        truncated_start = result.find("\n... [TRUNCATED")
        file_content = result[file_tag_end + 2 : truncated_start]
        assert len(file_content) == 100
        assert file_content == "x" * 100


# =============================================================================
# _read_context_files Tests
# =============================================================================


class TestReadContextFiles:
    """Tests for _read_context_files file reading and formatting."""

    def test_empty_list_returns_empty_string(self) -> None:
        """Empty context_files list should return empty string (no-op)."""
        result = _read_context_files([])
        assert result == ""

    def test_single_file_returns_codebase_context_block(self, tmp_path: Path) -> None:
        """Single valid file should produce a CODEBASE_CONTEXT block."""
        test_file = tmp_path / "main.py"
        test_file.write_text("def hello():\n    return 'world'")

        result = _read_context_files([str(test_file)])

        assert "<CODEBASE_CONTEXT>" in result
        assert "</CODEBASE_CONTEXT>" in result
        assert f'<FILE path="{test_file}">' in result
        assert "def hello():" in result
        assert "</FILE>" in result

    def test_multiple_files_all_included(self, tmp_path: Path) -> None:
        """Multiple valid files should all appear in the context block."""
        file_a = tmp_path / "a.py"
        file_b = tmp_path / "b.py"
        file_a.write_text("# file A content")
        file_b.write_text("# file B content")

        result = _read_context_files([str(file_a), str(file_b)])

        assert "# file A content" in result
        assert "# file B content" in result
        assert result.count("<FILE") == 2
        assert result.count("</FILE>") == 2

    def test_missing_file_skipped_gracefully(self, tmp_path: Path) -> None:
        """Missing files should be skipped with a warning, not crash."""
        existing_file = tmp_path / "exists.py"
        existing_file.write_text("# exists")
        missing_file = tmp_path / "missing.py"

        result = _read_context_files([str(existing_file), str(missing_file)])

        # Should still have context from the existing file
        assert "<CODEBASE_CONTEXT>" in result
        assert "# exists" in result
        # Missing file should not appear
        assert "missing.py" not in result.split("<FILE")[1] if "<FILE" in result else True

    def test_all_files_missing_returns_empty_string(self, tmp_path: Path) -> None:
        """If all files are missing, should return empty string."""
        result = _read_context_files([str(tmp_path / "nope.py")])
        assert result == ""

    def test_invalid_path_skipped_gracefully(self) -> None:
        """Invalid paths (traversal, relative) should be skipped with warning."""
        result = _read_context_files(["../../etc/passwd", "relative/path.py"])
        assert result == ""

    def test_truncation_at_max_chars(self, tmp_path: Path) -> None:
        """Files exceeding max_chars_per_file should be truncated."""
        test_file = tmp_path / "big.py"
        content = "x" * 20000
        test_file.write_text(content)

        result = _read_context_files([str(test_file)], max_chars_per_file=100)

        assert "TRUNCATED at 100 chars" in result
        # Should not contain the full content
        assert "x" * 20000 not in result

    def test_truncation_uses_default_max_chars(self, tmp_path: Path) -> None:
        """Default truncation limit should be MAX_CHARS_PER_FILE (10000)."""
        test_file = tmp_path / "big.py"
        content = "y" * (MAX_CHARS_PER_FILE + 5000)
        test_file.write_text(content)

        result = _read_context_files([str(test_file)])

        assert f"TRUNCATED at {MAX_CHARS_PER_FILE} chars" in result

    def test_file_at_max_chars_not_truncated(self, tmp_path: Path) -> None:
        """File exactly at max chars should NOT be truncated."""
        test_file = tmp_path / "exact.py"
        content = "z" * MAX_CHARS_PER_FILE
        test_file.write_text(content)

        result = _read_context_files([str(test_file)])

        assert "TRUNCATED" not in result
        assert content in result

    def test_preserves_file_path_in_tag(self, tmp_path: Path) -> None:
        """FILE tag should contain the original file path."""
        test_file = tmp_path / "module.py"
        test_file.write_text("import os")

        result = _read_context_files([str(test_file)])

        assert f'<FILE path="{test_file}">' in result

    def test_mixed_valid_and_invalid_files(self, tmp_path: Path) -> None:
        """Mix of valid and invalid files: valid ones included, invalid skipped."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("# valid content")

        result = _read_context_files(
            [
                str(valid_file),
                "../../etc/shadow",
                str(tmp_path / "nonexistent.py"),
            ]
        )

        assert "<CODEBASE_CONTEXT>" in result
        assert "# valid content" in result
        assert "shadow" not in result


# =============================================================================
# Orchestrator Context Block Injection Tests
# =============================================================================


class TestOrchestratorContextBlockInjection:
    """Tests for context_block injection into agent prompts."""

    @pytest.fixture
    def mock_provider_factory(self) -> MagicMock:
        """Create a mock provider factory that returns mock providers."""
        from debate_hall_mcp.providers import ProviderResponse

        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(
            return_value=ProviderResponse(
                content="Mock response content",
                model="mock-model",
                token_input=100,
                token_output=50,
            )
        )

        def factory(_config: RoleConfig) -> MagicMock:
            return mock_provider

        return MagicMock(side_effect=factory)

    def test_orchestrator_stores_context_block(self, tmp_path: Path) -> None:
        """Orchestrator should store context_block for later injection."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        context = "<CODEBASE_CONTEXT>\n<FILE>test</FILE>\n</CODEBASE_CONTEXT>"
        orchestrator = DebateOrchestrator(tier_config, tmp_path, context_block=context)

        assert orchestrator._context_block == context

    def test_orchestrator_default_context_block_is_none(self, tmp_path: Path) -> None:
        """Orchestrator context_block defaults to None."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(),
        )
        orchestrator = DebateOrchestrator(tier_config, tmp_path)

        assert orchestrator._context_block is None

    @pytest.mark.anyio
    async def test_context_block_injected_before_debate_state(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """Context block should appear BEFORE <DEBATE_STATE> in enhanced prompt."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none", compression_tier="none"),
        )
        context_block = '<CODEBASE_CONTEXT>\n<FILE path="test.py">\ndef foo(): pass\n</FILE>\n</CODEBASE_CONTEXT>'
        orchestrator = DebateOrchestrator(
            tier_config,
            tmp_path,
            provider_factory=mock_provider_factory,
            context_block=context_block,
        )

        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="Test prompt",
                    timeout=60,
                )

                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                # Context should appear before DEBATE_STATE
                context_pos = user_prompt.find("<CODEBASE_CONTEXT>")
                state_pos = user_prompt.find("<DEBATE_STATE>")
                assert context_pos >= 0, "CODEBASE_CONTEXT should be present"
                assert state_pos >= 0, "DEBATE_STATE should be present"
                assert context_pos < state_pos, "CODEBASE_CONTEXT should appear before DEBATE_STATE"

    @pytest.mark.anyio
    async def test_no_context_block_means_no_injection(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """When context_block is None, no CODEBASE_CONTEXT should appear."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none", compression_tier="none"),
        )
        orchestrator = DebateOrchestrator(
            tier_config,
            tmp_path,
            provider_factory=mock_provider_factory,
            context_block=None,
        )

        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="Test prompt",
                    timeout=60,
                )

                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                assert "<CODEBASE_CONTEXT>" not in user_prompt

    @pytest.mark.anyio
    async def test_context_block_injected_in_raci_mode(
        self, tmp_path: Path, mock_provider_factory: MagicMock
    ) -> None:
        """Context block should also be injected in RACI mode prompts."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(primer_tier="none", compression_tier="none"),
        )
        context_block = (
            '<CODEBASE_CONTEXT>\n<FILE path="raci.py">\n# raci\n</FILE>\n</CODEBASE_CONTEXT>'
        )
        orchestrator = DebateOrchestrator(
            tier_config,
            tmp_path,
            provider_factory=mock_provider_factory,
            context_block=context_block,
        )

        with patch.object(orchestrator, "_format_debate_state") as mock_format:
            mock_format.return_value = "<DEBATE_STATE>\ntest state\n</DEBATE_STATE>"
            with (
                patch("debate_hall_mcp.orchestrator.debate_get") as mock_get,
                patch("debate_hall_mcp.orchestrator.debate_turn"),
                patch("debate_hall_mcp.orchestrator.append_event"),
            ):
                mock_get.return_value = {
                    "thread_id": "test",
                    "topic": "test",
                    "status": "active",
                    "turn_count": 0,
                }

                provider = mock_provider_factory(tier_config.wind)
                await orchestrator._execute_raci_role_turn(
                    role="Wind",
                    provider=provider,
                    thread_id="test-thread",
                    user_prompt="RACI prompt",
                    timeout=60,
                )

                call_args = provider.complete.call_args
                user_prompt = call_args.kwargs.get("user_prompt") or call_args[1]["user_prompt"]

                assert "<CODEBASE_CONTEXT>" in user_prompt
                context_pos = user_prompt.find("<CODEBASE_CONTEXT>")
                state_pos = user_prompt.find("<DEBATE_STATE>")
                assert context_pos < state_pos


# =============================================================================
# run_debate Tool Integration Tests
# =============================================================================


class TestRunDebateContextFiles:
    """Tests for context_files parameter in run_debate tool."""

    @pytest.fixture
    def mock_tier_config(self) -> TierConfig:
        """Create a mock tier config."""
        return TierConfig(
            wind=RoleConfig(provider="cli", cli="claude", role="wind-agent"),
            wall=RoleConfig(provider="cli", cli="codex", role="wall-agent"),
            door=RoleConfig(provider="cli", cli="gemini", role="door-agent"),
            settings=TierSettings(consensus_required=False),
        )

    @pytest.fixture
    def mock_debate_result(self) -> DebateResult:
        """Create a mock debate result."""
        return DebateResult(
            thread_id="2026-01-30-test-topic-abc12345",
            topic="Test topic",
            status="synthesis",
            turn_count=3,
            synthesis="Final synthesis",
        )

    @pytest.mark.anyio
    async def test_run_debate_accepts_context_files(
        self,
        tmp_path: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate should accept context_files parameter without error."""
        context_file = tmp_path / "context.py"
        context_file.write_text("# context code")

        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_dir,
            patch("debate_hall_mcp.tools.orchestrate.DebateOrchestrator") as mock_orch_cls,
        ):
            mock_load.return_value = mock_tier_config
            mock_dir.return_value = tmp_path

            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_debate_result)
            mock_orch_cls.return_value = mock_orch

            result = await run_debate(
                topic="Test topic",
                context_files=[str(context_file)],
            )

        assert result["status"] == "synthesis"

    @pytest.mark.anyio
    async def test_run_debate_passes_context_block_to_orchestrator(
        self,
        tmp_path: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate should pass formatted context block to DebateOrchestrator."""
        context_file = tmp_path / "module.py"
        context_file.write_text("class MyClass:\n    pass")

        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_dir,
            patch("debate_hall_mcp.tools.orchestrate.DebateOrchestrator") as mock_orch_cls,
        ):
            mock_load.return_value = mock_tier_config
            mock_dir.return_value = tmp_path

            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_debate_result)
            mock_orch_cls.return_value = mock_orch

            await run_debate(
                topic="Test topic",
                context_files=[str(context_file)],
            )

        # Verify DebateOrchestrator was created with context_block
        call_kwargs = mock_orch_cls.call_args
        assert "context_block" in call_kwargs.kwargs
        assert call_kwargs.kwargs["context_block"] is not None
        assert "<CODEBASE_CONTEXT>" in call_kwargs.kwargs["context_block"]
        assert "class MyClass:" in call_kwargs.kwargs["context_block"]

    @pytest.mark.anyio
    async def test_run_debate_none_context_files_no_context_block(
        self,
        tmp_path: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate with None context_files should pass None context_block."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_dir,
            patch("debate_hall_mcp.tools.orchestrate.DebateOrchestrator") as mock_orch_cls,
        ):
            mock_load.return_value = mock_tier_config
            mock_dir.return_value = tmp_path

            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_debate_result)
            mock_orch_cls.return_value = mock_orch

            await run_debate(topic="Test topic", context_files=None)

        call_kwargs = mock_orch_cls.call_args
        assert call_kwargs.kwargs.get("context_block") is None

    @pytest.mark.anyio
    async def test_run_debate_empty_context_files_no_context_block(
        self,
        tmp_path: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate with empty context_files should pass None context_block."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_dir,
            patch("debate_hall_mcp.tools.orchestrate.DebateOrchestrator") as mock_orch_cls,
        ):
            mock_load.return_value = mock_tier_config
            mock_dir.return_value = tmp_path

            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_debate_result)
            mock_orch_cls.return_value = mock_orch

            await run_debate(topic="Test topic", context_files=[])

        call_kwargs = mock_orch_cls.call_args
        assert call_kwargs.kwargs.get("context_block") is None

    @pytest.mark.anyio
    async def test_run_debate_missing_files_still_succeeds(
        self,
        tmp_path: Path,
        mock_tier_config: TierConfig,
        mock_debate_result: DebateResult,
    ) -> None:
        """run_debate with all missing context_files should still run the debate."""
        with (
            patch("debate_hall_mcp.tools.orchestrate.load_tier_config") as mock_load,
            patch("debate_hall_mcp.tools.orchestrate.get_state_dir") as mock_dir,
            patch("debate_hall_mcp.tools.orchestrate.DebateOrchestrator") as mock_orch_cls,
        ):
            mock_load.return_value = mock_tier_config
            mock_dir.return_value = tmp_path

            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_debate_result)
            mock_orch_cls.return_value = mock_orch

            result = await run_debate(
                topic="Test topic",
                context_files=[str(tmp_path / "nonexistent.py")],
            )

        # Debate should still succeed
        assert result["status"] == "synthesis"
        # context_block should be None since no files could be read
        call_kwargs = mock_orch_cls.call_args
        assert call_kwargs.kwargs.get("context_block") is None
