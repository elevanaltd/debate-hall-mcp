# Debate #4 — Door consensus-phase synthesis (clink output)

**Clink**: `mcp__pal__clink` cli_name=claude role=door-agent
**Model**: claude-opus-4-6
**Duration**: 147.3s
**Session**: d700c91a-7cf8-4538-af29-6839de4852cb

The prompt body was the topic + `<DEBATE_STATE>` (same upstream content as the Wind clink + Wind's three PATH_CONTRACT_DIFF blocks + Wind's synthesis guidance) + the `format_door_consensus_prompt` text verbatim, with `rejector="Wind"` and `feedback` populated with Wind's diff summary and synthesis guidance (the natural mapping since Wind APPROVEd-with-guidance rather than REJECTing in the strict sense, but the consensus-phase prompt is the right shape to enforce the path-contract citation rule).

## Door's full response

> The thread doesn't exist in this worktree's state directory. The debate state was provided inline in the prompt, so I'll deliver the synthesis directly as my response.

---

## DOOR (LOGOS) — Refined Synthesis

### THEREFORE...

The optimal architecture for debate-hall-mcp is a **three-layer stack where each layer composes atop the one below**, not three alternatives competing for selection. Layer 0 (Primitives) is the singular ledger write-path. Layer 1 (Recipes) orchestrates primitives into debate patterns. Layer 2 (Query) presents `resolve_question()` as the recommended entry point for decision-memory retrieval. Path 3 is dead — statelessness and audit-completeness are mutually exclusive, full stop.

---

### PATH CONTRACT CITATIONS

**Path 1** had no new divergence; original frame stands. Both HARD_pass verdicts (north_star_identity, ledger_write_path_singularity) confirm that primitives already ARE the singular write-path in the current codebase — `init_debate`, `add_turn`, `close_debate` form the atomic operations through which all state mutations flow [path_1.divergence_marker: NO_NEW_DIVERGENCE].

**Path 2** — Wind disputes Wall's SOFT_disputed verdict on cognitive_state_isolation [path_2.disputed: cognitive_state_isolation]. Wind's argument is structurally sound: `resolve_question()` generates a unique thread_id per call, instantiates a fresh `DebateRoom` with its own file-locked persistence, and shares no cached state between invocations. The isolation is architectural (per-thread-id file separation + reader/writer locks + CAS retry), not accidental. I accept Wind's dispute — `resolve_question()` already satisfies I1 shared-nothing semantics by construction. This removes the need for defensive isolation machinery and clears the path to promote it as the primary query surface.

No constraints were reframed across any path — Wind accepted Wall's verdicts where they held and disputed on evidence where they didn't.

**Path 3** — Wind terminally accepts all three HARD_fail verdicts:
- [path_3.accepted: north_star_identity] — §1 identity is constitutive: the product IS debate orchestration; stripping it to a notary removes the reason the server exists. Any re-addition of orchestration converges back to P1.
- [path_3.accepted: ledger_write_path_singularity] — Without server-side state there is no ledger. Any attempt to reframe a stateless server into one that validates requires holding state — which exits the stateless premise. Self-cancelling.
- [path_3.accepted: audit_trail_completeness] — Audit completeness and statelessness are mutually exclusive in an adversarial model. You cannot verify what you cannot remember. The physics is terminal.

Path 3 is honestly dead. No reframe survives because the constraints are self-cancelling against the premise.

---

### TENSION ANALYSIS

| Wind's Position | Wall's Position | The Tension |
|-----------------|-----------------|-------------|
| MCP's value is trust infrastructure, not orchestration. Promote `resolve_question()` as primary surface returning DecisionRecord. | Primitives must remain the singular write-path (I4). Cognitive isolation must not bleed across queries (I1). | How to elevate a high-level query tool without undermining the primitive layer that guarantees integrity? |

### EMERGENT PATH

**Key Insight**: The tension dissolves when we recognize these are LAYERS, not alternatives. `resolve_question()` does not bypass primitives — it composes them. Each layer adds value without violating the layer below:

- **Layer 0 (Primitives)**: `init_debate`, `add_turn`, `close_debate`, `get_debate`, `pick_next_speaker`, `tombstone_turn`. These are the ONLY write-path to the ledger. Every mutation flows through `add_turn`'s hash-chain append. This is I4 incarnate.

- **Layer 1 (Recipes)**: `run_debate`, `resume_debate`, `consult`, `convene`. These orchestrate Layer 0 calls into patterns. `run_debate` calls `init_debate` → N×`add_turn` → `close_debate`. No recipe writes state except through Layer 0.

- **Layer 2 (Query)**: `resolve_question`, `extract_decision_record`, `search_decisions`. These compose Layer 1 orchestration and return structured decision artifacts. `resolve_question()` is the recommended entry point for clients who want a decision, not a debate.

**Third Way**: The layered stack means clients choose their entry point based on control needs — not that one layer replaces another. Fine-grained control users call Layer 0 directly. Most users call Layer 2 and get a `DecisionRecord` with full provenance.

---

### IMPLEMENTATION

1. **Document layer boundaries explicitly** — Each tool's docstring and the MCP tool listing should declare its layer membership (L0/L1/L2). The server registration in `server.py` should group tools by layer with clear section comments.

2. **Promote `resolve_question()` as recommended entry** — Client documentation and tool descriptions should guide new users to Layer 2 first. Description: "Recommended entry point for decision queries. Returns a DecisionRecord with answer, alternatives, rationale, and cryptographic provenance."

3. **Enforce layer discipline in code** — Layer 2 tools MUST call Layer 1 orchestration (never write state directly). Layer 1 recipes MUST call Layer 0 primitives (never bypass `add_turn` for state writes). This is already true in the current implementation; make it a tested invariant.

4. **Resolve the I1 dispute definitively** — Add an integration test proving `resolve_question()` shares no state between concurrent calls (parallel invocations with distinct topics produce isolated rooms with no cross-contamination). This converts Wind's structural argument into CI-enforced evidence.

5. **Acknowledge P3's death in ADR** — Record in the project's decision log that stateless-notary was evaluated and rejected on terminal grounds (audit-completeness requires server-side persistence; the constraints are self-cancelling).

---

### WHAT THIS ENABLES

The layered architecture creates emergence that neither "primitives only" nor "query only" achieves alone:

- **Composability without sacrifice**: Power users get raw primitives; most users get decisions. Neither group is second-class.
- **Auditability at every grain**: Layer 2 returns a `DecisionRecord` carrying `transcript_hash` — the hash chain from Layer 0 proves the decision's derivation without requiring the client to manage turns manually.
- **Trust escalation**: A client can start at Layer 2, inspect the DecisionRecord, and if skeptical, drop to Layer 0 to verify individual turns against the hash chain. Trust is earned through transparency, not demanded through opacity.
- **Future extensibility**: New recipes (Layer 1) and new query surfaces (Layer 2) compose freely without touching the integrity layer. The primitive layer is stable; innovation happens above it.
