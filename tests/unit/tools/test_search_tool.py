"""Tests for search_decisions MCP tool wrapper.

Issue #144: Decision Indexing & BM25 Search

Tests cover:
- Tool returns search results as JSON-compatible list
- Tool handles empty results gracefully
- Tool respects limit parameter
- Tool respects min_score parameter
"""

from datetime import UTC, datetime
from pathlib import Path

from debate_hall_mcp.decision import DecisionRecord


class TestSearchDecisionsTool:
    """Tests for search_decisions MCP tool wrapper."""

    def test_search_decisions_returns_list(self, tmp_path: Path) -> None:
        """Tool returns list of search results."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        # Setup: Create a decision
        context_dir = tmp_path / ".hestai" / "context"
        record = DecisionRecord(
            thread_id="2026-02-08-search-test",
            topic="OAuth2 Authentication Strategy",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use OAuth2 with JWT tokens.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        # Execute
        result = search_decisions(
            query="authentication",
            context_dir=context_dir,
        )

        # Verify
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_decisions_returns_expected_fields(self, tmp_path: Path) -> None:
        """Tool results contain expected fields."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"
        record = DecisionRecord(
            thread_id="2026-02-08-fields-test",
            topic="Database Architecture",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use PostgreSQL for primary data.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        result = search_decisions(
            query="database",
            context_dir=context_dir,
        )

        assert len(result["results"]) >= 1
        first_result = result["results"][0]
        assert "thread_id" in first_result
        assert "topic" in first_result
        assert "synthesis" in first_result
        assert "score" in first_result
        assert "decided_at" in first_result
        assert "file_path" in first_result

    def test_search_decisions_empty_results(self, tmp_path: Path) -> None:
        """Tool returns empty list for no matches."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"
        record = DecisionRecord(
            thread_id="2026-02-08-empty-test",
            topic="Specific Topic",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Specific synthesis.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        result = search_decisions(
            query="xyznonexistent",
            context_dir=context_dir,
        )

        assert result["results"] == []
        assert result["count"] == 0

    def test_search_decisions_respects_limit(self, tmp_path: Path) -> None:
        """Tool respects limit parameter."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"

        # Create 5 decisions
        for i in range(5):
            record = DecisionRecord(
                thread_id=f"2026-02-08-limit-test-{i}",
                topic=f"Test Topic {i}",
                decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
                synthesis=f"Test synthesis {i}.",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        result = search_decisions(
            query="test",
            limit=2,
            context_dir=context_dir,
        )

        assert len(result["results"]) == 2

    def test_search_decisions_respects_min_score(self, tmp_path: Path) -> None:
        """Tool respects min_score parameter."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"

        # High relevance decision
        record1 = DecisionRecord(
            thread_id="2026-02-08-high-score",
            topic="OAuth2 Authentication Strategy",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="OAuth2 provides authentication.",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source1",
        )
        export_decision_to_context(record1, context_dir)

        # Low relevance decision
        record2 = DecisionRecord(
            thread_id="2026-02-08-low-score",
            topic="Database Choice",
            decided_at=datetime(2026, 2, 8, 11, 0, 0, tzinfo=UTC),
            synthesis="Use PostgreSQL.",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 11, 5, 0, tzinfo=UTC),
            source_hash="source2",
        )
        export_decision_to_context(record2, context_dir)

        # High threshold should filter out low-scoring results
        result = search_decisions(
            query="OAuth2 authentication",
            min_score=0.5,
            context_dir=context_dir,
        )

        # All results should have score >= 0.5
        for r in result["results"]:
            assert r["score"] >= 0.5

    def test_search_decisions_includes_metadata(self, tmp_path: Path) -> None:
        """Tool result includes search metadata."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"
        record = DecisionRecord(
            thread_id="2026-02-08-meta-test",
            topic="Metadata Test",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        result = search_decisions(
            query="metadata",
            context_dir=context_dir,
        )

        assert "count" in result
        assert "query" in result
        assert result["query"] == "metadata"

    def test_search_decisions_empty_corpus(self, tmp_path: Path) -> None:
        """Tool handles empty decisions directory."""
        from debate_hall_mcp.tools.search import search_decisions

        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        result = search_decisions(
            query="anything",
            context_dir=context_dir,
        )

        assert result["results"] == []
        assert result["count"] == 0


class TestSearchDecisionsToolIntegration:
    """Integration tests with server registration."""

    def test_search_decisions_is_registered(self) -> None:
        """search_decisions tool is registered in server."""
        from debate_hall_mcp.server import create_server

        server = create_server()
        # Get registered tool names
        tool_names = [tool.name for tool in server._tool_manager.list_tools()]

        assert "search_decisions" in tool_names
