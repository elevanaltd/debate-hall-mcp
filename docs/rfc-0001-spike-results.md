# RFC-0001 Spike Results — #204 Pre-Build Gate

**Branch**: `spike/path-contract-prompts-only`
**Date**: 2026-05-03
**Provider**: local `claude` CLI, model `claude-haiku-4-5` for Wind/Wall/Door
**Corpus**: 5 historical debates (3 in-repo + 2 added in #195/RFC v3)

## Verdict

**GATE PASSED — proceed to build sub-issues #196–#205.**

- Strict score: **4/5 PASS** (≥4/5 threshold met).
- Substance score: **5/5 PASS** — the one "fail" is a cosmetic heading mismatch on Wall's side; the underlying JSON is fully valid path_contract format with correct closed-enum values.
- Door honored the conditional HARD_fail citation rule across **all 5 debates** without exception (5/5).

## What was actually tested

Three of the four prompt changes (Wind initial frame emission, Wall verdict emission, Door synthesis citation) were tested live through the full orchestrator flow. The fourth — the **Wind consensus prompt** (RFC §5.3) — was NOT tested in this spike because all 5 debates achieved consensus on first vote (`refinement_count = 0`), so the consensus path that triggers Wind's `diff` emission never executed.

This is a real testing gap; see "Gaps and follow-up" below.

## Setup notes

The first run (`9399375`) produced 5/5 invalid transcripts: spawned `claude --print` subprocesses inherited the project cwd and responded to the parent session's environmental context (CLAUDE.md, the stop-hook output, project git state) instead of the debate topic. Diagnosed with a smoke test from `/tmp` cwd. Fixed in `bc37635` by `chdir`-ing the runner to a fresh `tempfile.mkdtemp()` before any subprocess spawning.

## Scorecard — Run 2 (the valid run)

```
========================================================================
SPIKE SCORECARD — RFC-0001 path_contract prompts
========================================================================

--- cognitive-notary-arch : FAIL (cosmetic) ---
  Wind: 3/3 headings, 3/3 JSON ids, invariants used=['halting', 'per_turn_role_contract', 're_approval', 'single_wall_coherence']
  Wall: 0/3 verdicts (used '### Path N (Label)' instead of '### PATH_CONTRACT_VERDICT (path_N)')
        but ALL JSON inside is valid: HARD_pass=2, HARD_fail=3, SOFT_disputed=2
  Door: 13 citations across [accepted, disputed, reframed]
  HARD_fail paths: [path_2, path_3] — Door honored rule for both

--- decision-governance-tiers : PASS ---
  Wind: 3/3 headings, 3/3 JSON ids, invariants used=[re_approval, single_wall_coherence]
  Wall: 3/3 verdicts, HARD_pass=0, HARD_fail=2, SOFT_disputed=1
  Door: 17 citations across [accepted, reframed]
  HARD_fail paths: [path_2, path_3] — Door honored rule for both

--- mythology-in-octave : PASS ---
  Wind: 3/3 headings, 3/3 JSON ids, invariants used=[per_turn_role_contract, single_wall_coherence]
  Wall: 3/3 verdicts, HARD_pass=0, HARD_fail=3, SOFT_disputed=1
  Door: 3 citations across [accepted, disputed, reframed]
  HARD_fail paths: [path_1, path_3] — Door honored rule for both

--- rundebate-reliability : PASS ---
  Wind: 3/3 headings, 3/3 JSON ids, invariants used=[halting, per_turn_role_contract, single_wall_coherence]
  Wall: 3/3 verdicts, HARD_pass=0, HARD_fail=2, SOFT_disputed=1
  Door: 12 citations across [accepted, disputed, reframed]
  HARD_fail paths: [path_2, path_3] — Door honored rule for both

--- virtualprovider-vs-timebudget : PASS ---
  Wind: 3/3 headings, 3/3 JSON ids, invariants used=[re_approval, single_wall_coherence]
  Wall: 3/3 verdicts, HARD_pass=0, HARD_fail=2, SOFT_disputed=1
  Door: 4 citations across [accepted, reframed]
  HARD_fail paths: [path_1, path_2] — Door honored rule for both

GATE: 4/5 strict PASS  /  5/5 substance PASS  →  PROCEED
```

## Findings

### Strong evidence the prompts work

1. **Wind frame emission is robust.** All 5 debates produced 3/3 valid `PATH_CONTRACT_FRAME` JSON blocks with `path_id`, `assumed_problem`, `success_criterion`, `accepted_failure_mode`, `hard_invariants_touched` — and **zero off-enum invariant IDs** across 49 invariant uses. The closed-enum design (locked in §8 Q1) is honored without enforcement.
2. **Wall verdict emission is robust.** All 5 debates emitted verdict blocks with valid status values from the `{HARD_pass, HARD_fail, SOFT_disputed}` enum. Zero off-enum statuses.
3. **Door's conditional HARD_fail citation rule works.** Every single HARD_fail path across all 5 debates received an `accepted` or `reframed` citation in Door's synthesis — 100% adherence to the constraint-as-catalyst proof requirement.
4. **Door uses `reframed` substantively, not as filler.** The mythology debate is a particularly clean example: Wall HARD_failed Path 3's intent-driven semantics, and Door's synthesis genuinely reframed the underlying insight as "context-aware determinism, not intent-driven variance" — which is a new third-way solution, not a restatement.

### The one cosmetic miss

The cognitive-notary debate's Wall used `### Path 1 (Obvious)` / `### Path 2 (Adjacent)` / `### Path 3 (Heretical)` as section headings, then put the same JSON shape inside. This is a prompt-clarity issue, not a model failure. The fix for #198 is to make the heading rule more emphatic, e.g., "use the literal heading `### PATH_CONTRACT_VERDICT (path_N)` exactly as written so downstream tooling can locate it."

### Gaps and follow-up

**Wind consensus prompt (RFC §5.3) is untested.** All 5 debates reached consensus on first vote, so Wind never spoke creatively in the consensus phase, and the `wind_provider.complete()` content for the approval review is not stored as a turn (only the APPROVE/REJECT vote is captured as a `CONSENSUS_VOTE` event). This is the most important prompt in the design and we have no live evidence it works.

Two ways to close this gap as part of #198:

- **A (cheaper)**: extend `_execute_consensus_loop` to write the full Wind/Wall consensus response content into the events payload (or as a special turn type). This is a small orchestrator patch; one-line change to the existing event emit. Then re-run the spike; Wind's `PATH_CONTRACT_DIFF` blocks become inspectable.
- **B (slower)**: engineer a topic on which Wall would predictably reject Door's first synthesis (e.g., a topic where Wall flags HARD constraints that Door's first synthesis doesn't address). This forces the refinement loop and the diff emission. Less reliable but doesn't require code changes.

Recommend **A** as part of #200 (orchestrator validation guards), since the same patch enables both this spike test and the production "invalid contract rate" telemetry from RFC §7.3.

### Other observations worth noting

- **Wall used HARD_fail far more than HARD_pass** (10 HARD_fail vs 2 HARD_pass across 4 well-formatted debates). This is consistent with Wall's role as constraint enforcer but may be a sign that Haiku-4.5 over-weights pessimism. Worth watching in the A/B test (#203) — if HARD_fail rates differ materially between control and treatment, that's a signal.
- **Door citation density varied widely**: from 3 citations (mythology) to 17 (decision-governance). Both are valid — mythology had a tight 3-citation synthesis; governance had a longer treatment of all three categories per path. The conditional citation rule produces appropriate-density output.
- **Run timing**: 5 debates × Wind→Wall→Door turns, all reaching consensus on turn 1, took ~864s total (~14 min wall clock) on Haiku via local CLI. Per-debate range: 108s (virtualprovider) to 289s (decision-governance).

## Decision

Per the gate criteria in issue #204 (≥4/5 PASS):

✅ **Gate passed.** Build sub-issues #196–#205 are unblocked.

The four prompt edits in this spike (in `prompts/__init__.py`) feed directly into #198 — they are the prompts the build implements. The only follow-up recommended for #198 is making Wall's verdict heading rule more emphatic to avoid the cosmetic miss seen in cognitive-notary-arch.

## Artifacts

- **Branch**: `spike/path-contract-prompts-only`
- **Prompt edits**: `src/debate_hall_mcp/prompts/__init__.py` (commit `9399375`)
- **Runner**: `scripts/spike_pathcontract_runner.py`
- **Scorer**: `scripts/score_spike.py`
- **Raw transcripts**: `debates/spike-pathcontract/*.json` (force-added on this branch as evidence)
- **Tier config used**: `tiers.yaml` (gitignored, local only — uses `provider: cli, cli: claude, model: claude-haiku-4-5` for all three roles)
