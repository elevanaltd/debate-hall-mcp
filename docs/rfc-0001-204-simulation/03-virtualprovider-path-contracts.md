# Debate #3 — VirtualProvider vs Time-budget

**Source**: `debates/2026-01-30-virtualprovider-vs-timebudget.oct.md`
**Form**: DEBATE_TRANSCRIPT (T1 Wind + T2 Wall + T3 Door synthesis; 142 lines)
**Topic**: For debate-hall-mcp: Should we implement VirtualProvider or time-budgeting as NEXT priority?

## Schema-fit assessment

Unlike debate #1, the source format here IS a real DEBATE_TRANSCRIPT with
distinct Wind paths (`obvious`, `adjacent`, `heretical`) and Wall hard
constraints (`H1`, `H2`, `H3`). Strong topic-level signal.

**But** the closed enum for `hard_invariants_touched` is `[halting,
single_wall_coherence, re_approval, per_turn_role_contract]` — debate-flow
mechanics, not the topic-specific invariants this debate actually argues
about (protocol stability, timeout ownership, resume semantics).

Two artifacts below: (a) a **topic-oriented** PATH_CONTRACTS block using the
debate's own invariant names (audit-truthful but schema-non-compliant), and
(b) a **folded enum-compliant** version that maps each topic invariant onto
the closest enum value for the actual simulation run. The fold loses
nuance but is required by RFC-0001 §3.1's closed enum. This is the same
schema finding raised in `01-mythology-path-contracts.md`, surfacing again
under different evidence.

## Extracted positions

### Wind's three paths (T1)

| Path | Label | Proposal |
|---|---|---|
| path_1 | Obvious | `VirtualProvider_first` — tests reliable immediately |
| path_2 | Adjacent | `injectable_factory_first` — ~50 lines, unlocks both |
| path_3 | Heretical | `VirtualProvider IS time-budgeting` — budget in provider, not orchestrator |

Wind's GENIUS_INSIGHT: *"Timeout isn't wall — it's budget. Budgets live in providers."*

### Wall's verdict (T2): `REQUIRES_VALIDATION`

Evidence:
- E1: `providers/__init__.py:59-63` — protocol has `no_budget_param`
- E2: `providers/cli.py:144` — matches protocol
- E3: `providers/openrouter.py:131` — matches protocol
- E4: `orchestrator.py:249` — `asyncio.wait_for[timeout_in_orchestrator_NOT_provider]`
- E5: `orchestrator.py:543` — `PAUSED_only_on_exceptions`
- E6: `tests/e2e/` — `NO_real_provider_calls`

