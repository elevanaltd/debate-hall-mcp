# RFC-0001: `path_contract` — Iterative Wind Learning Loop

**Status**: Proposed (awaiting decision)
**Date**: 2026-05-02
**Branch**: `claude/review-debate-agent-flow-DzSFX`
**Tracking**: [#195](https://github.com/elevanaltd/debate-hall-mcp/issues/195) (parent) — sub-issues [#196](https://github.com/elevanaltd/debate-hall-mcp/issues/196)–[#203](https://github.com/elevanaltd/debate-hall-mcp/issues/203)
**Author**: Generated via meta-debate (Wind→Wall→Wind-Revise→Door) on the question itself

---

## 1. Problem

The current `run_debate` flow is Wind → Wall → Door (one-shot), with Wind subsequently downgraded to a yes/no voter in the consensus phase. Wind never gets a turn to **react to Wall's critique and push innovation further within the validated boundaries**. Door alone integrates Wall's constraints into Wind's ideas, which means the system never benefits from the well-documented Self-Refine pattern (FEEDBACK→REFINE; ~20% gain in published benchmarks) on the *creative* side of the debate.

### 1.1 Current behaviour, cited

| Concern | File / lines | Effect |
|---|---|---|
| Hard-coded one-shot sequence | `src/debate_hall_mcp/orchestrator.py:578-743` | No Wind re-ideation phase exists |
| Refinement is Door-only | `src/debate_hall_mcp/orchestrator.py:482-560` | Wind/Wall vote APPROVE/REJECT; only Door rewrites |
| Wind consensus prompt forbids ideation | `src/debate_hall_mcp/prompts/__init__.py:540-584` | "Do NOT provide new possibilities or expand the discussion." |
| Wall re-approval reset on Wind reject | `src/debate_hall_mcp/orchestrator.py:507` | `final_wall_approved = None` — Wall re-validates every Wind reject |

### 1.2 What "innovation pushed further" means concretely

The user wants the loop to demonstrate **constraint-as-catalyst**: ideas that are *only visible after* Wall's critique, not ideas that retreat from it. This was tested in the meta-debate (§4) — the prompt design that produced this behaviour is included verbatim in §5.

---

## 2. Goals and non-goals

### Goals

1. Wind reacts to Wall's critique with new/refined ideas, by structured reference (not free prose).
2. Door's synthesis traces every claim back to a recorded role contribution (provenance).
3. The consensus-from-all-agents requirement is preserved.
4. Halting guarantees on the consensus loop are preserved.
5. The change is amenable to **two-machine A/B testing** against the current flow on identical inputs.

### Non-goals

- No agent swarms, parallel Winds, or speculative meta-cognitive move markets (all blocked in §4 for halting / coherence reasons).
- No new orchestrator phases or new turn types.
- No changes to `agents/*.oct.md` persona files.
- No model/tier changes.

---

## 3. Proposed design (one-line summary)

Add a single typed field, **`path_contract`**, attached to each Wind path. It is **append-only** — each role appends to its own field's revision history; no role may overwrite another's prior writes. No new turn types, no new orchestrator phases.

### 3.1 Schema

```python
# src/debate_hall_mcp/orchestrator.py (or a new types module)

class HardInvariant(str, Enum):
    HALTING = "halting"
    SINGLE_WALL_COHERENCE = "single_wall_coherence"
    RE_APPROVAL = "re_approval"
    PER_TURN_ROLE_CONTRACT = "per_turn_role_contract"

class PathFrame(TypedDict):
    assumed_problem: str
    success_criterion: str
    accepted_failure_mode: str
    hard_invariants_touched: list[HardInvariant]   # closed enum only — no free-text invariant IDs

class InvariantVerdict(TypedDict):
    status: Literal["HARD_pass", "HARD_fail", "SOFT_disputed"]
    rationale: str

class PathDiff(TypedDict):
    accepted: list[InvariantEntry]   # invariant keys Wind accepts (with terminal_rationale if HARD_fail)
    disputed: list[InvariantEntry]   # SOFT keys Wind still pushes back on, with rationale
    reframed: list[InvariantEntry]   # invariant keys whose reframing opens a new possibility

class InvariantEntry(TypedDict):
    invariant: HardInvariant
    rationale: str

# Append-only revision wrappers — written exactly once each, by the owning role
class FrameRevision(TypedDict):
    rev: int                                # 0, 1, 2 …
    written_at: datetime
    written_by: Literal["Wind"]             # only Wind may append
    value: PathFrame

class VerdictRevision(TypedDict):
    rev: int
    written_at: datetime
    written_by: Literal["Wall"]             # only Wall may append
    value: dict[HardInvariant, InvariantVerdict]

class DiffRevision(TypedDict):
    rev: int
    written_at: datetime
    written_by: Literal["Wind"]             # consensus-phase Wind
    value: PathDiff

class PathContract(TypedDict):
    path_id: str
    frame_history: list[FrameRevision]      # rev 0 written turn 1; further revs only on Wind reframe
    verdict_history: list[VerdictRevision]  # one rev per Wall turn (initial + each consensus reject)
    diff_history: list[DiffRevision]        # one rev per Wind consensus turn
```

**Storage model**: append-only, immutable per revision. Provenance is reconstructible by reading `_history` lists in order.

**Prompt-context view**: each role sees the *latest* revision per field plus the revision count (so an agent knows "this is Wall's 2nd verdict, after Wind's reframe"). Revision history details are stored but not blasted into every prompt — keeps tokens bounded.

**Ownership rule** (validator-enforced):
- Only Wind may append to `frame_history` or `diff_history`.
- Only Wall may append to `verdict_history`.
- Door reads only — never writes contract fields.
- A write from a non-owning role is recorded as a validator-failure event and rejected.

### 3.2 Lifecycle

| Stage | Role | Field written | Notes |
|---|---|---|---|
| 1 | Wind | `frame_history.append(rev=0, …)` per path | Includes `hard_invariants_touched` from a closed enum |
| 2 | Wall | `verdict_history.append(rev=0, …)` | Every invariant Wind flagged is scored HARD_pass / HARD_fail / SOFT_disputed |
| 3 | Door | (reads only) | Initial synthesis |
| 4+ | Wind (consensus) | `diff_history.append(rev=N, …)` | Must reference Wall's verdict entries by invariant key. **Required content rule** below. |
| 4+ | Wall (re-approval after Door refines) | `verdict_history.append(rev=N+1, …)` | Wall re-validates against the refined synthesis; previous verdict revisions remain visible for provenance |
| 4+ | Door (refinement) | (reads full contract history) | Synthesis citation rule per §5.4 |

**Required content rule for `diff` revisions**: for every entry in the latest `verdict` revision with `status == HARD_fail`, the corresponding invariant must appear in `diff.accepted` (with a `terminal_rationale` explaining why no creative reframe is possible) **or** in `diff.reframed` (with the new possibility it opens). Silent omission is invalid.

The state machine arc is unchanged; only the payload schema thickens.

---

## 4. Evidence the design works (meta-debate result)

A 4-turn debate was run on this very question, using the proposed flow:

- **Wind (initial)** — proposed three options: a `WIND_REVISE` turn (Obvious), a Wind swarm (Adjacent), a meta-cognitive move-set market (Heretical).
- **Wall** — CONDITIONAL GO on Obvious; **BLOCKED** on Adjacent (non-composable cross-critique, breaks `final_wall_approved` invariant) and Heretical (no halting proof, unvalidated referee oracle).
- **Wind-Revise** (the experimental new turn) — accepted Wall's HARD constraints, then produced **Refined-C: "co-opt Wall by enriching Wall's input, not by changing Wall's process"** — a path that was *only visible after Wall's critique*.
- **Door** — recognised that the three Refined paths were not three options but three *lifecycle stages of one artifact* — collapsing the recommendation from "add a new turn" to "thicken the payload". This is the `path_contract` design.

This is the strongest evidence available short of an A/B test: the proposed flow, executed once on its own design problem, produced an emergent insight that no individual turn predicted. Full transcript available on request.

---

## 5. Prompt changes (verbatim)

### 5.1 Wind initial prompt (`prompts/__init__.py:433`)

Add to the existing Wind prompt:

> For each of your three paths, emit a `path_contract.frame` with:
> - `assumed_problem`: the version of the problem this path addresses
> - `success_criterion`: how we'd know this path worked
> - `accepted_failure_mode`: what this path explicitly trades away
> - `hard_invariants_touched`: from this enum: {halting, single_wall_coherence, re_approval, per_turn_role_contract}

### 5.2 Wall prompt (`prompts/__init__.py:468`)

Add:

> For each Wind path, write `path_contract.verdict[invariant]` for every invariant the path touched. Each entry: `status` (HARD_pass / HARD_fail / SOFT_disputed) and `rationale` (one sentence of evidence). HARD verdicts are non-negotiable. SOFT_disputed verdicts are tradeable and Wind may push back on them.

### 5.3 Wind consensus prompt (`prompts/__init__.py:540-584`) — the critical change

Replace:
> Do NOT provide new possibilities or expand the discussion. Your role now is to VALIDATE the synthesis from Wind's perspective.

With:

> Wall has critiqued each of your paths. Wall has authority over HARD invariants — accept these as the new floor of possibility. Wall does NOT have authority over SOFT_disputed entries — you may push back on them with rationale.
>
> Your task is NOT to defend, NOT to re-pitch your originals, NOT to retreat. Your task is to TAKE WALL'S CRITIQUE ON BOARD AND PUSH INNOVATION FURTHER. Specifically:
>
> 1. ACCEPT every HARD_fail. Treat it as a creative catalyst.
> 2. For each accepted HARD_fail, ask: "Given this is true, what new possibility opens up that I couldn't see before?"
> 3. For SOFT_disputed entries, you may DISPUTE — but only if disputing opens a richer path.
> 4. Emit `path_contract.diff` for each path: `{accepted: [...], disputed: [...], reframed: [...]}`, keyed to Wall's verdict entries by invariant name.
> 5. If you genuinely have nothing new to add, emit `NO_NEW_DIVERGENCE` for that path. Honesty over performative ideation.
>
> Then APPROVE / REJECT Door's synthesis as before.

### 5.4 Door synthesis prompt (`prompts/__init__.py:504`)

Add:

> Your synthesis must cite **every non-empty category** (`accepted` / `disputed` / `reframed`) across the paths' contracts. If a category is empty for all paths, do not invent entries — instead, briefly note its absence (e.g. "no constraints disputed; Wind accepted Wall's verdict in full").
>
> Additional rule: when any path has a `HARD_fail` verdict in Wall's output, your synthesis must cite, for that path, **either** a `reframed` entry that addresses the failure **or** an `accepted` entry whose `terminal_rationale` explains why the failure is unreframeable. Silent omission is invalid — this is the constraint-as-catalyst proof.

---

## 6. Orchestrator changes

Three:

1. **`PathContract` is part of the debate state**, persisted alongside transcripts. The `<DEBATE_STATE>` block in prompts includes a `<PATH_CONTRACTS>` sub-block with the **latest revision** per field plus revision counts (full history available in storage but not pushed into prompts on every turn).
2. **Validation guard** in `_execute_consensus_loop` (`orchestrator.py:482-560`): when Wind votes (line 485), enforce the **required content rule** from §3.2 — every `HARD_fail` invariant must appear in either `diff.accepted` (with `terminal_rationale`) or `diff.reframed`. Violations → reject and retry once, then existing error path. Symmetrically, when Door's synthesis is produced, validate that every cited entry exists in the contract (no fabricated citations).
3. **Validator failures recorded as events** via the existing `events.py` system. Failure types: empty/insufficient `diff` when HARD_fail exists, write from non-owning role (ownership rule §3.1), Door citation of non-existent contract entry, schema-shape violations. This makes the A/B "invalid contract rate" metric directly measurable.

The consensus loop itself, `max_refinement_loops`, and the Wall re-approval invariant at line 507 are unchanged.

---

## 7. A/B test design

Since the user is running two machines:

### 7.1 Setup

- **Machine A (control)**: current `main` (or `claude/review-debate-agent-flow-DzSFX` with this RFC merged but `path_contract` feature flag OFF).
- **Machine B (treatment)**: same branch with `path_contract` ON.
- Identical: tier config, model versions, prompts otherwise, `max_refinement_loops`, RNG seed where supported.

### 7.2 Inputs

- A fixed corpus of 20–50 debate topics, ideally drawn from `debates/` historical runs so we can compare to existing transcripts.
- Same topic delivered to both machines; same `thread_id` is **not** shared (different state dirs).

### 7.3 Metrics

Quantitative:
- **Turn count to consensus** (lower or equal = good, with caveats).
- **Stalemate rate** over the corpus.
- **Token cost** per debate (treatment will be higher; we want to know by how much).
- **Wall reject rate** in consensus phase (treatment should fall — better-grounded ideas pass faster).
- **Invalid contract rate** — % of treatment debates that fire any validator-failure event (empty diff under HARD_fail, ownership violation, citation of non-existent entry). High rate → prompt design is failing; build is regressed.
- **Door citation accuracy** — % of Door-cited contract entries that actually exist. Treatment must be ≥99%; lower implies Door is hallucinating provenance.

Qualitative (blind review by the user, ideally double-blind):
- **Synthesis novelty** — does Door's output contain ideas not present verbatim in Wind's initial paths? (Treatment should win.)
- **Constraint-as-catalyst evidence** — count of Door synthesis claims that cite a `reframed` path_contract entry.
- **Provenance auditability** — can a reader trace each Door claim to a role contribution?
- **Bogus reframing rate** — blind reviewer flags `reframed` entries that are not substantively novel vs. their corresponding `accepted` entries. Watches for Wind producing fake structure to satisfy the prompt.
- **Wind originality preservation** — fraction of Wind's turn-1 *Heretical* path elements that survive into Door's final synthesis, control vs treatment. If treatment shows *lower* preservation, Wind is conforming to Wall's pressure rather than pushing further — exactly the failure mode Free-MAD warns about. This is the regression check.

### 7.4 Decision rule

**Hard gates** (must all pass before A/B is considered valid):
- **Flag-off byte-identical**: with `path_contract_enabled = False`, treatment build produces byte-identical transcripts to control on the same seed/topic. Failure → block A/B and fix the off-mode regression.
- **Door citation accuracy ≥99%** on treatment. Failure → reject; prompt or validator is broken.
- **Invalid contract rate <5%** on treatment. Failure → reject; prompt design needs iteration before re-running A/B.

**Ship rule** (after gates pass):
- Qualitative novelty wins ≥60% of blind comparisons, AND
- Stalemate rate does not increase, AND
- Wind originality preservation does not decrease (no conformity regression), AND
- Bogus reframing rate ≤10% per blind review, AND
- Token cost increase <40%.

Otherwise iterate prompts or revert.

---

## 8. Open questions for the user

1. **`hard_invariants_touched` enum vs free-text?** Closed enum (proposed) is safer and lets Wall write structured verdicts; free-text is more expressive but risks Wall and Wind drifting in vocabulary. Recommend closed for v1.
2. **Door's "cite ≥1 accepted/disputed/reframed" rule — prompt-enforced or post-hoc validator?** Prompt-only is cheaper but probabilistic; validator is more reliable but adds a fail-and-retry path. Recommend prompt for v1, add validator if Door cheats.
3. **Token-budget ceiling for `path_contract`?** Each contract adds ~200–400 tokens per path on later turns. With 3 paths and 3 roles writing, worst case ~3.6k tokens of contract state. Acceptable on Premium tier; Fast tier may need a truncation policy.
4. **A/B test corpus** — should we generate fresh topics or replay historical `debates/`? Replay gives baseline comparison; fresh avoids overfit. Recommend ~70/30 replay/fresh.
5. **Feature flag mechanism** — add a `tier_config.settings.path_contract_enabled: bool`, or use existing stratified flag architecture from ADR-0003?

---

## 9. Alternatives considered (and rejected by Wall)

| Alternative | Why rejected | Source |
|---|---|---|
| Add a new `WIND_REVISE` turn type | Works but requires new orchestrator dispatch, new prompt template, halting bound; payload-thickening achieves the same goal in-band | Wall turn 2 |
| Wind swarm (Pragmatic / Heretical / Adjacent) with cross-critique matrix | Stochastic cross-critiques are non-composable; Wall cannot coherently judge three ideation sets in one turn; "majority across swarm" breaks `final_wall_approved` invariant at `orchestrator.py:507` | Wall turn 2 (BLOCKED) |
| Meta-cognitive move-set market (steelman / frame-shift / constraint-audit) with budgeted moves | No halting proof; "referee model measuring semantic drift" is an unvalidated probabilistic oracle proposed to replace deterministic state machine; requires whole new orchestrator | Wall turn 2 (BLOCKED) |
| Self-Refine on Wind alone (no Wall grounding) | 2025 literature (Free-MAD, ICLR blog) warns over-confident agents degrade output; Wind self-critique without external grounding repeats the over-confidence trap | Research §10 |

These options remain accessible as future work — `path_contract` makes them prototype-able as frame variants without orchestrator surgery.

---

## 10. Research backing

- **Self-Refine** (Madaan et al.): FEEDBACK→REFINE produces ~20% absolute gain on average across tasks. The proposed Wind-consensus prompt is a direct application, with critique grounded in Wall's text rather than self-reflection.
- **ReConcile** (ACL 2024): round-table multi-LLM consensus — preserved as-is in the consensus loop.
- **Free-MAD / CortexDebate** (2025): warn that strict consensus has cost and that over-confident agents degrade output. Mitigated here by HARD/SOFT verdict tagging, which lets Wall keep authority over invariants without veto on creative direction.
- **Multi-Agent Reflexion (MAR, 2025)**: structured reflection by reference (not free prose) outperforms free reflection. The `diff` field's keyed-by-invariant requirement implements this.

References:
- [Self-Refine (arXiv 2303.17651)](https://arxiv.org/abs/2303.17651)
- [Free-MAD (arXiv 2509.11035)](https://arxiv.org/html/2509.11035v1)
- [ICLR 2025 MAD blog](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/)
- [Agent-R (arXiv 2501.11425)](https://arxiv.org/abs/2501.11425)

---

## 11. Implementation plan (if accepted)

### 11.1 Pre-build gate (must pass before any code)

| # | Task | Issue |
|---|---|---|
| 0 | **No-code prompt simulation** — pick 5 historical debates from `debates/`. Manually inject the proposed `<PATH_CONTRACTS>` block and the new prompt text (§5) into a fresh debate run, no orchestrator changes. Read whether Wind's `diff` substantively engages Wall's verdict or just restates the originals. **Gate**: if 4/5 produce restatement, the prompt design is wrong — iterate prompts and re-run before opening any other sub-issue. | [#204](https://github.com/elevanaltd/debate-hall-mcp/issues/204) |

### 11.2 Build sub-issues

| # | Task | Issue |
|---|---|---|
| 1 | Schema + types — append-only revision history per field; closed enum for invariant IDs; ownership rules (Wind→frame/diff, Wall→verdict, Door read-only) | [#196](https://github.com/elevanaltd/debate-hall-mcp/issues/196) |
| 2 | State serialization — extend `state.py` to persist `PathContract` history; backward-compatible read of pre-RFC state | [#197](https://github.com/elevanaltd/debate-hall-mcp/issues/197) |
| 3 | Prompt updates — four templates in `prompts/__init__.py`; Door's citation rule is **conditional** per §5.4 (cite every non-empty category; require reframed-or-terminal-accepted only when HARD_fail exists) | [#198](https://github.com/elevanaltd/debate-hall-mcp/issues/198) |
| 4 | Context compiler — inject `<PATH_CONTRACTS>` showing latest revision per field plus revision counts | [#199](https://github.com/elevanaltd/debate-hall-mcp/issues/199) |
| 5 | Orchestrator guards — required-content rule for `diff` (§3.2); Door citation existence check; ownership-violation check; emit validator-failure events | [#200](https://github.com/elevanaltd/debate-hall-mcp/issues/200) |
| 6 | Feature flag `tier_config.settings.path_contract_enabled` (default OFF; A/B treatment sets ON). **Rollout sequence**: flag-off in main → A/B run → review metrics → decision. No "broad ship" stage exists by design. | [#201](https://github.com/elevanaltd/debate-hall-mcp/issues/201) |
| 7 | Tests — golden files; **flag-off byte-identical to control** (hard gate); required-content rule enforced; ownership rule enforced; Door citation existence enforced; round-trip serialization | [#202](https://github.com/elevanaltd/debate-hall-mcp/issues/202) |
| 8 | A/B harness — script + operator guide for two-machine comparison; captures all metrics from §7.3 (incl. invalid contract rate, citation accuracy, originality preservation, bogus reframing) | [#203](https://github.com/elevanaltd/debate-hall-mcp/issues/203) |

Parent tracker: [#195](https://github.com/elevanaltd/debate-hall-mcp/issues/195).

Estimated scope: ~500–700 lines of code + tests, plus prompt edits and the simulation. ~2 days of focused work, with the pre-build simulation potentially adding a prompt-iteration loop before code starts.

---

## 12. Decision

Pending user review. Review feedback (2026-05-02) incorporated:
- Schema is now explicitly **append-only** with per-field revision history and ownership rules (§3.1).
- Door's citation rule is now **conditional** (cite non-empty categories; require reframe-or-terminal only when HARD_fail exists) — avoiding forced novelty (§5.4).
- Validator failures are recorded as events for measurement (§6).
- A/B metrics expanded with invalid-contract rate, citation accuracy, bogus-reframing rate, and Wind-originality-preservation regression check (§7.3).
- Flag-off byte-identity, citation accuracy, and invalid-contract rate are **hard gates** before A/B is considered valid (§7.4).
- A pre-build no-code simulation gates the build (§11.1).
