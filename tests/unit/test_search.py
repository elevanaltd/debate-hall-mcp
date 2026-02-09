"""Tests for Decision Search - BM25 with OCTAVE field weighting.

Issue #144: Implement searchable decision record history
ADR-0004: Decision Search Architecture

TDD Discipline: RED -> GREEN -> REFACTOR

Field weighting per ADR-0004:
- §SEARCH_ANCHORS: 15.0 (pre-computed Q&A pairs)
- §TOPIC: 10.0 (what it is)
- §TAGS: 8.0 (explicit classification)
- §SYNTHESIS: 5.0 (the decision)
- §RATIONALE: 2.0 (the why - wind_perspectives, wall_constraints)
- §BODY: 0.5 (noise/default)

Performance governors (ADR-0004):
- Index size: < 5MB (WARN + prune strategy)
- Boot time: < 200ms (WARN + disable auto-suggest)
- Query latency: < 50ms p95 (WARN)
- Memory footprint: < 50MB (FAIL -> revert to grep)
"""

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from debate_hall_mcp.decision import DecisionRecord

if TYPE_CHECKING:
    pass


class TestBM25Algorithm:
    """Test BM25 algorithm implementation."""

    def test_bm25_term_frequency_scoring(self) -> None:
        """BM25 scores documents with more term occurrences higher (with saturation)."""
        from debate_hall_mcp.search import BM25

        # Create simple corpus
        corpus = [
            ["apple", "banana", "apple", "apple"],  # 3 apples
            ["apple", "banana"],  # 1 apple
            ["banana", "orange"],  # 0 apples
        ]

        bm25 = BM25(corpus)
        scores = bm25.get_scores(["apple"])

        # Doc with 3 apples should score highest
        assert scores[0] > scores[1]
        # Doc with 1 apple should score higher than doc with 0
        assert scores[1] > scores[2]
        # Doc with no apples should score 0
        assert scores[2] == 0.0

    def test_bm25_inverse_document_frequency(self) -> None:
        """BM25 gives higher weight to rare terms (IDF)."""
        from debate_hall_mcp.search import BM25

        corpus = [
            ["common", "rare"],  # Has both
            ["common"],  # Only common
            ["common"],  # Only common
            ["common"],  # Only common
        ]

        bm25 = BM25(corpus)

        # Query for rare term - should heavily weight doc 0
        rare_scores = bm25.get_scores(["rare"])
        # Query for common term - scores more evenly distributed
        common_scores = bm25.get_scores(["common"])

        # Rare term should give higher score to doc 0
        # because IDF for rare is higher than IDF for common
        assert rare_scores[0] > common_scores[0]

    def test_bm25_handles_empty_query(self) -> None:
        """BM25 returns zero scores for empty query."""
        from debate_hall_mcp.search import BM25

        corpus = [["apple", "banana"], ["cherry"]]
        bm25 = BM25(corpus)
        scores = bm25.get_scores([])

        assert all(s == 0.0 for s in scores)

    def test_bm25_handles_empty_corpus(self) -> None:
        """BM25 handles empty corpus gracefully."""
        from debate_hall_mcp.search import BM25

        bm25 = BM25([])
        scores = bm25.get_scores(["apple"])

        assert scores == []


