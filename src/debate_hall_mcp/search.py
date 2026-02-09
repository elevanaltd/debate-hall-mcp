"""Decision Search - BM25 with OCTAVE Field Weighting.

Issue #144: Implement searchable decision record history
ADR-0004: Decision Search Architecture

This module implements:
- BM25: Pure Python BM25 algorithm implementation
- DecisionSearchEngine: Field-weighted search over OCTAVE decision files
- SearchResult: Search result data structure
- find_precedent(): Agent-first search interface

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

from __future__ import annotations

import math
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Field weights per ADR-0004
FIELD_WEIGHTS: dict[str, float] = {
    "search_anchors": 15.0,
    "topic": 10.0,
    "tags": 8.0,
    "synthesis": 5.0,
    "wind_perspectives": 2.0,
    "wall_constraints": 2.0,
    "door_refinements": 2.0,
    "body": 0.5,
}

# BM25 parameters (standard values)
BM25_K1 = 1.5  # Term frequency saturation parameter
BM25_B = 0.75  # Document length normalization parameter


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Input text string

    Returns:
        List of lowercase word tokens
    """
    # Convert to lowercase, split on non-alphanumeric
    words = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return words


class BM25:
    """Pure Python BM25 ranking algorithm.

    Implements Okapi BM25 for term-based document ranking.
    Uses standard parameters: k1=1.5, b=0.75.
    """

    def __init__(
        self,
        corpus: list[list[str]],
        k1: float = BM25_K1,
        b: float = BM25_B,
    ) -> None:
        """Initialize BM25 with a corpus.

        Args:
            corpus: List of tokenized documents (list of word lists)
            k1: Term frequency saturation parameter (default 1.5)
            b: Document length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)

        # Calculate document lengths and average
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avg_doc_length = (
            sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 0
        )

        # Build document frequency table (how many docs contain each term)
        self.doc_freqs: dict[str, int] = {}
        for doc in corpus:
            seen_terms: set[str] = set()
            for term in doc:
                if term not in seen_terms:
                    self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
                    seen_terms.add(term)

        # Pre-compute IDF for all terms
        self.idf: dict[str, float] = {}
        for term, freq in self.doc_freqs.items():
            # IDF formula: log((N - n + 0.5) / (n + 0.5) + 1)
            # where N = corpus size, n = document frequency
            numerator = self.corpus_size - freq + 0.5
            denominator = freq + 0.5
            self.idf[term] = math.log(numerator / denominator + 1)

    def get_scores(self, query: list[str]) -> list[float]:
        """Calculate BM25 scores for all documents given a query.

        Args:
            query: List of query term tokens

        Returns:
            List of scores for each document in corpus
        """
        if not self.corpus:
            return []

        if not query:
            return [0.0] * self.corpus_size

        scores = [0.0] * self.corpus_size

        for term in query:
            if term not in self.idf:
                continue

            idf = self.idf[term]

            for doc_idx, doc in enumerate(self.corpus):
                # Count term frequency in document
                tf = doc.count(term)
                if tf == 0:
                    continue

                # BM25 term score formula
                doc_len = self.doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))
                scores[doc_idx] += idf * (numerator / denominator)

        return scores


@dataclass
class SearchResult:
    """A search result from decision search.

    Contains the matched decision summary with relevance score.
    """

    thread_id: str
    topic: str
    synthesis: str
    score: float
    decided_at: datetime
    file_path: Path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the search result
        """
        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "synthesis": self.synthesis,
            "score": self.score,
            "decided_at": self.decided_at.isoformat(),
            "file_path": str(self.file_path),
        }


@dataclass
class IndexedDecision:
    """Internal representation of an indexed decision."""

    thread_id: str
    topic: str
    synthesis: str
    decided_at: datetime
    file_path: Path
    # Field-specific tokens for weighted scoring
    field_tokens: dict[str, list[str]] = field(default_factory=dict)


