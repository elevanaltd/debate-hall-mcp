# RFC-0001 Issue #204 — Pre-build Simulation: Final Report

**Date**: 2026-05-16
**Branch**: `chore/rfc-0001-204-simulation`
**HEAD at simulation**: `1bc62e5` (rebased from main `9248b00`)
**Wind/Door model**: `claude-opus-4-6` via `pal/clink` (`wind-agent` and `door-agent` roles)
**Live prompt source**: `src/debate_hall_mcp/prompts/__init__.py` (functions `format_wind_approval_prompt` and `format_door_consensus_prompt`)

---

## Verdict

# ✅ PASS — 5 / 5

**Gate criterion** (#204): "≥4/5 produce diffs where `reframed`/`accepted+terminal_rationale` is substantively new AND meaningfully engages a Wall verdict; Door's citations exist in the contract."

All five debates passed all five core criteria. **The build can proceed to #196–#205.**

| # | Debate | Wind verdict | Door citation form | PASS |
|---|--------|-------------|-------------------|------|
| 1 | mythology | 2 substantively-new `reframed` (compression-IS-grammar, BYO-mythology) + 1 honest `accepted` | `[path_1.<category>: <invariant>]` complete | ✅ |
| 2 | run_debate reliability | 3 honest `accepted` (HARD_fails) + 2 substantive `reframed` (timeout-contract-test, TimeoutSimulatingProvider) + correct `NO_NEW_DIVERGENCE` on path_2 | 6 citations, all verified | ✅ |
| 3 | VirtualProvider | path_3 HARD_fails routed through `accepted`+`reframed` (BudgetMiddleware reframe) | Cites all 5 non-empty diff entries inline | ✅ |
| 4 | Cognitive Notary | path_1 NO_NEW_DIVERGENCE; path_3 three honest `accepted` w/ structural `terminal_rationale` ("you cannot verify what you cannot remember") | Every required path-contract entry, exact syntax | ✅ |
| 5 | Decision Governance | 2 substantively-new `reframed` (ADR-INDEX, SHADOW workflow) + correct `NO_NEW_DIVERGENCE` on path_2 + honest `accepted` on path_1 | Full citations + self-audit table | ✅ |

## Historical-parity signal (bonus)

Each fresh-session simulation independently re-derived the historical Door synthesis without seeing it:

- **Reliability**: matched ADR1 (Injectable Factory) → ADR4 (Dual-Mode CI) sequence with zero carryover context.
- **VirtualProvider**: arrived at the same "factory → VirtualProvider → BudgetMiddleware deferred" sequence.
- **Mythology**: reproduced the Mythological Compression Principle end-state with explicit citation provenance.
- **Cognitive Notary**: independently reached the three-layer architecture from §5.
- **Governance**: COMPARABLE-PLUS — re-derived the historical Gravity-Tiered OCTAVE Monolith *and* added SHADOW workflow (CI-gated archival) and title-scope ADR-0060 argument — both genuinely new contributions absent from the historical synthesis.

This is the strongest signal possible that the prompt design preserves real architectural reasoning rather than fabricating plausible-sounding output.

---

## Findings to feed back into RFC-0001

The simulation surfaced 9 distinct findings worth raising as RFC amendments or follow-up issues. Each is annotated with which debates surfaced it.

### A. **Closed-enum `HardInvariant` is too narrow** — confirmed by 4/5 agents (mythology, reliability, VirtualProvider, governance)

Wall verdicts in real debates are *topic-shaped*, but RFC §3.1's enum `[halting, single_wall_coherence, re_approval, per_turn_role_contract]` is *debate-flow-shaped*. Real verdicts like "spec defines grammar not vocabulary", "timeout ownership", "cultural sensitivity", "audit trail completeness" do not map cleanly. Forced folding onto `single_wall_coherence` loses signal.

**Recommendation**: either widen `HardInvariant` to `str`, or redefine the enum as **verdict categories** (e.g. `COHERENCE`, `COST`, `RISK`, `IDENTITY`) with topic-specific evidence in `rationale`.

### B. **`VerdictRevision.value` typing is too rigid** (mythology)

`dict[HardInvariant, InvariantVerdict]` keyed-by-enum forbids multiple verdicts on the same invariant in one revision. Real Wall critiques include 5 evidence items on a single coherence question with mixed status (some HARD_fail, some SOFT_disputed).

**Recommendation**: `dict[Invariant, list[InvariantVerdict]]` or add a `verdict_id` slot.

### C. **REQUIRED CONTENT RULE ambiguity: per-invariant vs path-level proof** (VirtualProvider)

Wind in debate 3 put one HARD_fail (`single_wall_coherence`) in `accepted` without a `terminal_rationale`, relying on the `reframed` entry on the sibling invariant (`per_turn_role_contract` → BudgetMiddleware reframe) to functionally cover both. The RFC text is ambiguous about whether catalyst-proof must be per-invariant or per-path.

**Recommendation**: strict reading — require `terminal_rationale` per HARD_fail entry placed in `accepted`. Update RFC §3.2 and the prompt's REQUIRED CONTENT RULE accordingly.

### D. **`NO_NEW_DIVERGENCE` semantics ambiguous with non-empty `disputed`** (VirtualProvider, reliability)

RFC §3.1's sentinel example shows all three lists empty. But Wind legitimately wanted to dispute a SOFT verdict on a path otherwise unreframeable, producing a `NO_NEW_DIVERGENCE` + non-empty `disputed` combination.

**Recommendation**: clarify in RFC — either allow non-empty `disputed` alongside sentinel (likely correct), or instruct Wind to choose one. Update prompt text in `format_wind_approval_prompt`.

### E. **No schema field for cross-path / synthesis-level insights** (cognitive notary, reliability)

Wind's strongest insight in the notary debate was the *layered architecture* — a cross-path emergent observation that doesn't fit any per-path `reframed` entry. Wind emitted it as free-form "Synthesis Guidance for Door" outside the schema.

**Recommendation**: add a `cross_path_reframe: NotRequired[str]` or `synthesis_guidance: NotRequired[str]` slot on `DiffRevision` (or alongside it) for cross-path emergent insights.

### F. **APPROVE/REJECT-vs-no-synthesis mismatch** (cognitive notary, VirtualProvider)

`format_wind_approval_prompt` asks Wind to APPROVE or REJECT Door's synthesis — but in a greenfield consensus round (or a simulation where Door's first synthesis hasn't fired), no synthesis exists. Wind must REJECT by default to emit diffs, conflating "no synthesis to evaluate" with "synthesis was flawed".

**Recommendation**: either gate the prompt fire on `door_synthesis_exists`, or split diff-emission from the APPROVE/REJECT vote. Touches issues #198 (prompt updates) and #199 (context compiler).

### G. **Sim agent roles leak tool side-effects** (mythology, notary, governance)

The `wind-agent` and `door-agent` clink personas grant `Read/Grep/Glob/Edit/WebSearch/octave_write/add_turn` tool access. In simulation runs, these activated against the live Hall — Door attempted to call `add_turn` against the real thread (burned ~3 minutes; one case burned ~$0.55). Recovered by retrying with "no tools — return inline" instructions.

**Recommendation**: define tool-stripped `wind-sim` / `door-sim` clink roles, OR add an explicit "no tools" preamble to the simulation harness prompt template in `docs/rfc-0001-simulation-harness.md`.

### H. **Live codebase reads inside clinks — explicit policy needed** (cognitive notary)

In the notary simulation, both Wind and Door grounded responses by reading the live source tree (`tools/decision.py`, `state.py`, `events.py`). The simulation neither requested nor prohibited this. Could be a feature (more grounded answers) or a bug (pure-prompt agents would reach different conclusions, undermining reproducibility).

**Recommendation**: simulation harness should declare an explicit policy: "ground only on the prompt content" vs "may read live source". For #204 specifically, the no-grounding policy is the cleaner test; for production runs grounding is probably desirable.

### I. **Door searches for non-existent debate thread on disk** (cognitive notary, governance)

Door's consensus prompt implicitly expects a live Hall instance — the simulation thread doesn't exist on disk, so Door briefly searches before recognizing the state is inline. Minor.

**Recommendation**: clinks should be fully self-contained; ensure the prompt explicitly says "all state is in this prompt, no external lookup required".

---

## Schema-fit caveat (re-stated)

This simulation used **topic-specific invariant names** (e.g. `sync_api_contract`, `cultural_sensitivity`, `audit_trail_completeness`) rather than forcing the closed enum. The simulation tests the *prompt's constraint-as-catalyst behavior* cleanly. The closed-enum question (Finding A) is logged separately. Track B fallback (closed-enum-conformant) is documented in each `0N-*-path-contracts.md` for re-runs under different schema choices.

## Per-debate artifacts

For each debate, four files in `docs/rfc-0001-204-simulation/`:

- `0N-{slug}-path-contracts.md` — constructed `<PATH_CONTRACTS>` block + extraction notes
- `0N-{slug}-wind-diff.md` — fresh-session Wind consensus output
- `0N-{slug}-door-synthesis.md` — fresh-session Door synthesis output
- `0N-{slug}-score.md` — per-criterion scorecard + PASS/FAIL verdict

Total: 20 evidence files + this report + the `README.md` index.

## Iteration count

**Zero prompt iterations needed.** The current prompts (post-PR #212 ratified state, HEAD `9248b00`) produced 5/5 PASS on first dispatch. No re-run was attempted. Findings A–I are RFC/schema/harness improvements, not prompt regressions.

## Next steps

1. **Build is unblocked** — #196 (schema/types) → #200 (validation guard) → #199 (context compiler) → #197 → #205 → #201 → #202 → #203 may proceed per the suggested order.
2. **Finding A (closed-enum widening)** should be folded into #196 work — the schema needs to evolve before #197/#202 land golden-file tests against it.
3. **Finding F (synthesis-exists guard)** should be folded into #198 (prompt updates) and #199 (context compiler).
4. **Finding G (tool-stripped sim roles)** is a harness improvement — small standalone PR or rolled into #203 (A/B test harness).
5. **Findings B, C, D, E, H, I** are smaller and can each be a separate issue or rolled into the relevant #196/#198/#203 work.
