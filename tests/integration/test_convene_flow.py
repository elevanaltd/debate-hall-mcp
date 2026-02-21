"""Integration tests for full convene lifecycle — Issue #179.

Phase 4 of the governance chat API epic (#173).

Tests the complete committee decision flow end-to-end:
convene() -> pick_next_speaker() -> add_turn(member) -> close_debate()

Scenarios:
- GO/NO-GO committee with split decision
- Review committee with three members
- Committee metadata tracking (responses, awaiting)
- Hash chain integrity across committee turns

TDD Discipline: RED phase — failing tests written before any GREEN implementation.
"""

from pathlib import Path

from debate_hall_mcp.state import (
    SessionType,
    load_debate_state,
)
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.convene import convene
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn


class TestConveneGoNoGoLifecycle:
    """Full GO/NO-GO committee lifecycle."""

    def test_go_nogo_committee_with_split_decision(self, tmp_path: Path) -> None:
        """GO/NO-GO committee: CRS=GO, CE=NO-GO, close with synthesis.

        Flow:
        1. convene(go_nogo) creates committee
        2. pick_next_speaker("CRS") + add_turn(GO)
        3. Verify CRS removed from awaiting
        4. pick_next_speaker("CE") + add_turn(NO-GO)
        5. Verify CE removed from awaiting, responses populated
        6. close_debate() with decision synthesis
        7. Verify complete transcript and committee_metadata
        """
        # Step 1: Convene committee
        result = convene(
            topic="PR #491 production readiness",
            members=["CRS", "CE"],
            brief="Review PR #491 implementation for production readiness",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )

        assert result["status"] == "active"
        assert result["session_type"] == "committee"
        assert result["decision_type"] == "go_nogo"
        assert result["members"] == ["CRS", "CE"]
        assert result["awaiting"] == ["CRS", "CE"]
        assert result["turn_count"] == 1
        thread_id = result["thread_id"]

        # Step 2: CRS responds GO
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- code quality meets standards, coverage at 92%",
            state_dir=tmp_path,
        )

        # Step 3: Verify CRS removed from awaiting
        room = load_debate_state(thread_id, tmp_path)
        assert "CRS" not in room.committee_metadata.awaiting
        assert "CE" in room.committee_metadata.awaiting
        assert room.committee_metadata.responses["CRS"] == "GO"

        # Step 4: CE responds NO-GO
        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="NO-GO -- security concern in auth module line 47",
            state_dir=tmp_path,
        )

        # Step 5: Verify CE removed, responses fully populated
        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert room.committee_metadata.responses["CE"] == "NO-GO"
        assert len(room.committee_metadata.responses) == 2

        # Step 6: Close with synthesis
        close_result = debate_close(
            thread_id=thread_id,
            synthesis="NO-GO: CE identified security concern in auth module. "
            "CRS approved code quality. Decision: block until security resolved.",
            state_dir=tmp_path,
            output_format="json",
        )
        assert close_result["thread_id"] == thread_id

        # Step 7: Verify final state
        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"
        assert room.session_type == SessionType.COMMITTEE
        assert len(room.turns) == 3  # brief + CRS + CE
        assert room.turns[0].role == "Chair"
        assert room.turns[1].role == "CRS"
        assert room.turns[2].role == "CE"

    def test_go_nogo_all_go_decision(self, tmp_path: Path) -> None:
        """GO/NO-GO committee where all members vote GO."""
        result = convene(
            topic="Deployment approval",
            members=["CRS", "CE"],
            brief="Approve deployment to production?",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Both members vote GO
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- all quality gates pass",
            state_dir=tmp_path,
        )

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="GO -- no security issues found",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert room.committee_metadata.responses == {"CRS": "GO", "CE": "GO"}

        debate_close(
            thread_id=thread_id,
            synthesis="GO: Unanimous approval from CRS and CE. Deploy approved.",
            state_dir=tmp_path,
            output_format="json",
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"


class TestConveneReviewLifecycle:
    """Full review committee lifecycle with three members."""

    def test_three_member_review_committee(self, tmp_path: Path) -> None:
        """Three-member review committee: sequential picks and responses.

        Flow:
        1. convene(review, members=[CRS, CE, PE]) creates 3-member committee
        2. Sequential pick + turn for each member
        3. Verify awaiting list shrinks correctly after each turn
        4. Close with synthesis
        """
        result = convene(
            topic="Architecture review for v2",
            members=["CRS", "CE", "PE"],
            brief="Review proposed architecture changes for v2 release",
            decision_type="review",
            state_dir=tmp_path,
        )

        assert result["members"] == ["CRS", "CE", "PE"]
        assert result["awaiting"] == ["CRS", "CE", "PE"]
        thread_id = result["thread_id"]

        # CRS reviews
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="Code structure looks clean. Suggest adding error boundaries.",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["CE", "PE"]
        # For review type, full content stored — I4 exact preservation
        assert (
            room.committee_metadata.responses["CRS"]
            == "Code structure looks clean. Suggest adding error boundaries."
        )

        # CE reviews
        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="Performance implications need benchmarking before approval.",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["PE"]

        # PE reviews
        debate_pick(thread_id=thread_id, role="PE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="PE",
            content="Architecture aligns with long-term scalability goals.",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert len(room.committee_metadata.responses) == 3

        # Close
        debate_close(
            thread_id=thread_id,
            synthesis="Three reviews complete. CRS suggests error boundaries, "
            "CE requires benchmarking, PE approves scalability alignment.",
            state_dir=tmp_path,
            output_format="json",
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"
        assert len(room.turns) == 4  # brief + 3 reviews

    def test_review_with_custom_chair(self, tmp_path: Path) -> None:
        """Review committee with custom chair_role."""
        result = convene(
            topic="Custom chair review",
            members=["CRS", "CE"],
            brief="Review with custom chair",
            chair_role="TechLead",
            decision_type="review",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        assert result["chair_role"] == "TechLead"

        # Verify chair's turn is recorded with custom role
        room = load_debate_state(thread_id, tmp_path)
        assert room.turns[0].role == "TechLead"

        # Participants include custom chair
        assert room.participants is not None
        roles = [p.role for p in room.participants]
        assert "TechLead" in roles
        assert "CRS" in roles
        assert "CE" in roles


class TestConveneChairAdditionalTurns:
    """Chair can add extra turns without affecting member tracking."""

    def test_chair_turn_does_not_affect_awaiting(self, tmp_path: Path) -> None:
        """Chair adding a turn does not remove anyone from awaiting."""
        result = convene(
            topic="Chair turns test",
            members=["CRS", "CE"],
            brief="Initial brief",
            chair_role="TechLead",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Chair adds clarification
        debate_pick(thread_id=thread_id, role="TechLead", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="TechLead",
            content="Please focus on security aspects specifically.",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == ["CRS", "CE"]
        assert room.committee_metadata.responses == {}


class TestConveneHashChainIntegrity:
    """Verify hash chain integrity across committee lifecycle (I4)."""

    def test_hash_chain_continuous_through_committee(self, tmp_path: Path) -> None:
        """Hash chain is continuous across brief + member turns + close."""
        result = convene(
            topic="Hash chain committee test",
            members=["CRS", "CE"],
            brief="Testing hash chain in committee sessions",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Member turns
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- hash chain test response from CRS",
            state_dir=tmp_path,
        )

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="GO -- hash chain test response from CE",
            state_dir=tmp_path,
        )

        # Verify hash chain
        room = load_debate_state(thread_id, tmp_path)
        assert len(room.turns) == 3

        for i in range(1, len(room.turns)):
            prev_turn = room.turns[i - 1]
            curr_turn = room.turns[i]
            assert curr_turn.previous_hash is not None
            assert prev_turn.hash is not None
            assert (
                curr_turn.previous_hash == prev_turn.hash
            ), f"Turn {i} prev_hash should match turn {i-1} content_hash"


class TestConveneGetDebateIntegration:
    """Verify get_debate returns committee metadata correctly."""

    def test_get_debate_returns_committee_metadata(self, tmp_path: Path) -> None:
        """get_debate() returns committee_metadata for committee sessions."""
        result = convene(
            topic="Get debate committee test",
            members=["CRS", "CE"],
            brief="Testing get_debate on committee",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)

        assert debate_info["session_type"] == "committee"
        assert "committee_metadata" in debate_info
        meta = debate_info["committee_metadata"]
        assert meta["decision_type"] == "go_nogo"
        assert meta["members"] == ["CRS", "CE"]
        assert meta["awaiting"] == ["CRS", "CE"]
        assert meta["responses"] == {}

    def test_get_debate_reflects_member_responses(self, tmp_path: Path) -> None:
        """get_debate() shows updated awaiting/responses after member turns."""
        result = convene(
            topic="Response tracking test",
            members=["CRS", "CE"],
            brief="Test response tracking",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # CRS responds
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- approved",
            state_dir=tmp_path,
        )

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)
        meta = debate_info["committee_metadata"]
        assert "CRS" not in meta["awaiting"]
        assert "CE" in meta["awaiting"]
        assert meta["responses"]["CRS"] == "GO"

    def test_get_debate_with_transcript_for_committee(self, tmp_path: Path) -> None:
        """get_debate(include_transcript=True) returns committee conversation."""
        result = convene(
            topic="Transcript committee test",
            members=["CRS"],
            brief="Committee transcript test",
            decision_type="review",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="Reviewed and approved.",
            state_dir=tmp_path,
        )

        debate_info = debate_get(
            thread_id=thread_id,
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert debate_info["turn_count"] == 2
        transcript = debate_info["transcript"]
        # Transcript includes System OCTAVE preamble + actual turns
        assert transcript[0]["role"] == "System"
        assert transcript[1]["role"] == "Chair"
        assert transcript[2]["role"] == "CRS"

    def test_get_debate_participants_for_committee(self, tmp_path: Path) -> None:
        """get_debate() returns participants list with chair and members."""
        result = convene(
            topic="Participants test",
            members=["CRS", "CE", "PE"],
            brief="Test participants",
            chair_role="TechLead",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)

        assert debate_info["participants"] is not None
        roles = [p["role"] for p in debate_info["participants"]]
        assert "TechLead" in roles
        assert "CRS" in roles
        assert "CE" in roles
        assert "PE" in roles
        assert len(roles) == 4


class TestConveneWithContext:
    """Committee sessions with context parameter."""

    def test_convene_with_context_includes_context_block(self, tmp_path: Path) -> None:
        """convene() with context prepends [CONTEXT] block to brief."""
        result = convene(
            topic="Context committee test",
            members=["CRS"],
            brief="Review the PR for production readiness",
            context="PR #491 modifies the authentication module.",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        room = load_debate_state(thread_id, tmp_path)
        first_turn = room.turns[0]
        assert "[CONTEXT]" in first_turn.content
        assert "PR #491 modifies the authentication module." in first_turn.content
        assert "[/CONTEXT]" in first_turn.content
        assert "Review the PR for production readiness" in first_turn.content


class TestConveneVoteLifecycle:
    """Full vote committee lifecycle (decision_type='vote').

    Contract: docs/173-governance-chat-api-contract.md:111 documents
    decision_type="vote" but integration tests only exercised go_nogo
    and review. This class fills that gap.
    """

    def test_vote_committee_full_lifecycle(self, tmp_path: Path) -> None:
        """Vote committee: create, members vote, close with synthesis.

        Flow:
        1. convene(vote, members=[CRS, CE, PE]) creates a vote committee
        2. Each member casts a vote via pick + turn
        3. Verify committee_metadata reflects vote responses
        4. close_debate() with synthesis
        5. Verify final state
        """
        result = convene(
            topic="ADR-042 naming convention vote",
            members=["CRS", "CE", "PE"],
            brief="Vote on proposed naming convention for ADR-042",
            decision_type="vote",
            state_dir=tmp_path,
        )

        assert result["status"] == "active"
        assert result["session_type"] == "committee"
        assert result["decision_type"] == "vote"
        assert result["members"] == ["CRS", "CE", "PE"]
        assert result["awaiting"] == ["CRS", "CE", "PE"]
        thread_id = result["thread_id"]

        # CRS votes
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="APPROVE -- naming convention is clear and consistent",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert "CRS" not in room.committee_metadata.awaiting
        assert "CE" in room.committee_metadata.awaiting
        assert "PE" in room.committee_metadata.awaiting
        # Vote type stores full content (not parsed like go_nogo) — I4 exact preservation
        assert (
            room.committee_metadata.responses["CRS"]
            == "APPROVE -- naming convention is clear and consistent"
        )

        # CE votes
        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="REJECT -- prefer snake_case over camelCase",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert "CE" not in room.committee_metadata.awaiting
        assert (
            room.committee_metadata.responses["CE"] == "REJECT -- prefer snake_case over camelCase"
        )

        # PE votes
        debate_pick(thread_id=thread_id, role="PE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="PE",
            content="APPROVE -- aligns with long-term architecture goals",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert len(room.committee_metadata.responses) == 3

        # Close with synthesis
        close_result = debate_close(
            thread_id=thread_id,
            synthesis="Vote result: 2 APPROVE (CRS, PE), 1 REJECT (CE). "
            "Motion carries by majority. ADR-042 naming convention adopted.",
            state_dir=tmp_path,
            output_format="json",
        )
        assert close_result["thread_id"] == thread_id

        # Verify final state
        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"
        assert room.session_type == SessionType.COMMITTEE
        assert len(room.turns) == 4  # brief + 3 votes
        assert room.committee_metadata.decision_type == "vote"
        assert room.turns[0].role == "Chair"
        assert room.turns[1].role == "CRS"
        assert room.turns[2].role == "CE"
        assert room.turns[3].role == "PE"

    def test_vote_committee_unanimous(self, tmp_path: Path) -> None:
        """Vote committee with unanimous approval."""
        result = convene(
            topic="Unanimous vote test",
            members=["CRS", "CE"],
            brief="Vote on simple proposal",
            decision_type="vote",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="YES -- fully in favor",
            state_dir=tmp_path,
        )

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="YES -- agreed",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.committee_metadata.awaiting == []
        assert len(room.committee_metadata.responses) == 2
        assert room.committee_metadata.responses["CRS"] == "YES -- fully in favor"
        assert room.committee_metadata.responses["CE"] == "YES -- agreed"

        debate_close(
            thread_id=thread_id,
            synthesis="Unanimous YES. Proposal adopted.",
            state_dir=tmp_path,
            output_format="json",
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"

    def test_vote_metadata_visible_via_get_debate(self, tmp_path: Path) -> None:
        """get_debate() returns vote committee metadata correctly."""
        result = convene(
            topic="Vote get_debate test",
            members=["CRS", "CE"],
            brief="Vote visibility test",
            decision_type="vote",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)

        assert debate_info["session_type"] == "committee"
        meta = debate_info["committee_metadata"]
        assert meta["decision_type"] == "vote"
        assert meta["members"] == ["CRS", "CE"]
        assert meta["awaiting"] == ["CRS", "CE"]

        # After one member votes
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="ABSTAIN -- need more information",
            state_dir=tmp_path,
        )

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)
        meta = debate_info["committee_metadata"]
        assert "CRS" not in meta["awaiting"]
        assert meta["responses"]["CRS"] == "ABSTAIN -- need more information"
