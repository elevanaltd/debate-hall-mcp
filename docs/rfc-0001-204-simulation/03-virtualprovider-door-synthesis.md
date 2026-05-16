# Debate #3 — Door clink output (consensus refinement synthesis)

**Clink CLI**: `claude` | **Role**: `door-agent` | **Model**: `claude-opus-4-6`
**Duration**: 33.4s | **Session**: `ef6c4fb1-cf01-4f1c-acc3-24e75f7e67aa`
**Prompt source**: `format_door_consensus_prompt()` (verbatim from
`src/debate_hall_mcp/prompts/__init__.py:590-657`), with `rejector="Wind"`
and `feedback=` the Wind feedback block emitted by the prior clink hop.
DEBATE_STATE includes T1 Wind + T2 Wall + PATH_CONTRACTS + Wind's
PATH_CONTRACT_DIFF blocks from `03-virtualprovider-wind-diff.md`.

## Door's verbatim response

## DOOR (LOGOS) - Refined Synthesis

### THEREFORE...

The implementation sequence is **Path 2 (injectable factory) → Path 1 (VirtualProvider)**, with Path 3 terminal as proposed but its architectural insight preserved as a future BudgetMiddleware design captured in backlog.

### TENSION_ANALYSIS

| Wind's Position | Wall's Position | The Tension |
|-----------------|-----------------|-------------|
| Injectable factory (~50 lines) unlocks both paths | Factory is pure refactor, no protocol change — validated | No tension; consensus achieved |
| VirtualProvider delivers test-controllability | VirtualProvider covers deterministic cases only | Framing dispute: controllability vs realism |
| Budget-in-provider is the elegant insight | Protocol break (HARD_fail), architectural inversion (HARD_fail) | Terminal as proposed; reframe required |

### PATH CONTRACT CITATIONS

**Path 2** had no new divergence; original frame stands. Both verdicts HARD_pass — injectable factory is validated as pure refactor with no protocol surface change. No constraints accepted, disputed, or reframed because none were needed.

**Path 1** had no new divergence; original frame stands. The SOFT_disputed entry merits incorporation:

- [path_1.disputed: single_wall_coherence] — Wind reframes VirtualProvider's purpose as *test-controllability* (deterministic substrate for orchestration logic validation), explicitly distinct from *test-realism* (network-dependent integration confidence). This refinement sharpens the implementation: VirtualProvider validates debate flow and turn sequencing; real-provider smoke tests remain a separate, optional layer.

**Path 3** carries two HARD_fail verdicts. Both are addressed:

- [path_3.accepted: per_turn_role_contract] — Wind accepts Wall's finding with terminal rationale: adding budget to `ModelProvider.complete()` is an interface migration requiring versioned protocol extension (v2), out of scope for this priority decision. The protocol boundary is load-bearing.
- [path_3.accepted: single_wall_coherence] — Wind accepts Wall's fantasy detection: `orchestrator.py:249` owns timeout via `asyncio.wait_for`; inverting ownership is an architectural rewrite, not a refactor.
- [path_3.disputed: halting] — Wind disputes in the *opposite* direction from Wall's concern. Rather than scope creep, voluntary-pause-on-budget-exhaustion becomes naturally achievable *after* paths 1+2 land — VirtualProvider can simulate budget exhaustion by raising the same exception type that triggers PAUSED, without changing halting semantics.
- [path_3.reframed: per_turn_role_contract] — The HARD_fail reveals budget-awareness belongs as **orchestrator-level middleware**, not in the provider protocol. A `BudgetMiddleware` wrapping `asyncio.wait_for` could track cumulative cost/time across turns without touching `ModelProvider`. The orchestrator already owns the timeout boundary — extend it with accounting, don't invert ownership.

### EMERGENT PATH

