===D3_04_SECURITY_REVIEW===

META:
  TYPE::SECURITY_REVIEW
  VERSION::"1.0"
  STATUS::COMPLETE
  FEATURE::"Stateful RACI Hall"
  ISSUE::"#163"
  PHASE::D3_SECURITY_GATE
  BLUEPRINT::"d3-blueprint-stateful-raci-hall.oct.md[v1.0]"
  NORTH_STAR::"stateful-raci-hall-north-star.oct.md[v1.1]"
  REVIEWER::"security-specialist[ETHOS]"
  REVIEWED_AT::"2026-02-14"
  PERMIT_SID::"4a8c50de-3a3b-44e0-b30e-97d776caad83"

===

## VERDICT::CONDITIONAL_PASS

The D3 Blueprint demonstrates strong security fundamentals across the majority
of its attack surface. Path traversal, state integrity, lock discipline, and I5
compliance are well-designed. However, three findings require remediation before
implementation proceeds to B0. Two are HIGH severity (context_files arbitrary
file read, provider_config secret persistence) and one is MEDIUM (hall_id
validation gap). None are CRITICAL.

Conditional on remediation of HIGH findings H-001 and H-002, the blueprint is
approved for implementation.

===

## FINDINGS

### H-001::HIGH — Arbitrary File Read via context_files

VULNERABILITY_CLASS::CWE-22 (Path Traversal) / CWE-552 (Files Accessible to External Party)

EVIDENCE::
- Blueprint S13 (lines 2293-2302): `hall_debate` reads arbitrary file paths from `context_files` using `Path(fpath).read_text(encoding="utf-8")` and injects content directly into agent prompts via `<FILE path="{fpath}">` tags.
- Blueprint S3.1 (line 918): `hall_open` accepts `context_files` as a list of absolute paths. Validation note says "context_files paths must be absolute if provided" but no actual validation implementation is specified.
- The `context_files` field is stored in HallState (S1.7 line 369-372) as `list[str]` with no validator.
- There is NO path restriction, NO allowlist, NO directory jail. A caller can set `context_files: ["/etc/passwd", "/root/.ssh/id_rsa", "~/.env"]` and the full contents will be injected into debate agent prompts.

IMPACT::
- Server-Side File Read (SSRF-like): Any MCP client calling `hall_open` can read arbitrary files on the server's filesystem, subject only to the process owner's permissions.
- Secret Exfiltration: Files containing secrets (API keys, credentials, SSH keys, environment files) can be read and injected into agent prompts, where they may be echoed back through turn content or sent to external LLM providers via OpenRouter.
- Data Leakage to Third Parties: If OpenRouterProvider is used, file contents are sent to external API endpoints.

RECOMMENDATION::
1. Add a `field_validator("context_files")` to HallState that validates:
   - All paths are absolute (reject relative paths)
   - All paths resolve within an allowlist of directories (e.g., the `state_dir` or project root)
   - No path contains `..` traversal sequences after resolution
   - No path points to sensitive directories (`/etc`, `~/.ssh`, `~/.config`, etc.)
2. Add a maximum file size limit (e.g., 64KB) to prevent memory exhaustion.
3. Add a maximum file count limit (e.g., 10 files) to prevent prompt injection volume attacks.
4. Consider a dedicated "context registry" that validates paths at registration time rather than read time.

---

### H-002::HIGH — Provider Config Secret Persistence in State

VULNERABILITY_CLASS::CWE-312 (Cleartext Storage of Sensitive Information) / CWE-532 (Insertion of Sensitive Information into Log File)

EVIDENCE::
- Blueprint S1.3 (line 164-167): `Participant.provider_config` is typed as `RoleConfig | None`. RoleConfig (from `config.py` line 26+) can contain provider credentials: the `openrouter` provider type requires an API key resolved from environment, and `cli_args` can contain arbitrary key-value pairs.
- Blueprint S3.4 (line 1083): The spec explicitly notes "provider_config is NOT included in event data to avoid persisting secrets" -- this is a correct defensive measure for the event ledger.
- HOWEVER: The Participant model is embedded in HallState (S1.7 line 342-344): `participants: dict[str, Participant]`. HallState is persisted to JSON at `{state_dir}/halls/{hall_id}.json` via `_save_hall_snapshot_unlocked` (S2.5 lines 854-874) using `state.model_dump_json(indent=2)`.
- This means `provider_config` (including any inline API keys or sensitive cli_args) IS persisted in the snapshot JSON file, even though it is excluded from the event ledger.
- The snapshot file is world-readable by default (no explicit file permissions set).

