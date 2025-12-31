# Enforcement Hardening - Orchestration Prompt

## Context

This prompt guides implementation of 5 enforcement hardening issues derived from the PR #34 quality review debate (2025-12-31). Wind (Gemini/ideator), Wall (Codex/validator), and Door (Claude/synthesizer) reached consensus on build order and priorities.

## Prerequisites

Load ho-mode and orchestration skills:
```
/bind ho
/skill ho-mode
/skill ho-orchestrate
```

## Build Order (Sequential Dependencies)

| Order | Issue | Title | Depends On |
|-------|-------|-------|------------|
| 1 | #36 | Cognition/role normalization | - |
| 2 | #37 | Mediated picks enforcement | #36 |
| 3 | #38 | Synthesis semantics in engine | #37 |
| 4 | #39 | Atomic persistence | #38 |
| 5 | #40 | Audit trail + tombstone context | #39 |

## Orchestration Strategy

### For Each Issue

1. **Create worktree branch**
   ```bash
   git worktree add ../issue-{N}-{short-name} -b issue-{N}-{short-name}
   ```

2. **Delegate to implementation-lead**
   - IL must load `/skill build-execution` for TDD discipline
   - IL implements RED→GREEN→REFACTOR cycle
   - Each commit must be atomic and pass CI

3. **Quality gates (delegate to specialists)**
   - code-review-specialist (CRS) via Codex for review
   - critical-engineer (CE) via Gemini for validation
   - test-methodology-guardian for test integrity

4. **Merge sequence**
   - PR per issue
   - Merge in order (don't merge #37 before #36)
   - Update PROJECT-CONTEXT after each merge

## Issue-Specific Guidance

### #36: Cognition/Role Normalization
**Key files:** `validation.py`
**Approach:** Add ROLE_COGNITION_MAP, check in validate(), WARN default, BLOCK strict
**Risk:** Breaking existing debates - ensure backward compat for None cognition

### #37: Mediated Picks Enforcement
**Key files:** `state.py`, `pick.py`, `turn.py`
**Approach:** Add `expected_next_role` field, persist on pick, enforce on turn
**Risk:** Deadlocks if expected role not initialized - handle None case

### #38: Synthesis Semantics
**Key files:** `close.py`, `validation.py`
**Approach:** Call LOGOS validation on synthesis content before closing
**Risk:** Breaking close for existing debates - WARN first, don't BLOCK

### #39: Atomic Persistence
**Key files:** `state.py`
**Approach:** tempfile + rename pattern, optional fsync
**Risk:** Platform differences - test on both macOS and Linux

### #40: Audit Trail + Tombstone Context
**Key files:** `state.py`, `admin.py`
**Approach:** AuditEvent model, audit_log field, preserve tombstone_hash
**Risk:** Schema migration for existing debates - handle missing field

## Deferred Work

**Hash chain verification** is BLOCKED until tombstone architecture is redesigned. The current tombstone implementation mutates content, which would break hash verification.

After #40 lands, create follow-up issue for:
- Append-only tombstone records
- Hash chain verification on load
- "Genius insights" from PR #34

## Success Criteria

- [ ] All 5 issues implemented and merged in order
- [ ] All tests passing (94+ tests, 90%+ coverage)
- [ ] No regressions in existing functionality
- [ ] PROJECT-CONTEXT updated with new implementation status
- [ ] Ready for release

## Notes

- HO coordinates, IL implements
- Never skip TDD (RED→GREEN→REFACTOR)
- Each issue is a separate PR for clean history
- Debate transcript: `debates/2025-12-31-pr34-quality-review.json`
