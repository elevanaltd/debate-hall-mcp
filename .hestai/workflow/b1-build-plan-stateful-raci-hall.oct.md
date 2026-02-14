===B1_BUILD_PLAN===

META:
  TYPE::BUILD_PLAN
  VERSION::"1.0"
  STATUS::RATIFIED
  FEATURE::"Stateful RACI Hall"
  ISSUE::"#163"
  PHASE::B1_HERMES_COORDINATION
  BLUEPRINT::"d3-blueprint-stateful-raci-hall.oct.md[v1.1]"
  B0_VALIDATION::"b0-validation-stateful-raci-hall.oct.md[v1.0][GO]"
  NORTH_STAR::"stateful-raci-hall-north-star.oct.md[v1.1]"
  AUTHOR::"task-decomposer[LOGOS]"
  DATE::"2026-02-14"
  ANCHOR_SID::"c5963ee6-67a9-495a-bc97-7cf50aaeae21"
  TASK_COUNT::24
  PHASE_COUNT::5
  ESTIMATED_NEW_TESTS::~94
  ESTIMATED_NEW_LOC::~1100

===

## PE_TECH_DEBT_ASSESSMENT

### TD-1: Orchestrator Refactor Creates Minimal New Debt

**Assessment:** The Phase 2 orchestrator refactor (adding `hall_context` and
`participant_providers` parameters) is additive and backward-compatible. Both
parameters default to None/{}, so no existing behavior changes. The per-spec
provider lookup inside the manifest loop (B2 amendment) replaces the single
provider pattern cleanly.

**Debt created:** Near-zero. The `_participant_providers` dict is a simple
lookup, not a complex dependency injection system. If future requirements
need provider lifecycle management (connection pooling, caching), this dict
will need wrapping in a ProviderRegistry abstraction. For V1, the dict is
sufficient.

**Recommendation:** ACCEPT. No preemptive abstraction needed. Monitor for
provider lifecycle complexity in V2.

### TD-2: parent_hall_id on DebateRoom -- Migration Debt

**Assessment:** Adding `parent_hall_id: str | None = None` and
`parent_thread_id: str | None = None` to DebateRoom creates zero migration
debt for V1. Pydantic handles missing fields with defaults. Old JSON files
load correctly.

**Debt risk:** If a future version makes these fields REQUIRED (e.g., all
debates must belong to a hall), a data migration script would be needed for
existing state files. This is unlikely for V1-V2 horizon since standalone
debates are a core use case.

**Recommendation:** ACCEPT. The Optional[str] approach is correct long-term.
Standalone debates (parent_hall_id=None) are a permanent valid state.

### TD-3: HallState Decoupling from DebateRoom

**Assessment:** The HallState model is appropriately decoupled from DebateRoom.
They share no inheritance, no embedded models. The connection is via string
references (thread_ids in active_debates/completed_debates, hall_id in
DebateRoom.parent_hall_id). This is the correct foreign-key-by-value pattern
for file-based persistence.

**Debt risk:** LOW. The only coupling point is the `load_debate_state` call
in the compression engine and hall_debate implementation. If DebateRoom's
persistence layer changes (e.g., SQLite migration), these calls would need
updating. But the interface is stable (thread_id -> DebateRoom).

**Recommendation:** ACCEPT. The decoupling is correct. No circular imports.
No shared mutation surfaces.

### TD-4: Time Bomb Dependencies -- Scale Concerns

**Assessment:** Four potential scale issues identified:

1. **Compressed log regeneration cost:** `generate_compressed_log` calls
   `load_debate_state` and `extract_decision_record` for EACH completed
   debate on every regeneration. With 100 completed debates, this involves
   100 file reads. For V1 with max_debates=20 default, this is acceptable.
   At scale (max_debates=100), this becomes a performance concern.

   **Mitigation path:** Cache decision records in HallState itself (add a
   `cached_decisions: list[dict]` field). Regeneration then only loads
   NEW completed debates. This is a Phase 2 optimization, not V1 debt.

2. **Event ledger growth:** The JSONL event ledger grows unbounded. With
   max_debates=100 and ~10 events per debate lifecycle, a hall could have
   ~1000+ events. The Smart Loader replays all events on cold start.

   **Mitigation path:** Event compaction (periodically rewrite snapshot from
   full replay, then truncate old events). The G1 benchmark in Phase 1 will
   provide data on actual replay latency. Only implement compaction if
   200ms target is missed at 200+ events.

3. **FileLock contention:** Coarse-grained hall lock serializes ALL hall
   operations. Under NR2 (single Hall instance per server), this is correct.
   Multi-Hall federation (NR2 violation) would require per-operation locks.

   **Mitigation path:** Fine-grained locks are explicitly deferred (DL4).
   No action needed for V1.

4. **Depth calculation cost:** `_calculate_depth` walks the parent_thread_id
   chain by loading DebateRoom state files. With max_depth=10, this is at
   most 10 file reads. Acceptable.

   **Mitigation path:** Cache depth on DebateRoom.parent_thread_id write.
   Only needed if depth checks become a hot path (unlikely -- only called
   on debate spawn).

**Recommendation:** ACCEPT all four. The G1 benchmark (P1T07) provides early
warning for items 1 and 2. Items 3 and 4 are bounded by configuration limits.

### TD-5: Pre-existing Technical Debt (Not Introduced by This Feature)

- **N-CE-3:** `_validate_thread_id_for_filesystem` uses weak blocklist.
  The blueprint's hall_id validator uses strict regex. Consider hardening
  thread_id validation as a SEPARATE PR (not part of this feature).

- **Existing events.py fsync gap:** events.py `append_event` lacks fsync.
  W-CE-2 notes this exists in the existing codebase too. Fixing it for
  hall events is in scope; fixing it for debate events is a SEPARATE PR.

**Recommendation:** Log both as separate issues. Do NOT scope-creep into
fixing pre-existing debt during this feature implementation.

===

## PHASE_1: Core Models and Event Infrastructure

