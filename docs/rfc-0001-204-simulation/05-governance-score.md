# Debate #5 — Scorecard (Decision Governance Synthesis)

**Source debate**: `debates/2026-04-28-decision-governance-synthesis.oct.md`
**Form**: SYNTHESIS only (186 lines, no raw turns in repo)
**Back-derivation**: PATHS and VERDICTS reconstructed from `.oct.md` §2, §2c, §2d, §2e, §4. RECONSTRUCTION_ONLY banner enforced in path-contracts file.
**Wind clink**: claude-opus-4-6, 49.5s, valid output
**Door clink**: claude-opus-4-6, 130.8s, valid output (synthesis delivered as text; `add_turn` failed due to Wind-first fixed-mode thread initialization — process artefact, not synthesis defect)

---

## Standard scoring criteria (per README §"Methodology" step 7)

### Criterion 1: Wind diff references Wall's verdict entries by invariant key

**PASS**

Wind's three PATH_CONTRACT_DIFF blocks cite Wall verdicts by their exact invariant keys:
- `path_1.accepted: process_proportionality` ← Wall HARD_fail
- `path_1.reframed: token_efficiency` ← Wall HARD_fail
- `path_2.disputed: format_decoupling_legitimacy` ← Wall SOFT_disputed
- `path_3.disputed: ADR_0060_compliance` ← Wall SOFT_disputed
- `path_3.reframed: documentation_drift_risk` ← Wall HARD_fail

All five Wall verdict entries that admit a diff response are addressed. No silent omissions.

### Criterion 2: `reframed` entries are substantively new (not restatements)

**PASS — strongly**

- **`path_1.reframed: token_efficiency`** proposes ADR-INDEX.md (single consolidated Markdown file containing all ADR content inline, ~4000 tokens). This is *not* a restatement of path_1 (which assumed detached files) and *not* a restatement of path_2 (which decouples format from mandate). It is a third storage strategy: strict ADR-0060 compliance with consolidated storage. Substantively new.
- **`path_3.reframed: documentation_drift_risk`** proposes SHADOW workflow with CI-gated archival. This is *not* a restatement of path_3 (which deletes eagerly) and *not* a restatement of §4 PRACTICAL_CAVEAT mitigation (which requires a human-supplied commit reference). The machine gatekeeps deletion via proof-of-enforcement. Substantively new.

### Criterion 3: HARD_fail `accepted` entries have honest `terminal_rationale`

**PASS**

`path_1.accepted: process_proportionality` carries:
> "Uniform ceremony cannot accommodate variable gravity without becoming either wasteful (full ceremony for trivia) or hollow (rubber-stamp Issues that exist only for compliance). The failure mode is intrinsic to the path's assumption of uniformity."

This is honest: it identifies the failure as intrinsic to the path's assumption (uniformity), not as a fixable parameter. It explains why no reframe rescues the path. The reasoning is specific to the path's structure, not boilerplate.

### Criterion 4: Wind doesn't invent fake `disputed` entries when Wall HARD_passed everything

**PASS**

- path_1 had zero SOFT_disputed and zero HARD_pass-with-objections. Wind correctly emitted empty `disputed: []`.
- path_2 had one SOFT_disputed (`format_decoupling_legitimacy`); Wind disputed it with a textual-entailment argument that opens a richer reading. Per consensus-prompt rule, this is legitimate ("you may dispute — but only if disputing opens a richer path"). Not a fake dispute.
- path_3 had one SOFT_disputed (`ADR_0060_compliance`); Wind disputed it with a self-consistency argument under the gravity heuristic. Legitimate per the same rule.

### Criterion 5: Door's citations exist in the contract (`[path_N.accepted: <invariant>]` syntax)

**PASS — exhaustively**

Door cites:
- `[path_1.accepted: process_proportionality]` ✓ (exists in Wind diff)
- `[path_1.reframed: token_efficiency]` ✓ (exists in Wind diff)
- `[path_1.disputed]` empty — noted ✓ (correct sentinel acknowledgement)
- `[path_2.disputed: format_decoupling_legitimacy]` ✓ (exists in Wind diff)
- `[path_2]` divergence_marker NO_NEW_DIVERGENCE acknowledged explicitly ✓
- `[path_3.reframed: documentation_drift_risk]` ✓ (exists in Wind diff)
- `[path_3.disputed: ADR_0060_compliance]` ✓ (exists in Wind diff)
- `[path_3.accepted]` empty — noted ✓ (correct sentinel acknowledgement)

Door's "CITATION COMPLETENESS" table at the bottom of the synthesis is a self-audit that matches Wind's diff exactly. No fabricated entries.