**Key Insight**: VirtualProvider is an *orchestration-correctness tool*, not a provider-fidelity simulator. This framing distinction (from Wind's path_1 dispute) resolves the SOFT tension cleanly — we are not pretending to test real providers; we are creating a deterministic substrate for validating debate mechanics.

**Third Way**: The sequence Path 2 → Path 1 is not merely additive. The injectable factory makes VirtualProvider trivially swappable at test time *without* monkey-patching or import-time coupling. This yields a testing architecture where orchestration correctness and provider integration are independently verifiable layers.

### IMPLEMENTATION

1. **Path 2: Injectable Factory** (~50 lines, pure refactor)
   - Extract provider construction into a factory callable
   - Pass factory as parameter to orchestrator (default: current behavior)
   - Tests can inject `lambda: VirtualProvider(...)` without touching production code
   - Gate: all existing tests pass unchanged; `ruff`, `mypy`, `pytest` green

2. **Path 1: VirtualProvider** (~100 lines, new implementation)
   - Implement `VirtualProvider` conforming to `ModelProvider` protocol
   - Accepts scripted responses (deterministic replay for turn sequencing tests)
   - Purpose: orchestration-correctness verification, NOT provider-fidelity simulation
   - Gate: new tests demonstrate deterministic debate-flow validation

3. **Backlog capture: BudgetMiddleware** (future work item, not current scope)
   - Orchestrator-level middleware wrapping `asyncio.wait_for`
   - Tracks cumulative cost/time across turns
   - VirtualProvider can simulate budget exhaustion via exception (no protocol change)
   - Requires: design RFC before implementation

### WHAT THIS ENABLES

- **Immediate**: Deterministic test coverage for orchestration logic, debate flow, and turn sequencing — the zero-coverage gap (Wall's E6) is closed for controllable scenarios
- **Structural**: Injectable factory means any future provider variant (budget-aware, rate-limited, cached) plugs in without protocol migration
- **Emergent (1+1=3)**: The combination of factory + VirtualProvider creates a *simulation harness* — budget exhaustion, network failures, slow responses all become testable via VirtualProvider scripting, without the architectural rewrite Path 3 would have required

### DECISION RECORD

| Item | Resolution |
|------|-----------|
| Sequence | Path 2 → Path 1 |
| Path 3 | Terminal as proposed; reframed as future BudgetMiddleware |
| VirtualProvider purpose | Orchestration-correctness tool |
| Remaining open | Real-provider smoke tests (optional, gated, separate concern) |

## Inline observations (not part of clink output)

- Door's synthesis **converges to the same answer the historical T3
  Door reached** (`debates/2026-01-30-virtualprovider-vs-timebudget.oct.md`
  lines 96-109): Budgeting via VirtualProvider, factory-first, no
  protocol change. Validates that the simulation harness preserves
  signal.
- Door **explicitly cites every non-empty diff category** as the
  consensus prompt demands:
  - `[path_1.disputed: single_wall_coherence]` ✓
  - `[path_3.accepted: per_turn_role_contract]` ✓
  - `[path_3.accepted: single_wall_coherence]` ✓
  - `[path_3.disputed: halting]` ✓
  - `[path_3.reframed: per_turn_role_contract]` ✓
  All five non-empty entries from Wind's diffs are cited.
- Door **acknowledges `NO_NEW_DIVERGENCE`** for path_1 and path_2
  explicitly ("had no new divergence; original frame stands") as the
  prompt requires — does not fabricate citations.
- Door **satisfies the HARD_fail catalyst rule**: path_3 has two
  HARD_fail verdicts; both have either a corresponding `accepted` entry
  (with `terminal_rationale` for `per_turn_role_contract`) OR a
  `reframed` entry that addresses the failure (for
  `per_turn_role_contract`). For `single_wall_coherence` the citation
  routes through `[path_3.accepted: single_wall_coherence]`. **Note**:
  Wind's diff for `single_wall_coherence.accepted` did NOT carry a
  `terminal_rationale` field — Door cites it anyway. This propagates the
  same ambiguity flagged in `wind-diff.md`: the validator must decide
  whether routing the catalyst through the sibling reframe entry
  satisfies the rule for both HARD_fails or only one. Strict reading:
  `single_wall_coherence` HARD_fail lacks its own catalyst proof.