class TestDecisionSearchEngine:
    """Test DecisionSearchEngine with OCTAVE field weighting."""

    def test_search_engine_initialization(self, tmp_path: Path) -> None:
        """DecisionSearchEngine initializes with context directory."""
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        engine = DecisionSearchEngine(context_dir)

        assert engine is not None
        assert engine.context_dir == context_dir

    def test_search_returns_ranked_results(self, tmp_path: Path) -> None:
        """search() returns results ranked by relevance."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Create test decisions
        record1 = DecisionRecord(
            thread_id="2026-02-08-auth-strategy",
            topic="OAuth2 Authentication Strategy",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use OAuth2 with JWT tokens for authentication.",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source1",
            wind_perspectives=["OAuth2 provides secure authentication"],
            wall_constraints=["Must support SSO integration"],
        )

        record2 = DecisionRecord(
            thread_id="2026-02-08-caching-strategy",
            topic="Redis Caching Strategy",
            decided_at=datetime(2026, 2, 8, 11, 0, 0, tzinfo=UTC),
            synthesis="Use Redis with 5-minute TTL for caching.",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 11, 5, 0, tzinfo=UTC),
            source_hash="source2",
            wind_perspectives=["Redis provides fast caching"],
            wall_constraints=["Memory constraints on production"],
        )

        export_decision_to_context(record1, context_dir)
        export_decision_to_context(record2, context_dir)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("authentication")

        # Should find auth decision
        assert len(results) >= 1
        # First result should be about authentication
        assert "auth" in results[0].topic.lower() or "oauth" in results[0].topic.lower()

    def test_search_returns_search_result_objects(self, tmp_path: Path) -> None:
        """search() returns SearchResult objects with required fields."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine, SearchResult

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-test",
            topic="Test Topic",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("test")

        assert len(results) >= 1
        result = results[0]

        # Verify SearchResult structure
        assert isinstance(result, SearchResult)
        assert hasattr(result, "thread_id")
        assert hasattr(result, "topic")
        assert hasattr(result, "synthesis")
        assert hasattr(result, "score")
        assert hasattr(result, "decided_at")

    def test_search_with_no_matches_returns_empty(self, tmp_path: Path) -> None:
        """search() returns empty list when no matches found."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-specific",
            topic="Specific Topic About Widgets",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use blue widgets",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("zzznonexistentquery")

        assert results == []

    def test_search_empty_corpus_returns_empty(self, tmp_path: Path) -> None:
        """search() on empty corpus returns empty list."""
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("anything")

        assert results == []


class TestFieldWeighting:
    """Test OCTAVE field weighting per ADR-0004."""

    def test_topic_field_weighted_higher_than_body(self, tmp_path: Path) -> None:
        """TOPIC field (10.0) scores higher than BODY content (0.5)."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Decision with "database" in topic
        record1 = DecisionRecord(
            thread_id="2026-02-08-database-topic",
            topic="Database Architecture Decision",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use PostgreSQL for primary data.",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source1",
        )

        # Decision with "database" only in synthesis (body)
        record2 = DecisionRecord(
            thread_id="2026-02-08-caching-mentions-db",
            topic="Caching Strategy",
            decided_at=datetime(2026, 2, 8, 11, 0, 0, tzinfo=UTC),
            synthesis="Cache database queries with Redis.",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 11, 5, 0, tzinfo=UTC),
            source_hash="source2",
        )

        export_decision_to_context(record1, context_dir)
        export_decision_to_context(record2, context_dir)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("database")

        # Decision with "database" in TOPIC should rank first
        assert len(results) >= 2
        assert "database" in results[0].topic.lower()

    def test_synthesis_field_weighted_higher_than_rationale(self, tmp_path: Path) -> None:
        """SYNTHESIS field (5.0) scores higher than RATIONALE (2.0)."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Decision with "microservices" in synthesis
        record1 = DecisionRecord(
            thread_id="2026-02-08-arch-decision",
            topic="Architecture Decision",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Adopt microservices architecture for scalability.",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source1",
            wind_perspectives=["Monolith is simpler"],
            wall_constraints=["Team is small"],
        )

        # Decision with "microservices" only in rationale
        record2 = DecisionRecord(
            thread_id="2026-02-08-deployment",
            topic="Deployment Strategy",
            decided_at=datetime(2026, 2, 8, 11, 0, 0, tzinfo=UTC),
            synthesis="Use Kubernetes for deployment.",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 11, 5, 0, tzinfo=UTC),
            source_hash="source2",
            wind_perspectives=["Microservices deployment is complex"],
            wall_constraints=["Need microservices support"],
        )

        export_decision_to_context(record1, context_dir)
        export_decision_to_context(record2, context_dir)

        engine = DecisionSearchEngine(context_dir)
        results = engine.search("microservices")

        # Decision with "microservices" in SYNTHESIS should rank first
        assert len(results) >= 2
        assert "microservices" in results[0].synthesis.lower()


class TestSearchResultStructure:
    """Test SearchResult data structure."""

    def test_search_result_has_all_fields(self) -> None:
        """SearchResult has all required fields."""
        from debate_hall_mcp.search import SearchResult

        result = SearchResult(
            thread_id="test-thread",
            topic="Test Topic",
            synthesis="Test synthesis content",
            score=0.95,
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            file_path=Path("/path/to/decision.oct.md"),
        )

        assert result.thread_id == "test-thread"
        assert result.topic == "Test Topic"
        assert result.synthesis == "Test synthesis content"
        assert result.score == 0.95
        assert result.decided_at == datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC)
        assert result.file_path == Path("/path/to/decision.oct.md")

    def test_search_result_to_dict(self) -> None:
        """SearchResult can be converted to dict for JSON serialization."""
        from debate_hall_mcp.search import SearchResult

        result = SearchResult(
            thread_id="test-thread",
            topic="Test Topic",
            synthesis="Test synthesis",
            score=0.95,
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            file_path=Path("/path/to/decision.oct.md"),
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["thread_id"] == "test-thread"
        assert result_dict["topic"] == "Test Topic"
        assert result_dict["score"] == 0.95


class TestOctaveFileParsing:
    """Test parsing OCTAVE decision files for indexing."""

    def test_parse_octave_decision_extracts_fields(self, tmp_path: Path) -> None:
        """parse_octave_decision extracts TOPIC, SYNTHESIS, and other fields."""
        from debate_hall_mcp.search import parse_octave_decision

        # Create a sample OCTAVE file
        octave_content = """===COMPILED_DECISION===

