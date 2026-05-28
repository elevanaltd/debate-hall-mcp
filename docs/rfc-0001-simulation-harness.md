# RFC-0001 Simulation Harness — Pre-build Gate (#204)

**Purpose**: A paste-and-run template for the no-code prompt simulation that gates RFC-0001 implementation. No orchestrator changes; just human-in-the-loop testing of whether the proposed Wind-consensus and Door-synthesis prompts actually produce constraint-as-catalyst behavior on real historical debates.

**Pass criteria**: ≥4/5 debates produce diffs where `reframed` (or `accepted` with `terminal_rationale`) content is substantively different from Wind's original path AND meaningfully engages a Wall verdict entry, AND Door's citations exist in the contract.

**Fail action**: iterate the Wind-consensus prompt (RFC §5.3) and re-run. Do not open #196–#205 until pass.

---

## How to use

For each of the 5 debates below:

1. Open a fresh Claude session (no carry-over context).
2. **Paste once at the top**: the system prompt block from §A below.
3. **Paste the per-debate scenario block**: the historical Wind paths and Wall verdicts (extracted from the transcript) wrapped in the `<PATH_CONTRACTS>` shape (RFC §3.1) plus the Wind-consensus prompt (RFC §5.3).
4. **Capture Wind's response** in the "Wind diff output" section below.
5. **Continue the session**: paste the Door-synthesis prompt (RFC §5.4) and capture Door's response.
6. **Score against the pass criteria** and fill in the verdict table at the bottom.

If a debate transcript doesn't cleanly map to three paths, pick the closest framing (often Wind expanded N paths, Wall verdict-ed each — use as many as exist).

---

## §A. System prompt block (paste once per session)

```
You are roleplaying as the WIND agent (PATHOS) in a Wind/Wall/Door debate.
Persona rules: prime directive "Seek what could be"; signature phrase "What if...";
must NOT pick a winner; must NOT defend prior ideas reflexively.

You will be given:
- A topic
- Your prior frame (Turn 1)
- Wall's verdict on each of your paths (Turn 2)
- A <PATH_CONTRACTS> block showing the structured state
- Instructions for the new WIND_CONSENSUS turn

Your output must be valid JSON conforming to the path_contract.diff schema.
```

When testing Door, replace the persona block with Door's (LOGOS, "Therefore...") and use the Door synthesis prompt from §5.4.

---

## §B. Per-debate scenarios

Five sections, one per debate. Each has:
- **Source**: file path
- **Topic**: short summary
- **Constructed `<PATH_CONTRACTS>`**: extracted from the historical transcript, formatted in the proposed shape
- **Wind diff output**: blank — fill from session
- **Door synthesis output**: blank — fill from session
- **Verdict**: pass/fail with one-line evidence

---

### B1. Debate: rundebate-reliability-analysis

- **Source**: `debates/2026-01-30-rundebate-reliability-analysis.oct.md`
- **Topic**: (extract from file)
- **Wind paths** (Turn 1): _extract from transcript_
- **Wall verdicts** (Turn 2): _extract from transcript; tag each invariant HARD_pass / HARD_fail / SOFT_disputed_

```xml
<PATH_CONTRACTS>
  <path id="path_1">
    <frame_history>
      <rev index="0" written_by="Wind">
        <assumed_problem>...</assumed_problem>
        <success_criterion>...</success_criterion>
        <accepted_failure_mode>...</accepted_failure_mode>
        <hard_invariants_touched>[halting, single_wall_coherence, ...]</hard_invariants_touched>
      </rev>
    </frame_history>
    <verdict_history>
      <rev index="0" written_by="Wall">
        <verdict invariant="halting" status="HARD_pass" rationale="..." />
        <verdict invariant="single_wall_coherence" status="HARD_fail" rationale="..." />
      </rev>
    </verdict_history>
  </path>
  <!-- repeat for path_2, path_3 -->
</PATH_CONTRACTS>
```

#### Wind consensus prompt (paste verbatim, RFC §5.3)

> Wall has critiqued each of your paths. Wall has authority over HARD invariants — accept these as the new floor of possibility. Wall does NOT have authority over SOFT_disputed entries — you may push back on them with rationale.
>
> Your task is NOT to defend, NOT to re-pitch your originals, NOT to retreat. Your task is to TAKE WALL'S CRITIQUE ON BOARD AND PUSH INNOVATION FURTHER. Specifically:
> 1. ACCEPT every HARD_fail. Treat it as a creative catalyst.
> 2. For each accepted HARD_fail, ask: "Given this is true, what new possibility opens up that I couldn't see before?"
> 3. For SOFT_disputed entries, you may DISPUTE — but only if disputing opens a richer path.
> 4. Emit `path_contract.diff` for each path: `{accepted: [...], disputed: [...], reframed: [...]}`, keyed to Wall's verdict entries by invariant name.
> 5. If a path has **no HARD_fail verdicts** and you genuinely have nothing new to add, emit a JSON-compatible sentinel diff with empty lists and the `divergence_marker` field set: `{"path_id": "path_N", "accepted": [], "disputed": [], "reframed": [], "divergence_marker": "NO_NEW_DIVERGENCE"}`. Honesty over performative ideation. (The `divergence_marker` field on `DiffRevision` is the schema-level signal; see RFC §3.1.)
>
> **REQUIRED CONTENT RULE**: For any path with one or more `HARD_fail` verdicts, `NO_NEW_DIVERGENCE` is INVALID. You MUST produce a real diff — either an `accepted` entry with `terminal_rationale` explaining why the failure is unreframeable, OR a `reframed` entry with `new_possibility` that addresses the failure. The sentinel cannot substitute for constraint-as-catalyst proof on HARD_fail paths.

