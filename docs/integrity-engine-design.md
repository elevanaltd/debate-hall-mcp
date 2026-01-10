# Integrity Engine Design

**Status**: Research & Design Phase
**Created**: 2026-01-10
**Author**: Research Analysis based on empirical git data

## Executive Summary

The Integrity Engine is a specialized debate mode for resolving "Coherence vs. Velocity" conflicts. It enables emergency bypasses with mandatory debt tracking, preventing the "broken windows" effect while maintaining development velocity during critical incidents.

## Problem Statement

### The 3AM Dilemma

**Scenario**: Production is down. A developer needs to deploy a hotfix but:
- Tests are failing
- Code review hasn't happened
- The fix introduces technical debt
- Waiting for proper process will cost $10k/hour

**Current Options**:
1. **Block**: Enforce integrity → business impact
2. **Allow**: Bypass integrity → long-term degradation

**Neither option is optimal.**

### The Broken Windows Effect

Research shows that integrity violations compound:
```
First bypass:  "Just this once"
Second bypass: "We did it before"
Third bypass:  "This is how we work now"
```

**Result**: Coherence decay, increasing maintenance burden.

## Solution: Debt Lock Mechanism

### Concept

A **Debt Lock** is:
1. **Permission** to bypass integrity constraints
2. **Obligation** to repair within defined SLA
3. **Blocking** on debt accumulation threshold

### Core Principles

1. **Transparency**: All bypasses are visible
2. **Accountability**: Debt has an owner
3. **Time-bounded**: Debt must be repaid
4. **Limited**: Can't accumulate infinite debt

## Coherence Metrics Framework

### Metric 1: Test Coverage Coherence

**Definition**: Percentage of code with automated tests

**Measurement**:
```python
coherence_test = (lines_covered / total_lines) * 100
```

**Thresholds**:
- **Coherent**: ≥80% coverage
- **Warning**: 60-79% coverage
- **Violated**: <60% coverage

**Debt Indicator**:
```python
if commit_reduces_coverage and coverage < 80:
    debt_type = "TEST_DEBT"
    severity = calculate_coverage_drop()
```

### Metric 2: Type Safety Coherence

**Definition**: Percentage of code with type annotations

**Measurement**:
```python
coherence_types = (typed_functions / total_functions) * 100
```

**Thresholds**:
- **Coherent**: ≥90% typed (strict mode)
- **Warning**: 70-89% typed
- **Violated**: <70% typed

**Debt Indicator**:
```python
if uses_type_ignore or uses_any:
    debt_type = "TYPE_DEBT"
    severity = count_type_bypasses()
```

### Metric 3: Architectural Coherence

**Definition**: Adherence to documented architectural decisions

**Measurement**:
```python
coherence_arch = check_adr_compliance(changes)
```

**Thresholds**:
- **Coherent**: All changes comply with ADRs
- **Warning**: Minor deviation with justification
- **Violated**: Major deviation without justification

**Debt Indicator**:
```python
if violates_adr and not has_justification:
    debt_type = "ARCHITECTURE_DEBT"
    severity = calculate_deviation_impact()
```

### Metric 4: Documentation Coherence

**Definition**: Code changes have corresponding documentation

**Measurement**:
```python
coherence_docs = (documented_changes / total_changes) * 100
```

**Thresholds**:
- **Coherent**: ≥80% documented
- **Warning**: 60-79% documented
- **Violated**: <60% documented

**Debt Indicator**:
```python
if public_api_changed and not docs_updated:
    debt_type = "DOC_DEBT"
    severity = count_undocumented_apis()
```

### Metric 5: Commit Quality Coherence

**Definition**: Commits follow conventional commit format and include context

**Measurement**:
```python
coherence_commits = has_conventional_format and has_description
```

**Thresholds**:
- **Coherent**: Conventional format + context
- **Warning**: Format correct, minimal context
- **Violated**: No format or context

**Debt Indicator**:
```python
if not conventional_commit_format:
    debt_type = "COMMIT_DEBT"
    severity = "LOW"  # Cosmetic but indicates rushed work
```

## Emergency Detection Patterns

### Time-Based Indicators

**Analysis of debate-hall-mcp git history**:
```
Late Night Commits (00:00-06:00): 8 found
  - 03:50:32: "fix: update octave-mcp dependency to >=0.3.1 for critical fixes"
  - 02:19:00: "fix(server): expose transcript metadata flag"
  - 02:11:12: "fix(get): gate transcript metadata behind include_metadata"
  - 02:04:02: "fix(state): validate speaker metadata fields"
```

