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
        """Valid Wall turn accepts 'VERDICT:' format."""
        validator = CognitionValidator()
        content = """
VERDICT: BLOCKED - Missing required tests

[EVIDENCE]
- No test coverage for new validation module
- pytest shows only existing tests passing

[REASONING]
TDD requires tests before implementation.
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
