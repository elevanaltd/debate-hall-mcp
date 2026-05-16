# Debate #5 — Door Synthesis (Consensus Phase, simulated)

**Invocation**: `mcp__pal__clink` cli_name=claude role=door-agent
**Model**: claude-opus-4-6
**Duration**: 130.8s
**Prompt source**: `src/debate_hall_mcp/prompts/__init__.py::format_door_consensus_prompt` (verbatim, with `rejector="Wind"` and a simulation framing note explaining that there is no prior Door synthesis)
**Inputs**: PATH_CONTRACTS block from `05-governance-path-contracts.md` + Wind diff from `05-governance-wind-diff.md`
**Note**: Door's first sentence flags that the underlying debate-hall thread refused the synthesis turn (Wind-first fixed mode); Door delivered the synthesis as text output without `add_turn` persistence. This does NOT invalidate the synthesis content — it is a process artefact of running clink against a fresh thread.

---

## Raw Door output

The debate was just initialized so it expects Wind first in fixed mode. Since this is a simulation where prior turns are external, I'll record the synthesis directly. The content is the deliverable — let me present it.

---

## DOOR (LOGOS) — Consensus-Phase Synthesis

### THEREFORE...

The evidence converges on a **Gravity-Tiered Governance Model** with three tiers, where ADR-0060 is honoured by scoping — not circumventing — its mandate, and where mechanization is gated by proof-of-enforcement rather than human intent. Uniform ceremony is dead; graduated ceremony, machine-verified at the lowest tier, is the emergent structure.

---

### TENSION_ANALYSIS

| Wind's Position | Wall's Position | The Tension |
|-----------------|-----------------|-------------|
| Path 1: Apply ADR-0060 uniformly — every decision gets Issue + ADR | Token cost (20x penalty) and process proportionality (ceremony overkill for zero-gravity decisions) are structural failures | Strict compliance vs. operational viability |
| Path 2: Tier by gravity — only ARCHITECTURAL gets Issues | All HARD invariants pass, but format decoupling is SOFT_disputed — is an OCTAVE node a legitimate ADR? | Substantive compliance vs. textual literalism |
| Path 3: Encode mechanizable rules, delete docs entirely | Documentation drift risk is HARD_fail — delete-first creates orphaned undetected rules | Mechanization efficiency vs. visibility during transition |

---

### CONSTRAINT-AS-CATALYST PROOF

#### Path 1: Two HARD_fails — one terminal, one reframed

**[path_1.accepted: process_proportionality]** — Wind accepts this as terminal and unreframeable. The terminal_rationale is precise: "Uniform ceremony cannot accommodate variable gravity without becoming either wasteful or hollow." This is not a fixable flaw; it is the structural insight that *gravity varies*, which is the seed of the tiered model itself. The failure of uniformity is the birth of graduation.

**[path_1.reframed: token_efficiency]** — Wind's ADR-INDEX.md proposal (single consolidated file, ~4000 tokens, strict ADR-0060 compliance preserved) genuinely dissolves the 20x token penalty *without* path_2's format decoupling. This is a real third option: path_1 with storage consolidation rather than path_2 with format decoupling. However, because process_proportionality remains terminally failed, this reframe cannot save path_1. **The synthesis absorbs this insight differently**: the storage consolidation principle (monolith over scatter) carries forward into the tiered model's OCTAVE monolith design, validating that a single-file approach is structurally superior for agent consumption.

**[path_1.disputed]** — Empty. Wind raised no disputes on path_1's verdicts; Wall's assessments were accepted as floor.

#### Path 2: No new divergence; SOFT dispute sharpened

**[path_2.disputed: format_decoupling_legitimacy]** — Wind's argument is textual entailment, not creative reinterpretation: ADR-0060's own title scopes it to "Architectural Decision Records"; non-architectural decisions are not ADRs; therefore ADR-0060 is *silent on them by design*. This dissolves the SOFT_disputed status from "defensible but contestable" to "correct by the standard's own terms."

**Path 2 had no new divergence** (`divergence_marker: NO_NEW_DIVERGENCE`); all HARD invariants pass and the original frame stands. No `accepted` or `reframed` entries exist — their absence is structural (nothing was broken to fix or reframe).

#### Path 3: One HARD_fail reframed, one SOFT dispute reinforced

**[path_3.reframed: documentation_drift_risk]** — Wind's SHADOW workflow is the constraint-as-catalyst proof for path_3. Instead of delete-then-encode (which Wall correctly HARD_failed), the doc persists with `SHADOW::PENDING_MECHANIZATION` status until CI *proves* enforcement exists. The machine gatekeeps deletion — the doc is consumed by proof, not removed by intent.

**[path_3.disputed: ADR_0060_compliance]** — If a mechanized rule has architectural consequences, the gravity heuristic scores it 1+ and routes it to TIER::ARCHITECTURAL, so it never reaches TIER::MICRO. The `not_applicable` exemption only applies to rules that are both mechanizable AND zero-gravity. Wall's concern is real but self-resolving under the classification heuristic.

**[path_3.accepted]** — Empty. Wind disputed or reframed all of path_3's tensions rather than accepting any as terminal.

---

### EMERGENT_PATH