def parse_octave_decision(file_path: Path) -> dict[str, Any]:
    """Parse an OCTAVE decision file and extract fields.

    Args:
        file_path: Path to OCTAVE decision file

    Returns:
        Dictionary with extracted fields
    """
    content = file_path.read_text()

    result: dict[str, Any] = {
        "thread_id": "",
        "topic": "",
        "synthesis": "",
        "status": "",
        "decided_at": None,
        "wind_perspectives": [],
        "wall_constraints": [],
        "door_refinements": [],
        "tags": [],
        "search_anchors": [],
    }

    # Extract THREAD_ID
    thread_match = re.search(r'THREAD_ID::"([^"]+)"', content)
    if thread_match:
        result["thread_id"] = thread_match.group(1)

    # Extract TOPIC
    topic_match = re.search(r'TOPIC::"([^"]+)"', content)
    if topic_match:
        result["topic"] = topic_match.group(1)

    # Extract SYNTHESIS
    synthesis_match = re.search(r'SYNTHESIS::"([^"]+)"', content)
    if synthesis_match:
        result["synthesis"] = synthesis_match.group(1)

    # Extract STATUS
    status_match = re.search(r"STATUS::(\w+)", content)
    if status_match:
        result["status"] = status_match.group(1)

    # Extract DECIDED_AT
    decided_match = re.search(r'DECIDED_AT::"([^"]+)"', content)
    if decided_match:
        try:
            result["decided_at"] = datetime.fromisoformat(decided_match.group(1))
        except ValueError:
            result["decided_at"] = datetime.now(UTC)

    # Extract WIND_PERSPECTIVES (list items)
    wind_section = re.search(r"WIND_PERSPECTIVES::\[\s*(.*?)\s*\]", content, re.DOTALL)
    if wind_section:
        items = re.findall(r'"([^"]+)"', wind_section.group(1))
        result["wind_perspectives"] = items

    # Extract WALL_CONSTRAINTS (list items)
    wall_section = re.search(r"WALL_CONSTRAINTS::\[\s*(.*?)\s*\]", content, re.DOTALL)
    if wall_section:
        items = re.findall(r'"([^"]+)"', wall_section.group(1))
        result["wall_constraints"] = items

    # Extract DOOR_REFINEMENTS (list items)
    door_section = re.search(r"DOOR_REFINEMENTS::\[\s*(.*?)\s*\]", content, re.DOTALL)
    if door_section:
        items = re.findall(r'"([^"]+)"', door_section.group(1))
        result["door_refinements"] = items

    # Extract TAGS if present
    tags_match = re.search(r"TAGS::\[([^\]]+)\]", content)
    if tags_match:
        items = re.findall(r'"([^"]+)"', tags_match.group(1))
        result["tags"] = items

    # Extract SEARCH_ANCHORS if present
    anchors_match = re.search(r"SEARCH_ANCHORS::\[([^\]]+)\]", content)
    if anchors_match:
        items = re.findall(r'"([^"]+)"', anchors_match.group(1))
        result["search_anchors"] = items

    return result