**Pattern**: Commits outside business hours suggest urgency

**Detection**:
```python
def is_emergency_time(commit_timestamp):
    hour = commit_timestamp.hour
    return hour >= 22 or hour <= 6  # 10PM - 6AM
```

### Message-Based Indicators

**Keywords Analysis**:
```python
EMERGENCY_KEYWORDS = [
    "HOTFIX", "URGENT", "CRITICAL", "EMERGENCY",
    "3AM", "production down", "outage", "incident"
]

BYPASS_INDICATORS = [
    "skip tests", "no review", "will fix later",
    "temporary", "workaround", "quick fix"
]

DEBT_MARKERS = [
    "TODO", "FIXME", "HACK", "XXX",
    "type: ignore", "# noqa", "pylint: disable"
]
```

**Detection**:
```python
def detect_emergency_commit(message):
    message_lower = message.lower()
    emergency_score = sum(1 for kw in EMERGENCY_KEYWORDS if kw.lower() in message_lower)
    bypass_score = sum(1 for kw in BYPASS_INDICATORS if kw.lower() in message_lower)
    return emergency_score > 0 or bypass_score >= 2
```

### Change-Based Indicators

**Red Flags**:
```python
def detect_integrity_violation(diff):
    violations = []

    # Reduced test coverage
    if diff.test_coverage_before > diff.test_coverage_after:
        violations.append(("TEST_COVERAGE_DROP", diff.coverage_delta))

    # Added type ignores
    if "type: ignore" in diff.changes:
        violations.append(("TYPE_IGNORE_ADDED", diff.count_type_ignores()))

    # Skipped quality gates
    if diff.modified_precommit_config:
        violations.append(("QUALITY_GATE_BYPASS", "pre-commit modified"))

    # Large changes without tests
    if diff.lines_changed > 100 and diff.test_lines_changed == 0:
        violations.append(("UNTESTED_LARGE_CHANGE", diff.lines_changed))

    return violations
```

## Debt Lock Workflow

### Phase 1: Emergency Detection

```python
def should_invoke_integrity_engine(commit_context):
    # Calculate coherence score
    coherence = calculate_coherence_metrics(commit_context)

    # Detect emergency indicators
    is_emergency = (
        is_emergency_time(commit_context.timestamp) or
        detect_emergency_commit(commit_context.message) or
        len(detect_integrity_violation(commit_context.diff)) > 0
    )

    # High-integrity violation in non-emergency = block immediately
    if coherence["overall"] < 60 and not is_emergency:
        return "BLOCK"

    # High-integrity violation in emergency = invoke debate
    if coherence["overall"] < 60 and is_emergency:
        return "INVOKE_INTEGRITY_ENGINE"

    # Low violation = allow with warning
    return "ALLOW"
```

### Phase 2: Integrity Debate

**Thread Format**: `YYYY-MM-DD-integrity-SEVERITY-subject`

**Example**: `2026-01-10-integrity-critical-production-hotfix`

**Debate Structure**:

```octave
===INTEGRITY_DEBATE===

CONTEXT::
  EMERGENCY::[production_outage, revenue_impact_10k_per_hour]
  VIOLATION::[test_coverage_drop[85%→62%], type_safety_bypass[3_ignores]]
  TIMESTAMP::2026-01-10T03:15:00Z
  DEVELOPER::shaun@elevana.io

WIND::VELOCITY_ARGUMENT
  IMPACT::[every_minute_costs_167_dollars]
  JUSTIFICATION::[fix_verified_manually, rollback_plan_exists]
  ALTERNATIVE::[proper_fix_requires_4_hours, business_unacceptable]
  REQUEST::DEBT_LOCK[bypass_tests, repair_within_48h]

WALL::INTEGRITY_ARGUMENT
  RISK::[untested_code_in_production, type_safety_compromised]
  HISTORY::[3_previous_bypasses_this_month]
  CONCERN::[broken_windows_effect, accumulating_debt]
  COUNTER::require_immediate_rollback_plan_before_deploy

DOOR::DECISION
  RULING::GRANT_DEBT_LOCK[conditional]
  CONDITIONS::[
    deploy_allowed_immediately,
    monitoring_enhanced[alert_on_errors],
    tests_written_within_24h,
    type_safety_restored_within_48h,
    retrospective_required
  ]
  DEBT_ID::DEBT-2026-001
  OWNER::shaun@elevana.io
  SLA::48_hours
  BLOCKING_DEBT_COUNT::this_is_2_of_5_allowed

===END===
```