IMPACT::
- API keys or sensitive provider configuration persisted in plaintext JSON on disk.
- The snapshot is written repeatedly (on every write path and read-repair). Multiple copies may exist in temp files if crashes occur.
- Any process with filesystem access to `state_dir` can read provider credentials.

RECOMMENDATION::
1. Exclude `provider_config` from snapshot serialization. Use `model_dump_json(exclude={"participants": {"__all__": {"provider_config"}}})` or mark the field with `exclude=True` in Pydantic.
2. Store provider_config in a separate in-memory registry that is reconstructed from `hall_register` calls at load time, or use a dedicated encrypted secrets store.
3. At minimum, set restrictive file permissions (0o600) on all snapshot and event files.
4. Document that API keys should be passed via environment variables (existing pattern in OpenRouterProvider), not inline in `provider_config`.

---

### M-001::MEDIUM — hall_id Validation Allows Characters Unsafe for Cross-Platform Use

VULNERABILITY_CLASS::CWE-20 (Improper Input Validation)

EVIDENCE::
- Blueprint S1.7 (lines 384-393): `validate_hall_id` checks only for `..`, `/`, and `\` patterns.
- Compare with `validate_participant_id` (S1.3 lines 181-192): uses a strict regex `^[a-zA-Z0-9_-]+$`.
- The hall_id validator allows spaces, special characters (e.g., `$`, `%`, `*`, `|`, `<`, `>`, control characters, Unicode), and NUL bytes. These can cause cross-platform filesystem issues, shell injection in log messages, or JSONL parsing anomalies.
- Existing `_validate_thread_id_for_filesystem` in state.py (line 614-628) uses the same weak pattern-blocklist approach.

IMPACT::
- On Windows, characters like `<`, `>`, `|`, `"`, `?`, `*` are invalid in filenames and will cause `OSError`.
- Hall IDs with shell metacharacters could be exploited if hall_id values are interpolated into log messages, error messages, or diagnostic scripts.
- Unicode or control characters in hall_id could cause JSONL parsing issues in the event ledger.

RECOMMENDATION::
1. Apply the same strict regex validation used for `participant_id`: `^[a-zA-Z0-9_-]+$`.
2. Also apply this to the auto-generated hall_id format in `hall_open` (S3.1 lines 2306-2310) -- the `safe_topic` slugification already filters characters, but explicitly validate the composed result.
3. Consider applying the same strict regex to `_validate_thread_id_for_filesystem` in state.py as a hardening measure for existing code.

---

### M-002::MEDIUM — apply_hall_event Reducer Trusts Event Data Without Validation

VULNERABILITY_CLASS::CWE-502 (Deserialization of Untrusted Data)

EVIDENCE::
- Blueprint S2.3 (lines 576-677): The `apply_hall_event` reducer directly constructs models from event data using `Participant(**event.data)` (line 602) and `RaciMatrix(**event.data["raci_matrix"])` (line 610).
- The event ledger is an append-only JSONL file on disk. If an attacker gains write access to the file (or if a corrupt/crafted event is injected), the reducer will blindly apply it.
- Specific risk: A crafted `PARTICIPANT_REGISTERED` event could inject a participant with arbitrary `provider_config` that overrides intended providers, or with a `participant_id` containing special characters (since the reducer bypasses the `field_validator` on `Participant.id` only if the data is pre-validated -- Pydantic DOES validate on construction, so this specific vector is mitigated by Pydantic validators).

