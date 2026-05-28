# Debate #1 — Mythology in OCTAVE: scoring against #204 gate criteria

**Inputs scored**:
- Wind diff: `docs/rfc-0001-204-simulation/01-mythology-wind-diff.md`
- Door synthesis: `docs/rfc-0001-204-simulation/01-mythology-door-synthesis.md`

## Scorecard

| Criterion | Pass/Fail | Quote |
|---|---|---|
| Wind diff references Wall's verdict entries by invariant key | PASS | All four invariants in Wind's diff (`single_dev_debt`, `audience_positioning`, `spec_grammar_coherence`, `cultural_sensitivity`) match invariant keys present in Wall's verdict_history. Example: Wind's `reframed` entry uses `"invariant": "spec_grammar_coherence"` which is Wall's HARD_fail key verbatim. |
| `reframed` entries are substantively new (not restatements) | PASS | Both reframes invert the original proposal rather than restating it. `spec_grammar_coherence` reframe: "Wall's grammar-not-vocabulary distinction reveals that mythological compression IS grammar, not vocabulary. RAGNAROK::SYSTEM_COLLAPSE is not a dictionary entry — the :: operator IS the grammar… No catalogue needed." This is a genuine inversion of Wind's original "10-tradition guide with examples per tradition" — the catalogue is eliminated and replaced with a grammar-level observation. `cultural_sensitivity` reframe: "pre-flattened mappings DEGRADE mythological compression… mythology works best when the author brings their own cultural fluency — OCTAVE should affirm 'bring your mythology' as a feature, not provide a cheat sheet." This converts the failure mode (reductive mappings) into a design principle (cultural fluency as compression asset). |
| HARD_fail `accepted` entries have honest `terminal_rationale` | N/A (vacuously PASS) | Wind did not place any HARD_fail invariants into `accepted` — both HARD_fails (`spec_grammar_coherence`, `cultural_sensitivity`) went into `reframed` instead. The only `accepted` entry is `single_dev_debt` which Wall scored SOFT_disputed, so `terminal_rationale` is not required. The required-content rule per RFC §3.2 is satisfied because every HARD_fail appears in `reframed` with `new_possibility`. |
| Wind doesn't invent fake `disputed` entries when Wall HARD_passed everything | PASS | Wall did not HARD_pass everything — Wall produced two HARD_fails, one HARD_pass, and two SOFT_disputed. Wind's single `disputed` entry targets `audience_positioning`, which Wall genuinely scored SOFT_disputed: "Audience perception is real but disputable — it depends on framing." Wind's dispute is on a real SOFT entry, not fabricated. |
| Door's citations exist in the contract (uses `[path_N.accepted: <invariant>]` syntax) | PASS | Door's synthesis contains four citations in the required syntax: `[path_1.reframed: spec_grammar_coherence]`, `[path_1.reframed: cultural_sensitivity]`, `[path_1.accepted: single_dev_debt]`, `[path_1.disputed: audience_positioning]`. All four invariants exist in Wind's PATH_CONTRACT_DIFF in the cited categories. No fabricated citations. |

## Overall verdict

**PASS** on all five listed criteria.

## Additional observations (informational, not gate criteria)

1. **Constraint-as-catalyst evidence is strong.** Wind's opening line ("Wall's two HARD_fails don't narrow the path — they sharpen it. The original proposal tried to *document* mythology. The constraint reveals we should *liberate* it.") is exactly the framing the RFC §5.3 prompt asks for. The reframes are not retreats; they are genuine inversions.

2. **Convergence with historical Door synthesis.** Both the historical Door (Mythological Compression Principle) and the simulated Door reach the same end-state: permission, not formalization; one paragraph in grammar docs; "Use mythology freely. Models already understand." This convergence is evidence that the contract-thickened flow does not destroy the original insight — it merely makes the provenance explicit.

3. **The simulated Door's synthesis is *stronger* than the historical one** in that it makes the cultural_sensitivity insight load-bearing ("bring your mythology" as a feature, not a workaround) rather than a side note. This suggests Wind's PATH_CONTRACT_DIFF *did* deliver new information that improved the synthesis — direct evidence for the RFC's claim about Self-Refine-style gains.

4. **Door's first-call anomaly is a real finding.** The `door-agent` clink role has Edit/Read/Grep/Glob/WebSearch tool grants and interpreted the simulation prompt as a live debate, attempting to call `add_turn` against the real thread (16 turns, USD 0.55, no synthesis text returned). The corrective continuation with "do NOT use tools" produced the synthesis cleanly. **#204 finding**: the simulation harness, when run through `pal/clink`, needs either (a) explicit "no tools" instruction in the prompt, or (b) a clink role definition with empty tool grants for simulation use.

5. **Schema-fit finding from path-contracts file holds.** The Track A topic-specific invariant names (`spec_grammar_coherence`, `cultural_sensitivity`, `single_dev_debt`, `audience_positioning`, `llm_zero_shot_premise`) were accepted by Wind and Door without complaint — the agents did not insist on the closed enum. This suggests the prompt-level RFC §3.1 closed-enum requirement may be over-constrained for *real* debates; for the flow-meta-debate that birthed RFC-0001 the enum makes sense, but for topic debates it forces information-loss. Recommend raising as a follow-up to #204.
