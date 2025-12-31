"""Cognition validation for debate-hall-mcp.

This module implements deterministic rule-based validation for the three cognition
archetypes: PATHOS (Wind), ETHOS (Wall), and LOGOS (Door).

Validation acts as a behavioral firewall - checking turn content BEFORE state commit
to ensure cognition contracts are honored.

Architecture:
- Deterministic rules (no LLM classification)
- Pre-commit validation (preserves hash chain integrity)
- PASS/WARN/BLOCK levels for progressive enforcement
- Unit testable pattern matching
- DoS protection via content length limits

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): Validates before state modification
- I4 (VERIFIABLE_EVENT_LEDGER): Validation occurs pre-commit (hash chain preserved)
"""

import re
from dataclasses import dataclass, field
from typing import Literal

# DoS protection: Maximum turn content length (32KB)
# Prevents memory/CPU spike from multi-MB payloads hitting regex operations
MAX_TURN_CONTENT_LENGTH = 32000

# Role to cognition mapping (Issue #36: Cognition/Role Normalization)
# Each debate role has a required cognition archetype:
# - Wind (divergent exploration) requires PATHOS
# - Wall (boundary enforcement) requires ETHOS
# - Door (convergent synthesis) requires LOGOS
ROLE_COGNITION_MAP: dict[str, str] = {
    "WIND": "PATHOS",
    "WALL": "ETHOS",
    "DOOR": "LOGOS",
}


@dataclass
class ValidationResult:
    """Result of cognition validation.

    Attributes:
        level: Severity level (PASS, WARN, BLOCK)
        violations: List of specific violations found
        hints: List of hints for fixing violations
    """

    level: Literal["PASS", "WARN", "BLOCK"]
    violations: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)


