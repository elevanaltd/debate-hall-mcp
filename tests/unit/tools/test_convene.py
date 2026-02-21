"""Tests for convene tool — committee decision sessions (Issue #178).

Phase 3 of the governance chat API epic (#173).

TDD Discipline: RED phase — these tests define the contract for the convene tool.
"""

import re
from pathlib import Path

import pytest

from debate_hall_mcp.state import SessionType, load_debate_state
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn

# --- Helper to import convene (will fail in RED phase) ---


def _convene(**kwargs):  # type: ignore[no-untyped-def]
    """Helper to call convene tool."""
    from debate_hall_mcp.tools.convene import convene

    return convene(**kwargs)


# --- Basic Creation ---


class TestConveneCreation:
    """Tests for convene tool creating committee sessions."""

    def test_convene_creates_committee_session(self, tmp_path: Path) -> None:
        """convene() creates a session with session_type=committee."""
        result = _convene(
            topic="Review PR #491",
            members=["CRS", "CE"],
            brief="Review this PR for production readiness",
            state_dir=tmp_path,
        )

        assert result["status"] == "active"
        assert result["session_type"] == "committee"
        assert result["decision_type"] == "review"
        assert result["chair_role"] == "Chair"
        assert result["members"] == ["CRS", "CE"]
        assert result["awaiting"] == ["CRS", "CE"]
        assert result["turn_count"] == 1
        assert "thread_id" in result

    def test_convene_with_custom_chair(self, tmp_path: Path) -> None:
        """convene() accepts custom chair_role."""
        result = _convene(
            topic="Architecture review",
            members=["CRS"],
            brief="Review architecture",
            chair_role="TechLead",
            state_dir=tmp_path,
        )

        assert result["chair_role"] == "TechLead"

    def test_convene_with_go_nogo_decision_type(self, tmp_path: Path) -> None:
        """convene() accepts go_nogo decision type."""
        result = _convene(
            topic="Production deploy",
            members=["CRS", "CE"],
            brief="Deploy to production?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )

        assert result["decision_type"] == "go_nogo"

    def test_convene_with_vote_decision_type(self, tmp_path: Path) -> None:
        """convene() accepts vote decision type."""
        result = _convene(
            topic="Feature selection",
            members=["CRS", "CE"],
            brief="Which feature to build?",
            decision_type="vote",
            state_dir=tmp_path,
        )

        assert result["decision_type"] == "vote"

    def test_convene_with_custom_thread_id(self, tmp_path: Path) -> None:
        """convene() accepts custom thread_id."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR",
            thread_id="2026-02-21-custom-thread-id",
            state_dir=tmp_path,
        )

        assert result["thread_id"] == "2026-02-21-custom-thread-id"

    def test_convene_auto_generates_thread_id(self, tmp_path: Path) -> None:
        """convene() auto-generates thread_id following date-slug-ulid pattern."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR",
            state_dir=tmp_path,
        )

        thread_id = result["thread_id"]
        # Should match YYYY-MM-DD-slug-ulid8 pattern
        assert re.match(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+-[a-z0-9]{8}$", thread_id)

    def test_convene_with_context(self, tmp_path: Path) -> None:
        """convene() prepends context to brief in first turn."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR for quality",
            context="PR changes auth module",
            state_dir=tmp_path,
        )

        # Load room and check first turn content
        room = load_debate_state(result["thread_id"], tmp_path)
        first_turn = room.turns[0]
        assert "[CONTEXT]" in first_turn.content
        assert "PR changes auth module" in first_turn.content
        assert "[/CONTEXT]" in first_turn.content
        assert "Review this PR for quality" in first_turn.content

    def test_convene_brief_without_context(self, tmp_path: Path) -> None:
        """convene() records brief as-is when no context provided."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR for quality",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        first_turn = room.turns[0]
        assert first_turn.content == "Review this PR for quality"
        assert "[CONTEXT]" not in first_turn.content

    def test_convene_brief_recorded_with_chair_role(self, tmp_path: Path) -> None:
        """convene() records brief as first turn with chair_role."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR",
            chair_role="TechLead",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        first_turn = room.turns[0]
        assert first_turn.role == "TechLead"

    def test_convene_custom_max_turns(self, tmp_path: Path) -> None:
        """convene() sets custom max_turns on the room."""
        result = _convene(
            topic="Review PR",
            members=["CRS"],
            brief="Review this PR",
            max_turns=20,
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.max_turns == 20


class TestConveneRoomState:
    """Tests for room state after convene."""

    def test_convene_room_is_mediated(self, tmp_path: Path) -> None:
        """convene() creates room with mode=mediated."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.mode.value == "mediated"

    def test_convene_room_session_type(self, tmp_path: Path) -> None:
        """convene() creates room with session_type=committee."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.session_type == SessionType.COMMITTEE

    def test_convene_participants_include_chair_and_members(self, tmp_path: Path) -> None:
        """convene() sets participants list with chair + all members."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            chair_role="TechLead",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.participants is not None
        roles = [p.role for p in room.participants]
        assert "TechLead" in roles
        assert "CRS" in roles
        assert "CE" in roles
        assert len(roles) == 3

    def test_convene_committee_metadata(self, tmp_path: Path) -> None:
        """convene() sets committee_metadata with correct fields."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.committee_metadata is not None
        assert room.committee_metadata.decision_type == "go_nogo"
        assert room.committee_metadata.members == ["CRS", "CE"]
        assert room.committee_metadata.responses == {}
        assert room.committee_metadata.awaiting == ["CRS", "CE"]
        assert room.committee_metadata.decision is None


# --- Validation ---


class TestConveneValidation:
    """Tests for convene tool input validation."""

    def test_empty_members_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for empty members list."""
        with pytest.raises(ValueError, match="at least 1"):
            _convene(
                topic="Review PR",
                members=[],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_duplicate_members_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for duplicate members."""
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            _convene(
                topic="Review PR",
                members=["CRS", "CRS"],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_chair_in_members_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError if chair_role appears in members."""
        with pytest.raises(ValueError, match="[Cc]hair"):
            _convene(
                topic="Review PR",
                members=["CRS", "Chair"],
                brief="Review this PR",
                chair_role="Chair",
                state_dir=tmp_path,
            )

    def test_invalid_decision_type_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for invalid decision_type."""
        with pytest.raises(ValueError, match="decision_type"):
            _convene(
                topic="Review PR",
                members=["CRS"],
                brief="Review this PR",
                decision_type="invalid",
                state_dir=tmp_path,
            )

    def test_empty_brief_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for empty brief."""
        with pytest.raises(ValueError, match="[Bb]rief"):
            _convene(
                topic="Review PR",
                members=["CRS"],
                brief="",
                state_dir=tmp_path,
            )

    def test_whitespace_brief_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for whitespace-only brief."""
        with pytest.raises(ValueError, match="[Bb]rief"):
            _convene(
                topic="Review PR",
                members=["CRS"],
                brief="   ",
                state_dir=tmp_path,
            )

    def test_empty_topic_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for empty topic."""
        with pytest.raises(ValueError, match="[Tt]opic"):
            _convene(
                topic="",
                members=["CRS"],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_empty_member_role_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for empty member role string."""
        with pytest.raises(ValueError, match="[Rr]ole|[Mm]ember"):
            _convene(
                topic="Review PR",
                members=["CRS", ""],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_non_ascii_member_role_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for non-ASCII member role."""
        with pytest.raises(ValueError, match="ASCII|printable"):
            _convene(
                topic="Review PR",
                members=["CRS", "\x00bad"],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_member_role_too_long_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for member role exceeding 128 chars."""
        with pytest.raises(ValueError, match="128|length"):
            _convene(
                topic="Review PR",
                members=["A" * 129],
                brief="Review this PR",
                state_dir=tmp_path,
            )

    def test_empty_chair_role_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError for empty chair_role."""
        with pytest.raises(ValueError, match="[Rr]ole|[Cc]hair"):
            _convene(
                topic="Review PR",
                members=["CRS"],
                brief="Review this PR",
                chair_role="",
                state_dir=tmp_path,
            )

    def test_existing_thread_id_raises(self, tmp_path: Path) -> None:
        """convene() raises ValueError/FileExistsError if thread_id already exists."""
        _convene(
            topic="First committee",
            members=["CRS"],
            brief="First brief",
            thread_id="2026-02-21-duplicate-test",
            state_dir=tmp_path,
        )

        with pytest.raises((ValueError, FileExistsError)):
            _convene(
                topic="Second committee",
                members=["CE"],
                brief="Second brief",
                thread_id="2026-02-21-duplicate-test",
                state_dir=tmp_path,
            )


# --- Committee Member Tracking ---


class TestCommitteeMemberTracking:
    """Tests for committee member tracking via add_turn."""

    def test_member_turn_removes_from_awaiting(self, tmp_path: Path) -> None:
        """When a member adds a turn, they're removed from awaiting."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Pick and add turn for CRS
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="Looks good to me",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert "CRS" not in room.committee_metadata.awaiting
        assert "CE" in room.committee_metadata.awaiting

    def test_member_turn_adds_to_responses(self, tmp_path: Path) -> None:
        """When a member adds a turn, their response is recorded."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="Code quality meets standards",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert "CRS" in room.committee_metadata.responses

    def test_non_member_turn_does_not_affect_tracking(self, tmp_path: Path) -> None:
        """Chair turn does not affect awaiting/responses."""
        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            chair_role="TechLead",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Chair adds another turn
        debate_pick(thread_id=thread_id, role="TechLead", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="TechLead",
            content="Please review carefully",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["CRS", "CE"]
        assert room.committee_metadata.responses == {}


class TestGoNoGoExtraction:
    """Tests for GO/NO-GO extraction in go_nogo decision_type."""

    def test_go_extracted_from_content(self, tmp_path: Path) -> None:
        """For go_nogo: 'GO' is extracted from turn content."""
        result = _convene(
            topic="Deploy review",
            members=["CRS"],
            brief="Ready to deploy?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO — code quality meets standards, coverage at 92%",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.responses["CRS"] == "GO"

    def test_nogo_extracted_from_content(self, tmp_path: Path) -> None:
        """For go_nogo: 'NO-GO' is extracted from turn content."""
        result = _convene(
            topic="Deploy review",
            members=["CE"],
            brief="Ready to deploy?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="NO-GO — security concern in auth module line 47",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.responses["CE"] == "NO-GO"

    def test_nogo_variant_extracted(self, tmp_path: Path) -> None:
        """For go_nogo: 'NOGO' variant is extracted."""
        result = _convene(
            topic="Deploy review",
            members=["CE"],
            brief="Ready to deploy?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="NOGO - missing test coverage",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.responses["CE"] == "NO-GO"

    def test_go_nogo_extraction_fails_stores_full_content(self, tmp_path: Path) -> None:
        """For go_nogo: if extraction fails, full content is stored."""
        result = _convene(
            topic="Deploy review",
            members=["CRS"],
            brief="Ready to deploy?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="I think we should wait for more testing",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.responses["CRS"] == "I think we should wait for more testing"

    def test_review_type_stores_full_content(self, tmp_path: Path) -> None:
        """For review decision_type: full content is always stored."""
        result = _convene(
            topic="Code review",
            members=["CRS"],
            brief="Review this code",
            decision_type="review",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO — looks good",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        # For review type, should store full content, not extract GO
        assert room.committee_metadata.responses["CRS"] == "GO — looks good"


# --- get_debate Integration ---


class TestConveneGetDebate:
    """Tests for get_debate with committee sessions."""

    def test_get_debate_returns_committee_metadata(self, tmp_path: Path) -> None:
        """get_debate() returns committee_metadata for committee sessions."""
        from debate_hall_mcp.tools.get import debate_get

        result = _convene(
            topic="Review PR",
            members=["CRS", "CE"],
            brief="Review this PR",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )

        get_result = debate_get(
            thread_id=result["thread_id"],
            state_dir=tmp_path,
        )

        assert get_result["session_type"] == "committee"
        assert "committee_metadata" in get_result
        assert get_result["committee_metadata"]["decision_type"] == "go_nogo"
        assert get_result["committee_metadata"]["members"] == ["CRS", "CE"]
        assert get_result["committee_metadata"]["awaiting"] == ["CRS", "CE"]


# --- Three-Member Full Flow ---


class TestThreeMemberFlow:
    """Integration test for three-member committee sequential flow."""

    def test_three_member_sequential_flow(self, tmp_path: Path) -> None:
        """Three-member committee: sequential picks and turns, awaiting shrinks correctly."""
        result = _convene(
            topic="Production readiness",
            members=["CRS", "CE", "TMG"],
            brief="Is the system ready for production?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]
        assert result["awaiting"] == ["CRS", "CE", "TMG"]

        # CRS responds GO
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO — code quality meets standards",
            state_dir=tmp_path,
        )
        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["CE", "TMG"]
        assert room.committee_metadata.responses["CRS"] == "GO"

        # CE responds NO-GO
        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="NO-GO — security vulnerability in auth module",
            state_dir=tmp_path,
        )
        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["TMG"]
        assert room.committee_metadata.responses["CE"] == "NO-GO"

        # TMG responds GO
        debate_pick(thread_id=thread_id, role="TMG", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="GO — testing coverage is sufficient",
            state_dir=tmp_path,
        )
        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert room.committee_metadata.responses["TMG"] == "GO"
        assert len(room.committee_metadata.responses) == 3


class TestConveneSlugEdgeCases:
    """Thread ID slug generation handles edge-case topics."""

    def test_leading_whitespace_topic(self, tmp_path: Path) -> None:
        """Topics with leading whitespace produce valid thread IDs."""
        result = _convene(
            topic="  hello world",
            members=["CRS"],
            brief="Review",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}-[a-zA-Z0-9]", tid)

    def test_emoji_only_topic(self, tmp_path: Path) -> None:
        """Emoji-only topics fall back to 'committee' slug."""
        result = _convene(
            topic="\U0001f525\U0001f525",
            members=["CRS"],
            brief="Review",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        assert "committee" in tid

    def test_multiple_spaces_topic(self, tmp_path: Path) -> None:
        """Topics with multiple spaces don't produce consecutive hyphens."""
        result = _convene(
            topic="hello   world",
            members=["CRS"],
            brief="Review",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        # No double hyphens before the ULID suffix
        parts = tid.rsplit("-", 1)  # Split off ULID
        assert "--" not in parts[0]
