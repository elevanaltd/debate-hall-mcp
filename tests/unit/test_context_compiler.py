"""Tests for Context Compiler - exporting decisions to .hestai/state/context/decisions/.

Issue #138: Layer 3 Query Enhancements - Decision Indexing

The Context Compiler feature exports DecisionRecords as compiled OCTAVE files
that can be read by future agents as part of their binding context.

TDD Discipline: RED->GREEN->REFACTOR
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.decision import DecisionRecord


class TestDecisionRecordToOctave:
    """Test converting DecisionRecord to OCTAVE format."""

    def test_format_decision_as_octave_returns_valid_octave(self) -> None:
        """format_decision_as_octave returns valid OCTAVE string."""
        from debate_hall_mcp.context_compiler import format_decision_as_octave

        record = DecisionRecord(
            thread_id="2026-01-15-test-decision",
            topic="Should we use TypeScript?",
            decided_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
            synthesis="Yes, TypeScript provides type safety benefits.",
            decision_hash="abc123def456",
            status="synthesis",
            extracted_at=datetime(2026, 1, 15, 12, 5, 0, tzinfo=UTC),
            source_hash="source123",
            wind_perspectives=["TypeScript improves developer experience"],
            wall_constraints=["Learning curve concern"],
            door_refinements=[],
            consensus_reached=True,
            consensus_votes={"wind": True, "wall": True},
            refinement_count=0,
            turn_count=3,
        )

        result = format_decision_as_octave(record)

        # Must be a string
        assert isinstance(result, str)
        # Must have OCTAVE document structure
        assert "===COMPILED_DECISION===" in result
        assert "===END===" in result
        # Must contain key fields
        assert "2026-01-15-test-decision" in result
        assert "Should we use TypeScript?" in result
        assert "Yes, TypeScript provides type safety benefits." in result

    def test_format_decision_includes_metadata(self) -> None:
        """OCTAVE output includes all metadata fields."""
        from debate_hall_mcp.context_compiler import format_decision_as_octave

        record = DecisionRecord(
            thread_id="2026-01-20-metadata-test",
            topic="Metadata test topic",
            decided_at=datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis",
            decision_hash="hash123",
            status="synthesis",
            extracted_at=datetime(2026, 1, 20, 10, 5, 0, tzinfo=UTC),
            source_hash="source456",
            consensus_reached=True,
            consensus_votes={"wind": True, "wall": True},
            refinement_count=2,
            turn_count=6,
        )

        result = format_decision_as_octave(record)

        # Check META section
        assert "META:" in result
        assert "TYPE::COMPILED_DECISION" in result
        assert "THREAD_ID::" in result
        # Check OUTCOME section
        assert "STATUS::synthesis" in result
        # Check VALIDATION section
        assert "CONSENSUS_REACHED::true" in result
        assert "REFINEMENT_COUNT::2" in result

    def test_format_decision_escapes_special_characters(self) -> None:
        """OCTAVE output escapes special characters in content."""
        from debate_hall_mcp.context_compiler import format_decision_as_octave

        record = DecisionRecord(
            thread_id="2026-01-21-escape-test",
            topic='Topic with "quotes" and\nnewlines',
            decided_at=datetime(2026, 1, 21, 10, 0, 0, tzinfo=UTC),
            synthesis='Synthesis with\ttabs and "quoted" text',
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 1, 21, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        result = format_decision_as_octave(record)

        # Newlines should be escaped
        assert "\\n" in result or "\n" not in result.split("===")[1]
        # Quotes should be escaped
        assert '\\"' in result or "quotes" in result


class TestExportDecisionToContext:
    """Test exporting DecisionRecord to context directory."""

    def test_export_creates_file_in_decisions_directory(self, tmp_path: Path) -> None:
        """export_decision_to_context creates file in decisions/ subdirectory."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-01-22-export-test",
            topic="Export test topic",
            decided_at=datetime(2026, 1, 22, 14, 0, 0, tzinfo=UTC),
            synthesis="Export test synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 1, 22, 14, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        context_dir = tmp_path / ".hestai" / "context"
        result_path = export_decision_to_context(record, context_dir)

        # File should be created in decisions/ subdirectory
        assert result_path.exists()
        assert result_path.parent.name == "decisions"
        assert result_path.parent.parent == context_dir

    def test_export_filename_follows_convention(self, tmp_path: Path) -> None:
        """Filename follows {YYYY-MM-DD}-{topic-slug}-{short_id}.oct.md convention."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-01-25-naming-test",
            topic="Should We Use MicroServices",
            decided_at=datetime(2026, 1, 25, 10, 0, 0, tzinfo=UTC),
            synthesis="Test",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 1, 25, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        context_dir = tmp_path / ".hestai" / "context"
        result_path = export_decision_to_context(record, context_dir)

        # Filename should follow convention
        assert result_path.suffix == ".md"
        assert ".oct" in result_path.name
        # Should include date
        assert "2026-01-25" in result_path.name
        # Should include slugified topic
        assert "should-we-use-microservices" in result_path.name.lower()
        # Should include short_id from thread_id (last hyphen-separated segment)
        # thread_id is "2026-01-25-naming-test", last segment is "test"
        assert "-test.oct.md" in result_path.name.lower()

    def test_export_file_contains_valid_octave(self, tmp_path: Path) -> None:
        """Exported file contains valid OCTAVE content."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-01-26-content-test",
            topic="Content validation test",
            decided_at=datetime(2026, 1, 26, 10, 0, 0, tzinfo=UTC),
            synthesis="This is the final decision content",
            decision_hash="abc123",
            status="synthesis",
            extracted_at=datetime(2026, 1, 26, 10, 5, 0, tzinfo=UTC),
            source_hash="def456",
            wind_perspectives=["Perspective A", "Perspective B"],
            wall_constraints=["Constraint X"],
            turn_count=4,
        )

        context_dir = tmp_path / ".hestai" / "context"
        result_path = export_decision_to_context(record, context_dir)

        content = result_path.read_text()

        # Validate structure
        assert "===COMPILED_DECISION===" in content
        assert "===END===" in content
        assert "This is the final decision content" in content
        assert "Perspective A" in content or "RATIONALE" in content

    def test_export_creates_decisions_directory_if_missing(self, tmp_path: Path) -> None:
        """Creates decisions/ directory if it doesn't exist."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-01-27-mkdir-test",
            topic="Directory creation test",
            decided_at=datetime(2026, 1, 27, 10, 0, 0, tzinfo=UTC),
            synthesis="Test",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 1, 27, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        # Context dir doesn't exist yet
        context_dir = tmp_path / ".hestai" / "context"
        assert not context_dir.exists()

        result_path = export_decision_to_context(record, context_dir)

        # Should have created the directories
        assert (context_dir / "decisions").exists()
        assert result_path.exists()

    def test_export_returns_absolute_path(self, tmp_path: Path) -> None:
        """export_decision_to_context returns absolute path."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-01-28-path-test",
            topic="Path test",
            decided_at=datetime(2026, 1, 28, 10, 0, 0, tzinfo=UTC),
            synthesis="Test",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 1, 28, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        context_dir = tmp_path / ".hestai" / "context"
        result_path = export_decision_to_context(record, context_dir)

        assert result_path.is_absolute()

    def test_export_filename_uniqueness_prevents_overwrite(self, tmp_path: Path) -> None:
        """Same topic on same day with different thread_ids creates unique files."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        # Two debates on same topic, same day, different thread_ids
        record1 = DecisionRecord(
            thread_id="2026-01-30-api-design-morning",
            topic="API Design",
            decided_at=datetime(2026, 1, 30, 9, 0, 0, tzinfo=UTC),
            synthesis="Morning decision: REST",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 1, 30, 9, 5, 0, tzinfo=UTC),
            source_hash="source1",
        )

        record2 = DecisionRecord(
            thread_id="2026-01-30-api-design-afternoon",
            topic="API Design",
            decided_at=datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC),
            synthesis="Afternoon decision: GraphQL",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 1, 30, 14, 5, 0, tzinfo=UTC),
            source_hash="source2",
        )

        context_dir = tmp_path / ".hestai" / "context"

        # Export both
        path1 = export_decision_to_context(record1, context_dir)
        path2 = export_decision_to_context(record2, context_dir)

        # Paths must be different (uniqueness)
        assert path1 != path2

        # Both files must exist (no overwrite)
        assert path1.exists()
        assert path2.exists()

        # Content should be different
        content1 = path1.read_text()
        content2 = path2.read_text()
        assert "Morning decision: REST" in content1
        assert "Afternoon decision: GraphQL" in content2

    def test_export_filename_uses_short_id_from_thread_id(self, tmp_path: Path) -> None:
        """Short ID is extracted from the last segment of thread_id."""
        from debate_hall_mcp.context_compiler import export_decision_to_context

        record = DecisionRecord(
            thread_id="2026-02-01-complex-topic-abc123",
            topic="Complex Topic",
            decided_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC),
            synthesis="Test",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 1, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )

        context_dir = tmp_path / ".hestai" / "context"
        result_path = export_decision_to_context(record, context_dir)

        # Filename should include the short_id "abc123"
        assert "abc123" in result_path.name.lower()


class TestSlugifyTopic:
    """Test topic slugification for filenames."""

    def test_slugify_converts_to_lowercase(self) -> None:
        """Slug is lowercase."""
        from debate_hall_mcp.context_compiler import slugify_topic

        assert slugify_topic("UPPERCASE") == "uppercase"

    def test_slugify_replaces_spaces_with_hyphens(self) -> None:
        """Spaces become hyphens."""
        from debate_hall_mcp.context_compiler import slugify_topic

        assert slugify_topic("hello world") == "hello-world"

    def test_slugify_removes_special_characters(self) -> None:
        """Special characters are removed."""
        from debate_hall_mcp.context_compiler import slugify_topic

        result = slugify_topic("What's the plan?")
        assert "'" not in result
        assert "?" not in result

    def test_slugify_truncates_long_topics(self) -> None:
        """Long topics are truncated to reasonable length."""
        from debate_hall_mcp.context_compiler import slugify_topic

        long_topic = "This is a very long topic that should be truncated " * 5
        result = slugify_topic(long_topic)

        # Should be reasonable length for a filename
        assert len(result) <= 60

    def test_slugify_handles_empty_topic(self) -> None:
        """Empty topic returns 'untitled'."""
        from debate_hall_mcp.context_compiler import slugify_topic

        assert slugify_topic("") == "untitled"
        assert slugify_topic("   ") == "untitled"


class TestIntegrationWithDebateClose:
    """Test integration of Context Compiler with debate_close tool."""

    def test_close_debate_with_export_flag(self, tmp_path: Path) -> None:
        """debate_close with export_decision=True exports to context."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        state_dir = tmp_path / "debates"
        context_dir = tmp_path / ".hestai" / "context"

        debate_init(
            thread_id="2026-02-01-export-integration",
            topic="Export integration test",
            octave_mode=False,
            state_dir=state_dir,
        )

        result = debate_close(
            thread_id="2026-02-01-export-integration",
            synthesis="Final decision for export test",
            state_dir=state_dir,
            export_decision=True,
            context_dir=context_dir,
        )

        # Should return export path in result
        assert "export_path" in result
        export_path = Path(result["export_path"])
        assert export_path.exists()
        assert (context_dir / "decisions").exists()

    def test_close_debate_without_export_flag_does_not_export(self, tmp_path: Path) -> None:
        """debate_close without export_decision=True does not export."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        state_dir = tmp_path / "debates"
        context_dir = tmp_path / ".hestai" / "context"

        debate_init(
            thread_id="2026-02-02-no-export",
            topic="No export test",
            octave_mode=False,
            state_dir=state_dir,
        )

        result = debate_close(
            thread_id="2026-02-02-no-export",
            synthesis="Final decision without export",
            state_dir=state_dir,
            # export_decision defaults to False
        )

        # Should NOT have export_path in result
        assert "export_path" not in result
        # decisions directory should not be created
        assert not (context_dir / "decisions").exists()

    def test_close_debate_export_uses_default_context_dir(self, tmp_path: Path) -> None:
        """debate_close with export uses project-relative context dir by default."""
        from debate_hall_mcp.tools.close import debate_close
        from debate_hall_mcp.tools.init import debate_init

        state_dir = tmp_path / "debates"

        debate_init(
            thread_id="2026-02-03-default-dir",
            topic="Default directory test",
            octave_mode=False,
            state_dir=state_dir,
        )

        # Set up a mock project root with .git marker
        (tmp_path / ".git").mkdir()

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = debate_close(
                thread_id="2026-02-03-default-dir",
                synthesis="Final decision",
                state_dir=state_dir,
                export_decision=True,
                # context_dir not specified - should use project-relative default
            )

            assert "export_path" in result
            export_path = Path(result["export_path"])
            # Should be in .hestai/state/context/decisions relative to project root
            # (Tier 3 three-tier architecture alignment)
            assert ".hestai" in str(export_path)
            assert "state" in str(export_path)
            assert "decisions" in str(export_path)
        finally:
            os.chdir(old_cwd)


class TestDecisionIndex:
    """Test decision indexing for discovery."""

    def test_list_decisions_returns_all_exported_decisions(self, tmp_path: Path) -> None:
        """list_decisions returns all decision files in context/decisions/."""
        from debate_hall_mcp.context_compiler import (
            export_decision_to_context,
            list_decisions,
        )

        context_dir = tmp_path / ".hestai" / "context"

        # Export multiple decisions
        for i in range(3):
            record = DecisionRecord(
                thread_id=f"2026-02-0{i + 1}-decision-{i}",
                topic=f"Decision topic {i}",
                decided_at=datetime(2026, 2, i + 1, 10, 0, 0, tzinfo=UTC),
                synthesis=f"Synthesis {i}",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, i + 1, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        decisions = list_decisions(context_dir)

        assert len(decisions) == 3
        # Should return paths
        assert all(isinstance(d, Path) for d in decisions)
        # All should have .oct.md extension
        assert all(".oct.md" in d.name for d in decisions)

    def test_list_decisions_empty_when_no_decisions(self, tmp_path: Path) -> None:
        """list_decisions returns empty list when no decisions exported."""
        from debate_hall_mcp.context_compiler import list_decisions

        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        decisions = list_decisions(context_dir)

        assert decisions == []

    def test_list_decisions_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """list_decisions creates decisions directory if it doesn't exist."""
        from debate_hall_mcp.context_compiler import list_decisions

        context_dir = tmp_path / ".hestai" / "context"
        # Don't create the directory

        decisions = list_decisions(context_dir)

        assert decisions == []
        # Should have created the directory
        assert (context_dir / "decisions").exists()


