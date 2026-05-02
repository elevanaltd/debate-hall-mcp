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

Add a single typed field, **`path_contract`**, attached to each Wind path. It is **mutated, not replaced** by each role as the path traverses Wind → Wall → (consensus-Wind) → Door. No new turn types, no new orchestrator phases.

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
    hard_invariants_touched: list[HardInvariant]

class InvariantVerdict(TypedDict):
    status: Literal["HARD_pass", "HARD_fail", "SOFT_disputed"]
    rationale: str

class PathDiff(TypedDict):
    accepted: list[str]      # invariant keys Wind now accepts
    disputed: list[str]      # SOFT keys Wind still pushes back on, with rationale
    reframed: list[str]      # invariant keys whose reframing opens a new possibility

class PathContract(TypedDict):
    path_id: str
    frame: PathFrame                          # written by Wind (turn 1)
    verdict: dict[str, InvariantVerdict]      # written by Wall (turn 2), keyed by invariant
    diff: PathDiff | None                     # written by Wind in consensus phase
```

### 3.2 Lifecycle

| Stage | Role | Field written | Notes |
|---|---|---|---|
| 1 | Wind | `frame` per path | Includes `hard_invariants_touched` from a closed enum (safer; see §8 Q1) |
| 2 | Wall | `verdict[invariant]` | Per path, every invariant Wind flagged is scored HARD_pass / HARD_fail / SOFT_disputed |
| 3 | Door | (reads only) | Initial synthesis; can be skipped for A/B variant where Wind always re-engages |
| 4+ | Wind (consensus) | `diff` | Must reference Wall's verdict entries by invariant key. **Empty `diff` is invalid** when any HARD_fail exists. |
| 4+ | Door (refinement) | (reads full contract history) | Synthesis must cite ≥1 `accepted`, ≥1 `disputed`, ≥1 `reframed` entry across paths |

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

> Your synthesis must cite **at least one** `accepted` entry, **at least one** `disputed` entry, and **at least one** `reframed` entry across the paths' contracts. This forces genuine integration — averaging or compromise will fail validation.

---

## 6. Orchestrator changes

Minimal. Only two:

1. **`PathContract` is part of the debate state**, persisted alongside transcripts. The `<DEBATE_STATE>` block in prompts includes a `<PATH_CONTRACTS>` sub-block with the contracts to date.
2. **Validation guard** in `_execute_consensus_loop` (`orchestrator.py:482-560`): when Wind votes (line 485), assert that for every path with `verdict` entries containing `HARD_fail`, the corresponding `diff` is non-empty. If empty → reject the Wind output and retry once before treating it as a malformed turn (existing error path).

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

Qualitative (blind review by the user, ideally double-blind):
- **Synthesis novelty** — does Door's output contain ideas not present verbatim in Wind's initial paths? (Treatment should win.)
- **Constraint-as-catalyst evidence** — count of Door synthesis claims that cite a `reframed` path_contract entry.
- **Provenance auditability** — can a reader trace each Door claim to a role contribution?

### 7.4 Decision rule

Ship treatment if: (a) qualitative novelty wins ≥60% of blind comparisons, (b) stalemate rate doesn't increase, (c) token cost increase <40%. Otherwise iterate or revert.

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

| # | Task | Issue |
|---|---|---|
| 1 | Schema + types (`PathContract`, `PathFrame`, `InvariantVerdict`, `PathDiff`, `HardInvariant`) — default-empty so existing flows degrade gracefully | [#196](https://github.com/elevanaltd/debate-hall-mcp/issues/196) |
| 2 | State serialization — extend `state.py` to persist contracts alongside transcripts | [#197](https://github.com/elevanaltd/debate-hall-mcp/issues/197) |
| 3 | Prompt updates — four templates in `prompts/__init__.py` (Wind initial, Wall, Wind consensus, Door) | [#198](https://github.com/elevanaltd/debate-hall-mcp/issues/198) |
| 4 | Context compiler — inject `<PATH_CONTRACTS>` sub-block into `<DEBATE_STATE>` | [#199](https://github.com/elevanaltd/debate-hall-mcp/issues/199) |
| 5 | Orchestrator guard — validation in `_execute_consensus_loop` for non-empty `diff` when HARD_fail exists | [#200](https://github.com/elevanaltd/debate-hall-mcp/issues/200) |
| 6 | Feature flag `tier_config.settings.path_contract_enabled` (default off; A/B treatment sets on) | [#201](https://github.com/elevanaltd/debate-hall-mcp/issues/201) |
| 7 | Tests — golden files; flag-off byte-identity; HARD_fail forces non-empty diff; Door cites all three diff categories | [#202](https://github.com/elevanaltd/debate-hall-mcp/issues/202) |
| 8 | A/B harness — script + operator guide for the two-machine comparison | [#203](https://github.com/elevanaltd/debate-hall-mcp/issues/203) |

Parent tracker: [#195](https://github.com/elevanaltd/debate-hall-mcp/issues/195).

Estimated scope: ~400–600 lines of code + tests, plus prompt edits. ~1–2 days of focused work.

---

## 12. Decision

Pending user review.