### Phase 3: Debt Tracking

**Debt Record Schema**:
```python
@dataclass
class DebtLock:
    debt_id: str  # "DEBT-2026-001"
    decision_id: str  # Link to integrity debate
    owner: str
    created_at: datetime
    violation_type: str  # "TEST_COVERAGE_DROP"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"
    sla_hours: int  # 48
    repair_deadline: datetime
    status: str  # "ACTIVE", "REPAID", "VIOLATED", "EXTENDED"
    blocking_count: int  # 2 of 5 allowed
```

**Storage**: `.hestai/context/debt/DEBT-ID.oct.md`

### Phase 4: Debt Enforcement

**Pre-Commit Hook**:
```python
def check_debt_status():
    active_debts = load_active_debts()

    # Check blocking threshold
    if len(active_debts) >= MAX_ACTIVE_DEBTS:
        raise BlockingError(
            f"Debt limit reached: {len(active_debts)}/{MAX_ACTIVE_DEBTS} active debts. "
            f"Repay existing debt before creating new bypasses."
        )

    # Check overdue debts
    overdue = [d for d in active_debts if d.is_overdue()]
    if overdue:
        raise BlockingError(
            f"Overdue debt detected: {[d.debt_id for d in overdue]}. "
            f"Resolve before proceeding."
        )
```

**Debt Dashboard**:
```
ACTIVE_DEBT_STATUS::
  DEBT-2026-001::[ACTIVE, 18h_remaining, owner:shaun, tests_written:YES, types_fixed:PENDING]
  DEBT-2025-352::[OVERDUE, 12h_past_deadline, owner:system, BLOCKING]

QUOTA::2_of_5_debt_locks_used
NEXT_BLOCK_AT::3_more_bypasses
```

## Debt Repayment

### Verification

```python
def verify_debt_repayment(debt_id: str, commit_sha: str):
    debt = load_debt(debt_id)

    # Check if violations are resolved
    current_metrics = calculate_coherence_metrics(commit_sha)
    original_violations = debt.violations

    resolved = []
    unresolved = []

    for violation in original_violations:
        if is_violation_resolved(violation, current_metrics):
            resolved.append(violation)
        else:
            unresolved.append(violation)

    if len(unresolved) == 0:
        debt.status = "REPAID"
        debt.repaid_at = datetime.now(UTC)
        save_debt(debt)
        return {"status": "REPAID", "debt_id": debt_id}
    else:
        return {"status": "INCOMPLETE", "unresolved": unresolved}
```

### Automatic Detection

```python
# Pre-commit hook checks
if commit_message.contains(f"Resolves: {debt_id}"):
    verification = verify_debt_repayment(debt_id, commit_sha)
    if verification["status"] == "REPAID":
        print(f"✅ Debt {debt_id} repaid successfully!")
    else:
        raise BlockingError(
            f"❌ Debt {debt_id} not fully repaid. "
            f"Unresolved: {verification['unresolved']}"
        )
```

## Configuration

### System-Level Thresholds

```python
INTEGRITY_ENGINE_CONFIG = {
    # Coherence thresholds
    "test_coverage_threshold": 80,
    "type_safety_threshold": 90,
    "documentation_threshold": 80,

    # Debt limits
    "max_active_debts": 5,
    "max_critical_debts": 2,
    "default_sla_hours": 48,

    # Emergency detection
    "emergency_hours": [(22, 6)],  # 10PM - 6AM
    "emergency_keywords": EMERGENCY_KEYWORDS,

    # Blocking policy
    "block_on_overdue": True,
    "block_on_quota_exceeded": True,
    "allow_sla_extension": True,  # Requires debate
}
```

### Project-Level Overrides

```yaml
# .hestai/config/integrity-engine.yaml
test_coverage_threshold: 85  # Stricter than default
max_active_debts: 3  # Lower quota for critical project
emergency_keywords:
  - "INCIDENT"
  - "SEV-1"
  - "customer-facing"
```

## Integration with Debate Hall

### Tool Extension

**New Tool**: `integrity_debate`

