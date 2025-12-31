"""Unit tests for debate_hall_mcp.validation module.

Tests cover:
- CognitionValidator with deterministic rule-based validation
- PATHOS/Wind validation rules (multiple options, questions)
- ETHOS/Wall validation rules ([VERDICT], [EVIDENCE], no hedging)
- LOGOS/Door validation rules (numbered steps, synthesis markers)
- ValidationResult levels (PASS, WARN, BLOCK)
- Edge cases (empty content, missing markers, None cognition)
"""

from debate_hall_mcp.validation import CognitionValidator, ValidationResult


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_pass_result(self) -> None:
        """PASS result has no violations."""
        result = ValidationResult(level="PASS", violations=[], hints=[])
        assert result.level == "PASS"
        assert len(result.violations) == 0
        assert len(result.hints) == 0

    def test_warn_result(self) -> None:
        """WARN result has violations but no blocking issues."""
        result = ValidationResult(
            level="WARN",
            violations=["Missing synthesis marker"],
            hints=["Consider using TENSION→PATTERN→CLARITY structure"],
        )
        assert result.level == "WARN"
        assert len(result.violations) == 1
        assert len(result.hints) == 1

    def test_block_result(self) -> None:
        """BLOCK result indicates critical violation."""
        result = ValidationResult(
            level="BLOCK",
            violations=["Missing required [VERDICT] marker"],
            hints=["Wall/ETHOS must start with [VERDICT] followed by evidence"],
        )
        assert result.level == "BLOCK"
        assert len(result.violations) == 1


class TestCognitionValidatorWindPathos:
    """Test Wind/PATHOS validation rules."""

    def test_valid_wind_with_numbered_options_and_questions(self) -> None:
        """Valid Wind turn has numbered options and questions."""
        validator = CognitionValidator()
        content = """
[STIMULUS]
The debate approaches synthesis.

[POSSIBILITIES]
1. We could merge immediately
2. We could run one more validation round
3. We could defer to orchestrator judgment

What criteria should guide our timing decision?
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_valid_wind_with_bullet_points_and_questions(self) -> None:
        """Valid Wind turn accepts bullet points as alternatives."""
        validator = CognitionValidator()
        content = """
[STIMULUS]
Multiple approaches exist.

[POSSIBILITIES]
- Approach A: immediate action
- Approach B: delayed validation
- Approach C: hybrid solution

Which path maximizes verification while minimizing delay?
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        assert result.level == "PASS"

    def test_wind_missing_options_triggers_block(self) -> None:
        """Wind without multiple options triggers BLOCK."""
        validator = CognitionValidator()
        content = """
[STIMULUS]
We should proceed with the plan.

This is the best approach.
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        assert result.level == "BLOCK"
        assert any("multiple options" in v.lower() for v in result.violations)

    def test_wind_missing_questions_triggers_block(self) -> None:
        """Wind without question marks triggers BLOCK."""
        validator = CognitionValidator()
        content = """
[STIMULUS]
Consider these options:

1. Option A
2. Option B
3. Option C

All are viable.
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        assert result.level == "BLOCK"
        assert any("question" in v.lower() for v in result.violations)

    def test_wind_single_conclusion_triggers_warn(self) -> None:
        """Wind with questions but no structured options triggers WARN."""
        validator = CognitionValidator()
        content = """
The answer is clear: proceed immediately.

Why would we wait?
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        # Has question mark (passes BLOCK), but no structured option lists (triggers WARN)
        assert result.level == "WARN"
        assert any("question" in v.lower() and "option" in v.lower() for v in result.violations)

    def test_wind_mixed_format_counts_all_options(self) -> None:
        """Wind with mixed numbered and bullet formats counts all options correctly."""
        validator = CognitionValidator()
        content = """
[STIMULUS]
Multiple approaches exist.

[POSSIBILITIES]
1. Approach A: numbered format
- Approach B: bullet format

Which approach should we take?
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        # Has 1 numbered + 1 bullet = 2 total options (should PASS, not WARN)
        assert result.level == "PASS"
        assert len(result.violations) == 0


