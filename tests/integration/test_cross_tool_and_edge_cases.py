"""Integration tests for cross-tool interactions and edge cases — Issue #179.

Phase 4 of the governance chat API epic (#173).

Tests:
- Cross-tool interaction: consult/convene with get_debate, force_close, tombstone
- Edge cases from B0 observations: exhaustion (I3), force_close on sessions (I5)
- Backward compatibility: standard debate still works alongside new session types

TDD Discipline: RED phase — failing tests written before any GREEN implementation.
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    DebateStatus,
    SessionType,
    load_debate_state,
)
from debate_hall_mcp.tools.admin import (
    debate_force_close,
    debate_tombstone,
)
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.consult import consult
from debate_hall_mcp.tools.convene import convene
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn

# --- Cross-Tool: force_close on consultation/committee sessions (I5) ---


class TestForceCloseOnGovernanceSessions:
    """force_close_debate works on consultation and committee sessions (I5)."""

    def test_force_close_consultation(self, tmp_path: Path) -> None:
        """force_close_debate() terminates an active consultation session."""
        result = consult(
            topic="Force close consultation test",
            advisor_role="TMG",
            question="Will this be force closed?",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Force close the consultation
        fc_result = debate_force_close(
            thread_id=thread_id,
            reason="Emergency: content policy violation detected",
            state_dir=tmp_path,
        )

        assert fc_result["status"] == "force_closed"
        assert "Emergency" in fc_result["reason"]

        # Verify room state
        room = load_debate_state(thread_id, tmp_path)
        assert room.status == DebateStatus.FORCE_CLOSED
        assert room.session_type == SessionType.CONSULTATION

        # Verify no more turns can be added — each call independently validated
        with pytest.raises(ValueError, match="Debate is not active"):
            debate_pick(thread_id=thread_id, role="TMG", state_dir=tmp_path)

        with pytest.raises(ValueError, match="debate is not active"):
            debate_turn(
                thread_id=thread_id,
                role="TMG",
                content="This should fail",
                state_dir=tmp_path,
            )

    def test_force_close_committee(self, tmp_path: Path) -> None:
        """force_close_debate() terminates an active committee session."""
        result = convene(
            topic="Force close committee test",
            members=["CRS", "CE"],
            brief="Committee to be force closed",
            decision_type="go_nogo",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # One member responds before force close
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- approved before force close",
            state_dir=tmp_path,
        )

        # Force close mid-committee
        fc_result = debate_force_close(
            thread_id=thread_id,
            reason="Emergency shutdown: time limit exceeded",
            state_dir=tmp_path,
        )

        assert fc_result["status"] == "force_closed"

        # Verify room state
        room = load_debate_state(thread_id, tmp_path)
        assert room.status == DebateStatus.FORCE_CLOSED
        assert room.session_type == SessionType.COMMITTEE
        # Committee metadata should still have partial data
        assert room.committee_metadata.responses["CRS"] == "GO"
        assert "CE" in room.committee_metadata.awaiting

    def test_force_close_reflected_in_get_debate(self, tmp_path: Path) -> None:
        """get_debate() reflects force_closed status for consultation."""
        result = consult(
            topic="FC get_debate test",
            advisor_role="TMG",
            question="Testing force close visibility",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_force_close(
            thread_id=thread_id,
            reason="Test reason",
            state_dir=tmp_path,
        )

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)
        assert debate_info["status"] == "force_closed"
        assert debate_info["session_type"] == "consultation"


# --- Cross-Tool: tombstone_turn on consultation/committee sessions (I4) ---


class TestTombstoneOnGovernanceSessions:
    """tombstone_turn works on consultation and committee turns (I4)."""

    def test_tombstone_consultation_turn(self, tmp_path: Path) -> None:
        """tombstone_turn() redacts content in a consultation session."""
        result = consult(
            topic="Tombstone consultation test",
            advisor_role="TMG",
            question="Question with sensitive data: SSN 123-45-6789",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Tombstone the question turn (index 0)
        ts_result = debate_tombstone(
            thread_id=thread_id,
            turn_index=0,
            reason="PII removal: contained SSN",
            state_dir=tmp_path,
        )

        assert ts_result["turn_index"] == 0

        # Verify content is redacted (reason is included in redacted text)
        room = load_debate_state(thread_id, tmp_path)
        assert "REDACTED" in room.turns[0].content
        # Original sensitive data (the SSN number itself) is gone
        assert "123-45-6789" not in room.turns[0].content
        # Session type preserved
        assert room.session_type == SessionType.CONSULTATION

    def test_tombstone_committee_turn(self, tmp_path: Path) -> None:
        """tombstone_turn() redacts content in a committee session."""
        result = convene(
            topic="Tombstone committee test",
            members=["CRS"],
            brief="Committee brief",
            decision_type="review",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # CRS adds a turn
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="Review with confidential details about Project X",
            state_dir=tmp_path,
        )

        # Tombstone the CRS turn (index 1, after brief at 0)
        ts_result = debate_tombstone(
            thread_id=thread_id,
            turn_index=1,
            reason="Confidential information redaction",
            state_dir=tmp_path,
        )

        assert ts_result["turn_index"] == 1

        room = load_debate_state(thread_id, tmp_path)
        assert "REDACTED" in room.turns[1].content
        assert "Project X" not in room.turns[1].content

    def test_tombstone_preserves_hash_chain(self, tmp_path: Path) -> None:
        """Hash chain remains valid after tombstoning a turn."""
        result = consult(
            topic="Tombstone hash test",
            advisor_role="TMG",
            question="Original question",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Advisor responds
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Advisor response",
            state_dir=tmp_path,
        )

        # Tombstone the first turn
        debate_tombstone(
            thread_id=thread_id,
            turn_index=0,
            reason="Test redaction",
            state_dir=tmp_path,
        )

        room = load_debate_state(thread_id, tmp_path)
        # Turns still exist (tombstone redacts content, doesn't delete)
        assert len(room.turns) == 2
        # Turn 0 is redacted but still has hash
        assert room.turns[0].hash is not None

        # Verify actual hash chain linkage (I4: previous_hash == prior turn's hash)
        for i in range(1, len(room.turns)):
            prev_turn = room.turns[i - 1]
            curr_turn = room.turns[i]
            assert prev_turn.hash is not None, f"Turn {i - 1} hash must not be None"
            assert curr_turn.previous_hash is not None, f"Turn {i} previous_hash must not be None"
            assert curr_turn.previous_hash == prev_turn.hash, (
                f"Turn {i} previous_hash ({curr_turn.previous_hash}) "
                f"must equal turn {i - 1} hash ({prev_turn.hash})"
            )


# --- Edge Case: I3 Exhaustion on consultation/committee ---


class TestExhaustionOnGovernanceSessions:
    """I3 exhaustion (max_turns reached) on consultation/committee sessions."""

    def test_consultation_exhaustion_at_max_turns(self, tmp_path: Path) -> None:
        """Consultation with max_turns=3 rejects turns after limit reached.

        B0 observation: 'Consultation can cycle within max_turns (by design, I3 enforced)'
        The engine raises ValueError but status stays ACTIVE (exhaustion is a guard,
        not a status transition — status only transitions via close_debate).
        """
        result = consult(
            topic="Exhaustion test",
            advisor_role="TMG",
            question="First question",
            max_turns=3,
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Turn 2: advisor responds
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="First response",
            state_dir=tmp_path,
        )

        # Turn 3: questioner follows up (at limit)
        debate_pick(thread_id=thread_id, role="Questioner", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="Questioner",
            content="Follow-up question",
            state_dir=tmp_path,
        )

        # Turn 4: should be rejected (over max_turns=3)
        debate_pick(thread_id=thread_id, role="TMG", state_dir=tmp_path)
        with pytest.raises(ValueError, match="exhausted"):
            debate_turn(
                thread_id=thread_id,
                role="TMG",
                content="This should be rejected due to exhaustion",
                state_dir=tmp_path,
            )

        # Verify room state: 3 turns recorded, no more accepted
        room = load_debate_state(thread_id, tmp_path)
        assert len(room.turns) == 3
        # Status stays ACTIVE (exhaustion guard prevents turns but doesn't
        # transition status — that happens via close_debate)
        assert room.status == DebateStatus.ACTIVE

    def test_committee_exhaustion_at_max_turns(self, tmp_path: Path) -> None:
        """Committee with max_turns=3 rejects turns after limit reached."""
        result = convene(
            topic="Committee exhaustion test",
            members=["CRS", "CE", "PE"],
            brief="Committee with tight turn limit",
            decision_type="go_nogo",
            max_turns=3,
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Turn 2: CRS responds
        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="GO -- approved",
            state_dir=tmp_path,
        )

        # Turn 3: CE responds (at limit)
        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="GO -- approved",
            state_dir=tmp_path,
        )

        # Turn 4: PE should be rejected (over max_turns=3)
        debate_pick(thread_id=thread_id, role="PE", state_dir=tmp_path)
        with pytest.raises(ValueError, match="exhausted"):
            debate_turn(
                thread_id=thread_id,
                role="PE",
                content="This should be rejected",
                state_dir=tmp_path,
            )

        room = load_debate_state(thread_id, tmp_path)
        assert len(room.turns) == 3
        # PE is still awaiting since they couldn't add their turn
        assert "PE" in room.committee_metadata.awaiting

    def test_force_close_on_exhausted_consultation(self, tmp_path: Path) -> None:
        """force_close works on consultation that has hit max_turns (I5 overrides I3).

        Even though turns are rejected after max_turns, force_close can still
        be used to formally close the session.
        """
        result = consult(
            topic="FC after exhaustion",
            advisor_role="TMG",
            question="Question",
            max_turns=2,
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Hit the limit (turn 2 of max 2)
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Response that exhausts the session",
            state_dir=tmp_path,
        )

        # Verify turns are rejected
        debate_pick(thread_id=thread_id, role="Questioner", state_dir=tmp_path)
        with pytest.raises(ValueError, match="exhausted"):
            debate_turn(
                thread_id=thread_id,
                role="Questioner",
                content="This should fail",
                state_dir=tmp_path,
            )

        # Force close should still work (I5 override)
        fc_result = debate_force_close(
            thread_id=thread_id,
            reason="Administrative cleanup of exhausted session",
            state_dir=tmp_path,
        )

        assert fc_result["status"] == "force_closed"
        room = load_debate_state(thread_id, tmp_path)
        assert room.status == DebateStatus.FORCE_CLOSED


# --- Backward Compatibility ---


class TestBackwardCompatibility:
    """Standard debate flow still works identically alongside new session types."""

    def test_standard_fixed_debate_unaffected(self, tmp_path: Path) -> None:
        """Standard fixed-mode debate works exactly as before."""
        debate_init(
            thread_id="2026-02-21-standard-debate-test",
            topic="Standard debate test",
            mode="fixed",
            max_turns=12,
            max_rounds=4,
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id="2026-02-21-standard-debate-test",
            role="Wind",
            content="Wind explores the space.",
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id="2026-02-21-standard-debate-test",
            role="Wall",
            content="Wall validates boundaries.",
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id="2026-02-21-standard-debate-test",
            role="Door",
            content="Door synthesizes.",
            state_dir=tmp_path,
        )

        room = load_debate_state("2026-02-21-standard-debate-test", tmp_path)
        assert room.session_type == SessionType.DEBATE
        assert len(room.turns) == 3
        assert room.participants is None
        assert room.committee_metadata is None

    def test_standard_mediated_debate_unaffected(self, tmp_path: Path) -> None:
        """Standard mediated-mode debate with Wind/Wall/Door works as before."""
        debate_init(
            thread_id="2026-02-21-mediated-debate-test",
            topic="Mediated debate test",
            mode="mediated",
            max_turns=12,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-mediated-debate-test",
            role="Wind",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2026-02-21-mediated-debate-test",
            role="Wind",
            content="Wind perspective.",
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-mediated-debate-test",
            role="Wall",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2026-02-21-mediated-debate-test",
            role="Wall",
            content="Wall perspective.",
            state_dir=tmp_path,
        )

        room = load_debate_state("2026-02-21-mediated-debate-test", tmp_path)
        assert room.session_type == SessionType.DEBATE
        assert len(room.turns) == 2

    def test_get_debate_shows_debate_session_type_for_standard(self, tmp_path: Path) -> None:
        """get_debate() returns session_type='debate' for standard debates."""
        debate_init(
            thread_id="2026-02-21-session-type-test",
            topic="Session type check",
            mode="fixed",
            max_turns=12,
            state_dir=tmp_path,
        )

        debate_info = debate_get(thread_id="2026-02-21-session-type-test", state_dir=tmp_path)
        assert debate_info["session_type"] == "debate"
        # Standard debates should not have committee_metadata
        assert debate_info.get("committee_metadata") is None


# --- Cross-tool: get_debate with include_transcript on governance sessions ---


class TestGetDebateTranscriptCrossTool:
    """get_debate(include_transcript=True) works for all session types."""

    def test_consultation_transcript_content_integrity(self, tmp_path: Path) -> None:
        """Full consultation transcript is returned with correct content."""
        result = consult(
            topic="Full transcript test",
            advisor_role="TMG",
            question="What is the best approach?",
            questioner_role="DevLead",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Use systematic approach with TDD.",
            state_dir=tmp_path,
        )

        debate_close(
            thread_id=thread_id,
            synthesis="TMG recommends TDD-based systematic approach.",
            state_dir=tmp_path,
            output_format="json",
        )

        debate_info = debate_get(
            thread_id=thread_id,
            include_transcript=True,
            state_dir=tmp_path,
        )

        transcript = debate_info["transcript"]
        # Transcript includes System OCTAVE preamble + actual turns
        assert transcript[0]["role"] == "System"
        assert transcript[1]["role"] == "DevLead"
        assert "best approach" in transcript[1]["content"]
        assert transcript[2]["role"] == "TMG"
        assert "TDD" in transcript[2]["content"]

    def test_committee_transcript_includes_all_turns(self, tmp_path: Path) -> None:
        """Committee transcript includes brief + all member turns."""
        result = convene(
            topic="Committee transcript test",
            members=["CRS", "CE"],
            brief="Review changes",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_pick(thread_id=thread_id, role="CRS", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CRS",
            content="CRS review comment.",
            state_dir=tmp_path,
        )

        debate_pick(thread_id=thread_id, role="CE", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="CE review comment.",
            state_dir=tmp_path,
        )

        debate_info = debate_get(
            thread_id=thread_id,
            include_transcript=True,
            state_dir=tmp_path,
        )

        transcript = debate_info["transcript"]
        # Transcript includes System OCTAVE preamble + actual turns
        assert transcript[0]["role"] == "System"
        assert transcript[1]["role"] == "Chair"
        assert transcript[2]["role"] == "CRS"
        assert transcript[3]["role"] == "CE"


# --- Multiple concurrent sessions ---


class TestConcurrentSessions:
    """Multiple session types can run concurrently without interference."""

    def test_consultation_and_committee_coexist(self, tmp_path: Path) -> None:
        """A consultation and committee can run simultaneously."""
        # Create consultation
        consult_result = consult(
            topic="Concurrent consult",
            advisor_role="TMG",
            question="Consultation question",
            thread_id="2026-02-21-concurrent-consult",
            state_dir=tmp_path,
        )

        # Create committee
        convene_result = convene(
            topic="Concurrent committee",
            members=["CRS"],
            brief="Committee brief",
            thread_id="2026-02-21-concurrent-committee",
            state_dir=tmp_path,
        )

        # Both are active
        consult_info = debate_get(thread_id=consult_result["thread_id"], state_dir=tmp_path)
        committee_info = debate_get(thread_id=convene_result["thread_id"], state_dir=tmp_path)

        assert consult_info["session_type"] == "consultation"
        assert consult_info["status"] == "active"
        assert committee_info["session_type"] == "committee"
        assert committee_info["status"] == "active"

        # Actions on one don't affect the other
        debate_turn(
            thread_id=consult_result["thread_id"],
            role="TMG",
            content="Advisor response",
            state_dir=tmp_path,
        )

        # Committee still has same state
        committee_info2 = debate_get(thread_id=convene_result["thread_id"], state_dir=tmp_path)
        assert committee_info2["turn_count"] == 1  # only the brief

    def test_standard_debate_and_consultation_coexist(self, tmp_path: Path) -> None:
        """Standard debate and consultation can run simultaneously."""
        # Standard debate
        debate_init(
            thread_id="2026-02-21-standard-concurrent",
            topic="Standard debate",
            mode="fixed",
            max_turns=12,
            state_dir=tmp_path,
        )

        # Consultation
        consult_result = consult(
            topic="Concurrent consultation",
            advisor_role="CE",
            question="Question?",
            thread_id="2026-02-21-consult-concurrent",
            state_dir=tmp_path,
        )

        # Both work independently
        debate_turn(
            thread_id="2026-02-21-standard-concurrent",
            role="Wind",
            content="Wind perspective.",
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id=consult_result["thread_id"],
            role="CE",
            content="CE response.",
            state_dir=tmp_path,
        )

        # Verify each has correct session type
        standard_info = debate_get(thread_id="2026-02-21-standard-concurrent", state_dir=tmp_path)
        consult_info = debate_get(thread_id=consult_result["thread_id"], state_dir=tmp_path)

        assert standard_info["session_type"] == "debate"
        assert standard_info["turn_count"] == 1
        assert consult_info["session_type"] == "consultation"
        assert consult_info["turn_count"] == 2