class TestExtractShortIdValidation:
    """Defense-in-depth validation for _extract_short_id (PR#191 CE finding).

    Although thread_id is validated upstream at debate creation, a DecisionRecord
    reaching _extract_short_id from another caller (e.g. import, external tool)
    could carry path separators or traversal tokens. This validator must reject
    such inputs at the boundary so the resulting filename suffix cannot break
    out of the decisions/ directory.
    """

    def test_extract_short_id_rejects_forward_slash(self) -> None:
        """Thread_id containing '/' must be rejected (path separator)."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("2026-01-30-evil/segment")

    def test_extract_short_id_rejects_backslash(self) -> None:
        """Thread_id containing '\\' must be rejected (Windows path separator)."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("2026-01-30-evil\\segment")

    def test_extract_short_id_rejects_parent_traversal(self) -> None:
        """Thread_id containing '..' must be rejected (path traversal)."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("2026-01-30-..-escape")

    def test_extract_short_id_rejects_null_byte(self) -> None:
        """Thread_id containing NUL byte must be rejected (control char)."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("2026-01-30-null\x00byte")

    def test_extract_short_id_rejects_newline(self) -> None:
        """Thread_id containing newline must be rejected (control char)."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("2026-01-30-line\nbreak")

    def test_extract_short_id_rejects_empty(self) -> None:
        """Empty thread_id must be rejected."""
        import pytest

        from debate_hall_mcp.context_compiler import _extract_short_id

        with pytest.raises(ValueError, match="invalid"):
            _extract_short_id("")

    def test_extract_short_id_accepts_valid_hyphenated(self) -> None:
        """Valid hyphenated thread_id returns last segment."""
        from debate_hall_mcp.context_compiler import _extract_short_id

        assert _extract_short_id("2026-01-30-api-design-morning") == "morning"

    def test_extract_short_id_accepts_valid_alphanumeric(self) -> None:
        """Valid alphanumeric thread_id returns first 8 chars."""
        from debate_hall_mcp.context_compiler import _extract_short_id

        assert _extract_short_id("abc123def456") == "abc123de"

    def test_extract_short_id_accepts_underscores(self) -> None:
        """Underscores are permitted in thread_ids (valid filename char)."""
        from debate_hall_mcp.context_compiler import _extract_short_id

        # Underscore must not be rejected; treated as no-hyphen path
        result = _extract_short_id("abc_def_ghi")
        assert result == "abc_def_"


class TestGetContextDir:
    """Test get_context_dir() path resolution for three-tier architecture."""

    def test_get_context_dir_returns_tier3_state_path(self, tmp_path: Path) -> None:
        """get_context_dir returns .hestai/state/context (Tier 3) by default."""
        import os

        from debate_hall_mcp.context_compiler import get_context_dir

        # Set up a mock project root with .git marker
        (tmp_path / ".git").mkdir()

        old_cwd = os.getcwd()
        # Clear env var if set
        old_env = os.environ.pop("DEBATE_HALL_CONTEXT_DIR", None)
        try:
            os.chdir(tmp_path)
            result = get_context_dir()

            # Should resolve to .hestai/state/context (Tier 3)
            assert result == tmp_path / ".hestai" / "state" / "context"
        finally:
            os.chdir(old_cwd)
            if old_env is not None:
                os.environ["DEBATE_HALL_CONTEXT_DIR"] = old_env

    def test_get_context_dir_falls_back_to_cwd_when_project_root_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When find_project_root() raises, fall back to Path.cwd()/.hestai/state/context.

        TMG finding (PR#191): the fallback branch in get_context_dir was untested.
        """
        import os

        from debate_hall_mcp import context_compiler

        # Force find_project_root to raise (simulate no .git/no markers found)
        def _raise(*_args: object, **_kwargs: object) -> "Path":
            raise FileNotFoundError("project root not found")

        monkeypatch.setattr(context_compiler, "find_project_root", _raise, raising=False)
        # Also patch the import location since get_context_dir imports it locally
        from debate_hall_mcp import state as state_module

        monkeypatch.setattr(state_module, "find_project_root", _raise)

        # Clear env var so we exercise the fallback rather than env override
        monkeypatch.delenv("DEBATE_HALL_CONTEXT_DIR", raising=False)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = context_compiler.get_context_dir()
            assert result == tmp_path / ".hestai" / "state" / "context"
        finally:
            os.chdir(old_cwd)

    def test_get_context_dir_respects_env_var_override(self, tmp_path: Path) -> None:
        """get_context_dir respects DEBATE_HALL_CONTEXT_DIR env var override."""
        import os

        from debate_hall_mcp.context_compiler import get_context_dir

        custom_dir = tmp_path / "custom" / "context"
        old_env = os.environ.get("DEBATE_HALL_CONTEXT_DIR")
        try:
            os.environ["DEBATE_HALL_CONTEXT_DIR"] = str(custom_dir)
            result = get_context_dir()

            assert result == custom_dir
        finally:
            if old_env is not None:
                os.environ["DEBATE_HALL_CONTEXT_DIR"] = old_env
            else:
                os.environ.pop("DEBATE_HALL_CONTEXT_DIR", None)
