"""Search decisions MCP tool.

Issue #144: Decision Indexing & BM25 Search
ADR-0004: Decision Search Architecture

This module provides the MCP tool wrapper for decision search.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.context_compiler import get_context_dir
from debate_hall_mcp.search import DecisionSearchEngine


def search_decisions(
    query: str,
    limit: int = 10,
    min_score: float = 0.0,
    context_dir: Path | None = None,
) -> dict[str, Any]:
    """Search for past decisions matching a query.

    Uses field-weighted BM25 to find relevant decisions from the
    decisions directory. Fields are weighted per ADR-0004:
    - SEARCH_ANCHORS: 15.0 (pre-computed Q&A pairs)
    - TOPIC: 10.0 (what it is)
    - TAGS: 8.0 (explicit classification)
    - SYNTHESIS: 5.0 (the decision)
    - RATIONALE: 2.0 (wind/wall perspectives)
    - BODY: 0.5 (noise)

    Args:
        query: Search query string
        limit: Maximum number of results (default 10)
        min_score: Minimum score threshold (default 0.0)
        context_dir: Context directory path (default: auto-detected)

    Returns:
        Dictionary with:
        - query: The search query
        - count: Number of results
        - results: List of matching decisions with:
            - thread_id: Decision thread ID
            - topic: Decision topic
            - synthesis: Decision synthesis (preview)
            - score: Relevance score (0-1)
            - decided_at: When decision was made
            - file_path: Path to decision file
    """
    # Resolve context directory
    if context_dir is None:
        context_dir = get_context_dir()

    # Create engine and search
    engine = DecisionSearchEngine(context_dir)
    results = engine.search(query, limit=limit, min_score=min_score)

    # Convert to dict format for JSON serialization
    result_dicts = [r.to_dict() for r in results]

    return {
        "query": query,
        "count": len(result_dicts),
        "results": result_dicts,
    }