---

## Standard scoring summary

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Wind diff references Wall by invariant key | PASS |
| 2 | `reframed` entries substantively new | PASS (strong — ADR-INDEX.md and SHADOW workflow both novel) |
| 3 | HARD_fail `accepted` has honest `terminal_rationale` | PASS |
| 4 | No fake `disputed` entries | PASS |
| 5 | Door's citations exist in contract | PASS (exhaustive, with self-audit table) |

**Overall verdict: PASS (5/5)** — strongest of the simulation criteria. Constraint-as-catalyst behaviour observed clearly on both HARD_fail invariants that admit reframing (path_1.token_efficiency, path_3.documentation_drift_risk) and honest acceptance on the one that does not (path_1.process_proportionality).

---

## Bonus criterion (specific to this debate)

**Does Door's synthesis arrive at something comparable to the historical "Gravity-Tiered OCTAVE Monolith" three-tier model — OR a substantively-different but equally-coherent third way?**

**Verdict: COMPARABLE-PLUS** — Door independently re-derives the historical 3-tier structure *and* adds a substantively new mechanism (SHADOW workflow) that the historical synthesis did not have.

### Comparison table

| Element | Historical synthesis (debates/...governance-synthesis.oct.md) | Door's fresh synthesis | Verdict |
|---------|--------------------------------------------------------------|------------------------|---------|
| Three tiers | ARCHITECTURAL / CONVENTION / MICRO (§2a) | ARCHITECTURAL / CONVENTION / MICRO | **Identical labels** |
| ARCHITECTURAL trigger | crosses_boundaries ∨ irreversible ∨ security_invariant (§2a) | cross-system consequence ∨ data-ownership ∨ irreversibility (gravity test scoring) | **Equivalent semantics** |
| Classification heuristic | mechanization_test → gravity_test (§2b) | mechanization_test → gravity_test (Door §"Implementation" step 1) | **Identical structure** |
| ADR-0060 stance | JUSTIFIED_EXTENSION_VIA_FORMAT_DECOUPLING (§2d) | "Honoured by scope, not circumvention" — title-scoped textual entailment | **Stronger framing** (Door's title-scope argument is textually tighter than historical's format-decoupling extension claim) |
| OCTAVE monolith storage | 100 nodes ≈ 3500 tokens vs 80000 detached (§2e) | `DECISIONS.oct.md` monolith, ~3500–5000 tokens for 100 decisions | **Equivalent quantification** |
| MICRO mechanization rule | "TIER_MICRO_requires_commit_reference_to_enforcement_code... BEFORE doc is deleted" (§4 mitigation) | SHADOW::PENDING_MECHANIZATION + CI-gated auto-archive | **Substantively new** — Door upgrades the mitigation from human-supplied commit reference to machine-verified proof-of-enforcement |
| Migration path | Four phases: metadata sweep, issue backfill, fractal collapse, archive verify (§3) | Not explicitly addressed (Door focused on steady-state model) | **Historical has migration; Door does not** |

### What Door added that the historical synthesis did not have

1. **SHADOW workflow as a first-class state machine**: the historical §4 caveat said "require commit reference BEFORE doc is deleted" — a human-trust mechanism. Door replaces this with a CI-gated state transition (`SHADOW::PENDING_MECHANIZATION` → `SHADOW::MECHANIZED`) where the machine performs the archival. This is a strict improvement: the historical version still requires a human to write "yes I added the linter rule" honestly; Door's version requires the CI to actually find and run the rule.

2. **ADR-INDEX.md as a recovered alternative**: Door explicitly notes (in path_1.reframed citation) that strict ADR-0060 with storage consolidation is a *valid* third option that the historical synthesis dismissed without considering. Door then explains why it is not adopted (process_proportionality remains terminal), but absorbs the insight (monolith storage is structurally superior). This level of explicit "considered and superseded" reasoning is absent in the historical synthesis.

### What the historical synthesis had that Door did not produce

1. **Four-phase migration path** (§3 of `.oct.md`): the historical synthesis includes a concrete migration plan for existing decision records. Door produced steady-state architecture but not the migration sequence. This is consistent with the simulation framing (Door was asked to synthesise, not to plan rollout), but it is a real gap relative to the historical artefact.

2. **Self-application clause** (§6 of `.oct.md`): the historical synthesis declares that adopting the model is itself an ARCHITECTURAL-tier decision per its own gravity test, with a token and ISSUE_REF. Door does not produce this self-applying meta-decision.

### Overall bonus verdict

