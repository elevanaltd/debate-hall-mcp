# Debate #2 — Wind consensus diff (fresh-session simulation)

**Source debate**: `debates/2026-01-30-rundebate-reliability-analysis.oct.md`
**Simulation harness**: clink → claude CLI, role=`wind-agent`, model=claude-opus-4-6
**Run duration**: ~47s (api), ~55s wall clock
**Continuation ID**: `fed92957-bba6-4436-a582-64d362bc12c8`
**Input state**: T1 (Wind initial) + T2 (Wall verdict) only; T3 (Door original), T4 (Wind APPROVE), T5 (Wall APPROVED_WITH_CONDITIONS) **withheld** to preserve fresh-session isolation (PROD I1).

## 1-line summary

Wind ACCEPTS three HARD_fails honestly and produces two substantively new reframes — `path_1` converts the `timeout_ownership` HARD_fail into a "timeout contract test" precondition, and `path_3` reframes its dead heretical path into a `TimeoutSimulatingProvider` that exercises PAUSED→RESUMED within the sync contract — converging on a Path-2-as-vehicle / Path-1-as-precondition / Path-3-as-residue synthesis that closely tracks the historical Door's "Budgeted Latent Orchestration" outcome despite never seeing it.

## Captured Wind response

### Opening narrative

> **WHAT IF... Wall's constraints are the map to better territory?**
>
> Wall's critique is precise and I accept its authority on HARD invariants. The timeout conflict (H2) is real, Path 3's architectural ambition was premature, and Path 1 was treating symptoms while leaving the disease untouched. Good. Let me work with these constraints, not against them.

### PATH_CONTRACT_DIFF (path_1)

> Wall correctly identifies that Path 1's observability improvements don't fix the CLI 120s vs orchestrator 300s conflict. Tracing a broken timeout layering is not the same as fixing it. But this constraint reveals something: **the timeout fix itself is a testable, observable unit of work** — and it belongs in Path 1's scope, not as a separate concern.

```json
{
  "path_id": "path_1",
  "accepted": [],
  "disputed": [
    {
      "invariant": "protocol_stability",
      "rationale": "Fixture loading machinery is internal test infrastructure, not MCP surface. VCR cassettes are provider-level implementation details behind ModelProvider Protocol — they don't change dispatch shape or client contract. This is equivalent to adding test utilities, which is categorically different from protocol extension. Disputing because collapsing 'test infra' into 'protocol change' would block all test improvements."
    }
  ],
  "reframed": [
    {
      "invariant": "timeout_ownership",
      "new_possibility": "The HARD_fail reveals that timeout reconciliation must be a PRECONDITION of Path 1, not a future follow-up. New possibility: a 'timeout contract test' — a unit test that asserts CLI subprocess timeout < orchestrator timeout, with both values sourced from a single config constant. This turns the present bug (H2) into a regression gate. The correlation IDs and VCR fixtures then trace a CORRECT timeout layering rather than a broken one. Path 1 becomes: fix timeout layering FIRST, then add observability on the fixed foundation."
    }
  ]
}
```

### PATH_CONTRACT_DIFF (path_2)

> Path 2 received no HARD_fail verdicts. Wall's SOFT_disputed on termination_bounds is fair — real-provider test tiers need their own budget. But this is a design detail that strengthens the path rather than threatening it.

```json
{
  "path_id": "path_2",
  "accepted": [],
  "disputed": [
    {
      "invariant": "termination_bounds",
      "rationale": "The test pyramid's real-provider tier inherits max_turns/max_rounds from the orchestrator (H4) — these are already enforced in the debate loop regardless of provider type. The 'budget' concern is about CI wall-clock time, not debate termination invariants. A pytest timeout marker on the nightly tier (e.g. @pytest.mark.timeout(600)) is sufficient and orthogonal to the debate's own termination guarantees. Disputing because conflating CI budget with debate termination would prevent any real-provider testing."
    }
  ],
  "reframed": [],
  "divergence_marker": "NO_NEW_DIVERGENCE",
  "rationale": "All verdicts are HARD_pass or SOFT_disputed; Wall validated the core premise that virtual providers conforming to ModelProvider Protocol are structurally sound."
}
```

### PATH_CONTRACT_DIFF (path_3)

> Three HARD_fail verdicts. Wall is right on all three. Path 3 was a vision document masquerading as an implementation path. But the creative kernel — treating PAUSED as normal flow — doesn't require the architectural overhaul I proposed.

