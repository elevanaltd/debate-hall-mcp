# Debate #2 — Door consensus-refinement synthesis (fresh-session simulation)

**Source debate**: `debates/2026-01-30-rundebate-reliability-analysis.oct.md`
**Simulation harness**: clink → claude CLI, role=`door-agent`, model=claude-opus-4-6
**Run duration**: ~185s (api), ~194s wall clock
**Continuation ID**: `8c7b1698-3782-478d-b71a-8b4f77c05415`
**Input state**: T1 Wind + T2 Wall + Wind's PATH_CONTRACT_DIFFs (from prior clink turn). T3 original Door, T4 Wind APPROVE, T5 Wall APPROVED_WITH_CONDITIONS **withheld**.

## 1-line summary

Door cites every non-empty contract category using the literal `[path_N.category: invariant]` form, honors the constraint-as-catalyst rule on all three HARD_fail paths (two terminal-accepts on path_3 + two reframes on path_1/path_3), and emerges a "Layered Reliability Through Constraint Compliance" third way that integrates Path 1's reframed timeout-contract-test, Path 2's standing virtual-provider pyramid, and Path 3's reframed TimeoutSimulatingProvider into a single dependency-ordered implementation sequence.

## Captured Door synthesis

### THEREFORE...

> The three paths converge on a single implementation sequence: **fix the timeout bug first, build virtual providers second, exercise PAUSED-as-normal-flow third**. Wall's constraints did not reduce scope — they revealed that Path 2 is the vehicle, Path 1's timeout fix is its precondition, and Path 3's creative kernel survives as a specific test provider within the pyramid. The organizing principle: **reliability is layered correctness, not bolted-on observability**.

### TENSION_ANALYSIS

| Wind's Position | Wall's Position | The Tension |
|-----------------|-----------------|-------------|
| Path 1: Observe and trace (VCR, correlation IDs) | H2: Tracing a broken timeout layering doesn't fix it | Observability without correctness is diagnostic theater |
| Path 2: Virtual providers conforming to ModelProvider | All HARD_pass or SOFT_disputed — validated | No fundamental tension; design details remain |
| Path 3: Event-driven async state machine | H1/H2/H3: breaks sync, relocates timeouts, needs new MCP surface | Architectural vision exceeds reliability mandate |

### PATH CONTRACT CITATIONS

**Path 1 — HARD_fail on `timeout_ownership`:**

- `[path_1.reframed: timeout_ownership]` — Wind converts the HARD_fail into a precondition: a "timeout contract test" asserting CLI timeout < orchestrator timeout, both from a single config constant. This turns H2 from a present bug into a regression gate. The reframe succeeds because it changes Path 1's sequencing (fix first, then observe) rather than dismissing Wall's finding.
- `[path_1.disputed: protocol_stability]` — Wind argues fixture loading is internal test infra, not MCP surface. Concur: VCR cassettes sit behind ModelProvider Protocol and don't alter dispatch shape. The SOFT_disputed resolves in Wind's favor.

**Path 2 — no new divergence:**

Path 2 carried `divergence_marker: NO_NEW_DIVERGENCE`; original frame stands. Wall validated the core premise (virtual providers conforming to ModelProvider Protocol are structurally sound). Wind's sole dispute `[path_2.disputed: termination_bounds]` correctly identifies that debate termination (max_turns/max_rounds, H4) is orthogonal to CI wall-clock budget — a pytest timeout marker on the nightly tier is sufficient. No reframe was needed; none was fabricated.

**Path 3 — three HARD_fails, constraint-as-catalyst proof:**

- `[path_3.accepted: sync_api_contract]` — Wind provides terminal_rationale: "H1 is correct and unreframeable within this path's scope. run_debate is synchronous, every existing caller depends on this, and async-by-default exceeds the reliability-improvement mandate." Honest capitulation, not weak retreat.
- `[path_3.accepted: protocol_stability]` — Wind provides terminal_rationale: "H3 is correct. get_events requires new MCP surface, new dispatch, new client contract. This is not a reliability improvement — it is a platform expansion." Correctly scoped as wrong-time-wrong-place.
- `[path_3.reframed: timeout_ownership]` — The creative kernel survives: Wind proposes a `TimeoutSimulatingProvider` that exercises PAUSED→RESUMED within the existing sync architecture. This merges with Path 2's virtual provider approach — DeterministicProvider gains a sibling that stress-tests the PAUSED flow path without breaking the sync contract or requiring new MCP surface. The eventually-consistent insight lives as a **test strategy** rather than a runtime architecture.
- `[path_3.disputed: termination_bounds]` — Wind disputes not to revive the dead path but to preserve a meta-insight: max_turns/max_rounds are counting-based (integer decrements), therefore provably terminating regardless of execution model. Academically sound and useful for future architectural work.

**Absence note**: No path had empty `accepted` + `disputed` + `reframed` categories requiring fabrication. Path 1 has no `accepted` entries (its HARD_fail was reframed rather than terminally accepted). Path 2 has no `accepted` or `reframed` entries (no HARD_fails to address). All non-empty categories are cited above.

### EMERGENT PATH: Layered Reliability Through Constraint Compliance