class TestCognitionValidatorWallEthos:
    """Test Wall/ETHOS validation rules."""

    def test_valid_wall_with_verdict_and_evidence(self) -> None:
        """Valid Wall turn has [VERDICT] and [EVIDENCE]."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED - The implementation meets all requirements.

[EVIDENCE]
- All tests passing (pytest output: 47 passed)
- Type checking clean (mypy: 0 errors)
- Code review approved by critical-engineer

[REASONING]
The three quality gates validate functional correctness.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_valid_wall_with_verdict_colon_format(self) -> None:
        """Valid Wall turn accepts 'VERDICT:' format with non-BLOCKED verdict."""
        validator = CognitionValidator()
        content = """
VERDICT: APPROVED - All requirements met

[EVIDENCE]
- Test coverage complete for new validation module
- pytest shows all tests passing

[REASONING]
TDD cycle complete: tests written and passing.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"

    def test_wall_missing_verdict_triggers_block(self) -> None:
        """Wall without [VERDICT] or VERDICT: triggers BLOCK."""
        validator = CognitionValidator()
        content = """
[EVIDENCE]
- Tests are passing
- Code looks good

[REASONING]
Everything seems fine.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "BLOCK"
        assert any("verdict" in v.lower() for v in result.violations)

    def test_wall_verdict_not_in_first_200_chars_triggers_block(self) -> None:
        """Wall with late [VERDICT] triggers BLOCK."""
        validator = CognitionValidator()
        # Create content with verdict after 200 chars
        padding = "X" * 250
        content = f"""
{padding}

