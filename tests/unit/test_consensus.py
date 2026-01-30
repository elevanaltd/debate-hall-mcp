"""Unit tests for consensus response parser (Phase 4: Consensus Implementation).

Tests the consensus response parsing:
- ConsensusResult model structure
- parse_consensus_response function
- Handling of APPROVE/REJECT variations
- Feedback extraction
- Edge cases
"""

from debate_hall_mcp.consensus import ConsensusResult, parse_consensus_response


class TestConsensusResultModel:
    """Tests for ConsensusResult Pydantic model."""

    def test_consensus_result_approved_with_feedback(self) -> None:
        """ConsensusResult should accept approved=True with feedback."""
        result = ConsensusResult(approved=True, feedback="Looks good!")
        assert result.approved is True
        assert result.feedback == "Looks good!"

    def test_consensus_result_rejected_with_feedback(self) -> None:
        """ConsensusResult should accept approved=False with feedback."""
        result = ConsensusResult(approved=False, feedback="Needs revision")
        assert result.approved is False
        assert result.feedback == "Needs revision"

    def test_consensus_result_approved_without_feedback(self) -> None:
        """ConsensusResult should accept approved=True without feedback."""
        result = ConsensusResult(approved=True, feedback=None)
        assert result.approved is True
        assert result.feedback is None

    def test_consensus_result_rejected_without_feedback(self) -> None:
        """ConsensusResult should accept approved=False without feedback."""
        result = ConsensusResult(approved=False, feedback=None)
        assert result.approved is False
        assert result.feedback is None


class TestParseConsensusResponseApprove:
    """Tests for parsing APPROVE responses."""

    def test_parse_simple_approve(self) -> None:
        """Should parse simple APPROVE response."""
        content = "APPROVE"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approved(self) -> None:
        """Should parse APPROVED response (past tense)."""
        content = "APPROVED"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approval(self) -> None:
        """Should parse APPROVAL response (noun form)."""
        content = "APPROVAL"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approve_lowercase(self) -> None:
        """Should parse lowercase approve."""
        content = "approve"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approve_mixed_case(self) -> None:
        """Should parse mixed case Approve."""
        content = "Approve"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approve_with_feedback(self) -> None:
        """Should parse APPROVE with feedback text."""
        content = """APPROVE

The synthesis effectively integrates Wind's expansion with Wall's constraints.
The implementation path is clear and actionable."""
        result = parse_consensus_response(content)
        assert result.approved is True
        assert result.feedback is not None
        assert "synthesis" in result.feedback.lower()

    def test_parse_approve_with_colon(self) -> None:
        """Should parse APPROVE: with colon prefix."""
        content = "APPROVE: This is well-reasoned synthesis."
        result = parse_consensus_response(content)
        assert result.approved is True
        assert result.feedback is not None
        assert "well-reasoned" in result.feedback


class TestParseConsensusResponseReject:
    """Tests for parsing REJECT responses."""

    def test_parse_simple_reject(self) -> None:
        """Should parse simple REJECT response."""
        content = "REJECT"
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_rejected(self) -> None:
        """Should parse REJECTED response (past tense)."""
        content = "REJECTED"
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_rejection(self) -> None:
        """Should parse REJECTION response (noun form)."""
        content = "REJECTION"
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_reject_lowercase(self) -> None:
        """Should parse lowercase reject."""
        content = "reject"
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_reject_mixed_case(self) -> None:
        """Should parse mixed case Reject."""
        content = "Reject"
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_reject_with_feedback(self) -> None:
        """Should parse REJECT with feedback text."""
        content = """REJECT

The synthesis fails to address the critical constraint raised by Wall.
The implementation path needs to account for the security implications."""
        result = parse_consensus_response(content)
        assert result.approved is False
        assert result.feedback is not None
        assert "security" in result.feedback.lower()

    def test_parse_reject_with_colon(self) -> None:
        """Should parse REJECT: with colon prefix."""
        content = "REJECT: Missing consideration of edge cases."
        result = parse_consensus_response(content)
        assert result.approved is False
        assert result.feedback is not None
        assert "edge cases" in result.feedback


class TestParseConsensusResponseEdgeCases:
    """Tests for edge cases in consensus parsing."""

    def test_parse_approve_with_leading_whitespace(self) -> None:
        """Should handle leading whitespace."""
        content = "   APPROVE"
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_reject_with_trailing_whitespace(self) -> None:
        """Should handle trailing whitespace."""
        content = "REJECT   "
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_approve_on_second_line(self) -> None:
        """Should find APPROVE on non-first line."""
        content = """## WIND (PATHOS) - Consensus Review

APPROVE

The synthesis captures the essential tension."""
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_approve_in_structured_format(self) -> None:
        """Should parse APPROVE in OCTAVE-style structured response."""
        content = """## WIND (PATHOS) - Consensus Vote

### VERDICT
APPROVE

### REASONING
The synthesis demonstrates emergent integration."""
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_parse_reject_in_structured_format(self) -> None:
        """Should parse REJECT in OCTAVE-style structured response."""
        content = """## WALL (ETHOS) - Consensus Vote

### VERDICT
REJECT

### REASONING
Insufficient evidence for the proposed implementation."""
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_ambiguous_defaults_to_reject(self) -> None:
        """Ambiguous response without clear APPROVE/REJECT should default to reject."""
        content = "I think this needs more work."
        result = parse_consensus_response(content)
        assert result.approved is False
        assert result.feedback is not None

    def test_parse_empty_string_defaults_to_reject(self) -> None:
        """Empty string should default to reject."""
        content = ""
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_parse_whitespace_only_defaults_to_reject(self) -> None:
        """Whitespace-only should default to reject."""
        content = "   \n\t  "
        result = parse_consensus_response(content)
        assert result.approved is False

    def test_approve_takes_precedence_when_both_present(self) -> None:
        """When both APPROVE and REJECT appear, first one wins."""
        content = """APPROVE

This is good, though I considered REJECT initially."""
        result = parse_consensus_response(content)
        assert result.approved is True

    def test_reject_first_when_before_approve(self) -> None:
        """When REJECT appears before APPROVE, REJECT wins."""
        content = """REJECT

The synthesis mentions APPROVE but I disagree."""
        result = parse_consensus_response(content)
        assert result.approved is False
