# Decision Search: Cross-Tier Quality & Cost Comparison

**Date**: 2026-02-04
**Branch**: debate-hall-refinements
**Purpose**: Determine optimal architecture for searchable decision record history via multi-tier debate

---

## Executive Summary

Three debate tiers evaluated whether and how to implement searchable decision record history in debate-hall-mcp:

| Tier | Cost | Consensus | Status | Pattern Name | Key Insight |
|------|------|-----------|--------|--------------|-------------|
| **Fast** | $0.019 | No | synthesis | "Self-Indexing Decision Graph" | Add SEARCH_ANCHORS at synthesis time |
| **Standard** | $0.35 | No | stalemate | "RAM-Resident Exocortex" | Agent-first interface, not user search |
| **Premium** | $0.87 | Yes | synthesis | "Structural Resonance Search" | Physics Budget + concrete test harness |

**Key Finding**: All tiers converged on **In-Memory BM25 with OCTAVE Field Weighting**. Premium tier provides most rigorous specification with explicit performance governors and test criteria.

---

## Topic Debated

> Should debate-hall-mcp implement searchable decision record history? Context: Debate-hall produces OCTAVE-format decision records (thread_id, topic, synthesis, rationale, validation fields). As usage grows, agents and users need to find relevant past decisions - e.g., "have we debated authentication approaches?" or "what was the consensus on caching?". Options: (A) BM25/keyword search - simple in-memory index with field weighting (TOPIC×10, SYNTHESIS×4, RATIONALE×2). Zero infrastructure, instant queries. (B) Vector embeddings - semantic search via embedding model + vector DB. Better for fuzzy/conceptual queries but requires infrastructure. (C) Hybrid - BM25 primary with vector fallback when <3 results. (D) Graph-based - decisions linked by topic/tags, navigable ontology. Trade-offs: infrastructure cost, query latency, semantic accuracy, maintenance burden, cold-start behavior. Note: OCTAVE structure already provides semantic organization via field names.

---

## Tier Configurations

| Setting | Fast | Standard | Premium |
|---------|------|----------|---------|
| max_turns | 6 | 12 | 16 |
| max_refinement_loops | 0 | 4 | 5 |
| consensus_required | false | false | **true** |
| Wind Model | Claude Haiku 4.5 | Claude Sonnet 4.5 | Claude Opus 4.5 |
| Wall Model | GPT-5-Mini | GPT-5.2 | GPT-5.2 Pro |
| Door Model | Gemini 3 Flash Preview | Gemini 3 Pro Preview | Gemini 3 Pro Preview |
| Wind Agent | wind-agent | ideator | edge-optimizer |
| Wall Agent | wall-agent | validator | critical-engineer |
| Door Agent | door-agent | synthesizer | technical-architect |

---

## Synthesis Comparison

### Fast Tier: "Self-Indexing Decision Graph (SIDG)"

**Core Insight**: Embed search anchors at synthesis time so decisions pre-answer common queries.

**Key Innovation**:
- Add `§META::SEARCH_ANCHORS::[Query:Answer]` to OCTAVE output
- Door generates Q&A pairs during synthesis ("What's our auth stance?" → "OAuth2")
- "Synthetic vectors" without embedding infrastructure

**Field Weights**: SEARCH_ANCHORS ×15, TOPIC ×10, SYNTHESIS ×5

**Escalation Trigger**: Zero-Hit rate >20% → migrate to hybrid Vector

**Unique Contribution**: "Continuity Check" - 1-turn micro-debate when search results found to verify relevance

---

### Standard Tier: "RAM-Resident Exocortex"

**Core Insight**: OCTAVE's compression means entire corpus fits in RAM (~2KB/record × 10,000 = 20MB)

**Key Innovation**:
- Agent-first interface: `consult_precedent()` tool, not user search bar
- "The Wise Agent" pattern: Agent cites history silently if score >0.85
- User is taught, never spammed