```python
@server.tool()
def integrity_debate(
    thread_id: str,
    emergency_context: str,
    violations: list[dict],
    developer: str,
    proposed_bypass: str,
    repair_plan: str,
) -> dict[str, Any]:
    """
    Initiate an Integrity Engine debate for emergency bypass approval.

    This automatically configures the debate with:
    - Wind: Velocity argument (emergency justification)
    - Wall: Integrity argument (violation analysis)
    - Door: Debt lock decision

    Returns debt_id if approved, blocks if denied.
    """
    # Initialize debate in integrity mode
    debate = init_debate(
        thread_id=thread_id,
        topic=f"Integrity Bypass: {emergency_context}",
        mode="mediated",
        max_rounds=1,
        max_turns=3,
        integrity_mode=True,  # New flag
    )

    # Pre-populate context
    debate.context = {
        "emergency": emergency_context,
        "violations": violations,
        "developer": developer,
        "proposed_bypass": proposed_bypass,
        "repair_plan": repair_plan,
    }

    return debate
```

### Debt Lock Schema

**Extension to DebateRoom**:

```python
class DebateRoom(BaseModel):
    # ... existing fields ...

    # Integrity Engine fields
    integrity_mode: bool = Field(default=False)
    debt_lock: DebtLock | None = Field(default=None)
    coherence_metrics: dict[str, float] | None = Field(default=None)
```

## Testing Strategy

### Simulated Emergency Scenarios

**Scenario 1: Production Hotfix**
```
Emergency: API endpoint returning 500 errors
Violation: Test coverage drop (85% → 62%)
Time: 03:15 AM
Impact: $10k/hour revenue loss
```

**Scenario 2: Security Patch**
```
Emergency: CVE disclosed for dependency
Violation: Skipping internal security review
Time: Business hours
Impact: Customer data at risk
```

**Scenario 3: Data Corruption**
```
Emergency: Database migration failed
Violation: Manual SQL bypass of migration system
Time: 11:30 PM
Impact: User accounts locked
```

### Success Criteria

1. **Emergency Detection**: 95% accuracy on test corpus
2. **Debt Tracking**: 100% of bypasses create debt records
3. **Repayment Rate**: >80% of debt locks repaid within SLA
4. **False Positives**: <5% of normal commits flagged
5. **Blocking Effectiveness**: Zero overdue debt accumulation

## Metrics & Monitoring

### Integrity Dashboard

```
SYSTEM_COHERENCE_SCORE::73[WARNING]
  TEST_COVERAGE::85[OK]
  TYPE_SAFETY::88[WARNING]
  DOCUMENTATION::62[VIOLATION]
  ARCHITECTURE::95[OK]
  COMMIT_QUALITY::78[WARNING]

ACTIVE_DEBT::2_of_5
  DEBT-2026-001[18h_remaining]
  DEBT-2026-002[44h_remaining]

DEBT_HISTORY_30D::
  Created: 8
  Repaid: 6 (75% repayment rate)
  Overdue: 1 (12.5% violation rate)
  Extended: 1

EMERGENCY_INCIDENTS::3_this_month
  Avg_Resolution: 36_hours
  Avg_Debt_SLA: 48_hours
```

## Open Questions

### Research Needed

1. **Coherence Score Aggregation**:
   - How do we weight different metrics?
   - Is test coverage more critical than type safety?
   - Should weights be project-specific?

2. **SLA Calibration**:
   - Is 48 hours realistic for all debt types?
   - Should critical debts have shorter SLAs?
   - How do we handle dependencies blocking repayment?

3. **Debt Accumulation Policy**:
   - Is 5 active debts the right limit?
   - Should limit scale with team size?
   - What happens when emergency exceeds quota?

4. **Extension Protocol**:
   - Can debt SLA be extended?
   - Requires another debate?
   - Auto-extension for legitimate blockers?

### Next Steps

1. **Prototype** coherence metrics calculation
2. **Test** on debate-hall-mcp git history (empirical validation)
3. **Refine** thresholds based on false positive rate
4. **Design** debt dashboard UI
5. **Implement** basic debt tracking system
6. **Pilot** with single project (debate-hall-mcp)

## Conclusion

The Integrity Engine provides a systematic approach to handling the "Coherence vs. Velocity" dilemma. By quantifying integrity violations, enabling transparent bypasses, and enforcing debt repayment, we prevent the broken windows effect while maintaining development velocity during emergencies.

**Key Innovation**: Debt Locks transform "bypass vs. block" into "bypass + obligation", aligning short-term pragmatism with long-term sustainability.

**Recommendation**: Proceed with prototype implementation and empirical testing on debate-hall-mcp repository.