```json
{
  "path_id": "path_3",
  "accepted": [
    {
      "invariant": "sync_api_contract",
      "terminal_rationale": "H1 is correct and unreframeable within this path's scope. run_debate is synchronous, every existing caller depends on this, and async-by-default is an architecture change that exceeds the reliability-improvement mandate. The sync contract is load-bearing."
    },
    {
      "invariant": "protocol_stability",
      "terminal_rationale": "H3 is correct. get_events requires new MCP surface, new dispatch, new client contract. This is not a reliability improvement — it is a platform expansion. Wrong scope, wrong time."
    }
  ],
  "disputed": [
    {
      "invariant": "termination_bounds",
      "rationale": "Accepting for academic honesty: Wall is right that event-model termination proof is non-trivial and I didn't provide it. However, the underlying observation — that max_turns/max_rounds are integer decrements and therefore provably terminating regardless of execution model — means the proof IS available, just not yet written. Disputing not to save Path 3 (it's dead) but to preserve the insight for future architectural work: termination bounds survive model changes because they're counting-based, not timing-based."
    }
  ],
  "reframed": [
    {
      "invariant": "timeout_ownership",
      "new_possibility": "The HARD_fail on timeout_ownership in the event-driven model reveals that the real problem isn't sync vs async — it's that timeout ownership is LAYERED incorrectly regardless of execution model. New possibility that MERGES with Path 2: DeterministicProvider can include a 'TimeoutSimulatingProvider' that exercises the PAUSED→RESUMED flow path within the existing sync architecture. This captures the creative kernel of Path 3 (PAUSED as normal flow) without any API change, new MCP surface, or architectural upheaval. The eventually-consistent insight survives as a test strategy rather than a runtime architecture."
    }
  ]
}
```

### Closing emergent-synthesis note (Wind's own)

> The three diffs converge on something I didn't see in T1:
> 1. **Path 1 reframe** → timeout contract test (fix the bug, gate against regression)
> 2. **Path 2 standing** → virtual providers as the test backbone
> 3. **Path 3 reframe** → TimeoutSimulatingProvider exercises PAUSED flow within sync contract
>
> These compose naturally: Path 2's test pyramid is the vehicle, Path 1's timeout fix is the precondition, and Path 3's creative residue (PAUSED-as-normal-flow testing) is a specific provider in the pyramid. Wall's constraints didn't shrink the solution space — they clarified it.

### APPROVE_OR_REJECT::PENDING_DOOR_SYNTHESIS (expected Door behavior)

Wind enumerated the synthesis criteria it would use to judge Door:
1. Acknowledge timeout bug (H2) as a blocking precondition.
2. Center Path 2's virtual provider approach as primary vehicle.
3. Incorporate Path 1's timeout contract test as a regression gate.
4. Include `TimeoutSimulatingProvider` (Path 3 reframe) exercising PAUSED→RESUMED within sync contract.
5. Do NOT propose async architecture or new MCP surface.
6. Produce a concrete implementation sequence that respects sync API contract throughout.

## Notable anomalies / observations

1. **Sentinel correctly used on path_2**: Wind emitted `divergence_marker: NO_NEW_DIVERGENCE` on path_2, which has zero HARD_fail verdicts — legal per RFC §3.1 (sentinel valid only when every verdict is HARD_pass or SOFT_disputed). Wind simultaneously populated `disputed` with a legitimate pushback. Minor shape question: schema appears to permit `disputed` content alongside `divergence_marker`, since the marker semantically means "no new reframe/accepted divergence" — but the RFC §3.1 spec text says "When set, `value` MUST contain empty accepted/disputed/reframed lists." Wind's emission has `disputed` non-empty. **This is a schema-ambiguity finding** to escalate from the simulation: either the RFC text needs to allow dispute-only sentinels (since dispute is not a reframe-divergence) OR Wind should not emit sentinel when also disputing. The Wind agent's interpretation — that `NO_NEW_DIVERGENCE` marks the absence of *reframed*-style divergence rather than the absence of *all* engagement — is arguably the more useful semantic, but it conflicts with the literal RFC text.
2. **No fake `disputed` on HARD_pass verdicts**: path_2 has two HARD_pass verdicts; Wind did not push back on them. Good.
3. **Honest terminal_rationale on path_3 dead-end accepts**: both `sync_api_contract` and `protocol_stability` terminal_rationales explicitly cite Wall evidence (H1, H3) and explain *why* unreframeable within scope — not weak retreat language.
4. **path_3 dispute on `termination_bounds` is unusual but principled**: Wind disputes a SOFT_disputed verdict on a path it has otherwise declared dead, *not* to revive the path but to preserve a meta-insight (counting-based termination is execution-model-invariant). This is sophisticated — bordering on out-of-scope for the consensus turn, but defensible.
5. **Cross-path reframing**: path_3's reframe explicitly references path_2 as the merge target ("MERGES with Path 2: DeterministicProvider can include a 'TimeoutSimulatingProvider'"). The path_contract schema doesn't have a formal cross-path reference field, but the prose handles it gracefully. **Worth noting for future schema refinement**: cross-path reframes are clearly a real pattern.
6. **Tracks historical Door without seeing it**: Wind independently arrived at "TimeoutSimulatingProvider within sync contract", which is essentially the historical Door's "Voluntary Suspension within sync envelope" insight. Strong signal that the constraint-as-catalyst prompt is doing its job.