**Field Weights**: TOPIC (10), SYNTHESIS (5), RATIONALE (2)

**Scale Verification**: 10,000 records = ~20MB base + ~200MB with Python overhead = fits RAM

**Escalation Trigger**: Index >500MB → migrate to Vector DB

---

### Premium Tier: "Structural Resonance Search"

**Core Insight**: OCTAVE structure itself is a semantic engine - field weights achieve "pseudo-semantic" search without embeddings.

**Key Innovation**:
- Concrete artifact specification: `search_index.json`
- "Physics Budget" constraints as runtime rules
- Explicit test harness with pass/fail criteria
- "Experiment with Kill Switch" pattern

**Field Weights**: §TOPIC 10.0, §TAGS 8.0, §SYNTHESIS 5.0, §RATIONALE 2.0, §BODY 0.5

**Performance Governor**:
```
RULE::If Index_Size > 5MB → Log(WARN) + Trigger(PRUNE_STRATEGY)
RULE::If Boot_Time > 200ms → Log(WARN) + Disable(AUTO_SUGGEST)
```

**Test Harness**:
- Cold_Boot_Latency: MUST < 200ms
- Query_Latency: MUST < 50ms (p95)
- Memory_Footprint: MUST < 50MB
- Relevance_Check: Query "auth" must rank "OAuth2 Strategy" (§TOPIC) above "mentioned auth" (§BODY)

---

## Architectural Convergence

All three tiers independently arrived at **the same core solution**:

> "In-Memory BM25 with OCTAVE Field Weighting exploits existing semantic structure without vector infrastructure"

**Common Agreements**:
1. **In-memory BM25** - no external vector DB needed
2. **Field weighting** - TOPIC highest, SYNTHESIS/TAGS next, RATIONALE lower
3. **Telemetry first** - measure before scaling to vectors
4. **Escalation triggers** - defined thresholds for when to upgrade
5. **Zero infrastructure** - single-process, no external dependencies

**Unique Contributions by Tier**:

| Tier | Unique Insight |
|------|----------------|
| **Fast** | `SEARCH_ANCHORS` field added at synthesis time (pre-computed Q&A) |
| **Standard** | Agent-first interface (not user search bar) |
| **Premium** | "Physics Budget" + concrete test harness + kill switch |

---

## Quality Analysis

### Wall Agent Comparison

| Metric | Fast (wall-agent) | Standard (validator) | Premium (critical-engineer) |
|--------|-------------------|---------------------|----------------------------|
| Model | GPT-5-Mini | GPT-5.2 | GPT-5.2 Pro |
| Verdict | CONDITIONAL GO | REQUIRES_VALIDATION | **CONDITIONAL** |
| Constraints | 5 (C1-C5) | Comprehensive | **Extensive catalog** |
| Evidence Quality | Strong citations | Very detailed | **Exhaustive** |
| Risk Assessment | 4 risks (R1-R4) | Detailed | **HIGH/MEDIUM/LOW** |
| Mitigations | 5 required (M1-M5) | Explicit | **Comprehensive** |

**Key Observation**: All three Wall agents engaged substantively with the new model configurations (GPT-5-Mini, GPT-5.2, GPT-5.2 Pro). This validates the model changes from GPT-5.2-Codex.

---

## Cost Analysis (OpenRouter Verified)

### Per-Model Breakdown

**Fast Tier** ($0.019 total):
| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Haiku 4.5 | Wind | 2,582 → 953 | $0.00735 |
| GPT-5-Mini | Wall | 3,359 → 2,856 | $0.00655 |
| Gemini 3 Flash Preview | Door | 5,072 → 695 | $0.00462 |