[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "BLOCK"
        assert any("first 200" in v.lower() or "verdict" in v.lower() for v in result.violations)

    def test_wall_missing_evidence_triggers_block(self) -> None:
        """Wall without [EVIDENCE] section triggers BLOCK."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[REASONING]
Looks good to me.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "BLOCK"
        assert any("evidence" in v.lower() for v in result.violations)

    def test_wall_hedging_language_triggers_warn(self) -> None:
        """Wall with hedging language triggers WARN."""
        validator = CognitionValidator()
        content = """
[VERDICT]
MAYBE_APPROVED - Perhaps this could work

[EVIDENCE]
- Tests might be passing
- Code seems okay

[REASONING]
It could be fine, maybe.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "WARN"
        assert any(
            "hedging" in v.lower() or "maybe" in v.lower() or "perhaps" in v.lower()
            for v in result.violations
        )

    def test_wall_blocked_verdict_without_block_nature_warns(self) -> None:
        """Wall with BLOCKED verdict but missing BLOCK_NATURE triggers WARN."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKED

[EVIDENCE]
- File does not exist
- No tests found

[REASONING]
Cannot proceed without required file.

REMEDIATION_REQUEST::"Create the missing file"
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "WARN"
        assert any("block_nature" in v.lower() for v in result.violations)
        assert any("block_nature" in h.lower() for h in result.hints)

    def test_wall_blocked_verdict_without_remediation_request_warns(self) -> None:
        """Wall with BLOCKED verdict but missing REMEDIATION_REQUEST triggers WARN."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKED

[EVIDENCE]
- Function not implemented
- Tests are missing

[REASONING]
Cannot validate without implementation.

BLOCK_NATURE::OPPORTUNITY
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "WARN"
        assert any("remediation_request" in v.lower() for v in result.violations)
        assert any("specific action" in h.lower() for h in result.hints)

    def test_wall_blocked_verdict_with_both_fields_passes(self) -> None:
        """Wall with BLOCKED verdict and both required fields passes."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKED

[EVIDENCE]
- tests/unit/test_auth_flow.py does not exist
- No test coverage for auth module

[REASONING]
TDD requires tests before implementation.

BLOCK_NATURE::OPPORTUNITY

VOID_IDENTIFIED::"tests/unit/test_auth_flow.py does not exist"
CONSTRUCTION_SPEC::"Unit tests covering login, logout, token refresh flows"
ACCEPTANCE_CRITERIA::"pytest passes with >80% coverage on auth module"

REMEDIATION_REQUEST::"Create test file with RED tests for auth flows before implementation"
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_wall_non_blocked_verdict_no_additional_checks(self) -> None:
        """Wall with non-BLOCKED verdict doesn't check for BLOCK_NATURE or REMEDIATION_REQUEST."""
        validator = CognitionValidator()
        content = """
VERDICT::APPROVED

[EVIDENCE]
- All tests passing (pytest output: 47 passed)
- Type checking clean (mypy: 0 errors)

[REASONING]
Implementation meets requirements.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_wall_blocked_verdict_various_formats(self) -> None:
        """Wall BLOCKED verdict detection works with various formats."""
        validator = CognitionValidator()

        # Test VERDICT: BLOCKED format
        content1 = """
VERDICT: BLOCKED

[EVIDENCE]
- Missing file

BLOCK_NATURE::CONSTRAINT
REMEDIATION_REQUEST::"Fix the constraint"
"""
        result1 = validator.validate(role="Wall", content=content1, cognition="ETHOS")
        assert result1.level == "PASS"

        # Test [VERDICT] BLOCKED format
        content2 = """
[VERDICT] BLOCKED

[EVIDENCE]
- Missing file

BLOCK_NATURE::OPPORTUNITY
REMEDIATION_REQUEST::"Create the file"
"""
        result2 = validator.validate(role="Wall", content=content2, cognition="ETHOS")
        assert result2.level == "PASS"


class TestCognitionValidatorDoorLogos:
    """Test Door/LOGOS validation rules."""

    def test_valid_door_with_numbered_steps(self) -> None:
        """Valid Door turn has numbered reasoning steps."""
        validator = CognitionValidator()
        content = """
[TENSION]
Speed vs. verification quality

[PATTERN]
1. Analyze system impact first
2. Implement minimal code second
3. Verify integration third

[CLARITY]
Sequential gates create emergent quality assurance.
"""
        result = validator.validate(role="Door", content=content, cognition="LOGOS")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_door_missing_numbered_steps_triggers_block(self) -> None:
        """Door without numbered steps triggers BLOCK."""
        validator = CognitionValidator()
        content = """
[TENSION]
Speed vs. verification

[PATTERN]
We should analyze, implement, and verify.

[CLARITY]
This creates quality.
"""
        result = validator.validate(role="Door", content=content, cognition="LOGOS")
        assert result.level == "BLOCK"
        assert any("numbered" in v.lower() or "step" in v.lower() for v in result.violations)

    def test_door_missing_synthesis_markers_triggers_warn(self) -> None:
        """Door without synthesis markers triggers WARN."""
        validator = CognitionValidator()
        content = """
Analysis:

1. First we need to understand the system
2. Then we implement the change
3. Finally we verify it works

This approach ensures quality.
"""
        result = validator.validate(role="Door", content=content, cognition="LOGOS")
        # Has numbered steps (passes BLOCK), but missing markers (triggers WARN)
        assert result.level == "WARN"
        assert any(
            "synthesis" in v.lower() or "marker" in v.lower() or "tension" in v.lower()
            for v in result.violations
        )


class TestCognitionValidatorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_none_cognition_passes_without_validation(self) -> None:
        """None cognition skips validation (backward compatibility)."""
        validator = CognitionValidator()
        content = "Any content without cognition markers"
        result = validator.validate(role="Wind", content=content, cognition=None)
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_empty_content_triggers_block(self) -> None:
        """Empty content triggers BLOCK for any cognition."""
        validator = CognitionValidator()
        result = validator.validate(role="Wind", content="", cognition="PATHOS")
        assert result.level == "BLOCK"
        assert any("empty" in v.lower() for v in result.violations)

    def test_whitespace_only_content_triggers_block(self) -> None:
        """Whitespace-only content triggers BLOCK."""
        validator = CognitionValidator()
        result = validator.validate(role="Wall", content="   \n\n   ", cognition="ETHOS")
        assert result.level == "BLOCK"
        assert any("empty" in v.lower() for v in result.violations)

    def test_unknown_cognition_passes_without_validation(self) -> None:
        """Unknown cognition value skips validation."""
        validator = CognitionValidator()
        content = "Any content"
        result = validator.validate(role="Wind", content=content, cognition="UNKNOWN")
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_case_insensitive_cognition(self) -> None:
        """Cognition validation is case-insensitive."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Wall", content=content, cognition="ethos")
        assert result.level == "PASS"

    def test_case_insensitive_markers(self) -> None:
        """Marker detection is case-insensitive."""
        validator = CognitionValidator()
        content = """
[verdict]
APPROVED

[evidence]
- Tests passing
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"

    def test_verdict_blocked_no_space_after_colon(self) -> None:
        """VERDICT:BLOCKED (no space after colon) should trigger BLOCKED detection."""
        validator = CognitionValidator()
        content = """