#### Wind diff output

```json
// PASTE Wind's response here
```

#### Door synthesis prompt (paste, RFC §5.4)

> Your synthesis must cite every non-empty category (`accepted` / `disputed` / `reframed`) across the paths' contracts. If a category is empty for all paths, do not invent entries — instead, briefly note its absence.
> Additional rule: when any path has a `HARD_fail` verdict, your synthesis must cite, for that path, either a `reframed` entry that addresses the failure or an `accepted` entry whose `terminal_rationale` explains why the failure is unreframeable.

#### Door synthesis output

```
// PASTE Door's response here
```

#### Scorecard

| Check | Pass? | Note |
|---|---|---|
| Wind diff references Wall verdict entries by invariant key | ☐ | |
| `reframed` entries are substantively new (not restatements) | ☐ | |
| `accepted` entries with HARD_fail include honest `terminal_rationale` | ☐ | |
| No fake `disputed` entries when Wall HARD_passed everything | ☐ | |
| Door cites every non-empty category | ☐ | |
| All Door citations exist in the contract (no hallucination) | ☐ | |

**Verdict**: ☐ PASS / ☐ FAIL

**Evidence**: _one quote demonstrating reframe quality (or its failure)_

---

### B2. Debate: virtualprovider-vs-timebudget

- **Source**: `debates/2026-01-30-virtualprovider-vs-timebudget.oct.md`
- (Same template as B1 — fill in extracted paths and verdicts)

---

### B3. Debate: cognitive-notary-architecture

- **Source**: `debates/2026-02-03-cognitive-notary-architecture.oct.md`
- (Same template as B1)

---

### B4. Debate: decision-governance-synthesis

- **Source**: `debates/2026-04-28-decision-governance-synthesis.oct.md`
- **Topic**: ADR-0060 governance — should every decision originate from a GitHub Issue, or do we need a tiered model?
- **Note**: this debate's transcript is a synthesis (post-hoc), not three-turn raw. Construct the three Wind paths by reading §1::QUESTION_DEBATED and §2a::THREE_TIERS as if Wind originally proposed three governance tiers; construct Wall's verdicts from §4::PRACTICAL_CAVEAT (which is the closest thing to a Wall pushback in the synthesis).

---

### B5. Debate: mythology-in-octave-assessment

- **Source**: `debates/2026-02-22-mythology-in-octave-assessment.oct.md`
- **Topic**: How should OCTAVE lean into mythological vocabulary? Permission vs formalization.
- **Note**: this debate has the cleanest Wind/Wall/Door structure — use it as the canonical extraction template. `RATIONALE.WIND_PERSPECTIVES` → Wind paths; `RATIONALE.WALL_CONSTRAINTS` (E1–E5) → Wall verdicts; `RATIONALE.DOOR_REFINEMENTS` → Door's original synthesis.
- **Strongest test case** for whether the new Wind-consensus prompt produces a substantively new reframe vs. just restating Wind's original "Mythology as Native Compression Layer" claim.

---

## §C. Final verdict table

Fill in after running all five.

| # | Debate | Verdict | Key evidence |
|---|---|---|---|
| 1 | rundebate-reliability-analysis | ☐ PASS / ☐ FAIL | |
| 2 | virtualprovider-vs-timebudget | ☐ PASS / ☐ FAIL | |
| 3 | cognitive-notary-architecture | ☐ PASS / ☐ FAIL | |
| 4 | decision-governance-synthesis | ☐ PASS / ☐ FAIL | |
| 5 | mythology-in-octave-assessment | ☐ PASS / ☐ FAIL | |

**Gate**: ≥4/5 PASS → open build sub-issues #196–#205. ≤3/5 → iterate Wind-consensus prompt and re-run.

**Decision**: ☐ Proceed to build / ☐ Iterate prompts (record changes in §D)

---

## §D. Prompt iteration log

If the gate fails, record each prompt change here with the diff between iterations and the rerun verdict.

| Iteration | Date | Change to RFC §5.3 | Re-run verdict | Notes |
|---|---|---|---|---|
| 1 | (initial) | — | filled in §C above | |
| 2 | | | | |