IMPACT::
- If an attacker can append to the JSONL file, they can inject arbitrary participants, change RACI assignments, or manipulate hall state via crafted events.
- Pydantic validation on model construction (Participant, RaciMatrix) provides some defense-in-depth here. Invalid data will raise `ValidationError`.
- The `load_hall_events` function (S2.4 lines 780-793) already catches `ValidationError` for corrupt lines, which provides partial mitigation.

RECOMMENDATION::
1. Wrap `Participant(**event.data)` and `RaciMatrix(**event.data["raci_matrix"])` in try/except `ValidationError` within the reducer, logging and skipping invalid events rather than crashing.
2. Consider adding a basic event signature or checksum to the HallEvent model (similar to the Turn hash chain) to detect tampering. This is a V2 enhancement.
3. Set restrictive file permissions (0o600) on event ledger files to reduce the attack surface for direct file injection.

---

### M-003::MEDIUM — No Event Append fsync Guarantees

VULNERABILITY_CLASS::CWE-367 (TOCTOU Race) / Durability Gap

EVIDENCE::
- Blueprint S2.2 (lines 508-514): `append_hall_event` opens the file in append mode and writes, but does NOT call `f.flush()` or `os.fsync(f.fileno())` before releasing the lock.
- Compare with `_save_hall_snapshot_unlocked` (S2.5 lines 866-869) which correctly does `f.flush()` + `os.fsync(f.fileno())`.
- Compare with existing `save_debate_state` in state.py (lines 750-754) which also correctly fsyncs.
- The event ledger is the source of truth ("Ledger is Truth; File is Checkpoint"). If the event is written to OS buffer but the process crashes before the buffer is flushed to disk, the event is lost but the snapshot may reflect it (since the snapshot IS fsynced in the write path).

IMPACT::
- On crash between event write (buffered) and snapshot write (fsynced), the snapshot could be ahead of the ledger. The Smart Loader would see no delta events and return the snapshot state, which includes an event that no longer exists in the ledger.
- This violates the "Ledger is Truth" governing principle.
- Risk is low in practice (OS buffers are typically flushed quickly, and debate operations are infrequent), but it breaks the correctness invariant.

RECOMMENDATION::
1. Add `f.flush()` and `os.fsync(f.fileno())` after the `f.write()` call in `append_hall_event` and in the `save_hall` event append code block (S2.5 line 843).
2. Apply the same pattern to existing `append_event` in events.py (line 221) which has the same gap.

---

### L-001::LOW — Compressed Log Injection into Agent Prompts

VULNERABILITY_CLASS::CWE-74 (Injection) / Prompt Injection

EVIDENCE::
- Blueprint S4.2 (lines 1372-1374): Hall context is injected via `<HALL_CONTEXT>\n{self._hall_context}\n</HALL_CONTEXT>`. The `compressed_log` content is derived from debate syntheses and topic strings that were produced by LLM agents.
- If a malicious agent produces a synthesis containing `</HALL_CONTEXT>` followed by injected instructions, it could escape the XML-tagged boundary and inject arbitrary prompt content for subsequent debate participants.

IMPACT::
- Low practical impact because: (a) all participants in a hall are configured by the hall operator; (b) synthesis content is already visible in the transcript; (c) MCP clients typically trust the server's prompt assembly.
- Nevertheless, this is a defense-in-depth concern for multi-tenant scenarios.

RECOMMENDATION::
1. Sanitize the `compressed_log` content before injection by escaping or stripping XML-like tags (`<`, `>`) that could conflict with the `<HALL_CONTEXT>` delimiter.
2. Alternatively, use a delimiter that is unlikely to appear in natural text (e.g., `===HALL_CONTEXT===` / `===END_HALL_CONTEXT===`, which aligns with existing OCTAVE patterns).

---

### L-002::LOW — Depth Calculation DoS via Deep Parent Chain Walk

VULNERABILITY_CLASS::CWE-400 (Uncontrolled Resource Consumption)

EVIDENCE::
- Blueprint S13 (lines 1234-1248): `_calculate_depth` walks the `parent_thread_id` chain by calling `load_debate_state` for each ancestor. This loads JSON files from disk in a while loop.
- With max_depth=10, this could mean 10 file reads per `hall_debate` call. If state files are large or on slow storage, this adds latency.
- The chain walk has no cycle detection. If a bug or file corruption creates a circular parent_thread_id reference, this becomes an infinite loop.