**Blueprint refs:** S1 (Data Models), S2 (Hydrated Snapshot), S14 (Error Taxonomy)
**Files to create:** `src/debate_hall_mcp/hall.py`, `tests/unit/test_hall.py`
**Files to modify:** `src/debate_hall_mcp/state.py`
**Exit criteria:** All hall.py tests pass + G1 benchmark < 200ms + W-CE-1 through W-CE-4 defensive code + mypy clean + ruff clean

---

### P1T01: HallStatus, ParticipantKind, HallEventType Enums and Custom Exceptions
TASK_ID: P1T01
TITLE: Implement enum definitions and custom exception classes
BLUEPRINT_REF: S1.1, S1.2, S1.5, S14
DESCRIPTION: Create hall.py with the three StrEnum classes (HallStatus, ParticipantKind, HallEventType) and all custom exception classes (HallNotFoundError, HallStatusError, ParticipantNotFoundError, ParticipantActiveError, DepthLimitExceeded, DebateLimitExceeded, ActiveDebatesExistError). These are the foundational types for all subsequent tasks.
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests verifying enum values (HallStatus.OPEN == "open", etc.), enum membership, exception message formatting, and exception attribute access (e.g., HallNotFoundError("x").hall_id == "x").
GREEN: Implement all three enums with documented values and all seven exception classes with typed attributes.
REFACTOR: Ensure all enums use StrEnum consistently. Verify exception inheritance hierarchy matches S14 (HallNotFoundError extends FileNotFoundError, others extend ValueError).
DEPENDS_ON: []
CE_WARNING: None
ESTIMATED_TESTS: 5

---

### P1T02: Participant and RaciMatrix Models with Validators
TASK_ID: P1T02
TITLE: Implement Participant and RaciMatrix Pydantic models
BLUEPRINT_REF: S1.3, S1.4
DESCRIPTION: Implement the Participant model with field_validators for participant_id (strict regex) and raci_designation (R|A|C|I|None). Implement the RaciMatrix model with model_validator for responsible != accountable, consulted max 5, informed max 3, and cross-role duplicate detection.
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests for: valid Participant creation, invalid participant_id characters rejected, invalid raci_designation rejected, valid RaciMatrix, same R/A rejected, >5 consulted rejected, duplicate across roles rejected.
GREEN: Implement both models with all validators per blueprint S1.3 and S1.4 specifications.
REFACTOR: Verify validator error messages are clear. Ensure RoleConfig import from config.py works correctly for provider_config field.
DEPENDS_ON: [P1T01]
CE_WARNING: None
ESTIMATED_TESTS: 7

---

### P1T03: HallEvent Model and HallState Model with Security Validators
TASK_ID: P1T03
TITLE: Implement HallEvent and HallState models with H-001/M-001 validators
BLUEPRINT_REF: S1.6, S1.7
DESCRIPTION: Implement HallEvent with ULID event_id, timezone-aware timestamp validator, and typed payload. Implement HallState with all fields per S1.7: hall_id validator (strict regex, M-001), context_files validator (H-001: max count, absolute paths, traversal rejection, sensitive directory blocklist), bounded numeric fields (max_depth 1-10, max_context_tokens 256-32768, max_debates 1-100).
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests for: HallEvent creation with ULID, timestamp parsing (ISO string, naive datetime), HallState with valid fields, bad hall_id rejected (M-001), context_files >10 rejected (H-001), relative paths rejected, traversal rejected, sensitive directories rejected, valid absolute paths accepted.
GREEN: Implement both models with all validators matching the exact code from blueprint S1.6 and S1.7.
REFACTOR: Verify MAX_CONTEXT_FILES and MAX_CONTEXT_FILE_SIZE class constants are accessible. Ensure all field bounds match blueprint specifications.
DEPENDS_ON: [P1T02]
CE_WARNING: None (H-001 and M-001 are RESOLVED amendments, not CE warnings)
ESTIMATED_TESTS: 10

---

### P1T04: Event Reducer (apply_hall_event) with W-CE-3 Defensive Handling
TASK_ID: P1T04
TITLE: Implement pure event reducer function with defensive error handling
BLUEPRINT_REF: S2.3
DESCRIPTION: Implement the apply_hall_event pure reducer function handling all 10 HallEventType cases. Each case mutates state according to the exact logic in blueprint S2.3. W-CE-3 mitigation: wrap model construction (Participant(**event.data), RaciMatrix(**event.data["raci_matrix"])) and dict access (event.data["participant_id"]) in try/except blocks. Log warning and skip malformed events instead of crashing replay.
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests for each event type: HALL_OPENED sets status, PARTICIPANT_REGISTERED adds to registry, PARTICIPANT_UNREGISTERED removes, RACI_ASSIGNED sets designations, DEBATE_SPAWNED adds to active + sets ACTIVE, DEBATE_COMPLETED moves to completed + auto-REVIEWING if no active, CONSULTATION_COMPLETED adds to completed, CONTEXT_COMPRESSED updates log, HALL_CLOSED sets ARCHIVED, HALL_FORCE_CLOSED sets FORCE_CLOSED. Add test: malformed event data logged and skipped (W-CE-3). Add test: last_event_id and updated_at always updated.
GREEN: Implement match/case reducer with all 10 branches plus W-CE-3 defensive try/except wrapping.
REFACTOR: Verify auto-transition to REVIEWING logic (only when ACTIVE and no active_debates). Ensure RACI designation reset clears all participants before setting new ones.
DEPENDS_ON: [P1T03]
CE_WARNING: W-CE-3 (apply_hall_event defensive handling)
ESTIMATED_TESTS: 12

---

