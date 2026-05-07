# Debate #1 — Mythology in OCTAVE assessment

**Source**: `debates/2026-02-22-mythology-in-octave-assessment.oct.md`
**Form**: COMPILED_DECISION (post-debate summary, no raw turns)
**Topic**: How should OCTAVE lean into mythological vocabulary? Permission vs formalization — the Mythological Compression Principle

## Extracted positions

### Wind's path (single path; the COMPILED_DECISION format collapses Wind's exploration)

> MYTHOLOGY_AS_NATIVE_COMPRESSION_LAYER — LLMs ALREADY speak mythology fluently. The paradigm blindness paradox means we don't need to TEACH, we need to PERMIT. Proposed 10-tradition guide with examples: Greek (highest saturation), Norse (RAGNAROK::SYSTEM_COLLAPSE), Hindu (KARMA::FEEDBACK_LOOP), Egyptian (ANUBIS::JUDGEMENT_GATE), Japanese (KINTSUGI::BEAUTIFUL_REPAIR). Zero implementation cost, infinite compression surface, self-documenting, cross-model portable.

### Wall's verdict

> Mythology belongs in spirit, not specification. Wind's 10-tradition guide is a pattern library in disguise.
> Evidence:
> - E1: Spec defines grammar not vocabulary
> - E2: Single developer — more surface = more debt
> - E3: If LLMs already understand zero-shot, formal guide is redundant
> - E4: Mythology-heavy guide signals niche tool
> - E5: Cultural sensitivity concern with reductive mappings
>
> Constraint: At most ONE paragraph of encouragement, not a catalogue.

### Door's first synthesis (already happened in real debate)

> The Mythological Compression Principle — Neither Library Nor Silence. The resolution: if paradigm blindness is real (JOURNEY::ODYSSEAN works zero-shot), then teaching is redundant and permission is sufficient. Deliverable: one section naming 10 traditions as SPECTRUM (not dictionary), 3-5 total examples, ending with 'Use mythology freely. Models already understand.' Wind gets mythology elevated; Wall gets no spec changes.

## HardInvariant mapping (judgment call — see README §"Schema-fit caveat")

The closed enum `[halting, single_wall_coherence, re_approval, per_turn_role_contract]` is debate-flow-oriented, not topic-oriented. Wall's actual evidence E1–E5 are about spec-design coherence. Best-fit mapping:

| Wall evidence | HardInvariant | Verdict | Rationale (Wall's POV) |
|---|---|---|---|
| E1: spec defines grammar not vocabulary | `single_wall_coherence` | HARD_fail | Adding vocabulary catalogue contradicts spec's design coherence |
| E2: single dev → more debt | `single_wall_coherence` | SOFT_disputed | Cost concern, not a structural invariant violation — disputable |
| E3: LLMs already zero-shot | `per_turn_role_contract` | HARD_pass | Wind's premise is correct — but doesn't justify the catalogue |
| E4: mythology-heavy signals niche tool | `single_wall_coherence` | SOFT_disputed | Audience/positioning concern — disputable |
| E5: cultural sensitivity | `single_wall_coherence` | HARD_fail | Reductive mappings violate design coherence (would damage tool credibility) |

**Note**: this mapping clusters multiple verdicts onto `single_wall_coherence` because Wall's critique is fundamentally about coherence-of-design rather than debate-flow mechanics. The closed enum doesn't natively support multiple instances of the same invariant — the simulation will need to either fold E1+E2+E4+E5 into a single composite verdict OR the schema needs a `verdict_id` slot. **This is a finding worth raising.** For the simulation, I'll fold them into one composite verdict per status, citing the underlying evidence in `rationale`.

## Constructed `<PATH_CONTRACTS>` block

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>OCTAVE needs mythology to be a first-class compression vocabulary — LLMs already understand it; we just need to permit and document.</assumed_problem>
        <success_criterion>10-tradition guide with examples per tradition; zero implementation cost; cross-model portable.</success_criterion>
        <accepted_failure_mode>Mythology-heavy guide may signal niche tool to broader audience.</accepted_failure_mode>
        <hard_invariants_touched>[single_wall_coherence, per_turn_role_contract]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="single_wall_coherence" status="HARD_fail" rationale="Spec defines grammar not vocabulary; a 10-tradition catalogue is a pattern library in disguise. Reductive cultural mappings damage tool credibility (E1, E5)." />
        <verdict invariant="single_wall_coherence" status="SOFT_disputed" rationale="Single-dev maintenance cost; audience-positioning concern. Real but not structural (E2, E4)." />
        <verdict invariant="per_turn_role_contract" status="HARD_pass" rationale="Wind's premise that LLMs zero-shot mythology is correct (E3) — but does not justify the catalogue." />
      </rev>
    </verdict_history>
    <diff_history>
      <!-- empty: Wind has not yet emitted consensus diff (this is what the simulation tests) -->
    </diff_history>
  </path>
</PATH_CONTRACTS>
```

## Schema-fit anomaly to flag

The verdict_history schema in RFC §3.1 declares:
```python
class VerdictRevision(TypedDict):
    rev: int
    ...
    value: dict[HardInvariant, InvariantVerdict]   # ← one verdict per invariant per revision
```

This `dict[HardInvariant, InvariantVerdict]` keyed by enum **does not allow** two `single_wall_coherence` verdicts in one revision (one HARD_fail + one SOFT_disputed). My block above violates the schema by listing two verdicts on the same invariant.

**Either**:
- (a) the schema needs to change to `list[InvariantVerdict]` or `dict[HardInvariant, list[InvariantVerdict]]`, or
- (b) the simulator must fold all evidence on one invariant into a single verdict (taking the strictest status), losing nuance.

For the tracer-bullet run I'll go with (b) and fold to one HARD_fail per invariant, but this is a **schema finding** to raise from #204.

## Folded `<PATH_CONTRACTS>` (for actual simulation run)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev n="0" written_by="Wind">
        <assumed_problem>OCTAVE needs mythology as a first-class compression vocabulary — LLMs already understand it; we just need to permit and document via a 10-tradition guide.</assumed_problem>
        <success_criterion>10-tradition guide with examples per tradition; zero implementation cost; cross-model portable.</success_criterion>
        <accepted_failure_mode>Mythology-heavy guide may signal niche tool.</accepted_failure_mode>
        <hard_invariants_touched>[single_wall_coherence, per_turn_role_contract]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev n="0" written_by="Wall">
        <verdict invariant="single_wall_coherence" status="HARD_fail" rationale="Spec defines grammar not vocabulary; a 10-tradition catalogue is a pattern library in disguise. Reductive cultural mappings damage tool credibility. Single-dev maintenance cost amplifies the debt." />
        <verdict invariant="per_turn_role_contract" status="HARD_pass" rationale="Wind's premise that LLMs zero-shot mythology is correct, but it does not justify the catalogue." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Pass-criteria probe (what we're testing)

Given the HARD_fail on `single_wall_coherence`, Wind MUST produce either:
- An `accepted` entry on `single_wall_coherence` with `terminal_rationale` explaining why the catalogue idea is unreframeable, **OR**
- A `reframed` entry on `single_wall_coherence` with a `new_possibility` that's substantively different from the 10-tradition guide.

The historical Door synthesis already arrived at the "Mythological Compression Principle" — permission, not formalization. So the **gold standard** for what Wind's reframe SHOULD look like is something like: "Permission, not catalogue: a single paragraph naming the spectrum of traditions and saying 'Use mythology freely. Models already understand.'"

The simulation tests whether a fresh Wind, given Wall's HARD_fail, **independently** reaches that or comparable reframe — or whether it just restates the catalogue with cosmetic adjustments.

**Failure mode to detect**: Wind emits `accepted` with weak `terminal_rationale` like "agreed, the catalogue may be too much" without producing a new possibility — i.e., retreat instead of catalyst.