**Key Insight**: The three paths are not alternatives — they are layers of a single graduated structure. Path_1's terminal failure reveals that gravity must vary. Path_2's clean HARD_pass set provides the tiered skeleton. Path_3's SHADOW reframe provides the mechanization protocol for the lowest tier. Path_1's storage consolidation insight validates the monolith form factor.

**Third Way: Gravity-Tiered Governance with Machine-Gated Mechanization**

| Tier | Gravity | Ceremony | Storage | ADR-0060 |
|------|---------|----------|---------|----------|
| **ARCHITECTURAL** | Cross-system consequences, data-ownership, irreversible commitments | GitHub Issue (number-matched) + OCTAVE node with `ISSUE_REF` | `DECISIONS.oct.md` monolith | **Fully governed** |
| **CONVENTION** | Team-wide effect, no architectural consequence | OCTAVE node inline, no Issue | `DECISIONS.oct.md` monolith | **Out of scope** — non-architectural decisions are not ADRs per ADR-0060's title-scoped mandate |
| **MICRO** | Mechanizable rules enforceable by tooling | `SHADOW::PENDING_MECHANIZATION` until CI proves enforcement → auto-archive | `DECISIONS.oct.md` → archive on proof | **Not applicable** — enforcement IS the record |

---

### IMPLEMENTATION

1. **Classification heuristic** (< 30 seconds):
   - **Mechanization test**: Expressible as linter/CI/schema/config? → candidate MICRO.
   - **Gravity test**: Score on cross-system consequence (0/1), data-ownership (0/1), irreversibility (0/1). Score ≥ 1 → ARCHITECTURAL (gravity overrides mechanizability). Score 0 + mechanizable → MICRO. Score 0 + not mechanizable → CONVENTION.
   - **Ceremony**: ARCHITECTURAL → Issue + OCTAVE node with `ISSUE_REF`. CONVENTION → OCTAVE node inline. MICRO → OCTAVE node with `SHADOW::PENDING_MECHANIZATION` + backlog ticket.

2. **SHADOW workflow for TIER::MICRO**:
   - Node in `DECISIONS.oct.md` carries `SHADOW::PENDING_MECHANIZATION` and `ENFORCEMENT_TARGET` (e.g., "eslint rule: kebab-case-filenames").
   - CI scans SHADOW nodes: enforcement exists and passes? → auto-transition to `SHADOW::MECHANIZED`, move to `DECISIONS-ARCHIVE.oct.md`. Not yet? → node stays visible as backlog.
   - **No human deletes a SHADOW doc.** The machine consumes it via proof.

3. **Monolith storage** (absorbing path_1's consolidation insight):
   - All active decisions in single `DECISIONS.oct.md` (~3500–5000 tokens for 100 decisions).
   - Archived MICRO decisions post-mechanization in `DECISIONS-ARCHIVE.oct.md` — accessible but off the agent's hot path.
   - ARCHITECTURAL nodes carry `ISSUE_REF: #NNN` for GitHub audit traversal.

4. **ADR-0060 compliance stance**:
   - ARCHITECTURAL: fully compliant — Issue exists, ADR node exists, numbers match.
   - CONVENTION: out of scope — ADR-0060 governs *Architectural* Decision Records; conventions are not architectural.
   - MICRO: not applicable — mechanized enforcement supersedes documentation; SHADOW ensures no gap during transition.

---

### WHAT_THIS_ENABLES

1. **1+1=3 emergence**: Neither path_2 alone (no mechanization protocol) nor path_3 alone (orphaned rules risk) produces a complete system. The SHADOW workflow from path_3's reframe, grafted onto path_2's tiered skeleton, creates a self-healing model where docs are either permanent (ARCHITECTURAL/CONVENTION) or transitional-with-proof (MICRO). The monolith form from path_1's reframe ensures agent efficiency regardless of tier.

2. **Zero orphaned rules**: SHADOW eliminates path_3's original HARD_fail — rules are never undocumented AND unenforced because documentation persists until enforcement is proven by CI.

3. **ADR-0060 honoured by scope, not circumvention**: Wind's textual-entailment argument [path_2.disputed: format_decoupling_legitimacy] means this model applies ADR-0060 exactly where the standard's own name says it applies and is silent where the standard is silent.

4. **Process proportionality**: Ceremony tracks consequence. A kebab-case naming rule gets a SHADOW node and a linter ticket. A data-ownership boundary gets a GitHub Issue and full audit trail.

---

### CITATION COMPLETENESS (Door's own table)

| Path | accepted | disputed | reframed | divergence |
|------|----------|----------|----------|------------|
| path_1 | `process_proportionality` (terminal) | empty — noted | `token_efficiency` | n/a |
| path_2 | empty — noted | `format_decoupling_legitimacy` | empty — noted | `NO_NEW_DIVERGENCE` |
| path_3 | empty — noted | `ADR_0060_compliance` | `documentation_drift_risk` | n/a |

All non-empty categories cited. All HARD_fail paths have either accepted-terminal or reframed entries cited. No fabricated entries for empty categories.

---

Note (Door's own closing remark): The `add_turn` call failed because the thread was freshly initialized and expects Wind first in fixed mode — the prior Wind/Wall turns exist in the external simulation thread `2026-04-28-decision-record-governance-for-01kqa2vb`, not in this debate-hall instance. The synthesis content above is the deliverable.