**Standard Tier** (~$0.35 total, includes refinement loops):
| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Sonnet 4.5 | Wind | 4,372 → 2,015 | $0.0433 |
| GPT-5.2 | Wall | 5,955 → 3,415 | $0.052 |
| Gemini 3 Pro Preview | Door (×4) | ~42,130 → ~13,896 | ~$0.25 |
| Claude Sonnet 4.5 | Consensus (×4) | ~13,644 → ~1,211 | ~$0.06 |
| GPT-5.2 | Consensus (×4) | ~13,436 → ~1,051 | ~$0.02 |

**Premium Tier** (~$0.87 total, includes consensus voting):
| Model | Role | Tokens (in→out) | Cost |
|-------|------|-----------------|------|
| Claude Opus 4.5 | Wind | 3,542 → 1,580 | $0.0572 |
| GPT-5.2 Pro | Wall | 3,371 → 1,461 | $0.316 |
| Gemini 3 Pro Preview | Door (×3) | ~18,926 → ~8,719 | ~$0.14 |
| Claude Opus 4.5 | Consensus (×3) | ~7,899 → ~921 | ~$0.06 |
| GPT-5.2 Pro | Consensus (×3) | ~3,747 → ~1,574 | ~$0.34 |

### Cost Summary

| Tier | Cost | Turns | Status | Cost per Turn |
|------|------|-------|--------|---------------|
| Fast | $0.019 | 3 | synthesis | $0.006 |
| Standard | $0.35 | 6 | stalemate | $0.058 |
| Premium | $0.87 | 5 | synthesis | $0.174 |
| **Total** | **$1.24** | 14 | **2/3 synthesis** | - |

### Cost Ratios

| Comparison | Ratio |
|------------|-------|
| Premium vs Fast | **46x** |
| Premium vs Standard | 2.5x |
| Standard vs Fast | 18x |

### Key Observations

1. **GPT-5.2 Pro dominates Premium cost**: ~$0.66 of $0.87 (76%) from GPT-5.2 Pro
2. **GPT-5-Mini excellent value**: Full engagement at $0.00655 (vs GPT-5.2-Codex's failures)
3. **Standard tier had 4 refinement loops**: Door couldn't reach consensus, drove up cost
4. **Fast tier best ROI**: Complete synthesis for $0.019 with substantive Wall constraints

---

## Optimal Solution

### Recommendation: Hybrid of Premium + Fast

The **Premium tier** provides the most rigorous specification:
- Concrete `search_index.json` artifact
- Performance Governor with explicit thresholds
- Test harness with falsifiable criteria
- "Experiment with Kill Switch" pattern

Enhanced with **Fast tier's** novel contribution:
- Add `SEARCH_ANCHORS::[Q:A]` to decision records at synthesis time
- Pre-computed query-answer pairs create "synthetic vectors"

### Implementation Path

1. **Schema Enhancement**: Add `§META::SEARCH_ANCHORS::[Query:Answer]` to OCTAVE output
2. **Indexer**: MiniSearch with Premium's field weights (TOPIC:10, TAGS:8, SYNTHESIS:5, RATIONALE:2)
3. **Performance Governor**: 5MB index limit, 200ms boot limit, 50ms query limit
4. **Agent Tool**: `find_precedent(query)` per Standard tier's agent-first pattern
5. **Kill Switch**: Revert to grep if metrics fail

---

## Artifacts

- Fast Thread: `2026-02-04-decision-search-fast`
- Standard Thread: `2026-02-04-decision-search-standard`
- Premium Thread: `2026-02-04-decision-search-premium`

---

## Conclusions

1. **All tiers converged on BM25 with field weighting**: Validates the pattern
2. **OCTAVE structure is the key insight**: Semantic fields enable "pseudo-semantic" search
3. **Premium provides production-ready spec**: Physics Budget + test harness
4. **Fast adds novel optimization**: SEARCH_ANCHORS at synthesis time
5. **Standard's agent-first pattern is correct**: Don't spam users, empower agents
6. **New Wall models validated**: GPT-5-Mini and GPT-5.2 engage substantively
7. **Total debate cost**: $1.24 for comprehensive architectural decision
