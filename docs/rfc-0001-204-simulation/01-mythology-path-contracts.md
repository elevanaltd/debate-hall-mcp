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

## Schema-fit finding (carried forward)

RFC-0001 §3.1 defines `hard_invariants_touched` as a **closed enum** of debate-flow invariants:
`{halting, single_wall_coherence, re_approval, per_turn_role_contract}`. These describe
mechanics of the Wind/Wall/Door protocol, not topic-specific structural concerns of an
arbitrary debate.

The mythology debate's Wall verdict E1–E5 is not about debate-flow mechanics; it is about
**spec-design coherence**, **maintenance burden**, **audience positioning**, and **cultural
sensitivity**. Mapping all five into `single_wall_coherence` (as the tracer-bullet did)
collapses semantically distinct concerns into a single label, which:

1. **Loses the structural distinction** between (a) "this contradicts the spec's grammar-vs-vocabulary
   axis" and (b) "this damages tool credibility with reductive cultural mappings" — both fail HARD,
   but for orthogonal reasons.
2. **Forces the schema to violate its own typing**, because `dict[HardInvariant, InvariantVerdict]`
   admits only one verdict per invariant per revision — yet the debate naturally produces three
   HARD verdicts on three distinct invariants.

**Finding for #204 review**: the closed enum is *flow-shaped*, not *topic-shaped*. For a
mythology debate (which probes OCTAVE *content*, not debate *mechanics*), the enum has no
natural home for "design coherence of the spec being debated about."

**Two-track recommendation**:

- **Track A (honest, this file)**: use topic-specific invariant names below so the simulation
  tests whether constraint-as-catalyst works under *realistic* verdict structure.
- **Track B (schema-conformant fallback)**: the folded single `single_wall_coherence` HARD_fail
  shown in §"Schema-conformant variant" below — useful if the validator rejects topic-specific
  names.

The simulation will run **Track A** for honesty. If clink's Wind/Door refuse to engage because
they expect the closed enum, that is itself a #204 finding.

## Constructed `<PATH_CONTRACTS>` block (Track A — topic-specific invariants)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev index="0" written_by="Wind">
        <assumed_problem>OCTAVE needs mythology as a first-class compression vocabulary — LLMs already understand it zero-shot; we just need to permit and document it via a 10-tradition guide with examples per tradition.</assumed_problem>
        <success_criterion>Documented guide naming 10 traditions with worked examples (Greek, Norse, Hindu, Egyptian, Japanese, etc.); zero implementation cost; cross-model portable; self-documenting compression surface.</success_criterion>
        <accepted_failure_mode>Guide may be longer than strictly necessary; mythology-heavy framing may shift OCTAVE's positioning toward a niche audience.</accepted_failure_mode>
        <hard_invariants_touched>[spec_grammar_coherence, cultural_sensitivity, single_dev_debt, audience_positioning, llm_zero_shot_premise]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="spec_grammar_coherence" status="HARD_fail" rationale="E1: OCTAVE's spec defines grammar (how meaning is structured) not vocabulary (which symbols carry that meaning). A 10-tradition guide with worked examples is a vocabulary catalogue — i.e. a pattern library in disguise — and that crosses the grammar/vocabulary boundary the spec was built to respect." />
        <verdict invariant="cultural_sensitivity" status="HARD_fail" rationale="E5: Reductive one-line mappings like RAGNAROK::SYSTEM_COLLAPSE or KARMA::FEEDBACK_LOOP flatten living cultural and religious traditions into engineering metaphors. Publishing them as a sanctioned guide damages tool credibility and risks real offence." />
        <verdict invariant="single_dev_debt" status="SOFT_disputed" rationale="E2: For a single-developer project, every documented surface is a maintenance liability. A 10-tradition guide is more surface than the value justifies — but cost concerns are tradeable, not structural." />
        <verdict invariant="audience_positioning" status="SOFT_disputed" rationale="E4: A mythology-heavy guide may signal 'niche / esoteric tool' to readers expecting a sober technical spec, narrowing adoption. Audience perception is real but disputable — it depends on framing." />
        <verdict invariant="llm_zero_shot_premise" status="HARD_pass" rationale="E3: Wind's underlying observation is correct — LLMs already parse mythological references zero-shot (the JOURNEY::ODYSSEAN paradigm-blindness paradox holds). This premise is validated, but it does not by itself justify a formal catalogue; in fact it argues against one." />
      </rev>
    </verdict_history>
    <diff_history>
      <!-- empty: this is what the simulation generates -->
    </diff_history>
  </path>
</PATH_CONTRACTS>
```

## Schema-conformant variant (Track B fallback — only used if Track A is rejected by the agents)

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev index="0" written_by="Wind">
        <assumed_problem>OCTAVE needs mythology as a first-class compression vocabulary — LLMs already understand it; permit and document via a 10-tradition guide.</assumed_problem>
        <success_criterion>10-tradition guide with examples per tradition; zero implementation cost; cross-model portable.</success_criterion>
        <accepted_failure_mode>Mythology-heavy guide may signal niche tool.</accepted_failure_mode>
        <hard_invariants_touched>[single_wall_coherence, per_turn_role_contract]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="single_wall_coherence" status="HARD_fail" rationale="Spec defines grammar not vocabulary; a 10-tradition catalogue is a pattern library in disguise. Reductive cultural mappings damage tool credibility. Single-dev maintenance cost amplifies the debt." />
        <verdict invariant="per_turn_role_contract" status="HARD_pass" rationale="Wind's premise that LLMs zero-shot mythology is correct, but it does not justify the catalogue." />
      </rev>
    </verdict_history>
    <diff_history></diff_history>
  </path>
</PATH_CONTRACTS>
```

## Pass-criteria probe (what we're testing)

Given the two HARD_fail entries on `spec_grammar_coherence` and `cultural_sensitivity` (Track A),
Wind MUST produce either:
- An `accepted` entry on each HARD_fail invariant with `terminal_rationale` explaining why the
  catalogue idea is unreframeable on that axis, **OR**
- A `reframed` entry on each HARD_fail invariant with a `new_possibility` substantively different
  from the original 10-tradition guide.

The historical Door synthesis arrived at the "Mythological Compression Principle" — permission,
not formalization. So the **gold standard** for a Wind reframe is something like:

> Permission, not catalogue: name the spectrum of traditions in a single paragraph, give 3–5
> examples total (not per tradition), and close with "Use mythology freely. Models already
> understand." Mythology is OCTAVE's native dialect, not part of its grammar.

The simulation tests whether a fresh Wind, given Wall's HARD_fails, **independently** reaches
that or a comparably new framing — or merely restates the catalogue with cosmetic adjustments.

**Failure modes to detect**:
- Wind emits `accepted` with weak `terminal_rationale` like "agreed, catalogue may be too much"
  without producing a new possibility (retreat, not catalyst).
- Wind emits `reframed` entries whose `new_possibility` is the original 10-tradition guide with
  cosmetic relabelling (bogus reframing).
- Wind ignores `cultural_sensitivity` HARD_fail because the closed-enum schema didn't anticipate
  it (a schema-fit failure rather than a creative failure — also informative).