### P1T05: Event Ledger Functions (append_hall_event, load_hall_events) with W-CE-2 fsync
TASK_ID: P1T05
TITLE: Implement event ledger persistence with fsync and filesystem safety
BLUEPRINT_REF: S2.1, S2.2
DESCRIPTION: Implement helper functions: _get_halls_dir, _get_hall_lock, _get_hall_events_file, _get_hall_state_file, _validate_hall_id_for_filesystem. Implement append_hall_event with FileLock, ULID generation, and W-CE-2 mitigation (f.flush() + os.fsync(f.fileno()) after event write). Implement load_hall_events with after-filter for delta replay, and _load_hall_events_unlocked for internal use. Implement corrupt line skipping (ValidationError catch).
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests for: halls/ directory creation, append_hall_event returns HallEvent with ULID, load_hall_events returns events in order, after-filter works correctly, corrupt JSONL line skipped with warning, hall_id filesystem safety validation, thread safety (concurrent appends don't corrupt).
GREEN: Implement all persistence functions per S2.2 with W-CE-2 fsync addition.
REFACTOR: Verify FileLock paths use halls/ subdirectory consistently. Ensure _load_hall_events_unlocked does NOT acquire lock (for use within load_hall).
DEPENDS_ON: [P1T04]
CE_WARNING: W-CE-2 (fsync on event ledger append)
ESTIMATED_TESTS: 7

---

### P1T06: Smart Loader (load_hall) with W-CE-1 Corrupt Snapshot Fallback and Save Path (save_hall) with H-002
TASK_ID: P1T06
TITLE: Implement Hydrated Snapshot read path with self-healing and write path with security
BLUEPRINT_REF: S2.4, S2.5, S2.6
DESCRIPTION: Implement load_hall (Smart Loader): acquire lock, load snapshot if exists (with W-CE-1 try/except for JSONDecodeError/ValidationError fallback to events-only), load delta events, replay through reducer, flush updated snapshot, release lock. Implement save_hall (write path): acquire lock, create event, append to JSONL with fsync (W-CE-2), apply reducer, flush snapshot, release lock. Implement _save_hall_snapshot_unlocked with atomic write (tempfile + os.replace), H-002 provider_config exclusion (model_dump_json exclude), and 0o600 permissions.
TEST_FILE: tests/unit/test_hall.py
PROD_FILE: src/debate_hall_mcp/hall.py
RED: Write tests for: load from events only (no snapshot), load from current snapshot (no replay), load from stale snapshot (delta replay), load not found (FileNotFoundError), corrupt snapshot falls back to events (W-CE-1), save_hall event-first ordering, atomic write pattern, snapshot excludes provider_config (H-002), snapshot file permissions 0o600, load without provider_config in snapshot.
GREEN: Implement load_hall, save_hall, _save_hall_snapshot_unlocked per blueprint S2.4-S2.5 with W-CE-1 and W-CE-2 mitigations.
REFACTOR: Verify lock discipline matches S2.6 table. Ensure no nested locks. Verify W-CE-1 logs warning on corrupt snapshot before fallback.
DEPENDS_ON: [P1T05]
CE_WARNING: W-CE-1 (corrupt snapshot fallback), W-CE-2 (fsync in save_hall), H-002 (provider_config exclusion)
ESTIMATED_TESTS: 10

---

### P1T07: DebateRoom Extension and G1 Replay Latency Benchmark
TASK_ID: P1T07
TITLE: Extend DebateRoom with parent fields and validate replay performance
BLUEPRINT_REF: S1.8, S9.1, S10 (G1)
DESCRIPTION: Add parent_hall_id and parent_thread_id Optional[str] fields to DebateRoom in state.py. Write golden test verifying old JSON state files deserialize with both fields as None. Write G1 replay latency benchmark: generate 50, 100, 200 hall events, measure load_hall time for full replay and delta replay, assert < 200ms.
TEST_FILE: tests/unit/test_hall.py + tests/golden/test_no_regression.py
PROD_FILE: src/debate_hall_mcp/state.py
RED: Write test_existing_state_deserialization (golden test: old JSON loads with parent_hall_id=None). Write benchmark tests for 50/100/200 events.
GREEN: Add two Optional[str] fields to DebateRoom. Verify all existing 864+ tests pass unchanged. Verify G1 benchmarks pass.
REFACTOR: Confirm backward compatibility by running full existing test suite. Mark benchmark tests with @pytest.mark.benchmark if available, or use simple time.time() assertions.
DEPENDS_ON: [P1T06]
CE_WARNING: None
ESTIMATED_TESTS: 4

---

## PHASE_2: Orchestrator Refactor

**Blueprint refs:** S4 (Orchestrator Refactor), S9.2
**Files to modify:** `src/debate_hall_mcp/orchestrator.py`
**Files to create/modify:** `tests/golden/test_no_regression.py` (add orchestrator golden tests)
**Exit criteria:** All 864+ existing tests pass + new golden tests pass + hall_context injection verified + mypy clean

---

### P2T01: Golden Tests for Existing Orchestrator Behavior
TASK_ID: P2T01
TITLE: Write golden tests proving existing orchestrator behavior unchanged
BLUEPRINT_REF: S9.2, S7.5
DESCRIPTION: Write golden tests that capture the current DebateOrchestrator behavior BEFORE any modifications. These tests serve as regression guards. Test that DebateOrchestrator with no hall params produces identical behavior for run(), run_speed(), and run_raci(). These tests must PASS before any orchestrator code changes.
TEST_FILE: tests/golden/test_no_regression.py
PROD_FILE: (no changes yet)
RED: Write test_existing_orchestrator_unchanged (verify DebateOrchestrator(tier_config, state_dir) works identically). Write test_existing_raci_mode_unchanged (verify run_raci without hall context produces same output). Tests should pass immediately since no code has changed.
GREEN: Verify tests pass with existing orchestrator code.
REFACTOR: Ensure golden tests use VirtualProvider or mock providers to avoid external dependencies.
DEPENDS_ON: [P1T07]
CE_WARNING: None
ESTIMATED_TESTS: 3

---

### P2T02: Add hall_context Parameter and Injection in _execute_*_turn Methods
TASK_ID: P2T02
TITLE: Add hall_context injection to orchestrator VTP prompt assembly
BLUEPRINT_REF: S4.1, S4.2
DESCRIPTION: Add `hall_context: str | None = None` parameter to DebateOrchestrator.__init__. Add `<HALL_CONTEXT>...</HALL_CONTEXT>` injection in the VTP prompt assembly section of _execute_role_turn, _execute_speed_role_turn, and _execute_raci_role_turn. The hall_context block is inserted AFTER context_block and BEFORE state_block per S4.2 template.
TEST_FILE: tests/unit/test_orchestrator_hall.py (new file for hall-specific orchestrator tests)
PROD_FILE: src/debate_hall_mcp/orchestrator.py
RED: Write test verifying: when hall_context=None, no HALL_CONTEXT tag appears in prompt (backward compatible). When hall_context="some context", the `<HALL_CONTEXT>some context</HALL_CONTEXT>` tag appears in the enhanced_prompt before state_block. Test all three _execute_*_turn methods.
GREEN: Add hall_context parameter to __init__, store as self._hall_context. Add injection block per S4.2 in all three _execute methods. Verify golden tests still pass.
REFACTOR: Verify prompt ordering: primer -> compression -> context_block -> HALL_CONTEXT -> state_block -> user_prompt.
DEPENDS_ON: [P2T01]
CE_WARNING: None
ESTIMATED_TESTS: 4

---

### P2T03: Add participant_providers Parameter and Per-Spec Provider Lookup
TASK_ID: P2T03
TITLE: Add per-participant provider lookup in run_raci manifest loop
BLUEPRINT_REF: S4.3, S4.4
DESCRIPTION: Add `participant_providers: dict[str, ModelProvider] | None = None` parameter to DebateOrchestrator.__init__. Modify run_raci to perform per-spec provider lookup INSIDE the `for spec in manifest.specs:` loop per the B2 amendment. When participant_providers is populated, look up provider by spec.role; fallback to default wind provider. When participant_providers is empty/None, use existing single-provider behavior.
TEST_FILE: tests/unit/test_orchestrator_hall.py
PROD_FILE: src/debate_hall_mcp/orchestrator.py
RED: Write test: participant_providers={} produces same behavior as before (backward compatible). Write test: participant_providers={"alice": mock_provider_a, "bob": mock_provider_b} causes each spec to use its own provider. Write test: participant not in mapping falls back to default provider.
GREEN: Add participant_providers parameter. Move provider creation inside manifest loop with conditional lookup per S4.3.
REFACTOR: Run all 864+ existing tests. Verify golden tests pass. Verify no import cycle from ModelProvider type hint (use TYPE_CHECKING if needed).
DEPENDS_ON: [P2T02]
CE_WARNING: None
ESTIMATED_TESTS: 3

---

## PHASE_3: Hall Lifecycle and Participant Management Tools

**Blueprint refs:** S3.1-S3.5 (5 of 7 tools), S6.1, S6.2
**Files to create:** `src/debate_hall_mcp/tools/hall.py`, `tests/unit/tools/test_hall_tools.py`
**Files to modify:** `src/debate_hall_mcp/server.py`
**Exit criteria:** 5 hall tools operational + all tests pass

---

### P3T01: hall_open Tool Implementation
TASK_ID: P3T01
TITLE: Implement hall_open MCP tool
BLUEPRINT_REF: S3.1
DESCRIPTION: Implement the hall_open async function in tools/hall.py. Auto-generates hall_id from topic+date+ULID if not provided. Creates initial HallState via save_hall with HALL_OPENED event. Validates all input parameters (topic non-empty, limits in range, context_files paths, hall_id uniqueness and safety).
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: basic hall creation with defaults, custom hall_id accepted, empty topic rejected, out-of-range limits rejected, duplicate hall_id rejected (FileExistsError), return dict has correct shape (hall_id, topic, status, etc.).
GREEN: Implement hall_open per S3.1 specification. Create tools/hall.py module.
REFACTOR: Verify hall_id auto-generation format matches "hall-YYYY-MM-DD-{slug}-{ulid8}". Ensure state_dir from get_state_dir() is used consistently.
DEPENDS_ON: [P1T07]
CE_WARNING: None
ESTIMATED_TESTS: 5

---

### P3T02: hall_register and hall_unregister Tool Implementation
TASK_ID: P3T02
TITLE: Implement participant registration and unregistration tools
BLUEPRINT_REF: S3.4, S3.5
DESCRIPTION: Implement hall_register: validate hall exists and is not archived/force_closed, validate participant_id uniqueness, validate prompt_source via get_agent_prompt() if provided, validate provider_config as RoleConfig if provided, emit PARTICIPANT_REGISTERED event (H-002: exclude provider_config from event data, store only in-memory). Implement hall_unregister: validate participant exists, validate not in active debate, emit PARTICIPANT_UNREGISTERED event.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: register with defaults, register with prompt_source (mock get_agent_prompt), register with bad prompt_source rejected, duplicate participant_id rejected, register on archived hall rejected, unregister basic, unregister active participant blocked, unregister not found rejected. Verify provider_config NOT in event data (H-002).
GREEN: Implement both tools per S3.4 and S3.5 specifications.
REFACTOR: Verify slugified participant_id generation from name. Ensure provider_config stored in hall.participants[pid] in-memory but excluded from event.data.
DEPENDS_ON: [P3T01]
CE_WARNING: None (H-002 is resolved amendment, applied here)
ESTIMATED_TESTS: 8

---

### P3T03: hall_status Tool Implementation
TASK_ID: P3T03
TITLE: Implement hall_status read-only tool
BLUEPRINT_REF: S3.2
DESCRIPTION: Implement hall_status: load hall via Smart Loader, return full state dict excluding provider_config from participants (H-002). Include computed fields (debate_count, participant_count). Handle FileNotFoundError for non-existent halls.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: basic status returns full state dict, not-found hall raises FileNotFoundError, provider_config not in returned participant data, computed fields (debate_count, participant_count) correct.
GREEN: Implement hall_status per S3.2 specification.
REFACTOR: Verify return dict shape matches S3.2 specification exactly (all fields present).
DEPENDS_ON: [P3T01]
CE_WARNING: None
ESTIMATED_TESTS: 3

---

### P3T04: hall_close Tool with I5 Force-Close and I8 Enforcement
TASK_ID: P3T04
TITLE: Implement hall_close with force cascade and active debate blocking
BLUEPRINT_REF: S3.3
DESCRIPTION: Implement hall_close: validate hall exists and is not already archived/force_closed. If force=False and active_debates exist, raise ActiveDebatesExistError (I8). If force=True, cascade force_close_debate to each active child debate, then emit HALL_FORCE_CLOSED event. Normal close: generate final compressed_log, emit HALL_CLOSED event with summary. Handle already-archived error.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: basic close archives hall, close with active debates blocked (I8), force-close with active debates cascades (I5), force-close calls force_close_debate for each active child, already-archived rejected, return dict has final compressed_log.
GREEN: Implement hall_close per S3.3 specification including force cascade logic.
REFACTOR: Verify child DebateRoom states transition to FORCE_CLOSED on cascade. Ensure HALL_FORCE_CLOSED vs HALL_CLOSED event selection is correct.
DEPENDS_ON: [P3T02]
CE_WARNING: None
ESTIMATED_TESTS: 5

---

### P3T05: Register 5 Tools in server.py
TASK_ID: P3T05
TITLE: Register hall_open, hall_status, hall_close, hall_register, hall_unregister in MCP server
BLUEPRINT_REF: S6.2 (server.py modifications)
DESCRIPTION: Add tool registration for the 5 Phase 3 tools in create_server() in server.py. Import from debate_hall_mcp.tools.hall. Update tool count in docstring. Verify all 5 tools appear in MCP tool listing.
TEST_FILE: tests/unit/tools/test_hall_tools.py (add server registration test)
PROD_FILE: src/debate_hall_mcp/server.py
RED: Write test verifying all 5 new tools are registered in the MCP server (tool names appear in server tool list).
GREEN: Add imports and @server.tool() registrations for 5 tools.
REFACTOR: Verify no import cycles. Run full test suite to confirm zero regression.
DEPENDS_ON: [P3T04]
CE_WARNING: None
ESTIMATED_TESTS: 1

---

## PHASE_4: Compression Engine and Debate Integration

**Blueprint refs:** S5 (Compression Engine), S3.6 (hall_debate), S3.7 (hall_consult), S13 (Implementation Detail)
**Files to create:** `src/debate_hall_mcp/compression.py`, `tests/unit/test_compression.py`
**Files to modify:** `src/debate_hall_mcp/tools/hall.py`, `src/debate_hall_mcp/server.py`
**Exit criteria:** All 7 tools operational + compression within token budget + G2 validated

---

### P4T01: Compression Engine -- OCTAVE Templates and Token Counting
TASK_ID: P4T01
TITLE: Implement compression templates, token counter, and ContextBudgetExceeded
BLUEPRINT_REF: S5.1, S5.2, S5.3 (partial), S14 (ContextBudgetExceeded)
DESCRIPTION: Create compression.py with: HALL_CONTEXT_TEMPLATE, DECISION_TEMPLATE, ACTIVE_DEBATE_TEMPLATE, PARTICIPANT_TEMPLATE strings. Implement DEFAULT_TOKEN_COUNTER (len(text) // 4), RESERVED_BUFFER_TOKENS = 200. Implement ContextBudgetExceeded exception. Implement _extract_verdict helper function (GO/NO-GO/CONDITIONAL/fallback detection).
TEST_FILE: tests/unit/test_compression.py
PROD_FILE: src/debate_hall_mcp/compression.py
RED: Write tests for: _extract_verdict("APPROVED: ...") returns "GO", _extract_verdict("NO-GO") returns "NO-GO", _extract_verdict("CONDITIONAL ...") returns "CONDITIONAL", _extract_verdict("something else") returns first 20 chars. Write test for template string format correctness (contains ===HALL_CONTEXT=== markers).
GREEN: Implement templates, token counter, exception, and _extract_verdict per S5.2-S5.3.
REFACTOR: Verify template format matches S5.2 exactly. Ensure DEFAULT_TOKEN_COUNTER is exported for test injection.
DEPENDS_ON: [P1T07]
CE_WARNING: None
ESTIMATED_TESTS: 5

---

### P4T02: generate_compressed_log with FIFO Eviction and Token Budget
TASK_ID: P4T02
TITLE: Implement full compressed log generation with budget enforcement
BLUEPRINT_REF: S5.3, S5.4, S10 (G2)
DESCRIPTION: Implement generate_compressed_log: extract decisions from completed debates via load_debate_state + extract_decision_record, build active debate summaries, build participant summary, assemble OCTAVE template, enforce token budget with FIFO eviction (remove oldest decisions when over budget, raise ContextBudgetExceeded if still over with <=3 decisions). Support custom token_counter callable. Implement G2 validation: test with 5/10/20/40 decisions to verify budget math.
TEST_FILE: tests/unit/test_compression.py
PROD_FILE: src/debate_hall_mcp/compression.py
RED: Write tests for: empty hall (minimal output), with completed debates (decisions listed), with active debates (turn counts shown), with participants (RACI shown), output fits within max_context_tokens, FIFO eviction when over budget, ContextBudgetExceeded when even 3 decisions exceed budget, custom token counter used, missing debate file skipped gracefully, OCTAVE format markers present.
GREEN: Implement generate_compressed_log per S5.3 with complete FIFO eviction loop.
REFACTOR: Verify token budget math matches S5.4 analysis. Run G2 benchmark if tiktoken available.
DEPENDS_ON: [P4T01]
CE_WARNING: None
ESTIMATED_TESTS: 9

---

### P4T03: _calculate_depth with W-CE-4 Cycle Detection
TASK_ID: P4T03
TITLE: Implement depth calculation with visited-set cycle detection guard
BLUEPRINT_REF: S3.6 (depth calculation)
DESCRIPTION: Implement _calculate_depth function in tools/hall.py: walk parent_thread_id chain via load_debate_state to count nesting depth. W-CE-4 mitigation: add visited = set() with cycle detection (if current_parent in visited: break) and safety cap (if depth > hall_state.max_depth: break) to prevent infinite loops from data corruption.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: root debate (no parent) returns depth=0, child of root returns depth=1, grandchild returns depth=2, missing parent debate returns current depth, circular parent reference does NOT infinite loop (W-CE-4), depth exceeding max_depth breaks early.
GREEN: Implement _calculate_depth per S3.6 with W-CE-4 visited-set and max_depth safety cap.
REFACTOR: Verify function handles all edge cases without exceptions (FileNotFoundError caught gracefully).
DEPENDS_ON: [P3T01, P1T07]
CE_WARNING: W-CE-4 (_calculate_depth cycle detection)
ESTIMATED_TESTS: 5

---

### P4T04: hall_debate Tool Implementation
TASK_ID: P4T04
TITLE: Implement hall_debate with orchestrator integration and compressed log regeneration
BLUEPRINT_REF: S3.6, S13
DESCRIPTION: Implement _hall_debate_impl per the ~250-line S13 specification. Sequence: load hall, validate status/participants/depth/debate count, build RACI config, emit RACI_ASSIGNED event, create participant providers from registry, build context block from context_files (H-001 size check), generate thread_id, emit DEBATE_SPAWNED event, pre-create DebateRoom with parent_hall_id/parent_thread_id (B1 amendment), create orchestrator with hall_context and participant_providers, run debate (raci/speed/standard), on success regenerate compressed_log and emit DEBATE_COMPLETED, on failure emit DEBATE_COMPLETED with "paused" status. Wire to hall_debate async tool function.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: RACI mode debate within hall (mock orchestrator), speed mode debate, depth limit exceeded (I8), max_debates exceeded (I3), unregistered participant rejected, context injection (compressed_log passed to orchestrator), debate failure emits DEBATE_COMPLETED with paused status, DebateRoom has parent_hall_id and parent_thread_id set.
GREEN: Implement _hall_debate_impl per S13 specification exactly.
REFACTOR: Verify event emission order matches S3.6: RACI_ASSIGNED -> DEBATE_SPAWNED -> (debate) -> DEBATE_COMPLETED. Ensure hall lock released before debate execution.
DEPENDS_ON: [P4T02, P4T03, P2T03]
CE_WARNING: None
ESTIMATED_TESTS: 8

---

### P4T05: hall_consult Tool Implementation
TASK_ID: P4T05
TITLE: Implement lightweight 2-turn consultation tool
BLUEPRINT_REF: S3.7
DESCRIPTION: Implement hall_consult: validate hall status (OPEN or ACTIVE), validate consultant is registered and kind="agent", create Speed-mode DebateRoom with max_turns=2 linked to hall (parent_hall_id set), run via orchestrator, record CONSULTATION_COMPLETED event with thread_id, consultant_id, question preview, and updated compressed_log. Resolve N-CE-2 (turn count ambiguity): implement as direct provider call with question as prompt, recording result as consultation event.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/tools/hall.py
RED: Write tests for: basic consultation returns response, human consultant rejected (kind != "agent"), non-existent consultant rejected, consultation recorded in hall events, compressed_log updated after consultation.
GREEN: Implement hall_consult per S3.7 specification with N-CE-2 resolution.
REFACTOR: Verify return dict shape matches S3.7 (hall_id, thread_id, question, consultant_id, response, token_count).
DEPENDS_ON: [P4T04]
CE_WARNING: None
ESTIMATED_TESTS: 4

---

### P4T06: Register hall_debate and hall_consult in server.py
TASK_ID: P4T06
TITLE: Register remaining 2 tools in MCP server
BLUEPRINT_REF: S6.2
DESCRIPTION: Add tool registration for hall_debate and hall_consult in create_server() in server.py. Update total tool count in docstring (14 + 7 = 21). Verify all 7 hall tools appear in MCP tool listing.
TEST_FILE: tests/unit/tools/test_hall_tools.py
PROD_FILE: src/debate_hall_mcp/server.py
RED: Write test verifying all 7 hall tools are registered (supplement P3T05 test).
GREEN: Add imports and @server.tool() registrations for hall_debate and hall_consult.
REFACTOR: Verify tool count docstring updated. Run full test suite.
DEPENDS_ON: [P4T05, P3T05]
CE_WARNING: None
ESTIMATED_TESTS: 1

---

## PHASE_5: E2E Verification and Hardening

**Blueprint refs:** S7.4 (Integration Tests), S7.5 (Golden Tests), S8 (I-Compliance), S10 (Evidence Gaps)
**Files to create:** `tests/integration/test_hall_integration.py`
**Files to modify:** `tests/golden/test_no_regression.py`
**Exit criteria:** All ~958+ tests pass + quality gates clean (ruff, black, mypy) + G1/G2/G3 resolved

---

### P5T01: Full Hall Lifecycle Integration Test
TASK_ID: P5T01
TITLE: End-to-end lifecycle: open -> register -> debate -> close
BLUEPRINT_REF: S7.4 (test_full_hall_lifecycle)
DESCRIPTION: Write integration test exercising the complete happy path: hall_open, hall_register (3 agents), hall_debate (RACI mode with mock providers), verify compressed_log generated, hall_close, verify ARCHIVED status and final compressed_log. Use VirtualProvider or mock providers throughout.
TEST_FILE: tests/integration/test_hall_integration.py
PROD_FILE: (no production changes)
RED: Write test_full_hall_lifecycle asserting: hall created, 3 participants registered, debate runs and completes, compressed_log contains decision, hall closes successfully.
GREEN: Verify integration test passes end-to-end.
REFACTOR: Extract test fixtures (hall creation, participant registration) for reuse across integration tests.
DEPENDS_ON: [P4T06]
CE_WARNING: None
ESTIMATED_TESTS: 1

---

### P5T02: Nested Debate Topology Integration Test (I8)
TASK_ID: P5T02
TITLE: Test recursive topology with depth enforcement and leaf-to-root closure
BLUEPRINT_REF: S7.4 (test_nested_debate_topology), S8 (I8 compliance)
DESCRIPTION: Write integration test: root debate spawns child debate (depth=1), child spawns grandchild (depth=2). Verify depth=3 spawn is rejected (max_depth=3). Verify parent close blocked while children active. Close grandchild, then child, then root (leaf-to-root). Verify parent_thread_id chain is correct throughout.
TEST_FILE: tests/integration/test_hall_integration.py
PROD_FILE: (no production changes)
RED: Write test_nested_debate_topology asserting: root at depth 0, child at depth 1, grandchild at depth 2, depth 3 rejected, parent cannot close while child active, leaf-to-root closure succeeds.
GREEN: Verify integration test passes.
REFACTOR: Verify all DebateRooms have correct parent_hall_id and parent_thread_id.
DEPENDS_ON: [P5T01]
CE_WARNING: None
ESTIMATED_TESTS: 1

---

### P5T03: Crash Recovery and Corrupt State Integration Tests
TASK_ID: P5T03
TITLE: Test self-healing for corrupt snapshot and corrupt event ledger
BLUEPRINT_REF: S7.4 (test_crash_recovery_read_repair), W-CE-1
DESCRIPTION: Write integration test: manually corrupt the hall JSON snapshot file, call load_hall, verify it falls back to events-only reconstruction (W-CE-1). Write test: manually inject corrupt JSONL line into event ledger, verify load_hall skips corrupt line and processes remaining events correctly. Write test: simulate crash between event append and snapshot flush (delete snapshot, keep events), verify next load_hall reconstructs correctly.
TEST_FILE: tests/integration/test_hall_integration.py
PROD_FILE: (no production changes)
RED: Write test_crash_recovery_read_repair (corrupt JSON snapshot -> events-only rebuild). Write test for corrupt event line skipping. Write test for missing snapshot + valid events.
GREEN: Verify all recovery scenarios pass.
REFACTOR: Verify warning logs emitted on corrupt data detection.
DEPENDS_ON: [P5T01]
CE_WARNING: W-CE-1 (verified via integration test)
ESTIMATED_TESTS: 3

---

### P5T04: Remaining Golden Tests and Full Regression Suite
TASK_ID: P5T04
TITLE: Complete golden tests for all backward compatibility guarantees
BLUEPRINT_REF: S7.5, S9
DESCRIPTION: Write remaining golden tests not yet covered: test_existing_debate_init_unchanged, test_existing_debate_turn_unchanged, test_existing_debate_get_unchanged (includes parent_hall_id=None), test_existing_debate_close_unchanged. These verify that adding hall fields to DebateRoom and orchestrator params does NOT change any existing tool behavior.
TEST_FILE: tests/golden/test_no_regression.py
PROD_FILE: (no production changes)
RED: Write 4 golden tests per S7.5 specification.
GREEN: Verify all pass (they should, since changes are additive).
REFACTOR: Organize golden tests by domain (state, tools, orchestrator).
DEPENDS_ON: [P5T01]
CE_WARNING: None
ESTIMATED_TESTS: 4

---

### P5T05: Quality Gates and Final Verification
TASK_ID: P5T05
TITLE: Run full test suite and all quality gates
BLUEPRINT_REF: S11 (Phase 5 exit criteria)
DESCRIPTION: Run ALL tests (~958+ total: 864 existing + ~94 new). Run quality gates: ruff check (zero violations), black check (zero formatting issues), mypy strict (zero errors). Verify G1 (replay latency < 200ms), G2 (token budget math validated), G3 (zero existing test breakage). Document final test count and coverage metrics.
TEST_FILE: (all test files)
PROD_FILE: (all production files)
RED: N/A (verification task, not TDD)
GREEN: All tests pass. All quality gates clean.
REFACTOR: Fix any quality gate violations discovered. Final code cleanup.
DEPENDS_ON: [P5T04, P5T03, P5T02]
CE_WARNING: None (all W-CE-1 through W-CE-4 verified by this point)
ESTIMATED_TESTS: 0 (verification only)

---

## DEPENDENCY_GRAPH

```
P1T01 -> P1T02 -> P1T03 -> P1T04 -> P1T05 -> P1T06 -> P1T07
                                                          |
                                                          v
                                              +-----------+-----------+
                                              |           |           |
                                              v           v           v
                                           P2T01       P3T01       P4T01
                                              |           |           |
                                              v           |           v
                                           P2T02         |        P4T02
                                              |           |           |
                                              v           v           |
                                           P2T03       P3T02         |
                                              |           |           |
                                              |           v           |
                                              |        P3T03         |
                                              |           |           |
                                              |           v           |
                                              |        P3T04         |
                                              |           |           |
                                              |           v           |
                                              |        P3T05         |
                                              |           |           |
                                              +-----+-----+          |
                                                    |                 |
                                                    v                 |
                                         P4T03 <----+-----------------+
                                              |
                                              v
                                           P4T04
                                              |
                                              v
                                           P4T05
                                              |
                                              v
                                           P4T06
                                              |
                                              v
                                           P5T01
                                              |
                                    +---------+---------+
                                    |         |         |
                                    v         v         v
                                 P5T02     P5T03     P5T04
                                    |         |         |
                                    +---------+---------+
                                              |
                                              v
                                           P5T05
```

**Topological order (valid execution sequence):**
P1T01 -> P1T02 -> P1T03 -> P1T04 -> P1T05 -> P1T06 -> P1T07 ->
P2T01 -> P2T02 -> P2T03 (parallel: P3T01, P4T01) ->
P3T01 -> P3T02 -> P3T03 -> P3T04 -> P3T05 ->
P4T01 -> P4T02 -> P4T03 -> P4T04 -> P4T05 -> P4T06 ->
P5T01 -> P5T02 / P5T03 / P5T04 (parallel) -> P5T05

**Note on parallelism:** Phases 2, 3, and 4T01 can start in parallel after
P1T07 completes. However, P4T04 (hall_debate) depends on BOTH P2T03 (orchestrator
refactor) AND P3T05 (tools registered), so these must converge before Phase 4
can complete. The recommended execution is sequential for a single implementer.

===

## CRITICAL_PATH

The longest dependency chain determines minimum implementation time:

```
P1T01 -> P1T02 -> P1T03 -> P1T04 -> P1T05 -> P1T06 -> P1T07 ->
P2T01 -> P2T02 -> P2T03 ->
P4T03 -> P4T04 -> P4T05 -> P4T06 ->
P5T01 -> P5T05
```

**Critical path length: 16 tasks**

Phase 1 (7 tasks) is the longest single phase and the foundation for everything.
Phase 4 (6 tasks) is the most complex phase due to orchestrator + compression +
hall_debate integration. Phase 3 (5 tasks) runs on a parallel path that must
converge with Phase 2 before Phase 4 can complete.

**Risk mitigation:** P4T04 (hall_debate) is the highest-risk single task due to
its integration of orchestrator, compression, providers, and event emission.
The blueprint provides ~250 lines of implementation code in S13 to reduce ambiguity.
Budget extra time for this task.

===

## CE_WARNING_TRACKER

| Warning | Severity | Task(s) | Phase | Description |
|---------|----------|---------|-------|-------------|
| W-CE-1 | MEDIUM | P1T06, P5T03 | 1, 5 | Corrupt JSON snapshot fallback: try/except around json.load in load_hall, fallback to events-only reconstruction. Implemented in P1T06, verified via integration test in P5T03. |
| W-CE-2 | MEDIUM | P1T05, P1T06 | 1 | Missing fsync on event ledger append: add f.flush() + os.fsync(f.fileno()) after event write in append_hall_event (P1T05) and save_hall (P1T06). |
| W-CE-3 | LOW | P1T04 | 1 | Reducer defensive handling: wrap Participant(**event.data), RaciMatrix(**event.data["raci_matrix"]), and dict access in try/except within apply_hall_event. Log warning and skip malformed events. |
| W-CE-4 | LOW | P4T03 | 4 | _calculate_depth cycle detection: add visited=set() with cycle detection guard and max_depth safety cap in the parent_thread_id walk loop. |

**All 4 warnings are assigned to specific tasks with implementation and verification.**

===

## QUALITY_GATES

### Phase 1 Exit Gate
- [ ] All tests in test_hall.py pass (~51 tests)
- [ ] G1 benchmark: 200 event replay < 200ms
- [ ] W-CE-1 implemented (corrupt snapshot fallback)
- [ ] W-CE-2 implemented (fsync on event append)
- [ ] W-CE-3 implemented (reducer defensive handling)
- [ ] DebateRoom extension does NOT break any existing tests (864+)
- [ ] mypy clean (hall.py)
- [ ] ruff clean (hall.py)

### Phase 2 Exit Gate
- [ ] All golden tests pass (orchestrator unchanged)
- [ ] hall_context injection verified in all 3 _execute_*_turn methods
- [ ] participant_providers per-spec lookup verified
- [ ] All 864+ existing tests STILL pass (zero regression)
- [ ] mypy clean (orchestrator.py changes)

### Phase 3 Exit Gate
- [ ] 5 hall tools operational (hall_open, hall_status, hall_close, hall_register, hall_unregister)
- [ ] All 5 tools registered in server.py
- [ ] All tool tests pass (~22 tests)
- [ ] I5 force-close cascade verified
- [ ] I8 active debate blocking verified
- [ ] H-002 provider_config exclusion verified in events and status output

### Phase 4 Exit Gate
- [ ] All 7 hall tools operational
- [ ] Compression within token budget (G2 validated)
- [ ] FIFO eviction tested
- [ ] W-CE-4 implemented (_calculate_depth cycle detection)
- [ ] hall_debate integration verified (RACI + speed modes)
- [ ] hall_consult verified (N-CE-2 resolved)
- [ ] All 7 tools registered in server.py (21 total)

### Phase 5 Exit Gate (FINAL)
- [ ] All ~958+ tests pass (864 existing + ~94 new)
- [ ] ruff check: 0 violations
- [ ] black check: 0 formatting issues
- [ ] mypy strict: 0 errors
- [ ] G1 validated (replay latency)
- [ ] G2 validated (token budget)
- [ ] G3 validated (zero regression)
- [ ] All 4 CE warnings (W-CE-1 through W-CE-4) implemented and verified
- [ ] Integration tests pass (lifecycle, nesting, crash recovery)
- [ ] Golden tests pass (backward compatibility)

===

## BLUEPRINT_SECTION_COVERAGE

| Blueprint Section | Task(s) | Coverage |
|------------------|---------|----------|
| S1.1 HallStatus | P1T01 | FULL |
| S1.2 ParticipantKind | P1T01 | FULL |
| S1.3 Participant | P1T02 | FULL |
| S1.4 RaciMatrix | P1T02 | FULL |
| S1.5 HallEventType | P1T01 | FULL |
| S1.6 HallEvent | P1T03 | FULL |
| S1.7 HallState | P1T03 | FULL |
| S1.8 DebateRoom Extension | P1T07 | FULL |
| S2.1 File Layout | P1T05 | FULL |
| S2.2 Event Ledger Functions | P1T05 | FULL |
| S2.3 Event Reducer | P1T04 | FULL |
| S2.4 Smart Loader | P1T06 | FULL |
| S2.5 Save Hall | P1T06 | FULL |
| S2.6 Lock Discipline | P1T06 | FULL |
| S3.1 hall_open | P3T01 | FULL |
| S3.2 hall_status | P3T03 | FULL |
| S3.3 hall_close | P3T04 | FULL |
| S3.4 hall_register | P3T02 | FULL |
| S3.5 hall_unregister | P3T02 | FULL |
| S3.6 hall_debate | P4T03, P4T04 | FULL |
| S3.7 hall_consult | P4T05 | FULL |
| S4.1 Orchestrator init | P2T02 | FULL |
| S4.2 _execute_role_turn | P2T02 | FULL |
| S4.3 run_raci providers | P2T03 | FULL |
| S4.4 Backward compat | P2T01 | FULL |
| S5.1-S5.4 Compression | P4T01, P4T02 | FULL |
| S6 Module Structure | P3T05, P4T06 | FULL |
| S7 Test Strategy | P5T01-P5T04 | FULL |
| S8 I-Compliance | P5T01, P5T02 | FULL |
| S9 Migration | P1T07, P2T01 | FULL |
| S10 Evidence Gaps (G1-G3) | P1T07, P4T02, P5T05 | FULL |
| S11 Implementation Sequence | (entire plan) | FULL |
| S12 Imports | (each task) | FULL |
| S13 hall_debate Detail | P4T04 | FULL |
| S14 Error Taxonomy | P1T01 | FULL |

**All 14 blueprint sections (S1-S14) are mapped to at least one task.**

===

[DEPENDENCY_GRAPH]

Validated: The dependency graph forms a valid DAG with no cycles.
- 24 tasks total
- Maximum in-degree: 3 (P4T04 depends on P4T02, P4T03, P2T03)
- Maximum out-degree: 3 (P1T07 enables P2T01, P3T01, P4T01)
- Critical path: 16 tasks
- Parallelizable branches: 3 (Phase 2, Phase 3, P4T01-P4T02 can run in parallel after P1T07)

===END===
