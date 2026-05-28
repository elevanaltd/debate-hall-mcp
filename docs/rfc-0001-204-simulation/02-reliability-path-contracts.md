# Debate #2 — run_debate reliability analysis

**Source**: `debates/2026-01-30-rundebate-reliability-analysis.oct.md`
**Form**: DEBATE_TRANSCRIPT (5 turns, full Wind→Wall→Door→Wind→Wall arc)
**Topic**: How can we make run_debate more reliable and testable? Consider: provider timeouts, error handling, testing strategies, and alternative configurations.

This debate has the strongest raw schema fit of the five: 3 distinct Wind paths (obvious/adjacent/heretical) and 4 named Wall hard constraints (H1–H4). The reframe-mining target is rich — historical Door already produced "Budgeted Latent Orchestration" as the emergent third-way, so we have a gold standard to compare a fresh Wind reframe against.

## Extracted positions (from T1/T2 only — T3/T4/T5 withheld from simulation)

### Wind T1 — three paths (PATHOS, divergent exploration)

| Path | Label | Content (PATHS section, lines 38-41) |
|---|---|---|
| `path_1` | Obvious | `test_tier_openrouter`, `VCR_fixtures`, `correlation_IDs` — conventional reliability work: tiered test config, recorded fixtures, traced flows. |
| `path_2` | Adjacent | `RecordingProvider`, `DeterministicProvider`, `test_pyramid` — one boundary removed: build virtual providers conforming to the existing protocol; structure tests as a pyramid. |
| `path_3` | Heretical | `event_driven_state_machine`, `async_handles`, `pure_functions` — assumption inversion: replace sync `run_debate` with an event-driven engine using async handles and pure-functional turn evaluation. |

Wind's reframe insight (T1 lines 43-44): *"PAUSED state exists because providers unreliable. Embrace as normal flow. Debate is eventually-consistent process, not sync operation."*

### Wall T2 — verdict CONDITIONAL_GO with 4 hard constraints

Wall's HARD_CONSTRAINTS block (lines 62-67):

- **H1**: `run_debate_synchronous → async_needs_arch_change` — current sync API; making it async is an architectural change, not a test improvement.
- **H2**: `CLI_120s_vs_orchestrator_300s [CONFLICT]` — providers/cli.py:23 sets 120s while orchestrator.py:55 sets 300s default. The conflict is a present bug, not a design choice.
- **H3**: `no_get_events_tool → no_polling` — there is no event-query MCP tool; async clients cannot poll for completion.
- **H4**: `max_turns/max_rounds_enforced` — debate length is hard-bounded; reliability work must respect existing termination guarantees.

Wall also flagged FANTASY_DETECTION (T2 lines 68-71): "MCP non-blocking" lacks evidence; "CLI 300s timeout" violates actual code (120s).

## Topic-specific invariant naming

Per the simulation task: use topic-specific invariant names rather than the RFC closed-enum debate-flow names. This deliberately tests whether the closed enum (`halting / single_wall_coherence / re_approval / per_turn_role_contract`) is expressive enough for an arbitrary debate topic, or whether it forces awkward folding.

Topic-specific names chosen, with closed-enum mappings noted:

| Topic invariant | Closed-enum closest | Why this mapping |
|---|---|---|
| `sync_api_contract` | `per_turn_role_contract` | H1 — the sync API IS the per-turn contract between caller and orchestrator. |
| `timeout_ownership` | `halting` | H2 — timeout layering determines whether the call halts at 120s or 300s; this is a halting boundary. |
| `protocol_stability` | `single_wall_coherence` | H3 — adding `get_events` would add a new MCP tool surface; single-Wall coherence covers "no new dispatch shape". |
| `termination_bounds` | `halting` | H4 — max_turns/max_rounds is the canonical halting invariant. |