class DecisionSearchEngine:
    """Field-weighted BM25 search engine for OCTAVE decision files.

    Implements lazy indexing - index is built on first search, not at
    initialization. This keeps boot time under 200ms per ADR-0004.

    Field weights per ADR-0004:
    - §SEARCH_ANCHORS: 15.0
    - §TOPIC: 10.0
    - §TAGS: 8.0
    - §SYNTHESIS: 5.0
    - §RATIONALE: 2.0
    - §BODY: 0.5
    """

    def __init__(self, context_dir: Path) -> None:
        """Initialize search engine with context directory.

        Args:
            context_dir: Path to .hestai/context directory
        """
        self.context_dir = context_dir
        self._index_built = False
        self._last_index_time: float = 0.0
        self._decisions: list[IndexedDecision] = []
        self._bm25_indices: dict[str, BM25] = {}

    def rebuild_index(self) -> None:
        """Force rebuild of the search index.

        Scans the decisions/ directory and indexes all OCTAVE files.
        """
        decisions_dir = self.context_dir / "decisions"

        # Ensure directory exists
        if not decisions_dir.exists():
            decisions_dir.mkdir(parents=True, exist_ok=True)
            self._decisions = []
            self._bm25_indices = {}
            self._index_built = True
            self._last_index_time = time.time()
            return

        # Find all decision files
        decision_files = sorted(decisions_dir.glob("*.oct.md"))

        self._decisions = []

        for file_path in decision_files:
            try:
                fields = parse_octave_decision(file_path)

                # Build field-specific tokens
                field_tokens: dict[str, list[str]] = {}

                # Topic field (weight 10.0)
                if fields.get("topic"):
                    field_tokens["topic"] = tokenize(fields["topic"])

                # Synthesis field (weight 5.0)
                if fields.get("synthesis"):
                    field_tokens["synthesis"] = tokenize(fields["synthesis"])

                # Wind perspectives (weight 2.0)
                wind_text = " ".join(fields.get("wind_perspectives", []))
                if wind_text:
                    field_tokens["wind_perspectives"] = tokenize(wind_text)

                # Wall constraints (weight 2.0)
                wall_text = " ".join(fields.get("wall_constraints", []))
                if wall_text:
                    field_tokens["wall_constraints"] = tokenize(wall_text)

                # Door refinements (weight 2.0)
                door_text = " ".join(fields.get("door_refinements", []))
                if door_text:
                    field_tokens["door_refinements"] = tokenize(door_text)

                # Tags (weight 8.0)
                tags_text = " ".join(fields.get("tags", []))
                if tags_text:
                    field_tokens["tags"] = tokenize(tags_text)

                # Search anchors (weight 15.0)
                anchors_text = " ".join(fields.get("search_anchors", []))
                if anchors_text:
                    field_tokens["search_anchors"] = tokenize(anchors_text)

                # Decided at
                decided_at = fields.get("decided_at") or datetime.now(UTC)

                indexed = IndexedDecision(
                    thread_id=fields.get("thread_id", ""),
                    topic=fields.get("topic", ""),
                    synthesis=fields.get("synthesis", ""),
                    decided_at=decided_at,
                    file_path=file_path,
                    field_tokens=field_tokens,
                )
                self._decisions.append(indexed)

            except Exception:
                # Skip malformed files
                continue

        # Build BM25 index for each field
        self._bm25_indices = {}

        for field_name in FIELD_WEIGHTS:
            # Extract tokens for this field from all decisions
            corpus = []
            for decision in self._decisions:
                tokens = decision.field_tokens.get(field_name, [])
                corpus.append(tokens)

            if any(corpus):  # Only create index if there's content
                self._bm25_indices[field_name] = BM25(corpus)

        self._index_built = True
        self._last_index_time = time.time()

    def _ensure_index(self) -> None:
        """Build index if not already built (lazy indexing)."""
        if not self._index_built:
            self.rebuild_index()

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for decisions matching a query.

        Uses field-weighted BM25 scoring. Fields with higher weights
        contribute more to the final score.

        Args:
            query: Search query string
            limit: Maximum number of results (default 10)
            min_score: Minimum score threshold (default 0.0)

        Returns:
            List of SearchResult objects, ranked by relevance
        """
        self._ensure_index()

        if not self._decisions:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Calculate weighted scores across all fields
        combined_scores = [0.0] * len(self._decisions)

        for field_name, weight in FIELD_WEIGHTS.items():
            if field_name in self._bm25_indices:
                bm25 = self._bm25_indices[field_name]
                field_scores = bm25.get_scores(query_tokens)

                for i, score in enumerate(field_scores):
                    combined_scores[i] += score * weight

        # Normalize scores to 0-1 range
        max_score = max(combined_scores) if combined_scores else 0
        if max_score > 0:
            normalized_scores = [s / max_score for s in combined_scores]
        else:
            normalized_scores = combined_scores

        # Build results with scores
        results: list[SearchResult] = []

        for i, decision in enumerate(self._decisions):
            score = normalized_scores[i]
            if score > min_score:
                results.append(
                    SearchResult(
                        thread_id=decision.thread_id,
                        topic=decision.topic,
                        synthesis=decision.synthesis,
                        score=score,
                        decided_at=decision.decided_at,
                        file_path=decision.file_path,
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply limit
        return results[:limit]

    def get_index_size(self) -> int:
        """Get approximate size of the index in bytes.

        Returns:
            Approximate memory usage of the index in bytes
        """
        self._ensure_index()

        # Rough estimate based on stored data
        size = 0

        for decision in self._decisions:
            # Thread ID, topic, synthesis strings
            size += len(decision.thread_id)
            size += len(decision.topic)
            size += len(decision.synthesis)

            # Field tokens
            for tokens in decision.field_tokens.values():
                for token in tokens:
                    size += len(token) + 50  # Overhead per token

        # BM25 indices overhead
        for bm25 in self._bm25_indices.values():
            size += sys.getsizeof(bm25.idf)
            size += sys.getsizeof(bm25.doc_freqs)
            size += len(bm25.corpus) * 100  # Rough corpus overhead

        return size


def find_precedent(
    query: str,
    context_dir: Path,
    threshold: float = 0.85,
) -> list[SearchResult]:
    """Agent-first search interface for finding relevant precedent.

    Returns decisions only if score > threshold (default 0.85).
    Empty list if no strong match, preventing hallucinated connections.

    This is the primary interface for agents to discover relevant
    past decisions. Silent incorporation into reasoning.

    Args:
        query: Natural language question about past decisions
        context_dir: Path to .hestai/context directory
        threshold: Minimum score threshold (default 0.85)

    Returns:
        List of highly relevant SearchResult objects (score > threshold)
    """
    engine = DecisionSearchEngine(context_dir)
    return engine.search(query, min_score=threshold)