IMPACT::
- Low severity. max_depth is capped at 10 (HallState validator), limiting the walk to 10 iterations maximum.
- A circular reference bug would cause an infinite loop, but this requires data corruption rather than external attack.

RECOMMENDATION::
1. Add a `max_iterations` guard (e.g., `max_depth + 1`) to the while loop in `_calculate_depth` to prevent infinite loops.
2. Track visited `thread_id` values to detect cycles explicitly:
```python
visited = set()
while current_parent is not None:
    if current_parent in visited:
        raise IntegrityError(f"Circular parent chain at {current_parent}")
    visited.add(current_parent)
    depth += 1
    ...
```

---

### L-003::LOW — hall_id Auto-Generation Leaks Timing via ULID Suffix

VULNERABILITY_CLASS::CWE-200 (Information Exposure)

EVIDENCE::
- Blueprint S13 (lines 2306-2310): Auto-generated `thread_id` uses `str(ULID())[:8].lower()` as suffix. ULIDs encode millisecond timestamps, so the first 10 characters encode creation time.
- Using only the first 8 characters means the full timestamp is truncated, but the date portion is already in the `YYYY-MM-DD` prefix, so this is largely redundant.

IMPACT::
- Negligible. Creation timing is not sensitive data in this context. The `created_at` timestamp is already a public field on HallState.

RECOMMENDATION::
- INFORMATIONAL only. No action required. Documenting for completeness.

---

### I-001::INFORMATIONAL — Lock Mechanism Mismatch Between Hall and Debate Subsystems

EVIDENCE::
- Blueprint S2 uses `FileLock` (from `filelock` library) for hall operations.
- Existing state.py uses `fasteners.InterProcessReaderWriterLock` for debate state operations.
- Blueprint S12 (line 2114) explicitly notes: "fasteners (not needed for hall; hall uses filelock directly)".
- Two different locking libraries with different semantics are now in use within the same codebase.

IMPACT::
- No direct security impact since hall locks and debate locks operate on separate file paths (different directories: `halls/` vs root `state_dir/`).
- Potential confusion for future developers regarding which locking pattern to use.
- `filelock` provides only exclusive locks; `fasteners` provides reader/writer locks. Hall operations cannot benefit from concurrent reads.

RECOMMENDATION::
- INFORMATIONAL. Consider standardizing on one library in a future refactoring. The blueprint's choice of `filelock` for coarse-grained hall operations is acceptable given that hall operations are infrequent (DL4 rationale).

---

### I-002::INFORMATIONAL — No Rate Limiting on Hall Tool Calls

EVIDENCE::
- No rate limiting or throttling is specified for any of the 7 new MCP tools.
- An aggressive MCP client could call `hall_open` repeatedly to create thousands of halls, consuming disk space and file descriptors.

IMPACT::
- Denial of service via resource exhaustion is possible in theory but mitigated by: (a) the MCP protocol is typically used in trusted client-server configurations; (b) NR2 specifies "one Hall instance per server process for V1".

RECOMMENDATION::
- INFORMATIONAL for V1. Consider adding hall count limits or rate limiting for V2 multi-tenant scenarios.

===

## SECURITY_AREA_ASSESSMENT

### 1. Path Traversal (hall_id and participant_id)

ASSESSMENT::MEDIUM (Partially Adequate)

- `participant_id`: COMPLIANT. Strict regex `^[a-zA-Z0-9_-]+$` (S1.3 line 187). This is the gold standard.
- `hall_id`: MEDIUM risk. Blocklist approach (S1.7 lines 390-392) is insufficient. See M-001.
- `thread_id` (existing): Uses same weak blocklist in `_validate_thread_id_for_filesystem` (state.py line 82-83, 614-628). Existing risk, not introduced by this blueprint.
- Existing `save_debate_state` and `load_debate_state` both call the validator. Good.

### 2. Injection Risks (topic, name, compressed_log)

