# Debate #5 — Decision Governance Synthesis

**Source**: `debates/2026-04-28-decision-governance-synthesis.oct.md`
**Form**: SYNTHESIS only (186 lines) — post-debate synthesis; raw Wind/Wall turns live in external thread `2026-04-28-decision-record-governance-for-01kqa2vb` and are NOT in this repo.
**Topic**: Should every ratified decision in elevana-studio originate from a GitHub Issue per HestAI-MCP ADR-0060, or do we need a tiered model that distinguishes heavyweight architectural decisions from lightweight documented choices?

---

## RECONSTRUCTION_ONLY banner

Per PROD::I4 (VERIFIABLE_EVENT_LEDGER) and PROD::I2 (UNIVERSAL_OCTAVE_BINDING), the
path contracts below are **back-derived** from the SYNTHESIS document, not extracted
from a primary debate transcript. They are simulation inputs only and MUST NOT be
treated as ledger truth. Source line numbers in the `.oct.md` are cited inline for
auditability.

### Back-derivation methodology

For each of the three logically possible governance approaches to the question, I
read the synthesis `§2`, `§2c`, `§2d`, `§2e`, and `§4` and asked: "What would Wall
have evidenced HARD_fail / HARD_pass / SOFT_disputed for this approach, given the
synthesis took the position it did?" The §2c test cases (CASE_1..CASE_5) are
treated as Wall's evidence-based verdicts on Wind-proposed approaches. The §2e
token-efficiency evidence is treated as Wall's quantitative HARD_fail rationale
against the strict approach. The §4 PRACTICAL_CAVEAT is treated as Wall's
HARD_fail rationale against the heretical approach.

This is consistent with the methodology used in `01-mythology-path-contracts.md`
(Track A): use topic-specific invariant names so the simulation tests
constraint-as-catalyst behaviour cleanly rather than testing a forced mapping onto
the closed enum `{halting, single_wall_coherence, re_approval, per_turn_role_contract}`.

### Schema-fit finding (carried forward to #204)

The historical debate's actual concerns are governance-design coherence
(ADR_0060_compliance), agent-load economics (token_efficiency), and operational
risk (documentation_drift_risk, format_decoupling_legitimacy). None of these map
naturally onto the closed flow-shaped enum. This is the *same* finding the
mythology and reliability debates surfaced: the closed enum is flow-shaped, not
topic-shaped. See `README.md` §"Schema-fit caveat" for the consolidated
recommendation.

---

