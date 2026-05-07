# RFC-0001 Issue #204 — Pre-build Simulation Results

**Status**: In progress (tracer-bullet phase)
**Started**: 2026-05-07
**Gate**: ≥4/5 debates produce diffs where `reframed`/`accepted+terminal_rationale` is substantively new AND meaningfully engages a Wall verdict; Door's citations exist in the contract.

## Methodology

For each historical debate:

1. **Extract** Wind paths and Wall verdicts from the transcript. Map topic-specific Wall constraints onto the closed-enum `HardInvariant` (halting, single_wall_coherence, re_approval, per_turn_role_contract) by **closest analogy**. Where no clean mapping exists, use `single_wall_coherence` (the catch-all coherence-of-design invariant).
2. **Construct** `<PATH_CONTRACTS>` block per RFC §3.1 schema.
3. **Run Wind consensus** via fresh `mcp__pal__clink` (Claude, Codex, or Gemini — varied per debate to avoid model bias) with: system prompt + historical state up through Door's first synthesis + new `<PATH_CONTRACTS>` block + new Wind-consensus prompt text from `src/debate_hall_mcp/prompts/__init__.py::format_wind_approval_prompt` (HEAD `9248b00` post-#213).
4. **Capture Wind diff output**.
5. **Run Door synthesis** with Wind's diff appended.
6. **Capture Door synthesis output**.
7. **Score**:
   - Pass criteria per debate (#204):
     - Wind diff references Wall's verdict entries by invariant key
     - `reframed` entries are substantively new (not restatements)
     - HARD_fail `accepted` entries have honest `terminal_rationale`
     - Wind doesn't invent fake `disputed` entries when Wall HARD_passed everything
     - Door's citations exist in the contract

## Schema-fit caveat

Historical debates aren't structured around the RFC's closed-enum debate-flow invariants (HALTING / SINGLE_WALL_COHERENCE / RE_APPROVAL / PER_TURN_ROLE_CONTRACT). Wall's actual critiques in the corpus are topic-specific (e.g., "spec defines grammar not vocabulary", "single dev → more debt"). The mapping is a **judgment call**; I've documented the chosen mapping in each debate's `path-contracts.md` so the simulation can be re-run with different mappings if the gate fails.

This itself is a finding worth surfacing to the RFC: if topic-specific Wall constraints don't fit the closed enum cleanly, the schema may need either an open `topic_invariant` slot or a richer mapping convention.

## Corpus

| # | Debate | Form | Status |
|---|--------|------|--------|
| 1 | `2026-02-22-mythology-in-octave-assessment.oct.md` | COMPILED_DECISION (24 lines) | tracer bullet — input drafted |
| 2 | `2026-01-30-rundebate-reliability-analysis.oct.md` | DEBATE_TRANSCRIPT (168 lines) | pending |
| 3 | `2026-01-30-virtualprovider-vs-timebudget.oct.md` | DEBATE_TRANSCRIPT (142 lines) | pending |
| 4 | `2026-02-03-cognitive-notary-architecture.oct.md` | DEBATE_TRANSCRIPT (139 lines) | pending |
| 5 | `2026-04-28-decision-governance-synthesis.oct.md` | SYNTHESIS (186 lines) | pending |

## Phase status

- [x] Phase A1: methodology + tracer-bullet input (mythology PATH_CONTRACTS)
- [ ] Phase A2: user calibration check on PATH_CONTRACTS format
- [ ] Phase B: extract + draft PATH_CONTRACTS for remaining 4 debates
- [ ] Phase C: run 5×Wind + 5×Door simulations
- [ ] Phase D: score + iterate prompts if needed
- [ ] Phase E: post report on #204

## Next decision point

After tracer bullet (mythology) PATH_CONTRACTS draft, **stop for user calibration** before running LLM simulations. Reasons:

1. Schema-fit mapping is judgment-heavy and the user may want a different convention.
2. The simulation runs cost ~10 LLM calls (~30-60 min wall time); better to validate input format first.
3. If the closed-enum mapping is too forced, the simulation tests something different than the issue intends — surfacing this *before* burning the runs is cheaper.
