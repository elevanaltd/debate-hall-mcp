# Debate #3 — Simulation score

**Topic**: For debate-hall-mcp: Should we implement VirtualProvider or
time-budgeting as NEXT priority?
**Source**: `debates/2026-01-30-virtualprovider-vs-timebudget.oct.md`
**Artifacts scored**:
- `03-virtualprovider-path-contracts.md`
- `03-virtualprovider-wind-diff.md` (clink session `2dcbb5a4`)
- `03-virtualprovider-door-synthesis.md` (clink session `ef6c4fb1`)

## Criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| C1 | **PATH_CONTRACT_FRAME** — three paths defined with `assumed_problem`, `success_criterion`, `accepted_failure_mode`, `hard_invariants_touched` from closed enum | PASS | `path-contracts.md` §"Folded enum-compliant" block: three `<path>` elements with all four required fields populated; `hard_invariants_touched` uses only `per_turn_role_contract`, `single_wall_coherence`, `halting` (all from the closed enum) |
| C2 | **PATH_CONTRACT_VERDICT** — Wall's verdicts include at least one HARD_fail with cited rationale | PASS | `path_3` has TWO HARD_fail verdicts: `per_turn_role_contract` (cites E1 `providers/__init__.py:59-63`, E2 `cli.py:144`, E3 `openrouter.py:131`) and `single_wall_coherence` (cites E4 `orchestrator.py:249` + Wall's FANTASY_DETECTION) |
| C3 | **Wind clink starts with REJECT** (no Door synthesis available pre-synthesis) | PASS | Wind clink output begins literally: `"REJECT\n\nNo Door synthesis exists yet to approve."` |
| C4 | **Wind emits one PATH_CONTRACT_DIFF per path** as fenced JSON with the literal heading format | PASS | Three `### PATH_CONTRACT_DIFF (path_N)` headings present (`path_1`, `path_2`, `path_3`), each followed by valid JSON fence |
| C5 | **HARD_fail catalyst rule** — every HARD_fail invariant on a path appears in either `accepted` (with `terminal_rationale`) or `reframed` (with `new_possibility`) | PARTIAL | path_3 has 2 HARD_fail verdicts. `per_turn_role_contract`: appears in `accepted` WITH `terminal_rationale` ("The protocol boundary is load-bearing…") AND in `reframed` WITH `new_possibility` ("BudgetMiddleware wrapping asyncio.wait_for…") — fully compliant. `single_wall_coherence`: appears ONLY in `accepted` WITHOUT a `terminal_rationale` field. **STRICT READING: non-compliant** — REQUIRED CONTENT RULE says "in either `accepted` (with `terminal_rationale`) or `reframed`". **LENIENT READING: compliant** — the sibling reframe on `per_turn_role_contract` substantively addresses the architectural-ownership concern that `single_wall_coherence` flagged |
| C6 | **NO_NEW_DIVERGENCE sentinel** legitimacy — only used when path has no HARD_fail | PASS | Sentinel used on path_1 (verdicts: HARD_pass + SOFT_disputed) and path_2 (verdicts: HARD_pass + HARD_pass). Never used on path_3 (HARD_fail present). Compliant with §3.1 |
| C7 | **Wind disputes SOFT_disputed productively** (opens richer path, not argumentative) | PASS | path_1 dispute reframes `single_wall_coherence` as test-controllability ≠ test-realism (orthogonal goals → two-layer testing). path_3 dispute on `halting` argues the constraint is preserved while creative seed survives. Both substantive, not defensive |
| C8 | **Door cites EVERY non-empty diff category** using inline `[path_N.category: invariant]` form | PASS | Door cites: `[path_1.disputed: single_wall_coherence]`, `[path_3.accepted: per_turn_role_contract]`, `[path_3.accepted: single_wall_coherence]`, `[path_3.disputed: halting]`, `[path_3.reframed: per_turn_role_contract]` — all five non-empty entries enumerated |
| C9 | **Door acknowledges NO_NEW_DIVERGENCE explicitly** rather than fabricating citations | PASS | Verbatim: *"Path 2 had no new divergence; original frame stands"* and *"Path 1 had no new divergence; original frame stands"* |
| C10 | **Door's synthesis is actionable** with numbered concrete steps | PASS | Three-step IMPLEMENTATION block with line counts, gates, and backlog deferral; matches real-debate IMPLEMENTATION_PRIORITY structure |
| C11 | **Signal-fidelity check** — simulated synthesis converges to or is comparable with the historical T3 Door / SYNTHESIS section | PASS | Real synthesis: *"Budgeting via VirtualProvider"* with sequence `1::Injectable_Factory → 2::VirtualProvider → 3::Budget_Compliance_Tests` (transcript lines 114-131). Simulated synthesis: *"Path 2 (injectable factory) → Path 1 (VirtualProvider)"* with BudgetMiddleware backlog. Same ordering, same architectural conclusion, framing of VirtualProvider purpose slightly different (orchestration-correctness tool vs Budget Compliance Simulator) — both honor the "no protocol change" insight |
| C12 | **Prompts cited verbatim** from `src/debate_hall_mcp/prompts/__init__.py` (no paraphrase) | PASS | Wind prompt: `format_wind_approval_prompt` body (lines 673-759) reproduced byte-for-byte in clink call. Door prompt: `format_door_consensus_prompt` body (lines 617-657) reproduced byte-for-byte with `rejector="Wind"` substitution |
| C13 | **Schema-fit anomaly** — closed enum `[halting, single_wall_coherence, re_approval, per_turn_role_contract]` accommodates the topic | PARTIAL | The debate's actual stakes (protocol stability, timeout ownership, resume semantics) had to be **folded** onto the enum. `protocol_signature_stability` → `per_turn_role_contract`; `timeout_ownership` and `resume_semantics` → `single_wall_coherence`. The fold loses nuance and replicates the schema-fit finding raised in `01-mythology-path-contracts.md`. Audit-truthful topic-oriented block is provided alongside |

