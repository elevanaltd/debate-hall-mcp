# debate-hall-mcp: Deep-Dive Quality Report

## Context
Follow-up to prior audit. Combines earlier recommendations with deeper source review to harden safety, integrity, and operability.

## Findings & Recommendations

1) **Enforce mediated picks & role validity**
- `debate_pick` explicitly notes it is “informational only” and does not persist the chosen role, so mediated debates can be bypassed by calling `debate_turn` with any role. Add an `expected_next_role` field to `DebateRoom`, persist picks, and reject mismatches in `debate_turn` for mediated mode. Also validate `role` against the `VALID_ROLES` set for both modes so malformed inputs cannot enter the ledger. 【F:src/debate_hall_mcp/tools/pick.py†L20-L77】【F:src/debate_hall_mcp/tools/turn.py†L18-L113】

2) **Verify the hash chain on load (tamper detection)**
- `load_debate_state` trusts on-disk JSON and never recomputes or validates turn hashes, so silent edits bypass the append-only guarantee. Recalculate hashes on load and fail-fast if any link breaks before returning a `DebateRoom`. 【F:src/debate_hall_mcp/state.py†L186-L206】

3) **Add immutable audit trail for tombstones and force-closes**
- Tombstoning overwrites content in-place and force-close only updates status; neither records who/why in an append-only way. Emit an auxiliary audit entry (e.g., `audits/THREAD.log`) capturing actor, reason, timestamp, and pre/post hashes to preserve accountability without mutating history. 【F:src/debate_hall_mcp/tools/admin.py†L16-L109】

4) **Require synthesis semantics in the engine**
- `DebateEngine.close_debate` assumes the caller provided synthesis for `SYNTHESIS` but does not enforce it; a blank synthesis could be recorded if future callers bypass the tool-level check. Guard inside the engine so the invariant holds regardless of entrypoint. 【F:src/debate_hall_mcp/tools/close.py†L11-L45】【F:src/debate_hall_mcp/engine.py†L107-L141】

5) **Harden persistence writes**
- State is written with a single `open(..., "w")` call; interrupted writes can leave a truncated JSON that `load_debate_state` will happily parse as corrupted but “valid” structure. Write to a temp file and `rename` atomically, and consider fsync to disk for durability on crashes. 【F:src/debate_hall_mcp/state.py†L163-L206】

6) **Normalize cognition/role pairing**
- `debate_turn` validates cognition content but never ensures `role` aligns with its intended archetype (Wind/PATHOS, Wall/ETHOS, Door/LOGOS). Add a map and block mismatched pairings in strict mode to prevent callers from bypassing the behavioral firewall semantics. 【F:src/debate_hall_mcp/tools/turn.py†L18-L113】

7) **Preserve remediation context when tombstoning**
- Tombstoning replaces content but does not emit a derived hash of the removed content, making remediation unverifiable. Store a `tombstone_hash` or ciphertext of the original turn so future audits can attest redactions without reintroducing the sensitive text. 【F:src/debate_hall_mcp/tools/admin.py†L60-L109】

## Genius Insights
- **Integrity beacons for cross-instance attestation:** In addition to per-turn hashes, derive a rolling “room seal” (e.g., Merkle root + cumulative HMAC keyed by a deployment secret) after each mutation and persist it alongside state. On load, recompute both the hash chain and the seal; on save, optionally emit the seal to an external transparency log (or envoy sidecar) so separate MCP instances can mutually attest to ledger freshness and detect forked histories even if disk is tampered. 【F:src/debate_hall_mcp/state.py†L163-L206】
- **Capability-bound turn receipts (new):** Mint a short-lived, signed capability token at `debate_init` and require it on every mutating tool call; embed the token ID into each `Turn` for non-repudiation. This prevents unauthorized tool invocations, ties turns to authenticated initiators, and creates verifiable receipts without adding heavyweight auth infrastructure. 【F:src/debate_hall_mcp/tools/init.py†L32-L101】【F:src/debate_hall_mcp/tools/turn.py†L18-L113】