class CognitionValidator:
    """Validates turn content against cognition behavioral contracts.

    Implements deterministic rule-based validation for:
    - PATHOS/Wind: Multiple options + questions (divergent exploration)
    - ETHOS/Wall: [VERDICT] + [EVIDENCE] + no hedging (boundary enforcement)
    - LOGOS/Door: Numbered steps + synthesis markers (convergent structure)

    Validation levels:
    - PASS: Content meets cognition contract
    - WARN: Minor violations (advisory, non-blocking by default)
    - BLOCK: Critical violations (blocks turn in strict mode)
    """

    def validate(
        self, role: str, content: str, cognition: str | None, strict: bool = False
    ) -> ValidationResult:
        """Validate turn content against cognition contract.

        Args:
            role: Agent role (Wind, Wall, Door) - reserved for future validation logging
            content: Turn content to validate
            cognition: Cognitive archetype (PATHOS, ETHOS, LOGOS) or None
            strict: If True, BLOCK on None/unknown cognition (security mode)

        Returns:
            ValidationResult with level and violations/hints

        Note:
            - Non-strict mode: None/unknown cognition skips validation (backward compatibility)
            - Strict mode: None/unknown cognition BLOCKs (security requirement)
            - Validation is case-insensitive for cognition and markers
            - DoS protection: Content exceeding MAX_TURN_CONTENT_LENGTH is rejected early
        """
        # Normalize role to uppercase for comparison
        normalized_role = role.upper() if role else None

        # DoS protection: Check content length BEFORE expensive regex operations
        if len(content) > MAX_TURN_CONTENT_LENGTH:
            return ValidationResult(
                level="BLOCK",
                violations=[
                    f"Content exceeds maximum length of {MAX_TURN_CONTENT_LENGTH} characters"
                ],
                hints=["Reduce content size to prevent resource exhaustion"],
            )

        # Normalize cognition to uppercase for comparison
        normalized_cognition = cognition.upper() if cognition else None

        # Handle None cognition based on strict flag
        if not normalized_cognition:
            if strict:
                return ValidationResult(
                    level="BLOCK",
                    violations=["No cognition specified"],
                    hints=["Specify cognition (PATHOS, ETHOS, or LOGOS) in strict mode"],
                )
            return ValidationResult(level="PASS")  # Backward compatibility

        # Handle unknown cognition values based on strict flag
        if normalized_cognition not in ("PATHOS", "ETHOS", "LOGOS"):
            if strict:
                return ValidationResult(
                    level="BLOCK",
                    violations=[f"Unknown cognition: {normalized_cognition}"],
                    hints=["Use PATHOS, ETHOS, or LOGOS for cognition"],
                )
            return ValidationResult(level="PASS")  # Backward compatibility

        # Check for empty content
        if not content or not content.strip():
            return ValidationResult(
                level="BLOCK",
                violations=["Content is empty"],
                hints=["Provide substantive content for the turn"],
            )

        # Check role/cognition pairing (Issue #36: Cognition/Role Normalization)
        # Only check if both role and cognition are valid values
        if normalized_role and normalized_cognition:
            expected_cognition = ROLE_COGNITION_MAP.get(normalized_role)
            if expected_cognition and normalized_cognition != expected_cognition:
                # Role/cognition mismatch detected
                role_lower = normalized_role.lower().capitalize()
                expected_lower = expected_cognition
                violation_msg = (
                    f"Role/cognition mismatch: {role_lower} requires {expected_lower}, "
                    f"but {normalized_cognition} was specified"
                )
                hint_msg = f"{role_lower} must use {expected_lower} cognition"
                if strict:
                    return ValidationResult(
                        level="BLOCK",
                        violations=[violation_msg],
                        hints=[hint_msg],
                    )
                else:
                    return ValidationResult(
                        level="WARN",
                        violations=[violation_msg],
                        hints=[hint_msg],
                    )

        # Route to appropriate validator
        if normalized_cognition == "PATHOS":
            return self._validate_pathos(content)
        elif normalized_cognition == "ETHOS":
            return self._validate_ethos(content)
        elif normalized_cognition == "LOGOS":
            return self._validate_logos(content)
        else:
            # Should never reach here due to earlier check
            return ValidationResult(level="PASS")

    def _validate_pathos(self, content: str) -> ValidationResult:
        """Validate Wind/PATHOS turn (divergent exploration).

        REQUIRED (BLOCK):
        - Multiple options (numbered lists OR bullet points)
        - Question marks (exploration signal)

        WARN:
        - Single conclusion without alternatives

        Args:
            content: Turn content to validate

        Returns:
            ValidationResult with PASS, WARN, or BLOCK
        """
        violations = []
        hints = []
        level: Literal["PASS", "WARN", "BLOCK"] = "PASS"

        # Check for multiple options (numbered or bulleted lists)
        has_numbered_list = bool(re.search(r"^\s*\d+\.", content, re.MULTILINE))  # Numbered: "1."
        has_bullet_list = bool(
            re.search(r"^\s*[-*]", content, re.MULTILINE)
        )  # Bullets: "- " or "* "

        # Check for question marks
        has_questions = "?" in content

        # Both are REQUIRED - check both first to give complete feedback
        has_options = has_numbered_list or has_bullet_list

        if not has_options and not has_questions:
            # Missing both - BLOCK
            violations.append("Missing multiple options (no numbered lists or bullet points found)")
            violations.append("Missing questions (no question marks found)")
            hints.append("Wind/PATHOS must present multiple options AND ask questions")
            level = "BLOCK"
        elif not has_options:
            # Has questions but no list options - WARN for exploratory questions without structured options
            violations.append("Questions found but no structured option lists detected")
            hints.append("Wind/PATHOS should present options using numbered lists or bullet points")
            level = "WARN"  # Downgrade to WARN if questions present
        elif not has_questions:
            # Has options but no questions - BLOCK
            violations.append("Missing questions (no question marks found)")
            hints.append("Wind/PATHOS must ask questions to explore possibilities")
            level = "BLOCK"
        else:
            # Has both - check count for WARN
            numbered_count = len(re.findall(r"^\s*\d+\.", content, re.MULTILINE))
            bullet_count = len(re.findall(r"^\s*[-*]", content, re.MULTILINE))
            total_options = numbered_count + bullet_count  # Count ALL options from both formats

            if total_options < 2:
                violations.append("Single conclusion without alternatives detected")
                hints.append("Wind/PATHOS should present at least 2-3 distinct options")
                level = "WARN"

        return ValidationResult(level=level, violations=violations, hints=hints)

    def _validate_ethos(self, content: str) -> ValidationResult:
        """Validate Wall/ETHOS turn (boundary enforcement).

        REQUIRED (BLOCK):
        - [VERDICT] or "VERDICT:" in first 200 chars
        - [EVIDENCE] section present

        WARN:
        - Hedging language ("maybe", "perhaps", "could be")
        - BLOCKED verdict without BLOCK_NATURE (Wall Content Contract)
        - BLOCKED verdict without REMEDIATION_REQUEST (Wall Content Contract)

        Args:
            content: Turn content to validate

        Returns:
            ValidationResult with PASS, WARN, or BLOCK
        """
        violations = []
        hints = []
        level: Literal["PASS", "WARN", "BLOCK"] = "PASS"

        # Check for [VERDICT] or VERDICT: in first 200 chars (case-insensitive)
        first_200 = content[:200].lower()
        has_verdict = "[verdict]" in first_200 or "verdict:" in first_200

        if not has_verdict:
            violations.append("Missing [VERDICT] or VERDICT: in first 200 characters")
            hints.append(
                "Wall/ETHOS must start with [VERDICT] or VERDICT: followed by clear judgment"
            )
            level = "BLOCK"

        # Check for [EVIDENCE] section (case-insensitive)
        has_evidence = "[evidence]" in content.lower()

        if not has_evidence:
            violations.append("Missing [EVIDENCE] section")
            hints.append("Wall/ETHOS must provide [EVIDENCE] to support verdict")
            level = "BLOCK"

        # WARN: Check for BLOCKED verdict content contract (docs/wall-content-contract.oct.md)
        # Detect BLOCKED verdict patterns: "VERDICT::BLOCKED", "[VERDICT] BLOCKED", "VERDICT:BLOCKED" (no space)
        content_lower = content.lower()
        has_blocked_verdict = bool(
            re.search(
                r"(?:verdict\s*::\s*|\[verdict\]\s*|verdict\s*:\s*)blocked\b",
                content_lower,
            )
        )

        if has_blocked_verdict and level == "PASS":  # Only check if not already blocked
            # Check for BLOCK_NATURE:: with valid value (CONSTRAINT or OPPORTUNITY)
            block_nature_match = re.search(
                r"block_nature\s*::\s*(constraint|opportunity)\b", content_lower
            )
            has_valid_block_nature = bool(block_nature_match)

            # Check for REMEDIATION_REQUEST::
            has_remediation_request = bool(re.search(r"remediation_request\s*::", content_lower))

            if not has_valid_block_nature:
                violations.append(
                    "BLOCKED verdict missing BLOCK_NATURE:: (should be CONSTRAINT or OPPORTUNITY)"
                )
                hints.append(
                    "Wall Content Contract: BLOCKED verdicts should specify BLOCK_NATURE::CONSTRAINT or BLOCK_NATURE::OPPORTUNITY"
                )
                level = "WARN"

            if not has_remediation_request:
                violations.append("BLOCKED verdict missing REMEDIATION_REQUEST::")
                hints.append(
                    "Wall Content Contract: BLOCKED verdicts should include REMEDIATION_REQUEST:: with specific action"
                )
                level = "WARN"

        # WARN: Check for hedging language
        hedging_words = ["maybe", "perhaps", "could be", "might be", "seems", "appears"]
        found_hedging = [word for word in hedging_words if word in content.lower()]

        if found_hedging and level == "PASS":  # Only warn if not already blocked
            violations.append(f"Hedging language detected: {', '.join(found_hedging)}")
            hints.append("Wall/ETHOS should provide definitive judgments, not hedged uncertainty")
            level = "WARN"

        return ValidationResult(level=level, violations=violations, hints=hints)

    def _validate_logos(self, content: str) -> ValidationResult:
        """Validate Door/LOGOS turn (convergent synthesis).

        REQUIRED (BLOCK):
        - Numbered reasoning steps (1., 2., 3.)

        WARN:
        - Missing synthesis markers (TENSION, PATTERN, STRUCTURE, CLARITY)

        Args:
            content: Turn content to validate

        Returns:
            ValidationResult with PASS, WARN, or BLOCK
        """
        violations = []
        hints = []
        level: Literal["PASS", "WARN", "BLOCK"] = "PASS"

        # Check for numbered steps
        has_numbered_steps = bool(re.search(r"^\s*\d+\.", content, re.MULTILINE))

        if not has_numbered_steps:
            violations.append("Missing numbered reasoning steps")
            hints.append(
                "Door/LOGOS must use numbered steps (1., 2., 3.) to show reasoning structure"
            )
            level = "BLOCK"

        # WARN: Check for synthesis markers
        synthesis_markers = ["tension", "pattern", "structure", "clarity"]
        found_markers = [marker for marker in synthesis_markers if marker in content.lower()]

        if not found_markers and level == "PASS":  # Only warn if not already blocked
            violations.append("Missing synthesis markers (TENSION, PATTERN, STRUCTURE, CLARITY)")
            hints.append("Door/LOGOS should use synthesis markers to show emergent structure")
            level = "WARN"

        return ValidationResult(level=level, violations=violations, hints=hints)