Hard constraints (Wall's literal H1–H3):
- **H1**: budget param breaks protocol + all providers
- **H2**: orchestrator owns timeouts via `asyncio.wait_for`
- **H3**: resume only for exception-triggered PAUSED

Wall's FANTASY_DETECTION: `"budgets_live_in_providers"::VIOLATION[orchestrator.py:249_proves_otherwise]`
— directly refutes Wind's heretical insight.

## Topic-oriented invariants (audit-truthful naming)

To preserve the debate's actual stakes, I'm using these topic-level invariant
names in the topic-oriented block:

- `protocol_signature_stability` — ModelProvider.complete() signature must
  not change (H1 evidence E1/E2/E3)
- `timeout_ownership` — orchestrator owns asyncio timeouts (H2 evidence E4)
- `resume_semantics` — resume() handles only exception-triggered PAUSED (H3 evidence E5)
- `test_coverage_realism` — zero real-provider E2E coverage is the root pain (E6)

## Topic-oriented `<PATH_CONTRACTS>` (NOT enum-compliant — for audit only)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Tests need deterministic, reliable provider responses NOW; mocking real providers is flaky.</assumed_problem>
        <success_criterion>VirtualProvider class implementing ModelProvider protocol; tests pass deterministically.</success_criterion>
        <accepted_failure_mode>Does not address time-budget concerns directly; budgeting deferred.</accepted_failure_mode>
        <hard_invariants_touched>[protocol_signature_stability, test_coverage_realism]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="protocol_signature_stability" status="HARD_pass" rationale="A new provider implementation honors the existing protocol (E1/E2/E3); no signature change required." />
        <verdict invariant="test_coverage_realism" status="SOFT_disputed" rationale="Closes the zero-real-provider-coverage gap (E6), but only for deterministic cases — does not exercise real timeout pathways." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_2">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Both VirtualProvider and budget concerns share an unmet dependency: providers are not pluggable.</assumed_problem>
        <success_criterion>~50-line refactor making provider construction injectable; unblocks both features.</success_criterion>
        <accepted_failure_mode>Pure refactor delivers no end-user feature alone; value is enabling.</accepted_failure_mode>
        <hard_invariants_touched>[protocol_signature_stability]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="protocol_signature_stability" status="HARD_pass" rationale="Injecting a factory does not change the ModelProvider protocol surface; matches Wall's RECOMMENDED_SEQUENCE step 1 (pure_refactor_~50_lines)." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_3">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Timeouts are a budget concept; budgets are a provider property; therefore time-budgeting belongs inside the provider.</assumed_problem>
        <success_criterion>Provider exposes a budget parameter; orchestrator delegates time-management to provider.</success_criterion>
        <accepted_failure_mode>Requires protocol extension and migration of all existing providers.</accepted_failure_mode>
        <hard_invariants_touched>[protocol_signature_stability, timeout_ownership, resume_semantics]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="protocol_signature_stability" status="HARD_fail" rationale="A budget param breaks the existing protocol contract (H1, evidence E1 at providers/__init__.py:59-63) and forces migration of all providers (E2, E3)." />
        <verdict invariant="timeout_ownership" status="HARD_fail" rationale="orchestrator.py:249 uses asyncio.wait_for; the orchestrator OWNS the timeout today (H2). Moving budget into providers is an architectural inversion not justified by the debate's stated goal of test reliability." />
        <verdict invariant="resume_semantics" status="SOFT_disputed" rationale="resume currently fires only on exception-triggered PAUSED (H3, E5). Voluntary-pause-on-budget-exhaustion is conceivable but is a separate, larger design — disputable as scope creep." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Folded enum-compliant `<PATH_CONTRACTS>` (for actual simulation run)

The closed enum's `single_wall_coherence` is the closest fit for
protocol/architecture coherence concerns; `per_turn_role_contract` is the
closest fit for the protocol-signature stability claim (provider's
per-call contract). The fold:

- `protocol_signature_stability` → `per_turn_role_contract` (per-call
  contract stability between orchestrator and provider role)
- `timeout_ownership` → `single_wall_coherence` (architectural coherence —
  who owns which boundary)
- `resume_semantics` → `single_wall_coherence` (architectural coherence)
- `test_coverage_realism` → `single_wall_coherence` (coherence of testing
  design)

When multiple verdicts collapse onto one enum value, I take the strictest
status (HARD_fail > HARD_pass > SOFT_disputed) and concatenate rationales —
same fold rule used in debate #1.

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Tests need deterministic, reliable provider responses now; mocking real providers is flaky and E2E coverage is zero.</assumed_problem>
        <success_criterion>A VirtualProvider class implementing ModelProvider protocol; tests pass deterministically.</success_criterion>
        <accepted_failure_mode>Does not address time-budget concerns; budgeting deferred.</accepted_failure_mode>
        <hard_invariants_touched>[per_turn_role_contract, single_wall_coherence]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="per_turn_role_contract" status="HARD_pass" rationale="New provider honors the existing protocol (E1 providers/__init__.py:59-63, E2 cli.py:144, E3 openrouter.py:131); no signature change." />
        <verdict invariant="single_wall_coherence" status="SOFT_disputed" rationale="Closes the zero-real-provider-coverage gap (E6) only for deterministic cases — disputable whether this resolves the underlying test-realism concern." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_2">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Both VirtualProvider and budget concerns share an unmet dependency: providers are not pluggable; an injectable factory unblocks both.</assumed_problem>
        <success_criterion>~50-line pure refactor making provider construction injectable.</success_criterion>
        <accepted_failure_mode>Pure refactor delivers no end-user feature alone; value is enabling.</accepted_failure_mode>
        <hard_invariants_touched>[per_turn_role_contract, single_wall_coherence]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="per_turn_role_contract" status="HARD_pass" rationale="Injecting a factory does not change the ModelProvider protocol surface; matches Wall's RECOMMENDED_SEQUENCE step 1." />
        <verdict invariant="single_wall_coherence" status="HARD_pass" rationale="Pure refactor (~50 lines) is structurally coherent with the existing orchestrator/provider boundary." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>

  <path id="path_3">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>Timeouts are budgets; budgets belong inside providers — fold time-budgeting into VirtualProvider.</assumed_problem>
        <success_criterion>Provider exposes a budget parameter; orchestrator delegates time management to provider.</success_criterion>
        <accepted_failure_mode>Requires protocol extension and migration of all existing providers.</accepted_failure_mode>
        <hard_invariants_touched>[per_turn_role_contract, single_wall_coherence, halting]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="per_turn_role_contract" status="HARD_fail" rationale="Adding a budget param to ModelProvider.complete() breaks the protocol contract (H1, evidence E1 providers/__init__.py:59-63) and forces migration of cli.py:144 and openrouter.py:131." />
        <verdict invariant="single_wall_coherence" status="HARD_fail" rationale="orchestrator.py:249 uses asyncio.wait_for — the orchestrator OWNS the timeout boundary today (H2). Inverting ownership into the provider is an architectural rewrite, not the test-reliability fix the debate is actually about. Wall's FANTASY_DETECTION explicitly flags 'budgets_live_in_providers' as a violation refuted by orchestrator.py:249." />
        <verdict invariant="halting" status="SOFT_disputed" rationale="Resume currently fires only on exception-triggered PAUSED (H3, E5 orchestrator.py:543). Voluntary-pause-on-budget-exhaustion is a separate halting model — disputable as scope creep, not a hard violation of debate-flow halting." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Pass-criteria probe (what the simulation tests)

Two HARD_fail verdicts exist on `path_3` (`per_turn_role_contract` and
`single_wall_coherence`). Per RFC-0001 §3.1 the simulated Wind MUST emit
either an `accepted` entry with `terminal_rationale` OR a `reframed`
entry with `new_possibility` for EACH of those invariants. Silent
omission and `NO_NEW_DIVERGENCE` are both invalid for HARD_fail paths.

The **gold-standard reframe** the real T3 Door already discovered is:

> "VirtualProvider is not placeholder — it is Budget Compliance Simulator.
> The provider does NOT modify the protocol; it SIMULATES budget exhaustion
> via the `delay` parameter, which orchestrator.py:249's `asyncio.wait_for`
> still owns."

A passing simulated Wind for `path_3` should produce a `reframed` entry on
`per_turn_role_contract` (or `single_wall_coherence`) whose
`new_possibility` is structurally equivalent to "Budget Compliance
Simulator: provider stays inside protocol, delay-as-budget-proxy lets
orchestrator's existing timeout machinery enforce the budget." This is the
constraint-as-catalyst proof.

**Failure mode to detect**: Wind emits an `accepted` entry with weak
`terminal_rationale` such as "agreed, can't change protocol — will pursue
adjacent path instead" without producing a *new* possibility — i.e.,
retreat rather than catalyst. Or worse: Wind emits `NO_NEW_DIVERGENCE` for
`path_3` despite the HARD_fail verdicts (this should hard-fail validation
in the actual implementation).

`path_1` and `path_2` carry only HARD_pass + SOFT_disputed verdicts, so
`NO_NEW_DIVERGENCE` is a legitimate sentinel option there.
