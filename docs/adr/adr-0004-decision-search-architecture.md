# ADR-0004: Decision Search Architecture

**Status**: Proposed
**Date**: 2026-02-04
**Decision Makers**: Wind/Wall/Door Debate (Cross-Tier Synthesis)
**Context**: Searchable decision record history for debate-hall-mcp

## Context

A Wind/Wall/Door debate was conducted across three tiers (fast, standard, premium) to determine whether and how to implement searchable decision record history in debate-hall-mcp.

As debate-hall produces OCTAVE-format decision records, users and agents need to find relevant past decisions:
- "Have we debated authentication approaches?"
- "What was the consensus on caching strategy?"
- "Show me decisions related to database architecture"

Each tier produced a distinct synthesis:
- **Fast tier** ($0.019): "Self-Indexing Decision Graph" - add SEARCH_ANCHORS at synthesis time
- **Standard tier** ($0.35): "RAM-Resident Exocortex" - agent-first interface, not user search
- **Premium tier** ($0.87): "Structural Resonance Search" - Physics Budget + concrete test harness

## Decision

Implement **In-Memory BM25 with OCTAVE Field Weighting**, enhanced with synthesis-time search anchors.

### Core Insight

All three tiers converged on the same fundamental realization:

> "OCTAVE structure already provides semantic organization. Field-weighted BM25 achieves 'pseudo-semantic' search without vector infrastructure."

### Architecture: Structural Resonance Search (Premium)

