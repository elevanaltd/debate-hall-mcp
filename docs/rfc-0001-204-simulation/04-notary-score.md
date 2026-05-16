# Debate #4 — Score (Cognitive Notary Architecture)

**Path-contracts**: `04-notary-path-contracts.md`
**Wind diff**: `04-notary-wind-diff.md`
**Door synthesis**: `04-notary-door-synthesis.md`

## Criteria (from `README.md` §"Methodology" item 7)

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Wind diff references Wall's verdict entries by invariant key | PASS | path_2's `disputed` cites `cognitive_state_isolation` (the SOFT_disputed verdict). path_3's `accepted` cites all three HARD_fail invariants (`north_star_identity`, `ledger_write_path_singularity`, `audit_trail_completeness`). All four invariant keys are exact matches to Wall's verdict block. |
| 2 | `reframed` entries are substantively new (not restatements of the original path) | N/A (vacuously) | Wind emitted ZERO `reframed` entries. This is honest — Wind argued the path-3 reframes are terminally blocked because the constraints are self-cancelling against the stateless premise. The simulation criterion does not require fabricated reframes; it requires that any emitted reframe be substantive. |
| 3 | HARD_fail `accepted` entries have honest `terminal_rationale` | PASS | All three path_3 `accepted` entries include `terminal_rationale` with structural explanations (identity-is-constitutive, statelessness-self-cancels, you-cannot-verify-what-you-cannot-remember). Each terminal_rationale identifies *why* the constraint cannot be reframed, not just *that* Wind agrees. |
| 4 | Wind doesn't invent fake `disputed` entries when Wall HARD_passed everything | PASS | path_1 (two HARD_passes) correctly emits `NO_NEW_DIVERGENCE` sentinel with rationale. No fabricated `disputed`/`accepted`/`reframed`. |
| 5 | Door's citations exist in the contract (`[path_N.accepted: <invariant>]` syntax) | PASS | Door cites: `[path_1.divergence_marker: NO_NEW_DIVERGENCE]`, `[path_2.disputed: cognitive_state_isolation]`, `[path_3.accepted: north_star_identity]`, `[path_3.accepted: ledger_write_path_singularity]`, `[path_3.accepted: audit_trail_completeness]`. Every citation maps to a real entry in Wind's diff. No invented citations. |

**Aggregate verdict**: **PASS** (5/5 with criterion 2 vacuously satisfied).

## Constraint-as-catalyst engagement

Wind did not produce a *reframe* for path_3, but it DID produce constraint-catalyst behavior at the *inter-path* level: Wind's synthesis guidance to Door ("P1 + P2 as LAYERS, not alternatives") IS the creative emergence that arose from killing path_3. The "Cognitive Notary" reframe (Brain AND Notary) that the historical Door synthesis arrived at is structurally identical to the layered architecture Door synthesized in this simulation:

- Historical Door §5 LAYER_1_PRIMITIVES + LAYER_2_COGNITION + LAYER_3_QUERY
- Simulation Door Layer 0 (Primitives) + Layer 1 (Recipes) + Layer 2 (Query)

The simulation independently reached the same three-layer architecture without ever seeing the historical synthesis. This is strong evidence that the path-contract refinement protocol preserves the constraint-as-catalyst behavior end-to-end.

## Honesty signal

Wind's path_3 response is the cleanest possible execution of the "honesty over performative ideation" rule: rather than invent a reframe for the sake of producing one, Wind acknowledged that the three HARD_fails are *self-cancelling against the path's own premise* and emitted three `accepted` entries with structural terminal_rationale. The creative work then migrated to the inter-path synthesis guidance, which is the *correct* locus for it.

## Anomalies (forwarded to Phase E)

1. **Wind's APPROVE/REJECT verdict on a non-existent Door synthesis.** `format_wind_approval_prompt` asks Wind to APPROVE/REJECT Door's synthesis. In our simulation §5 SYNTHESIS is intentionally withheld so the Door synthesis must be generated fresh; this means there is no synthesis for Wind to approve at the consensus-DIFF step. Wind acknowledged this and called the approval "conditional", but the prompt's APPROVE/REJECT semantics are awkward here. **Finding**: the consensus-phase prompts assume a specific turn order (Door → Wind-consensus → Door-refinement) that the simulation harness reverses (Wind-diff before Door synthesis). Either the harness should run an initial Door synthesis first, or the consensus prompts should detach the diff emission from the APPROVE/REJECT vote.

2. **Wind/Door performed live codebase reads inside the clink.** Both agents used their Read/Grep/Glob tools to ground their responses in `tools/decision.py`, `state.py`, `events.py`, etc. The simulation prompt did not request this but did not forbid it. This produces empirically richer responses than pure-prompt simulation but also means the simulation is testing *codebase-grounded path refinement*, not *pure prompt-driven path refinement*. **Finding to log**: future simulations should decide explicitly whether agents may perform live reads, since this materially affects the test signal — pure-prompt agents would have to reason about isolation structurally rather than empirically.

3. **Door said "The thread doesn't exist in this worktree's state directory."** Door briefly looked for a real debate thread before realizing the state was inline. No-op for the simulation but indicates the consensus prompts implicitly expect a real Hall instance.

4. **Inter-path reframe vs. per-path reframe.** Wind's actual creative output (the layered architecture) lives outside the PATH_CONTRACT_DIFF schema — it was attached as free-form "Synthesis Guidance for Door". The RFC-0001 schema currently has no slot for cross-path emergent insights, only per-path diffs. **Finding**: consider an optional `cross_path_reframe` or `synthesis_guidance` field in the consensus turn output, so this signal isn't lost when the only structured output is per-path diffs.