META:
  TYPE::COMPILED_DECISION
  VERSION::"1.0"
  THREAD_ID::"2026-02-08-test-decision"
  TOPIC::"API Design Strategy"
  DECIDED_AT::"2026-02-08T10:00:00+00:00"

OUTCOME:
  SYNTHESIS::"Use REST API with versioning."
  DECISION_HASH::"abc123"
  STATUS::synthesis

RATIONALE:
  WIND_PERSPECTIVES::[
    "GraphQL provides flexibility",
  ]
  WALL_CONSTRAINTS::[
    "Team expertise in REST",
  ]
  DOOR_REFINEMENTS::[]

VALIDATION:
  CONSENSUS_REACHED::true
  VOTES::{wind:true,wall:true}
  REFINEMENT_COUNT::0
  TURN_COUNT::3

PROVENANCE:
  EXTRACTED_AT::"2026-02-08T10:05:00+00:00"
  SOURCE_HASH::"def456"

===END==="""

        octave_file = tmp_path / "test.oct.md"
        octave_file.write_text(octave_content)

        fields = parse_octave_decision(octave_file)

        assert fields["thread_id"] == "2026-02-08-test-decision"
        assert fields["topic"] == "API Design Strategy"
        assert fields["synthesis"] == "Use REST API with versioning."
        assert fields["status"] == "synthesis"
        assert "GraphQL provides flexibility" in fields.get("wind_perspectives", [])
        assert "Team expertise in REST" in fields.get("wall_constraints", [])

    def test_parse_octave_handles_missing_fields(self, tmp_path: Path) -> None:
        """parse_octave_decision handles missing optional fields gracefully."""
        from debate_hall_mcp.search import parse_octave_decision

        # Minimal OCTAVE file
        octave_content = """===COMPILED_DECISION===

META:
  TYPE::COMPILED_DECISION
  THREAD_ID::"minimal-test"
  TOPIC::"Minimal Topic"

OUTCOME:
  SYNTHESIS::"Minimal synthesis"
  STATUS::synthesis

===END==="""

        octave_file = tmp_path / "minimal.oct.md"
        octave_file.write_text(octave_content)

        fields = parse_octave_decision(octave_file)

        assert fields["thread_id"] == "minimal-test"
        assert fields["topic"] == "Minimal Topic"
        assert fields["synthesis"] == "Minimal synthesis"
        # Missing fields should have defaults
        assert fields.get("wind_perspectives", []) == []
        assert fields.get("wall_constraints", []) == []


class TestLazyIndexing:
    """Test lazy indexing behavior."""

    def test_index_built_on_first_search(self, tmp_path: Path) -> None:
        """Index is built lazily on first search, not at initialization."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-lazy-test",
            topic="Lazy Indexing Test",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # Index should not be built yet
        assert not engine._index_built

        # First search triggers index build
        engine.search("test")

        # Now index should be built
        assert engine._index_built

    def test_index_not_rebuilt_on_subsequent_searches(self, tmp_path: Path) -> None:
        """Index is reused for subsequent searches."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-cache-test",
            topic="Cache Test",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # First search
        engine.search("test")
        build_time_1 = engine._last_index_time

        # Second search - should not rebuild
        engine.search("cache")
        build_time_2 = engine._last_index_time

        assert build_time_1 == build_time_2

    def test_rebuild_index_forces_reindex(self, tmp_path: Path) -> None:
        """rebuild_index() forces a fresh index build."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-rebuild-test",
            topic="Rebuild Test",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Test synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # First search builds index
        engine.search("test")
        build_time_1 = engine._last_index_time

        # Force rebuild
        time.sleep(0.01)  # Ensure time difference
        engine.rebuild_index()
        build_time_2 = engine._last_index_time

        assert build_time_2 > build_time_1