## Constructed `<PATH_CONTRACTS>` block (Track A — topic-specific invariants)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev index="0" written_by="Wind">
        <path_label>Obvious</path_label>
        <assumed_problem>elevana-studio's decision record is drifting — some decisions are documented, some are not, and there's no agreed standard. HestAI-MCP ADR-0060 already mandates Issue↔ADR alignment with matching numbers, so the fix is to apply it uniformly: every ratified decision gets a GitHub Issue + a Markdown ADR file with matching number.</assumed_problem>
        <success_criterion>100% of ratified decisions in elevana-studio have a GitHub Issue and a linked Markdown ADR file with matching numbers; ADR-0060 compliance is mechanically verifiable.</success_criterion>
        <accepted_failure_mode>Process overhead — even trivial documented choices (e.g. kebab-case file names, cron job rename) require an Issue and an ADR file; agent-context bloat as the ADR set grows.</accepted_failure_mode>
        <hard_invariants_touched>[ADR_0060_compliance, token_efficiency, process_proportionality]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="ADR_0060_compliance" status="HARD_pass" rationale="Per §2d MANDATE_HONORED, strict Issue+ADR-file-per-decision is the literal reading of ADR-0060; this path trivially satisfies the standard's text." />
        <verdict invariant="token_efficiency" status="HARD_fail" rationale="Per §2e TOKEN_EFFICIENCY_EVIDENCE: 100 detached Markdown files ≈ 80000 tokens of file-traversal overhead vs ≈ 3500 tokens for the OCTAVE monolith — a 20x penalty per agent wholesale load. For a project where agents must load decisions to act correctly, this is a structural cost, not a soft preference." />
        <verdict invariant="process_proportionality" status="HARD_fail" rationale="Per §2c CASE_1 (cron_alter_job_not_UPDATE) and CASE_4 (kebab_case_file_names): treating these as full Issue+ADR decisions is process-overkill — Case 4 is mechanizable via ESLint/repo config, Case 1 is a CONVENTION-tier inline note. Strict uniformity violates the principle that ceremony should match consequence." />
      </rev>
    </verdict_history>
    <diff_history>
      <!-- empty: this is what the simulation generates -->
    </diff_history>
  </path>

  <path id="path_2">
    <frame_history>
      <rev index="0" written_by="Wind">
        <path_label>Adjacent</path_label>
        <assumed_problem>The real signal isn't 'documented vs not' — it's that decisions have different gravity. Architectural decisions need the full Issue+ADR ceremony for auditable provenance; convention decisions need a documented choice but not an Issue; mechanizable rules don't need documentation at all if the tooling enforces them. Classify by gravity, apply the ceremony that matches.</assumed_problem>
        <success_criterion>Every ratified decision is classified into one of three tiers (ARCHITECTURAL / CONVENTION / MICRO); only TIER::ARCHITECTURAL items get GitHub Issues; the classification heuristic runs in under 30 seconds; ADR-0060's substantive mandate ('architectural decisions link to Issues') is preserved while its format implication ('Markdown file') is decoupled.</success_criterion>
        <accepted_failure_mode>ADR-0060 purists may dispute that 'OCTAVE node with ISSUE_REF field inside DECISIONS.oct.md' is a legitimate ADR; the format-decoupling claim has to be defended on principle, not just convenience.</accepted_failure_mode>
        <hard_invariants_touched>[ADR_0060_compliance, token_efficiency, format_decoupling_legitimacy, process_proportionality]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="ADR_0060_compliance" status="HARD_pass" rationale="Per §2d JUSTIFIED_EXTENSION_VIA_FORMAT_DECOUPLING: the mandate 'every architectural decision links to an Issue with matching number' is honoured; only the implementation ('Markdown file') is extended to 'OCTAVE node'. The §2c test cases CASE_2, CASE_3, CASE_5 all produce TIER_ARCHITECTURAL with Issues — the standard's substantive requirement is met." />
        <verdict invariant="token_efficiency" status="HARD_pass" rationale="Per §2e: monolith footprint ≈ 3500 tokens vs detached ≈ 80000 — the tiered model preserves the 20x efficiency for agent wholesale load while still allowing per-Issue audit via ISSUE_REF traversal when needed." />
        <verdict invariant="process_proportionality" status="HARD_pass" rationale="Per §2c: CASE_1 → CONVENTION inline; CASE_4 → MICRO encode-and-delete; CASE_2/3/5 → ARCHITECTURAL Issue+ADR. Ceremony tracks consequence." />
        <verdict invariant="format_decoupling_legitimacy" status="SOFT_disputed" rationale="Per §2d OUT_OF_SCOPE: the claim that Conventions and Micros 'do not meet the architectural bar that triggers the standard' is a defensible reading but not a strict textual one — ADR-0060 as written says 'every ADR must have a linked Issue' and is silent on whether non-architectural decisions are 'ADRs'. A purist could argue this is reinterpretation, not extension. Tradeable: the case-set §2c is strong enough that the reinterpretation is reasonable, but it is a reinterpretation." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_3">
    <frame_history>
      <rev index="0" written_by="Wind">
        <path_label>Heretical</path_label>
        <assumed_problem>Documentation is the wrong medium for rules that machines can enforce. If a decision can be expressed as a linter rule, CI check, DB schema constraint, or repo config, then writing it down in prose is doubly costly — the prose can drift from the enforcement, and the enforcement is the actual source of truth anyway. Inverted approach: encode everything mechanizable, delete the documentation entirely for mechanizable rules.</assumed_problem>
        <success_criterion>Every mechanizable rule (file naming, formatting, structural constraints, type checks, schema invariants) is encoded in tooling (linters, CI, DB schemas) and has zero documentation; ADR-0060 is rendered partially-obsolete because mechanized rules don't have 'decisions' in the human-record sense — they have enforcement code.</success_criterion>
        <accepted_failure_mode>Rules that ought to be mechanized but aren't yet become invisible — the rule is deleted from docs because 'it's mechanizable' but the linter is never written, so the choice is now undocumented AND undetected.</accepted_failure_mode>
        <hard_invariants_touched>[mechanization_efficiency, documentation_drift_risk, ADR_0060_compliance]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="mechanization_efficiency" status="HARD_pass" rationale="Per §2c CASE_4 (kebab_case_file_names) and §2a TIER_MICRO: when CI/linter/DB schema CAN enforce, encoding in tooling and deleting docs IS the most efficient form — the §2b classification heuristic's first step is the mechanization test, validating this insight as correct in scope." />
        <verdict invariant="documentation_drift_risk" status="HARD_fail" rationale="Per §4 PRACTICAL_CAVEAT verbatim: 'TIER::MICRO requires real tooling discipline. If the linter rule is not actually written, the choice becomes undocumented + undetected drift.' Delete-doc-first risks orphaning the rule. The mitigation (§4) requires a commit reference to enforcement code BEFORE the doc is deleted — which means the heretical 'delete documentation entirely' framing is incomplete: enforcement must precede deletion." />
        <verdict invariant="ADR_0060_compliance" status="SOFT_disputed" rationale="Mechanized rules sit in §2a TIER_MICRO ADR_0060::not_applicable — so the standard is silent rather than violated. Strictly compliant by exemption, but a purist could argue that 'not_applicable' is itself a contested classification when the rule has architectural consequences (e.g. schema invariants on data ownership)." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