```
SYSTEM::DECISION_SEARCH_ENGINE

COMPONENT::INDEXER
  TRIGGER::FileSystem.Watch(`decisions/*.md`)
  PARSER::Regex(OCTAVE_GRAMMAR) → Extract[§TOPIC, §SYNTHESIS, §RATIONALE, §TAGS, §SEARCH_ANCHORS]
  WEIGHTING::[
    §SEARCH_ANCHORS::15.0  // Pre-computed Q&A (Fast tier contribution)
    §TOPIC::10.0           // "What it is"
    §TAGS::8.0             // "Explicit Class"
    §SYNTHESIS::5.0        // "The Decision"
    §RATIONALE::2.0        // "The Why"
    §BODY::0.5             // "Noise"
  ]
  OUTPUT::`./assets/search_index.json`

COMPONENT::QUERY_ENGINE
  LOAD::Read(`search_index.json`)
  MODE::InMemory
  CAPABILITY::[
    Prefix_Match::True ("auth"→"authentication"),
    Fuzzy_Match::0.2 (Typos allowed),
    Snippet_Gen::Return `§SYNTHESIS` as preview
  ]

COMPONENT::PERFORMANCE_GOVERNOR
  RULE::If Index_Size > 5MB → Log(WARN) + Trigger(PRUNE_STRATEGY)
  RULE::If Boot_Time > 200ms → Log(WARN) + Disable(AUTO_SUGGEST)
  RULE::If Query_Latency > 50ms → Log(WARN)
```

### Schema Enhancement: SEARCH_ANCHORS (Fast Tier)

Add pre-computed Q&A pairs during synthesis:

```octave
§META::SEARCH_ANCHORS::[
  Q::\"What is our authentication strategy?\"→A::\"OAuth2 with JWT tokens\",
  Q::\"How do we handle caching?\"→A::\"Redis with 5-minute TTL\"
]
```

The Door agent generates these during synthesis, creating "synthetic vectors" without embedding infrastructure.

### Agent Interface: Precedent Tool (Standard Tier)

Primary consumer is agents, not user UI:

```python
def find_precedent(query: str) -> List[DecisionSummary]:
    """
    Agent-first search interface.

    Returns decisions only if score > threshold (0.85).
    Empty list if no strong match, preventing hallucinated connections.
    """
    results = search_index.query(query)
    return [r for r in results if r.score > 0.85]
```

Agents call this during reasoning, silently incorporating relevant history.

### Performance Constraints (Premium Tier)

Explicit "Physics Budget" with kill switch:

| Metric | Threshold | Action if Exceeded |
|--------|-----------|-------------------|
| Index_Size | 5MB | WARN + PRUNE_STRATEGY |
| Boot_Time | 200ms | WARN + Disable AUTO_SUGGEST |
| Query_Latency | 50ms (p95) | WARN |
| Memory_Footprint | 50MB | FAIL → Revert to grep |

### Validation Criteria

Test harness with pass/fail criteria:

1. **Cold_Boot_Latency**: MUST < 200ms
2. **Query_Latency**: MUST < 50ms (p95)
3. **Memory_Footprint**: MUST < 50MB
4. **Relevance_Check**: Query "auth" must rank "OAuth2 Strategy" (§TOPIC) above "mentioned auth" (§BODY)

## Implementation Path

### Phase 1: Schema Enhancement
1. Add `§META::SEARCH_ANCHORS` to OCTAVE decision record schema
2. Update Door synthesis to generate Q&A pairs
3. Validate with existing decision records

### Phase 2: Indexer
1. Implement MiniSearch-based indexer with field weighting
2. Create `search_index.json` artifact
3. Add FileSystem.Watch for incremental updates

### Phase 3: Query Engine
1. Implement `find_precedent()` agent tool
2. Add prefix matching and fuzzy search
3. Return §SYNTHESIS snippets as previews

### Phase 4: Performance Governor
1. Implement threshold monitoring
2. Add telemetry logging
3. Create kill switch mechanism

### Phase 5: Validation
1. Generate 1000 synthetic OCTAVE records
2. Run test harness
3. Verify all metrics pass

## Consequences

### Positive

1. **Zero infrastructure**: Single-process, in-memory, no external dependencies
2. **Pseudo-semantic search**: Field weighting achieves conceptual matching without embeddings
3. **Self-measuring**: Telemetry validates effectiveness before scaling
4. **Agent-first**: Empowers agents without spamming users
5. **Pre-computed anchors**: SEARCH_ANCHORS reduce query-time computation
6. **Kill switch**: Graceful degradation to grep if metrics fail

### Negative

1. **Memory bound**: Corpus limited to what fits in RAM (~25k decisions at 50MB)
2. **Synthesis overhead**: Door must generate SEARCH_ANCHORS (adds ~5% to synthesis time)
3. **No true semantic search**: Synonyms and conceptual queries limited

### Neutral

1. **Escalation path defined**: Clear triggers for when to upgrade to vectors
2. **Maintenance minimal**: Index rebuilds automatically on file changes

## Alternatives Considered

### Vector Embeddings (Option B)
**Rejected because**: Adds infrastructure (embedding model, vector DB), increases cold-start latency, premature optimization for current scale.

**Escalation trigger**: If Zero-Hit rate >20% after 100 queries, reconsider.

### Graph-Based Navigation (Option D)
**Rejected because**: Requires schema migration, retroactive tagging, ongoing ontology governance. Higher maintenance burden without proven benefit.

**Future consideration**: If decision lineage becomes primary use case.

## Validation

This architecture was validated through cross-tier debate:
- **Architectural convergence**: All three tiers arrived at in-memory BM25 with field weighting
- **Consensus**: Premium tier achieved synthesis with comprehensive constraints
- **Scale verification**: 10,000 records = ~20MB base, fits RAM comfortably
- **Risk mitigation**: Performance Governor with explicit kill switch

## References

- `docs/test-reports/2026-02-04-decision-search-cross-tier-comparison.md`
- `debates/2026-02-04-decision-search-fast.json`
- `debates/2026-02-04-decision-search-standard.json`
- `debates/2026-02-04-decision-search-premium.json`

## Decision Provenance

| Tier | Thread ID | Status | Cost |
|------|-----------|--------|------|
| Fast | `2026-02-04-decision-search-fast` | synthesis | $0.019 |
| Standard | `2026-02-04-decision-search-standard` | stalemate | $0.35 |
| Premium | `2026-02-04-decision-search-premium` | synthesis | $0.87 |

**Total debate cost**: $1.24 for comprehensive architectural decision