## Anomalies surfaced

A1. **Sibling-citation ambiguity (C5)**. When two HARD_fail verdicts on the
   same path are "addressed" by a single `reframed` entry that
   substantively covers both, RFC-0001's REQUIRED CONTENT RULE is unclear
   whether the second HARD_fail still needs its own `accepted` entry
   with `terminal_rationale`. Wind here chose to put the second HARD_fail
   in `accepted` *without* `terminal_rationale`. The validator
   implementation in #204 must pick a side. **Recommendation**: require
   per-invariant catalyst proof (strict reading), even when one reframe
   would functionally subsume both — the schema field is per-invariant,
   so the rule should match.

A2. **Closed-enum fit for non-debate-flow topics (C13)**. The same
   topic-oriented-vocabulary loss flagged in debate #1 recurs here.
   `protocol_signature_stability`, `timeout_ownership`, and
   `resume_semantics` are first-class invariants of THIS debate but get
   collapsed onto two enum slots. **Recommendation**: either widen the
   closed enum, or formalize a "fold map" the simulator emits alongside
   the contract so the audit trail preserves topic-level meaning.

A3. **Path 1 SOFT dispute reframing (informational, not a finding)**.
   Wind's `single_wall_coherence` dispute on path_1 introduces a new
   conceptual distinction (test-controllability vs test-realism) that
   does NOT structurally change the path, yet Wind sets
   `divergence_marker: NO_NEW_DIVERGENCE` while also emitting a
   non-empty `disputed` list. The §3.1 sentinel example shows all three
   lists empty in the sentinel case. **Recommendation**: clarify whether
   the sentinel is "all three lists empty" or "no HARD_fail handling
   required" — these differ when SOFT disputes are productive. Lenient
   reading accepts the current Wind output; strict reading rejects it.

A4. **Prompt is single-shot (informational)**. The Wind consensus prompt
   asks Wind to APPROVE/REJECT *and* emit diffs in one turn. In a
   greenfield round (no Door synthesis exists yet), Wind must REJECT by
   default because there is nothing to approve, but that REJECT signal
   is semantically different from "rejected after reading a flawed
   synthesis". The orchestrator may want to gate when this prompt fires
   (only after a Door synthesis exists). Out of scope for #204; worth
   flagging.

## Overall verdict

**PASS** — with two PARTIAL items (C5 sibling-citation, C13 schema-fit)
flagged as RFC-0001 findings rather than simulation failures.

The simulation harness successfully:
1. Drove a faithful two-hop Wind→Door consensus refinement using verbatim
   prompts from `prompts/__init__.py`.
2. Produced contract artifacts conformant with RFC-0001 §3.1 structure.
3. Exercised the HARD_fail catalyst rule under realistic ambiguity
   (sibling-invariant coverage).
4. Converged to the same architectural conclusion as the historical
   debate transcript (factory→VirtualProvider, BudgetMiddleware
   deferred), validating signal preservation.

The TWO partial items are not blocking — they surface design questions
the #204 validator implementation must answer before the harness can be
used to gate real debates.