ASSESSMENT::LOW (Adequate with Caveats)

- `topic`: No length limit specified in `hall_open` beyond `min_length=1` on HallState. The `safe_topic` slugification in auto-generated IDs (S13 line 2308) correctly filters characters.
- `name`: Bounded at 128 characters (S1.3 line 155). Good.
- `compressed_log`: Generated server-side by `generate_compressed_log` (S5.1-S5.3), not directly user-controlled. Individual field values (topic, verdict, constraint) are truncated. See L-001 for prompt injection concern.
- `context_files`: HIGH risk. See H-001.

### 3. State Integrity (Hydrated Snapshot exploitation)

ASSESSMENT::LOW (Adequate)

- The Hydrated Snapshot pattern (S2.3-S2.4) derives state from the event ledger via a pure reducer function. The snapshot is a cache, not the source of truth.
- The Smart Loader (S2.4) performs read-repair: if the snapshot is stale, delta events are replayed. If the snapshot is corrupt, full reconstruction from events is possible.
- The reducer uses Pydantic model construction (`Participant(**event.data)`, `RaciMatrix(**event.data["raci_matrix"])`) which provides input validation. See M-002 for error handling improvement.
- Event injection requires filesystem write access. File locking prevents concurrent corruption from legitimate processes. See M-003 for fsync gap.

### 4. Lock Security (FileLock DoS, stale locks)

ASSESSMENT::LOW (Adequate)

- Hall operations use coarse-grained `FileLock` (S2.6). The lock scope is well-defined per operation type.
- "No nested locks" (S2.6 line 886): Hall lock and debate lock are never held simultaneously. This eliminates deadlock risk by design.
- The `with lock:` context manager pattern ensures lock release on exceptions.
- `filelock.FileLock` handles stale locks: if the process holding the lock crashes, the OS releases the file lock (on POSIX). On Windows, this depends on OS behavior.
- No explicit lock timeout is specified. A hung process holding the hall lock would block all hall operations indefinitely. This is a low risk given the single-process model (NR2).
- RECOMMENDATION: Consider adding a `timeout` parameter to FileLock acquisition (e.g., `lock.acquire(timeout=30)`) for defense against unexpected hangs.

### 5. Data Exposure (provider_config with API keys)

ASSESSMENT::HIGH (Requires Remediation)

- Event ledger: GOOD. Blueprint explicitly excludes `provider_config` from event data (S3.4 line 1083).
- Snapshot JSON: BAD. `provider_config` is persisted in the snapshot via HallState.participants serialization. See H-002.
- `hall_status` tool return: The spec (S3.2 lines 970-979) does NOT include `provider_config` in the return dict. GOOD.
- OpenRouter provider reads API keys from environment variables (`OPENROUTER_API_KEY`). If a user passes the key inline in `provider_config.cli_args`, it would be persisted.

### 6. I5 Compliance (Sovereign Safety Override)

ASSESSMENT::COMPLIANT

- `hall_close(force=True)` (S3.3 lines 1005-1041): Force-closes all active debates. Emits `HALL_FORCE_CLOSED` event. Transitions to FORCE_CLOSED status.
- HallStatus includes `FORCE_CLOSED` as a terminal state (S1.1 line 115).
- `FORCE_CLOSED` and `ARCHIVED` halls reject all mutation operations (register, unregister, debate spawn).
- Existing `force_close_debate` tool continues to work for individual debates within or outside halls.
- Force-close cascades to child debates: the blueprint specifies "cascade_close_active_debates" in the hall_close return description.
- The I5 implementation is correct and complete. The kill switch operates at both hall level and individual debate level.

### 7. Concurrency Safety (Race conditions)

ASSESSMENT::LOW (Adequate with M-003 caveat)