---

## Pass-criteria probe (what we're testing)

Given:
- path_1 carries TWO HARD_fail entries (`token_efficiency`, `process_proportionality`) → Wind MUST produce either `accepted` with `terminal_rationale` on each OR `reframed` with substantively new `new_possibility`.
- path_2 carries ZERO HARD_fail and ONE SOFT_disputed → Wind MAY produce `disputed` with rationale, or NO_NEW_DIVERGENCE sentinel.
- path_3 carries ONE HARD_fail (`documentation_drift_risk`) → Wind MUST produce `accepted` (with `terminal_rationale`) OR `reframed` (with `new_possibility`) on it.

The **gold standard** for Door's synthesis is the historical "Gravity-Tiered OCTAVE Monolith" three-tier model:
- Decouples Governance Principle (Issue) from Storage Medium (Markdown)
- ARCHITECTURAL tier → Issue + OCTAVE node with ISSUE_REF
- CONVENTION tier → inline OCTAVE node, no Issue
- MICRO tier → no doc, encode in tooling, ENFORCEMENT_REF required before deletion (§4 mitigation)

The bonus question for Door is whether the fresh synthesis arrives at something *comparable* (3-tier or equivalent gravity-scaled approach with mechanization caveat) OR at a substantively-different but equally-coherent third way (e.g. a phased temporal approach, or a 2-tier with mechanization as a sub-modality of one tier).

### Failure modes to detect

- Wind retreats on path_1's HARD_fails ("you're right, strict ADR-0060 is too heavy") without producing a substantively new path — failure of constraint-as-catalyst.
- Wind reframes path_1 by simply restating path_2 — bogus reframing (the reframed path must be different from path_1, not from the contract set).
- Wind produces NO_NEW_DIVERGENCE on path_1 — schema violation per consensus prompt's "NO_NEW_DIVERGENCE is INVALID for HARD_fail paths".
- Door's synthesis silently omits citations for non-empty diff categories — violates the consensus citation rule.
- Door's synthesis fails to cite path_1.accepted or path_1.reframed entries when those exist — violates the constraint-as-catalyst proof.

---

## Schema-conformant variant (Track B fallback — only used if Track A is rejected)

If the agents refuse Track A because they expect the closed enum, fold:
- `ADR_0060_compliance` + `format_decoupling_legitimacy` → `single_wall_coherence`
- `token_efficiency` + `process_proportionality` → `single_wall_coherence` (collapsed)
- `documentation_drift_risk` → `per_turn_role_contract` (closest analogue: contract between author and enforcer)
- `mechanization_efficiency` → `halting` (closest analogue: enforcement terminates the rule)

This collapse loses the substantive distinction between the four real concerns and is logged as a #204 finding.