**Key Insight**: Wall's HARD_fail on `timeout_ownership` (H2) is the load-bearing constraint. It appears in both Path 1 and Path 3's verdict history. Wind's response in both cases converges on the same realization: the timeout conflict must be fixed as infrastructure before any observability or testing work has value. This is the precondition that unifies all three paths.

**Third Way** (refined from historical "Budgeted Latent Orchestration"):

1. **Timeout Contract Layer** (from `[path_1.reframed: timeout_ownership]`):
   - Single source of truth for timeout values
   - Contract test: `assert CLI_TIMEOUT < ORCHESTRATOR_TIMEOUT`
   - Regression gate prevents future layering violations
2. **Virtual Provider Pyramid** (from Path 2, standing frame):
   - `RecordingProvider` — captures real provider responses for replay
   - `DeterministicProvider` — predictable responses for unit tests
   - `TimeoutSimulatingProvider` — (from `[path_3.reframed: timeout_ownership]`) exercises PAUSED→RESUMED flow within sync envelope
   - All conform to `ModelProvider` Protocol (E5)
3. **Dual-Mode CI** (emergent from composition):
   - Fast tier: virtual providers, no network, seconds
   - Validation tier: real providers (nightly), pytest timeout markers per `[path_2.disputed: termination_bounds]`

### IMPLEMENTATION SEQUENCE

1. **Fix H2 bug** — reconcile CLI 120s / orchestrator 300s into single config constant with contract test
2. **Injectable provider factory** — orchestrator accepts `provider_factory` callable (backward-compatible)
3. **Virtual providers** — RecordingProvider, DeterministicProvider, TimeoutSimulatingProvider (all implement ModelProvider Protocol)
4. **Test pyramid** — unit (deterministic) → integration (recording/replay) → validation (real, nightly)
5. **PAUSED-flow coverage** — TimeoutSimulatingProvider exercises voluntary suspension, proving PAUSED is normal flow without architectural change

### WHAT THIS ENABLES (1+1=3)

- **From Path 1 + Path 2**: Observability becomes meaningful because it traces a *correct* timeout layering through *deterministic* providers — no more debugging phantom failures caused by the H2 bug itself.
- **From Path 2 + Path 3**: The eventually-consistent insight (PAUSED as normal flow) becomes a *testable property* rather than an *architectural requirement*. We can prove PAUSED→RESUMED works correctly without breaking the sync contract.
- **From all three**: The implementation sequence naturally orders itself — each step's output is the next step's precondition. No parallel workstreams with hidden dependencies.

### REMAINING DESIGN DECISIONS (for implementation phase)

1. Config constant location: `orchestrator.py` top-level vs dedicated `config.py`
2. Provider factory signature: `Callable[..., ModelProvider]` vs `ProviderFactory` protocol
3. TimeoutSimulatingProvider granularity: fixed delay vs stochastic (for chaos testing)

### CONSENSUS STATUS (Door's own roll-up)

All HARD_fail verdicts accounted for:
- **Accepted with terminal rationale**: path_3 `sync_api_contract`, path_3 `protocol_stability`
- **Reframed into constructive preconditions**: path_1 `timeout_ownership` (→ contract test), path_3 `timeout_ownership` (→ TimeoutSimulatingProvider)
- **No silent omissions**.

The synthesis preserves the sync API contract (H1), resolves the timeout conflict (H2), requires no new MCP surface (H3), and respects termination bounds (H4).

## Notable anomalies / observations

1. **Citation form is exactly as RFC §5.4 specifies**: every contract reference uses the literal `[path_N.category: invariant]` form. Six explicit citations (`path_1.reframed`, `path_1.disputed`, `path_2.disputed`, `path_3.accepted` ×2, `path_3.reframed`, `path_3.disputed`). All citations correspond to entries that actually exist in Wind's diffs — no fabricated provenance.
2. **NO_NEW_DIVERGENCE acknowledged explicitly**: Door wrote *"Path 2 carried `divergence_marker: NO_NEW_DIVERGENCE`; original frame stands"* — exactly as RFC §5.4 prescribes. No invented citations for path_2's empty `accepted` / `reframed`.
3. **Both HARD_fail proof modes used on path_3**: two `accepted` entries with `terminal_rationale` AND a `reframed` entry — the consensus-phase Door prompt accepts either, but Door used both, demonstrating that "terminal-accept here, reframe there" can coexist within a single path. This is a useful proof point for the design: the schema's two modes are not mutually exclusive at the path level.
4. **Emergent ordering not in any Wind path**: the sequenced "fix H2 first → virtual providers → PAUSED-flow coverage" ordering is genuinely emergent. No single Wind path proposed it; Wind's own closing prose hinted at a composition but did not produce the dependency-ordered implementation sequence Door emerged. 1+1=3 is demonstrated.
5. **Side-channel tool-use during the turn**: Door's metadata shows `num_turns: 14` and brief Haiku usage — the agent attempted to invoke `add_turn` / `octave_write` against this worktree's state files (which don't exist here) before falling back to inline delivery. This is a **simulation-harness artifact, not a debate-content issue** — the agent persona's environmental expectation (write to debate file) collided with the simulation context (no debate file in scope). Worth noting for harness design.
6. **No `holistic-orchestrator` ho-liaison call or tool storm** beyond the file-write attempt — the agent stayed in the synthesis role.
