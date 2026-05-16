# RFC-0001 Issue #204 — Pre-build Simulation Results

**Status**: In progress (Phase B+C+D dispatched in parallel)
**Started**: 2026-05-07
**Gate**: ≥4/5 debates produce diffs where `reframed`/`accepted+terminal_rationale` is substantively new AND meaningfully engages a Wall verdict; Door's citations exist in the contract.

## Methodology

For each historical debate, an independent agent runs the simulation end-to-end:

1. **Extract** Wind paths and Wall verdicts from the transcript. Use **topic-specific invariant names** (e.g. `sync_api_contract`, `cultural_sensitivity`, `audit_trail_completeness`) rather than forcing onto the closed enum. This makes the simulation a more honest test of constraint-as-catalyst behavior; the closed-enum question is logged separately as a schema finding.
2. **Construct** `<PATH_CONTRACTS>` block per RFC §3.1 shape.
3. **Run Wind consensus** via fresh `mcp__pal__clink` (cli=claude, role=wind-agent) with: Wind/PATHOS system prompt + historical state up through Wall's verdict (excluding the historical Door synthesis and final approvals) + new `<PATH_CONTRACTS>` block + new Wind-consensus prompt text verbatim from `src/debate_hall_mcp/prompts/__init__.py::format_wind_approval_prompt`.
4. **Capture Wind diff output**.
5. **Run Door synthesis** via fresh `mcp__pal__clink` (cli=claude, role=door-agent) with same DEBATE_STATE + Wind's diff + Door consensus prompt text verbatim from `format_door_consensus_prompt`.
6. **Capture Door synthesis output**.
7. **Score** against:
   - Wind diff references Wall's verdict entries by invariant key
   - `reframed` entries are substantively new (not restatements of the original path)
   - HARD_fail `accepted` entries have honest `terminal_rationale`
   - Wind doesn't invent fake `disputed` entries when Wall HARD_passed everything
   - Door's citations exist in the contract (`[path_N.accepted: <invariant>]` syntax)

## Schema-fit caveat (logged finding)

Historical debates aren't structured around the RFC's closed-enum debate-flow invariants (HALTING / SINGLE_WALL_COHERENCE / RE_APPROVAL / PER_TURN_ROLE_CONTRACT). Wall's actual critiques in the corpus are topic-specific. We chose **topic-specific invariant names** so the simulation tests the prompt's constraint-as-catalyst behavior cleanly rather than testing a forced mapping.

**Finding for RFC-0001**: the closed enum is too narrow for real-world Wall verdicts. The schema needs either an open `topic_invariant: str` slot, or `HardInvariant` should be re-defined as an *enum of verdict categories* (e.g., COHERENCE, COST, RISK, IDENTITY) with topic-specific evidence in `rationale`.

**Secondary finding**: `VerdictRevision.value: dict[HardInvariant, InvariantVerdict]` forbids multiple verdicts on the same invariant in one revision. Reality requires `dict[Invariant, list[InvariantVerdict]]` or a `verdict_id` slot.

## Corpus

| # | Debate | Form | Schema fit |
|---|--------|------|-----------|
| 1 | `2026-02-22-mythology-in-octave-assessment.oct.md` | COMPILED_DECISION (24 lines) | single path; back-derived |
| 2 | `2026-01-30-rundebate-reliability-analysis.oct.md` | DEBATE_TRANSCRIPT (168 lines) | 3 Wind paths + 4 Wall HARD constraints — strong fit |
| 3 | `2026-01-30-virtualprovider-vs-timebudget.oct.md` | DEBATE_TRANSCRIPT (142 lines) | 3 Wind paths + 3 Wall HARD constraints — strong fit |
| 4 | `2026-02-03-cognitive-notary-architecture.oct.md` | DEBATE_RECORD (139 lines) | 3 proposals + GO/CONDITIONAL_GO/NO_GO verdicts |
| 5 | `2026-04-28-decision-governance-synthesis.oct.md` | SYNTHESIS only (186 lines) | back-derived from §2 model |

## Per-debate artifacts

Each debate produces 4 files in this directory:
- `0N-{slug}-path-contracts.md` — input: the constructed `<PATH_CONTRACTS>` block + extraction notes
- `0N-{slug}-wind-diff.md` — output: Wind's fresh consensus diff (clink response)
- `0N-{slug}-door-synthesis.md` — output: Door's fresh synthesis (clink response)
- `0N-{slug}-score.md` — per-criterion scorecard + PASS/FAIL verdict

## Phase status

- [x] Phase A1: methodology + tracer-bullet draft (mythology)
- [x] Phase B+C+D dispatched: 5 parallel oa-router agents, each handling one debate end-to-end (PATH_CONTRACTS → Wind clink → Door clink → score)
- [ ] Phase E: aggregate verdicts, write consolidated report, commit artifacts, post on #204