- Hall write path (S2.5): Event append + reducer + snapshot flush all under single `FileLock`. Atomic.
- Hall read path (S2.4): Load snapshot + delta replay + snapshot flush all under single `FileLock`. Atomic.
- Child debate operations use independent locks (`{thread_id}.lock`). No cross-lock dependencies.
- The "release hall lock BEFORE spawning child debate" pattern (S2.6 line 887) prevents lock escalation deadlocks.
- Between hall lock release and DEBATE_COMPLETED event (S13 lines 2336-2396), another process could modify hall state. This is handled by re-loading hall state: `hall = load_hall(hall_id, state_dir)` before emitting DEBATE_COMPLETED.
- See M-003 for the fsync gap that could violate "Ledger is Truth" invariant on crash.

### 8. Input Validation (MCP tool inputs)

ASSESSMENT::LOW (Adequate)

- `hall_open`: topic min_length=1 validated. max_depth bounded [1,10]. max_context_tokens bounded [256,32768]. max_debates bounded [1,100]. All via Pydantic Field validators.
- `hall_register`: name bounded [1,128]. kind validated against enum. participant_id strict regex. provider_config validated as RoleConfig.
- `hall_debate`: mode validated against string set. participant IDs cross-referenced against registry. depth checked against max_depth. Debate count checked against max_debates.
- `hall_consult`: question must be non-empty. consultant_id must be registered and kind="agent".
- `hall_close`: force is boolean. hall must exist and not be terminal.
- `hall_unregister`: participant must be registered and not active.
- Overall validation coverage is thorough. The main gap is `context_files` (H-001) and `hall_id` format (M-001).

===

## COMPLIANCE_MATRIX::I5_SOVEREIGN_SAFETY_OVERRIDE

| Requirement | Blueprint Mechanism | Status |
|-------------|-------------------|--------|
| Hall-level kill switch | `hall_close(force=True)` emits `HALL_FORCE_CLOSED`, cascades to active debates | COMPLIANT |
| Terminal state enforcement | `FORCE_CLOSED` status rejects all mutations | COMPLIANT |
| Debate-level kill switch preserved | Existing `force_close_debate` tool unchanged | COMPLIANT |
| Audit trail for force-close | `HALL_FORCE_CLOSED` event in JSONL ledger | COMPLIANT |
| Status transition correctness | `ANY -> FORCE_CLOSED` transition allowed (S1.1 line 108) | COMPLIANT |
| No circumvention via hall isolation | Force-close operates on hall state directly, not through debate channels | COMPLIANT |
| I5 constraint text | "System governance supersedes Agent autonomy always" | ENFORCED by hall_close force path bypassing I8 active debate checks |

OVERALL_I5::COMPLIANT

===

## FINDINGS_SUMMARY

| ID | Severity | Title | Remediation Required |
|----|----------|-------|---------------------|
| H-001 | HIGH | Arbitrary File Read via context_files | YES - Before B0 |
| H-002 | HIGH | Provider Config Secret Persistence in Snapshot | YES - Before B0 |
| M-001 | MEDIUM | hall_id Validation Allows Unsafe Characters | YES - During Phase 1 |
| M-002 | MEDIUM | Reducer Trusts Event Data Without Error Handling | YES - During Phase 1 |
| M-003 | MEDIUM | No fsync on Event Ledger Append | YES - During Phase 1 |
| L-001 | LOW | Compressed Log Prompt Injection | Recommended |
| L-002 | LOW | Depth Calculation Cycle Detection Missing | Recommended |
| L-003 | LOW | hall_id Auto-Generation Leaks Timing | Informational |
| I-001 | INFORMATIONAL | Lock Library Mismatch | No action required |
| I-002 | INFORMATIONAL | No Rate Limiting | No action required |

CRITICAL_COUNT::0
HIGH_COUNT::2
MEDIUM_COUNT::3
LOW_COUNT::3
INFORMATIONAL_COUNT::2

===

## GATE_DECISION

VERDICT::CONDITIONAL_PASS

CONDITIONS::[
  1::"Remediate H-001 (context_files path restriction) in the blueprint before B0",
  2::"Remediate H-002 (provider_config snapshot exclusion) in the blueprint before B0",
  3::"M-001, M-002, M-003 may be addressed during Phase 1 implementation"
]

NEXT_STEP::"Design-architect updates blueprint with H-001 and H-002 remediation, then proceeds to B0 validation gate"

===END===