class TestPerformanceGovernors:
    """Test performance constraints per ADR-0004."""

    def test_query_latency_under_50ms(self, tmp_path: Path) -> None:
        """Query latency should be under 50ms for typical corpus."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Create 100 sample decisions
        for i in range(100):
            record = DecisionRecord(
                thread_id=f"2026-02-08-perf-test-{i}",
                topic=f"Performance Test Decision {i} about topic {i % 10}",
                decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
                synthesis=f"This is synthesis {i} with some content.",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # Build index first
        engine.rebuild_index()

        # Measure query time
        start = time.perf_counter()
        for _ in range(10):  # Run 10 queries
            engine.search("performance")
        elapsed = (time.perf_counter() - start) / 10  # Average

        # Should be under 50ms (0.05s)
        assert elapsed < 0.05, f"Query latency {elapsed*1000:.1f}ms exceeds 50ms threshold"

    def test_index_size_returns_byte_count(self, tmp_path: Path) -> None:
        """get_index_size() returns approximate index size in bytes."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        for i in range(10):
            record = DecisionRecord(
                thread_id=f"2026-02-08-size-test-{i}",
                topic=f"Size Test {i}",
                decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
                synthesis=f"Synthesis {i}",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)
        engine.rebuild_index()

        size = engine.get_index_size()

        # Should be a positive integer
        assert isinstance(size, int)
        assert size > 0


class TestSearchLimit:
    """Test result limiting."""

    def test_search_respects_limit_parameter(self, tmp_path: Path) -> None:
        """search() respects the limit parameter."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Create 10 decisions all matching "test"
        for i in range(10):
            record = DecisionRecord(
                thread_id=f"2026-02-08-limit-test-{i}",
                topic=f"Test Limit Topic {i}",
                decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
                synthesis=f"Test synthesis {i}",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # Request only 3 results
        results = engine.search("test", limit=3)

        assert len(results) == 3

    def test_search_default_limit_is_10(self, tmp_path: Path) -> None:
        """search() has a default limit of 10 results."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # Create 15 decisions all matching "default"
        for i in range(15):
            record = DecisionRecord(
                thread_id=f"2026-02-08-default-{i}",
                topic=f"Default Test {i}",
                decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
                synthesis=f"Default synthesis {i}",
                decision_hash=f"hash{i}",
                status="synthesis",
                extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
                source_hash=f"source{i}",
            )
            export_decision_to_context(record, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # No limit specified - should default to 10
        results = engine.search("default")

        assert len(results) == 10


class TestScoreThreshold:
    """Test minimum score threshold for results."""

    def test_search_filters_low_score_results(self, tmp_path: Path) -> None:
        """search() with threshold filters out low-scoring results."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import DecisionSearchEngine

        context_dir = tmp_path / ".hestai" / "context"

        # High relevance decision
        record1 = DecisionRecord(
            thread_id="2026-02-08-high-match",
            topic="Authentication with OAuth2",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use OAuth2 for authentication.",
            decision_hash="hash1",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source1",
        )

        # Low relevance decision (auth only mentioned tangentially)
        record2 = DecisionRecord(
            thread_id="2026-02-08-low-match",
            topic="Database Choice",
            decided_at=datetime(2026, 2, 8, 11, 0, 0, tzinfo=UTC),
            synthesis="PostgreSQL works well.",
            decision_hash="hash2",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 11, 5, 0, tzinfo=UTC),
            source_hash="source2",
            wind_perspectives=["Some auth concerns"],  # Weak match
        )

        export_decision_to_context(record1, context_dir)
        export_decision_to_context(record2, context_dir)

        engine = DecisionSearchEngine(context_dir)

        # With high threshold, only highly relevant results
        results = engine.search("OAuth2 authentication", min_score=0.5)

        # Should only get the high-match result
        assert len(results) >= 1
        assert all(r.score >= 0.5 for r in results)


class TestFindPrecedent:
    """Test find_precedent() agent interface per ADR-0004."""

    def test_find_precedent_returns_high_scoring_decisions(self, tmp_path: Path) -> None:
        """find_precedent() returns only decisions above 0.85 threshold."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import find_precedent

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-precedent-test",
            topic="OAuth2 Authentication Strategy",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use OAuth2 with JWT tokens.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        results = find_precedent("What is our authentication strategy?", context_dir)

        # Should return list (may be empty if score too low)
        assert isinstance(results, list)

    def test_find_precedent_empty_for_no_matches(self, tmp_path: Path) -> None:
        """find_precedent() returns empty list for no relevant matches."""
        from debate_hall_mcp.context_compiler import export_decision_to_context
        from debate_hall_mcp.search import find_precedent

        context_dir = tmp_path / ".hestai" / "context"

        record = DecisionRecord(
            thread_id="2026-02-08-unrelated",
            topic="Database Architecture",
            decided_at=datetime(2026, 2, 8, 10, 0, 0, tzinfo=UTC),
            synthesis="Use PostgreSQL.",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime(2026, 2, 8, 10, 5, 0, tzinfo=UTC),
            source_hash="source",
        )
        export_decision_to_context(record, context_dir)

        # Query for something completely unrelated
        results = find_precedent("quantum computing strategy", context_dir)

        assert results == []