VERDICT:BLOCKED

[EVIDENCE]
- Missing file

BLOCK_NATURE::CONSTRAINT
REMEDIATION_REQUEST::"Fix the issue"
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        # Should detect BLOCKED verdict and pass with required fields
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_block_nature_invalid_value_warns(self) -> None:
        """BLOCK_NATURE::INVALID should WARN (invalid value)."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKED

[EVIDENCE]
- Missing file

BLOCK_NATURE::INVALID
REMEDIATION_REQUEST::"Fix it"
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        # Should WARN because INVALID is not CONSTRAINT or OPPORTUNITY
        assert result.level == "WARN"
        assert any("block_nature" in v.lower() for v in result.violations)

    def test_block_nature_lowercase_constraint_passes(self) -> None:
        """BLOCK_NATURE::constraint (lowercase) should PASS."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKED

[EVIDENCE]
- Missing required file

BLOCK_NATURE::constraint
REMEDIATION_REQUEST::"Create the file"
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        # Should PASS with lowercase constraint
        assert result.level == "PASS"
        assert len(result.violations) == 0

    def test_verdict_blocked_false_positive_protection(self) -> None:
        """VERDICT::BLOCKEDNESS should NOT trigger BLOCKED detection."""
        validator = CognitionValidator()
        content = """
VERDICT::BLOCKEDNESS_NOT_APPLICABLE

[EVIDENCE]
- Tests passing
- No blockers found

[REASONING]
The concept of blockedness does not apply here.
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        # Should PASS - "BLOCKEDNESS" should not match due to word boundary
        assert result.level == "PASS"
        assert len(result.violations) == 0


class TestRoleCognitionEnforcement:
    """Test role/cognition pairing enforcement (Issue #36).

    Validates that:
    - Wind requires PATHOS cognition
    - Wall requires ETHOS cognition
    - Door requires LOGOS cognition
    - Mismatches WARN in non-strict mode
    - Mismatches BLOCK in strict mode
    - None cognition is allowed for backward compatibility
    """

    # === Valid Pairings ===

    def test_wind_with_pathos_passes(self) -> None:
        """Wind with PATHOS is a valid pairing."""
        validator = CognitionValidator()
        content = """
1. Option A
2. Option B

What should we choose?
"""
        result = validator.validate(role="Wind", content=content, cognition="PATHOS")
        assert result.level == "PASS"

    def test_wall_with_ethos_passes(self) -> None:
        """Wall with ETHOS is a valid pairing."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Wall", content=content, cognition="ETHOS")
        assert result.level == "PASS"

    def test_door_with_logos_passes(self) -> None:
        """Door with LOGOS is a valid pairing."""
        validator = CognitionValidator()
        content = """
[TENSION]
Speed vs quality

1. Analyze first
2. Implement second
3. Verify third
"""
        result = validator.validate(role="Door", content=content, cognition="LOGOS")
        assert result.level == "PASS"

    # === Invalid Pairings - Non-Strict Mode (WARN) ===

    def test_wind_with_ethos_warns_nonstrict(self) -> None:
        """Wind with ETHOS warns in non-strict mode."""
        validator = CognitionValidator()
        # Content valid for ETHOS but role is Wind
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Wind", content=content, cognition="ETHOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)
        assert any("wind" in v.lower() and "pathos" in v.lower() for v in result.violations)

    def test_wind_with_logos_warns_nonstrict(self) -> None:
        """Wind with LOGOS warns in non-strict mode."""
        validator = CognitionValidator()
        content = """
[TENSION]
Speed vs quality

1. Analyze first
2. Implement second
3. Verify third
"""
        result = validator.validate(role="Wind", content=content, cognition="LOGOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    def test_wall_with_pathos_warns_nonstrict(self) -> None:
        """Wall with PATHOS warns in non-strict mode."""
        validator = CognitionValidator()
        content = """
1. Option A
2. Option B

What should we choose?
"""
        result = validator.validate(role="Wall", content=content, cognition="PATHOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)
        assert any("wall" in v.lower() and "ethos" in v.lower() for v in result.violations)

    def test_wall_with_logos_warns_nonstrict(self) -> None:
        """Wall with LOGOS warns in non-strict mode."""
        validator = CognitionValidator()
        content = """
[TENSION]
Speed vs quality

1. Analyze first
2. Implement second
3. Verify third
"""
        result = validator.validate(role="Wall", content=content, cognition="LOGOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    def test_door_with_pathos_warns_nonstrict(self) -> None:
        """Door with PATHOS warns in non-strict mode."""
        validator = CognitionValidator()
        content = """
1. Option A
2. Option B

What should we choose?
"""
        result = validator.validate(role="Door", content=content, cognition="PATHOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)
        assert any("door" in v.lower() and "logos" in v.lower() for v in result.violations)

    def test_door_with_ethos_warns_nonstrict(self) -> None:
        """Door with ETHOS warns in non-strict mode."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Door", content=content, cognition="ETHOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    # === Invalid Pairings - Strict Mode (BLOCK) ===

    def test_wind_with_ethos_blocks_strict(self) -> None:
        """Wind with ETHOS blocks in strict mode."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Wind", content=content, cognition="ETHOS", strict=True)
        assert result.level == "BLOCK"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    def test_wall_with_pathos_blocks_strict(self) -> None:
        """Wall with PATHOS blocks in strict mode."""
        validator = CognitionValidator()
        content = """
1. Option A
2. Option B

What should we choose?
"""
        result = validator.validate(role="Wall", content=content, cognition="PATHOS", strict=True)
        assert result.level == "BLOCK"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    def test_door_with_ethos_blocks_strict(self) -> None:
        """Door with ETHOS blocks in strict mode."""
        validator = CognitionValidator()
        content = """
[VERDICT]
APPROVED

[EVIDENCE]
- Tests passing
"""
        result = validator.validate(role="Door", content=content, cognition="ETHOS", strict=True)
        assert result.level == "BLOCK"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    # === Backward Compatibility ===

    def test_none_cognition_allowed_nonstrict(self) -> None:
        """None cognition is allowed in non-strict mode (backward compatibility)."""
        validator = CognitionValidator()
        content = "Any content without cognition validation"
        # All roles should pass with None cognition in non-strict mode
        for role in ["Wind", "Wall", "Door"]:
            result = validator.validate(role=role, content=content, cognition=None, strict=False)
            assert result.level == "PASS", f"Role {role} should pass with None cognition"

    def test_none_cognition_blocks_strict(self) -> None:
        """None cognition blocks in strict mode (existing behavior)."""
        validator = CognitionValidator()
        content = "Any content"
        result = validator.validate(role="Wind", content=content, cognition=None, strict=True)
        assert result.level == "BLOCK"
        assert any("no cognition" in v.lower() for v in result.violations)

    # === Case Insensitivity ===

    def test_role_cognition_case_insensitive(self) -> None:
        """Role and cognition matching is case-insensitive."""
        validator = CognitionValidator()
        content = """
1. Option A
2. Option B

What should we choose?
"""
        # Test lowercase role with uppercase cognition
        result = validator.validate(role="wind", content=content, cognition="PATHOS")
        assert result.level == "PASS"

        # Test uppercase role with lowercase cognition
        result = validator.validate(role="WIND", content=content, cognition="pathos")
        assert result.level == "PASS"

        # Test mixed case
        result = validator.validate(role="Wind", content=content, cognition="Pathos")
        assert result.level == "PASS"

    # === Mismatch takes priority over content validation ===

    def test_mismatch_warn_not_blocked_by_content_pass(self) -> None:
        """Role/cognition mismatch WARN is returned even if content passes cognition validation."""
        validator = CognitionValidator()
        # Valid PATHOS content (has options and questions)
        content = """
1. Option A
2. Option B

What should we choose?
"""
        # Wall with PATHOS content should WARN on mismatch, not pass
        result = validator.validate(role="Wall", content=content, cognition="PATHOS", strict=False)
        assert result.level == "WARN"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)

    def test_mismatch_block_takes_priority_over_content_block(self) -> None:
        """Role/cognition BLOCK takes priority over content validation BLOCK in strict mode."""
        validator = CognitionValidator()
        # Invalid PATHOS content (missing options and questions)
        content = "Simple statement without options or questions."
        # Wind with ETHOS should BLOCK on mismatch, mentioning role/cognition
        result = validator.validate(role="Wind", content=content, cognition="ETHOS", strict=True)
        assert result.level == "BLOCK"
        assert any("role" in v.lower() and "cognition" in v.lower() for v in result.violations)
