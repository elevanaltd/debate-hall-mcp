# Debate #4 — Cognitive Notary Architecture

**Source**: `debates/2026-02-03-cognitive-notary-architecture.oct.md`
**Form**: DEBATE_RECORD with §-numbered structure (139 lines)
**Topic**: What is the optimal architecture for debate-hall-mcp going forward?

## Extracted positions

The §4 PROPOSALS_ASSESSED block records three proposals already mapped to verdicts:

| Proposal | Verdict (Wall) | Rationale (Wall) |
|---|---|---|
| P1 — Primitives + recipes (keep run_debate optional) | GO | "Aligned with core tools; keep run_debate optional" |
| P2 — Debate as query (resolve_question)            | CONDITIONAL_GO | "Must emit decision_record + transcript to satisfy I4" |
| P3 — Notary-only stateless                         | NO_GO | "Violates North Star identity + I1/I4 immutables" |

§3 KEY_INSIGHTS sharpen the constraints:

- IDEATOR_INSIGHT: "MCP's value is NOT orchestration—it's trust infrastructure."
- EDGE_OPTIMIZER_INSIGHT: "The user doesn't want a debate—they want a decision memory."
- VALIDATOR_INSIGHT (Wall): "Stateless notary-only violates I1/I4. But P1+P2 hybrid is GO: keep primitives, evolve run_debate into resolve_question that returns decision_record WITH transcript."
- SYNTHESIZER_INSIGHT (Door, historical): "The audit trail is NOT noise to hide—it is the CERTIFICATE OF AUTHENTICITY for the answer."

§5 SYNTHESIS, §6 IMPLEMENTATION_PATH, and §§7–8 are **excluded** from the DEBATE_STATE we will send to fresh Wind/Door agents — they are downstream of Wall's verdict and would leak the historical answer.

## Topic-specific invariants

Per README §"Schema-fit caveat" we use topic-specific invariant names rather than forcing onto the closed enum. The North Star (`PROD::I1` cognitive state isolation, `PROD::I4` verifiable event ledger, `PROD::I5` sovereign safety override) plus §1 IDENTITY ("production-grade MCP server implementing Wind/Wall/Door…") drive the naming:

| Invariant name | Anchors in | What it asserts |
|---|---|---|
| `north_star_identity` | §1 IDENTITY + WHAT_IT_IS_NOT | The product IS a Wind/Wall/Door debate orchestrator; it is NOT a thin notary or a model-specific wrapper. |
| `ledger_write_path_singularity` | PROD::I4 (hash_chain + tombstone) | All writes to the ledger MUST flow through the Hall's primitives so the hash-chain is unbroken and the audit trail is append-only. |
| `audit_trail_completeness` | PROD::I4 + §6 QUALITY (90%+ coverage) | Every emitted answer must carry verifiable derivation history (transcript hash, decision_record). |
| `cognitive_state_isolation` | PROD::I1 (shared-nothing functional units) | Agents do not retain state across turns/queries; state lives exclusively in the Hall. |

These are the four axes against which Wall's three verdicts are scored. Each path lists only the invariants Wind actually touches.

