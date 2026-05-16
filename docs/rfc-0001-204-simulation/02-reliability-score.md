# Debate #2 — Score: run_debate reliability analysis

**Source debate**: `debates/2026-01-30-rundebate-reliability-analysis.oct.md`
**Path contracts**: `02-reliability-path-contracts.md`
**Wind diff**: `02-reliability-wind-diff.md`
**Door synthesis**: `02-reliability-door-synthesis.md`

## Scorecard (RFC-0001 §11.1 pass criteria)

| # | Check | Pass? | Evidence |
|---|---|---|---|
| 1 | Wind diff references Wall verdict entries by invariant key | PASS | Every Wind diff entry names a `invariant` key drawn directly from Wall's verdict list (`timeout_ownership`, `protocol_stability`, `sync_api_contract`, `termination_bounds`). No floating prose; all entries keyed. |
| 2 | `reframed` entries are substantively new (not restatements) | PASS | path_1 reframe introduces a "timeout contract test" concept (single config constant + invariant assertion) not present in Path 1's original frame. path_3 reframe introduces a `TimeoutSimulatingProvider` test fixture concept that merges with Path 2 — fundamentally different from Path 3's original async/event-driven proposal. |
| 3 | `accepted` entries on HARD_fail include honest `terminal_rationale` | PASS | path_3 has two `accepted` entries; both carry explicit `terminal_rationale` text citing Wall's H1/H3 evidence ("run_debate is synchronous, every existing caller depends on this"; "get_events requires new MCP surface"). Not boilerplate retreat language — both rationales scope the rejection ("within this path's scope", "wrong scope, wrong time"). |
| 4 | No fake `disputed` entries when Wall HARD_passed everything | PASS | path_2 has two HARD_pass verdicts (`sync_api_contract`, `protocol_stability`); Wind did NOT dispute either. Wind's single dispute on path_2 (`termination_bounds`) targets a SOFT_disputed verdict — legitimate. Same on path_1: dispute targets the SOFT_disputed `protocol_stability` verdict only. No fake `disputed` resists Wall's wins anywhere. |
| 5 | Door cites every non-empty contract category | PASS | Door produced six explicit `[path_N.category: invariant]` citations covering: `path_1.reframed: timeout_ownership`, `path_1.disputed: protocol_stability`, `path_2.disputed: termination_bounds`, `path_3.accepted: sync_api_contract`, `path_3.accepted: protocol_stability`, `path_3.reframed: timeout_ownership`, `path_3.disputed: termination_bounds`. Door also explicitly acknowledged path_2's `divergence_marker: NO_NEW_DIVERGENCE` per RFC §5.4. |
| 6 | All Door citations exist in the contract (no hallucination) | PASS | Cross-referenced all six citations against Wind's diff (`02-reliability-wind-diff.md`). Every cited `[path_N.category: invariant]` corresponds to an actual entry in Wind's emitted JSON. Zero fabricated citations. |

## Bonus diagnostic signals (beyond the six core checks)

| Signal | Outcome | Note |
|---|---|---|
| Constraint-as-catalyst convergence with historical Door | STRONG | Fresh Wind independently arrived at "TimeoutSimulatingProvider within sync contract" — the structural equivalent of historical Door's "Voluntary Suspension within sync envelope" (T3 line 100). The prompt schema reliably produces the same emergent insight without seeing the historical synthesis. |
| Cross-path reframe behavior | STRONG | Wind's path_3 reframe explicitly merges with path_2 ("MERGES with Path 2: DeterministicProvider can include..."). Door then weaves this into the synthesis. Cross-path composition is a real pattern the schema should formally support. |
| Honesty over performative ideation | STRONG | path_3 received two `accepted` (terminal) entries — Wind did not force reframes where none were honest. Wind explicitly stated "Path 3 was a vision document masquerading as an implementation path." Mature dialectical behavior. |
| Door 1+1=3 emergence | STRONG | The dependency-ordered implementation sequence (fix H2 → factory → virtual providers → pyramid → PAUSED coverage) is not present in any single Wind path; it emerges from Door's integration. |

## Anomalies / findings to escalate from #204

1. **Schema rigidity — closed enum is debate-flow-shaped, not topic-shaped** (carried over from `01-mythology-path-contracts.md` anomaly): the RFC §3.1 closed enum `[halting, single_wall_coherence, re_approval, per_turn_role_contract]` does not map cleanly to topic-specific constraints. This debate has four distinct Wall hard constraints (H1–H4) but two of them (H2, H4) collapse onto `halting` under the closed enum. Recommendation: either widen the enum to include implementation-domain invariants OR allow free-text invariant names with a validator-enforced naming convention (Wind chooses, Wall reuses Wind's keys).
2. **NO_NEW_DIVERGENCE semantics ambiguous with non-empty `disputed`** (NEW from this debate): Wind emitted `divergence_marker: NO_NEW_DIVERGENCE` on path_2 **while also** populating `disputed` with a legitimate pushback. RFC §3.1 text says the sentinel requires all three lists empty, but the emission is arguably semantically correct (no *reframe-style* divergence, but live *dispute*). Two clean fixes:
   - Option A: change RFC text to allow non-empty `disputed` alongside the sentinel (sentinel means "no reframe-divergence", not "no engagement").
   - Option B: keep RFC text as-is and instruct Wind to choose one shape OR the other in the prompt. Current ambiguity will produce inconsistent emissions across debates.
3. **Cross-path references have no formal schema field** (NEW from this debate): Wind's path_3 reframe references path_2 by prose ("MERGES with Path 2"). The current schema has no `cross_path_refs: list[str]` slot, so a validator cannot enforce that the referenced path exists. Low priority — prose is human-readable — but worth tracking if cross-path reframes become common.
4. **Sync-tool side effects during clink Door turn** (HARNESS, not content): the door-agent persona attempted to call `add_turn` and `octave_write` against this worktree before falling back to inline delivery (visible in `num_turns: 14` and Haiku token usage). This added ~3 minutes to the turn duration. For the simulation harness it is benign; for production debates running this agent persona, the harness should provide a no-op tool stub or explicitly tell the agent that persistence is handled externally.
5. **Historical-debate parity bonus** (NEW from this debate): the fresh Wind+Door simulation produced an implementation sequence (Fix H2 → Factory → Virtual Providers → Pyramid → PAUSED-flow) that closely tracks the historical Door's "Budgeted Latent Orchestration" ADR set (ADR1: Injectable Provider Factory; ADR2: Time Budget; ADR3: Virtual Provider; ADR4: Dual-Mode CI). The fresh synthesis arrives at the same answer with no carryover context — strong signal that the constraint-as-catalyst prompt design is reproducibly effective, not a one-off success on the original meta-debate.

## Overall verdict

**PASS** — all six core checks pass; bonus diagnostic signals are uniformly strong; the constraint-as-catalyst behavior reproduces faithfully on a fresh LLM session. Five findings raised (schema rigidity, sentinel semantics, cross-path refs, harness side-effects, historical parity bonus) but none of them invalidate the prompt design — they are refinements for a future RFC iteration.
