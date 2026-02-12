"""Consensus response parsing for debate-hall-mcp auto-orchestration (Phase 4).

This module implements:
- ConsensusResult: Model for parsed consensus vote
- parse_consensus_response: Parser for APPROVE/REJECT responses

The consensus mechanism enables Wind and Wall to review Door's synthesis
and vote on whether it adequately represents their perspectives.

Parsing Strategy:
- Fuzzy matching for APPROVE/APPROVED/APPROVAL and REJECT/REJECTED/REJECTION
- Case-insensitive matching
- First match wins when both appear
- Feedback extraction from remaining content
- Defaults to REJECT if no clear decision found (fail-safe)
"""

import re

from pydantic import BaseModel, Field


class ConsensusResult(BaseModel):
    """Result of parsing a consensus vote response.

    Fields:
    - approved: Whether the agent voted to approve the synthesis
    - feedback: Optional feedback text (especially useful for rejections)
    """

    approved: bool = Field(..., description="Whether the vote is APPROVE (True) or REJECT (False)")
    feedback: str | None = Field(default=None, description="Optional feedback from the reviewer")


# Patterns for matching approval/rejection keywords
# Using word boundaries to avoid false matches in prose
# YIELD is added for Speed mode (Issue #139) - counts as implicit approval
APPROVE_PATTERN = re.compile(r"\b(APPROVE|APPROVED|APPROVAL|YIELD)\b", re.IGNORECASE)
REJECT_PATTERN = re.compile(r"\b(REJECT|REJECTED|REJECTION)\b", re.IGNORECASE)


def parse_consensus_response(content: str) -> ConsensusResult:
    """Parse a consensus vote response to extract APPROVE/REJECT decision.

    Parsing rules:
    1. Search for APPROVE/APPROVED/APPROVAL or REJECT/REJECTED/REJECTION
    2. Case-insensitive matching
    3. First keyword found determines the vote (position-based priority)
    4. Extract remaining content as feedback
    5. If no clear keyword found, default to REJECT (fail-safe)

    Args:
        content: The full response content from Wind or Wall

    Returns:
        ConsensusResult with approved status and optional feedback
    """
    if not content or not content.strip():
        return ConsensusResult(approved=False, feedback=None)

    # Find positions of first APPROVE and REJECT keywords
    approve_match = APPROVE_PATTERN.search(content)
    reject_match = REJECT_PATTERN.search(content)

    # Determine which keyword appears first (if any)
    approve_pos = approve_match.start() if approve_match else float("inf")
    reject_pos = reject_match.start() if reject_match else float("inf")

    if approve_pos == float("inf") and reject_pos == float("inf"):
        # No clear keyword found - default to reject with content as feedback
        return ConsensusResult(approved=False, feedback=content.strip())

    # First keyword wins
    approved = approve_pos < reject_pos

    # Extract feedback: everything after the keyword match
    if approved and approve_match:
        keyword_end = approve_match.end()
    elif not approved and reject_match:
        keyword_end = reject_match.end()
    else:
        keyword_end = 0

    # Get content after keyword, cleaning up formatting
    remaining = content[keyword_end:].strip()

    # Remove leading colon, dash, or newlines
    remaining = re.sub(r"^[\s:.\-\n]+", "", remaining).strip()

    feedback = remaining if remaining else None

    return ConsensusResult(approved=approved, feedback=feedback)