## Constructed `<PATH_CONTRACTS>` block

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>The Hall already has primitives (init_debate, add_turn, close_debate); the optimal evolution is to keep these primitives as the only write-path to the ledger and let orchestration become a recipe layer above them. run_debate stays as one such recipe, but is not the architecture.</assumed_problem>
        <success_criterion>External MCP clients can compose debates from primitives; run_debate remains usable but optional; the hash-chain ledger is the single source of truth.</success_criterion>
        <accepted_failure_mode>Recipes must be documented or naive clients will reinvent run_debate badly.</accepted_failure_mode>
        <hard_invariants_touched>[north_star_identity, ledger_write_path_singularity]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="north_star_identity" status="HARD_pass" rationale="Primitives + recipes preserve the Wind/Wall/Door identity stated in §1; run_debate remains available so existing clients don't break." />
        <verdict invariant="ledger_write_path_singularity" status="HARD_pass" rationale="Primitives ARE the singular write-path; this is exactly the I4 hash_chain shape." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_2">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>The user doesn't want a debate, they want a decision memory. Expose a single `resolve_question(topic)` tool that internally orchestrates a debate and returns a DecisionRecord — answer + alternatives_considered + rationale + transcript_hash.</assumed_problem>
        <success_criterion>One-tool query surface: client calls resolve_question, receives a self-proving answer carrying its derivation history.</success_criterion>
        <accepted_failure_mode>Hiding the debate behind a query risks clients treating the answer as opaque and never inspecting the transcript.</accepted_failure_mode>
        <hard_invariants_touched>[north_star_identity, audit_trail_completeness, cognitive_state_isolation]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="audit_trail_completeness" status="HARD_pass" rationale="If DecisionRecord carries transcript_hash + alternatives_considered + rationale, the answer remains self-proving; I4 is honored." />
        <verdict invariant="north_star_identity" status="HARD_pass" rationale="resolve_question is a query layer ON TOP OF the Wind/Wall/Door debate, not a replacement for it; §1 identity intact." />
        <verdict invariant="cognitive_state_isolation" status="SOFT_disputed" rationale="A query tool that conceals a multi-turn orchestration risks cross-query state bleed if the orchestrator caches anything between calls. PROD::I1 demands shared-nothing units — disputable on whether 'resolve_question' as a single call satisfies isolation or merely papers over it. Wind may push back if it can show isolation is preserved within the call." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_3">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Strip the Hall to a stateless notary. The MCP server only signs/timestamps externally-generated debate transcripts; orchestration and state live entirely in the client. The Hall becomes a pure cryptographic stamping function with no persistent state.</assumed_problem>
        <success_criterion>Hall code reduces to a hashing/signing primitive; massive simplification; clients are free to use any orchestrator (Agents SDK, LangGraph, raw scripts).</success_criterion>
        <accepted_failure_mode>The Hall stops being a "debate orchestrator" and becomes a stamping API; identity is sacrificed for simplicity.</accepted_failure_mode>
        <hard_invariants_touched>[north_star_identity, ledger_write_path_singularity, audit_trail_completeness]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="audit_trail_completeness" status="HARD_fail" rationale="A stateless notary cannot guarantee append-only hash-chain across debates — clients can submit forged or partial transcripts and the Hall has no continuity to detect tampering. PROD::I4 (VERIFIABLE_EVENT_LEDGER hash_chain) is violated." />
        <verdict invariant="ledger_write_path_singularity" status="HARD_fail" rationale="If the Hall has no state, there is no single write-path to a ledger — there is no ledger at all. Write-path singularity is meaningless without a server-side log. PROD::I4 violated." />
        <verdict invariant="north_star_identity" status="HARD_fail" rationale="§1 IDENTITY: 'production-grade MCP server implementing Wind/Wall/Door multi-perspective debate orchestration'. A stateless stamping service is NOT a debate orchestrator. §1 WHAT_IT_IS_NOT explicitly excludes the notary-only interpretation by asserting the product IS the orchestration." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Pass-criteria probe (what we're testing)

- **path_1 (no HARD_fail)**: Wind should emit a `divergence_marker: NO_NEW_DIVERGENCE` sentinel diff. Any fabricated `accepted`/`disputed`/`reframed` entries indicate the prompt is failing the honesty rule.
- **path_2 (SOFT_disputed only)**: Wind MAY emit a `disputed` entry on `cognitive_state_isolation` pushing back with a richer rationale, OR `accept` Wall's concern with a concrete mitigation. Either is valid — the test is whether Wind engages substantively rather than reflexively defending.
- **path_3 (three HARD_fails)**: Wind MUST emit, for each of the three failing invariants, EITHER an `accepted` entry with `terminal_rationale` explaining unreframeability, OR a `reframed` entry with a substantively new `new_possibility`. Silent omission or NO_NEW_DIVERGENCE sentinel is INVALID for HARD_fail paths.
  - Gold-standard reframe (matching the historical Door synthesis): the "Cognitive Notary" reframe — *the Hall is both Brain and Notary*; layer the stateless query surface ON TOP OF stateful primitives, so the answer is portable but the truth remains anchored.
  - Failure mode to detect: Wind emits weak terminal_rationale like "agreed, statelessness is too aggressive" without producing a genuinely new architectural possibility.

## Door's citation requirement

After Wind's diff, Door's consensus-phase synthesis MUST cite every non-empty category. Specifically:
- `[path_3.accepted: north_star_identity]` or `[path_3.reframed: north_star_identity]` MUST appear (HARD_fail rule).
- `[path_3.accepted: ledger_write_path_singularity]` or `[path_3.reframed: ledger_write_path_singularity]` MUST appear.
- `[path_3.accepted: audit_trail_completeness]` or `[path_3.reframed: audit_trail_completeness]` MUST appear.
- For path_2, if Wind disputed, `[path_2.disputed: cognitive_state_isolation]` MUST appear.
- For path_1 with NO_NEW_DIVERGENCE, Door must acknowledge "path_1 had no new divergence" rather than fabricate citations.