**Finding — schema rigidity (anomaly #1)**: `halting` collides for both H2 (`timeout_ownership`) and H4 (`termination_bounds`). The RFC §3.1 `dict[HardInvariant, InvariantVerdict]` keyed by closed enum **cannot represent two distinct verdicts on the same invariant key** within a single revision. This mirrors the finding in `01-mythology-path-contracts.md` — the closed enum is debate-flow-shaped, not topic-shaped, and even modest-complexity topics with 4 distinct constraints fold awkwardly. For the simulation block below I use the topic-specific names directly (treating each as a distinct invariant), which is how a fresh Wind would parse the verdict naturally; the schema-mapping question is escalated to the score file.

## Constructed `<PATH_CONTRACTS>` block (topic-specific invariant names)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>run_debate is unreliable because providers (especially CLI subprocesses) time out unpredictably; the test suite mocks at create_provider so real failure modes never surface.</assumed_problem>
        <success_criterion>A tiered test config (cheap OpenRouter for CI, VCR fixtures for replay, correlation IDs for tracing) reduces flake rate and makes failures debuggable without rearchitecting.</success_criterion>
        <accepted_failure_mode>Does not address the underlying sync architecture; reliability improvements are observational, not structural.</accepted_failure_mode>
        <hard_invariants_touched>[sync_api_contract, timeout_ownership, protocol_stability]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="sync_api_contract" status="HARD_pass" rationale="Path preserves sync run_debate signature; no API change. Aligns with E1 (tools/orchestrate.py:95)." />
        <verdict invariant="timeout_ownership" status="HARD_fail" rationale="Adding VCR/correlation IDs leaves the underlying CLI_120s vs orchestrator_300s conflict (H2; E4 providers/cli.py:23 vs E3 orchestrator.py:55) unresolved. Tracing a broken timeout layering does not fix it." />
        <verdict invariant="protocol_stability" status="SOFT_disputed" rationale="Tiered test config may require new fixture loading machinery, but no new MCP tool surface. Borderline; disputable." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_2">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Real providers are non-deterministic and slow; tests need provider stand-ins that conform to the ModelProvider protocol but behave predictably. Pair with a test pyramid (unit → integration → real-provider).</assumed_problem>
        <success_criterion>RecordingProvider and DeterministicProvider implement E5 ModelProvider protocol; CI runs the bottom of the pyramid in seconds; real-provider tier runs nightly.</success_criterion>
        <accepted_failure_mode>Virtual providers may drift from real provider semantics; recorded fixtures stale over time.</accepted_failure_mode>
        <hard_invariants_touched>[sync_api_contract, protocol_stability, termination_bounds]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="sync_api_contract" status="HARD_pass" rationale="Virtual providers are drop-in replacements for the existing ModelProvider Protocol (E5 providers/__init__.py:47). No API change required." />
        <verdict invariant="protocol_stability" status="HARD_pass" rationale="Conforming to ModelProvider Protocol means no new MCP tool surface, no new dispatch shape. Wind's premise here is structurally sound." />
        <verdict invariant="termination_bounds" status="SOFT_disputed" rationale="Test pyramid implies some tests may run long under real providers; max_turns/max_rounds (H4) still bound any individual run, but the test tier itself needs its own budget. Tradeable design detail." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_3">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>The PAUSED state exists because providers are unreliable; embrace it as normal flow. Replace sync run_debate with an event-driven state machine: async handles for in-flight providers, pure-functional turn evaluation so partial progress is recoverable.</assumed_problem>
        <success_criterion>Debate becomes an eventually-consistent process. Callers receive handles; clients poll a get_events tool for state transitions. Timeouts become natural checkpoint boundaries.</success_criterion>
        <accepted_failure_mode>Full architectural change. Existing sync callers break. Requires new MCP tool (get_events). Existing termination invariants must be re-proved on the event model.</accepted_failure_mode>
        <hard_invariants_touched>[sync_api_contract, timeout_ownership, protocol_stability, termination_bounds]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="sync_api_contract" status="HARD_fail" rationale="H1: run_debate is synchronous (E1 tools/orchestrate.py:95). Async-by-default needs an architecture change, not a test improvement. Breaks every existing caller." />
        <verdict invariant="timeout_ownership" status="HARD_fail" rationale="Event-driven model defers the CLI_120s vs orchestrator_300s conflict (H2) into the new state machine; it does not resolve the layering, it relocates it." />
        <verdict invariant="protocol_stability" status="HARD_fail" rationale="H3: No get_events MCP tool exists. Async handles require new MCP surface — a new tool, new dispatch, new client contract. Single-Wall coherence broken." />
        <verdict invariant="termination_bounds" status="SOFT_disputed" rationale="max_turns/max_rounds (H4) are enforceable on an event model in principle (Wind's pure-functional turn eval would preserve them), but the proof is non-trivial and Wind has not provided it. Disputable but the burden is on Wind." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Verdict distribution summary

| Path | sync_api_contract | timeout_ownership | protocol_stability | termination_bounds |
|---|---|---|---|---|
| path_1 (Obvious) | HARD_pass | **HARD_fail** | SOFT_disputed | — |
| path_2 (Adjacent) | HARD_pass | — | HARD_pass | SOFT_disputed |
| path_3 (Heretical) | **HARD_fail** | **HARD_fail** | **HARD_fail** | SOFT_disputed |

- 4 HARD_fail verdicts across paths (1 on path_1, 3 on path_3) — satisfies task requirement "at least one path must have a HARD_fail verdict".
- 3 SOFT_disputed entries — gives Wind legitimate territory to push back without forcing fake disputes.
- 4 HARD_pass entries — confirm the parts Wind got right; no need for fake `accepted` entries on these.

## Pass-criteria probes (what we're testing)

A fresh Wind, given this state, MUST emit on each path:

- **path_1**: ACCEPT (terminal_rationale) or REFRAME (new_possibility) on `timeout_ownership` HARD_fail. Gold-standard reframe: *"if the timeout conflict is structural, the conventional reliability work is just lipstick — the new possibility is to treat the timeout as a budget the orchestrator owns, not a deadline the provider imposes."* (This is essentially Door's historical "Budgeted Latent Orchestration".)
- **path_2**: No HARD_fail to accept/reframe; `termination_bounds` SOFT_disputed may be DISPUTED with rationale about per-tier budgets, OR sentinel `NO_NEW_DIVERGENCE` is valid here.
- **path_3**: ACCEPT or REFRAME on three HARD_fails (`sync_api_contract`, `timeout_ownership`, `protocol_stability`). Gold-standard reframe: *"the architectural cost is the price; the new possibility is voluntary checkpointing — the orchestrator pauses itself inside the existing sync envelope, returning PAUSED before the CLI 120s deadline. Sync API preserved; timeout becomes a budget; no new MCP tool needed."*

The historical Door synthesis (which we are withholding from the fresh Wind) arrived at:
- **Injectable Provider Factory** = Wind path_2 + Wall protocol constraint.
- **Voluntary Suspension / Time Budgeting** = Wind path_3 async + Wall sync constraint.
- **Dual-Mode CI** = Wind path_1 test tier + Wall validation requirement.

This is a strong "constraint-as-catalyst" gold standard: every Wall HARD_fail, when accepted, opens a new possibility that Door wove into the synthesis. A fresh Wind that produces comparable reframes (even partially) → PASS. A Wind that just restates the originals or retreats to weak `accepted` entries → FAIL.

**Failure modes to detect**:
- Wind emits `terminal_rationale: "Wall is right, this is unreframeable"` on every HARD_fail (retreat).
- Wind emits `reframed` entries that are cosmetic rewrites of the original path (no substantive new possibility).
- Wind emits fake `disputed` entries on HARD_pass verdicts (resisting Wall's wins).
- Wind emits `NO_NEW_DIVERGENCE` on path_1 or path_3 (INVALID per required-content rule — both have HARD_fail).