**COMPARABLE-PLUS** with one significant gap (migration plan). The fresh Door synthesis independently re-derived the 3-tier model with high structural fidelity to the historical version, sharpened the ADR-0060 stance with a textual-entailment argument that is *stronger* than the historical "format decoupling" framing, and upgraded the MICRO-tier safety mechanism from human-trust to machine-verification. This is meaningful evidence that the Wind/Wall/Door prompt machinery can re-derive a known-good architectural decision from back-derived inputs — and that the constraint-as-catalyst behaviour can even *exceed* the historical synthesis on specific points.

---

## Notes on the back-derivation limitation

**Was the back-derivation a meaningful limitation?**

**Partially — but less than expected.**

### Where back-derivation helped (or was neutral)

- The `.oct.md` synthesis is rich enough in §2c test cases, §2d ADR_0060_STANCE, §2e token quantification, and §4 PRACTICAL_CAVEAT that constructing plausible Wall verdicts was tractable. The Wall verdicts in `05-governance-path-contracts.md` are derivable with minimal inference — most rationales quote `.oct.md` sections directly.
- Wind clearly engaged the back-derived verdicts *as* verdicts; there is no sign that Wind treated them as suspicious or non-canonical. The Wind diff cites specific Wall rationales (e.g., "Wall's 20x penalty (80k vs 3.5k tokens)") that came from the back-derivation, not from a primary turn.

### Where back-derivation likely limited the simulation

- **No genuine Wind path_1 framing existed** — the obvious "strict ADR-0060 uniform" position is plausible but was almost certainly never *seriously* proposed in the original debate because the participants started from the gravity-tiered intuition. The simulated Wind therefore engages with a straw-ish Path 1. The fact that Wind still produced a *substantively new* ADR-INDEX.md reframe shows constraint-as-catalyst worked anyway.
- **path_2 was effectively the historical answer** — Wall HARD_passed everything because path_2 mirrors the historical synthesis. This produces a "thin" diff (NO_NEW_DIVERGENCE) which is structurally correct but reveals that path_2 was not a real divergent option. A genuinely independent simulation might have had path_2 framed differently to force more friction.
- **Door's re-derivation may be partly memory-leak** — claude-opus-4-6's training corpus may include the historical synthesis or similar gravity-tiered governance discussions, biasing Door toward the 3-tier model independent of the simulation inputs. The strength of the structural match (identical tier labels, identical heuristic structure) is suspicious in this respect. **Caveat**: even if memory leak contributed, the SHADOW workflow upgrade and the title-scoped textual-entailment argument are clearly Door's own contributions; they don't appear in the historical synthesis at all.

### Conclusion on back-derivation

The simulation is *informative* but should be treated as a weaker signal than debates 2-4 (which had full Wind/Wall/Door transcripts). The bonus verdict (COMPARABLE-PLUS) is robust against the back-derivation limitation because the *new* contributions (SHADOW, title-scope argument, ADR-INDEX.md consideration) are inarguably outside the historical artefact.

---

## Anomalies and process notes

1. **Door `add_turn` failure**: Door clink reported that the debate-hall thread expected Wind-first in fixed mode and refused the synthesis turn. This is a *process-layer* artefact — the simulation does not run inside a real debate-hall thread; clink invoked the Door agent with the system prompt and got a clean text response. The synthesis content is fully captured; only the in-thread persistence step failed. **#204 finding**: when running consensus-phase synthesis simulations against fresh threads, the orchestrator must either (a) use mediated mode, or (b) pre-populate the thread with synthetic Wind/Wall turns to satisfy fixed-mode role-rotation invariants. Documented for the consolidated report.

2. **Closed-enum schema fit**: the four real concerns in this debate (`ADR_0060_compliance`, `token_efficiency`, `process_proportionality`, `format_decoupling_legitimacy`, `documentation_drift_risk`, `mechanization_efficiency`) collapse poorly onto `{halting, single_wall_coherence, re_approval, per_turn_role_contract}`. This is the third independent debate (mythology, reliability, governance) where the closed enum is flow-shaped while the real verdicts are topic-shaped. Carry forward to consolidated #204 finding.

3. **PROD::I3 (FINITE_DIALECTIC_CLOSURE) honoured**: both Wind and Door clinks were one-shot — no iteration. Each prompt encoded the full state needed for a complete response. Per `path-contracts.md` §"Pass-criteria probe", this is the constraint that disciplined the prompt design.

4. **PROD::I4 (VERIFIABLE_EVENT_LEDGER) honoured**: the RECONSTRUCTION_ONLY banner in `05-governance-path-contracts.md` explicitly labels the back-derived material as simulation input. None of the four artefacts in this directory pretends to be debate-transcript truth.
