"""Integration tests for full consult lifecycle — Issue #179.

Phase 4 of the governance chat API epic (#173).

Tests the complete advisory consultation flow end-to-end:
consult() -> add_turn(advisor) -> add_turn(follow-up) -> close_debate(synthesis)

Verifies:
- Transcript integrity (hash chain)
- session_type in get_debate response
- Turn count progression
- Full conversation flow with follow-ups

TDD Discipline: RED phase — failing tests written before any GREEN implementation.
"""

from pathlib import Path

from debate_hall_mcp.state import (
    load_debate_state,
)
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.consult import consult
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn


class TestConsultFullLifecycle:
    """Full consult lifecycle: question -> advisor response -> follow-up -> close."""

    def test_full_consult_lifecycle(self, tmp_path: Path) -> None:
        """Complete consult flow from creation through closure.

        Flow:
        1. consult() creates session with question
        2. add_turn() — advisor responds
        3. add_turn() — questioner follows up
        4. add_turn() — advisor responds again
        5. close_debate() — synthesis
        6. Verify final state
        """
        # Step 1: Create consultation
        result = consult(
            topic="TDD guidance for async providers",
            advisor_role="TMG",
            question="Best TDD pattern for async providers?",
            questioner_role="DevLead",
            state_dir=tmp_path,
        )

        assert result["status"] == "active"
        assert result["session_type"] == "consultation"
        assert result["turn_count"] == 1
        thread_id = result["thread_id"]

        # Step 2: Advisor responds
        turn1 = debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Use the AAA pattern (Arrange-Act-Assert) with async fixtures.",
            state_dir=tmp_path,
        )
        assert turn1["turn_count"] == 2

        # Step 3: Questioner follows up
        debate_pick(thread_id=thread_id, role="DevLead", state_dir=tmp_path)
        turn2 = debate_turn(
            thread_id=thread_id,
            role="DevLead",
            content="What about error cases in async providers?",
            state_dir=tmp_path,
        )
        assert turn2["turn_count"] == 3

        # Step 4: Advisor responds again
        debate_pick(thread_id=thread_id, role="TMG", state_dir=tmp_path)
        turn3 = debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Error cases should use pytest.raises with async context managers.",
            state_dir=tmp_path,
        )
        assert turn3["turn_count"] == 4

        # Step 5: Close with synthesis
        close_result = debate_close(
            thread_id=thread_id,
            synthesis="TMG advised AAA pattern with async fixtures for happy paths "
            "and pytest.raises for error cases in async providers.",
            state_dir=tmp_path,
            output_format="json",
        )
        assert close_result["thread_id"] == thread_id

        # Step 6: Verify final state
        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"
        assert len(room.turns) == 4
        assert room.turns[0].role == "DevLead"
        assert room.turns[1].role == "TMG"
        assert room.turns[2].role == "DevLead"
        assert room.turns[3].role == "TMG"

    def test_consult_lifecycle_with_context(self, tmp_path: Path) -> None:
        """Consult lifecycle with context parameter — context appears in transcript."""
        result = consult(
            topic="Security review",
            advisor_role="CE",
            question="Is this auth implementation safe?",
            context="We are using JWT tokens with 24h expiry.",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Verify context in first turn
        room = load_debate_state(thread_id, tmp_path)
        assert "[CONTEXT]" in room.turns[0].content
        assert "JWT tokens" in room.turns[0].content
        assert "Is this auth implementation safe?" in room.turns[0].content

        # Advisor responds
        debate_turn(
            thread_id=thread_id,
            role="CE",
            content="The JWT implementation looks solid but add token rotation.",
            state_dir=tmp_path,
        )

        # Close
        debate_close(
            thread_id=thread_id,
            synthesis="CE approved JWT implementation with recommendation for token rotation.",
            state_dir=tmp_path,
            output_format="json",
        )

        room = load_debate_state(thread_id, tmp_path)
        assert room.status.value == "synthesis"
        assert len(room.turns) == 2


class TestConsultHashChainIntegrity:
    """Verify hash chain integrity across the full consult lifecycle (I4)."""

    def test_hash_chain_continuous_through_consultation(self, tmp_path: Path) -> None:
        """Each turn's hash chains to the previous turn's hash."""
        result = consult(
            topic="Hash chain test",
            advisor_role="TMG",
            question="Testing hash chain integrity",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Add advisor response
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Hash chain should be continuous.",
            state_dir=tmp_path,
        )

        # Follow-up
        debate_pick(thread_id=thread_id, role="Questioner", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="Questioner",
            content="Can you verify?",
            state_dir=tmp_path,
        )

        # Final response
        debate_pick(thread_id=thread_id, role="TMG", state_dir=tmp_path)
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Verified — hash chain is continuous.",
            state_dir=tmp_path,
        )

        # Verify hash chain
        room = load_debate_state(thread_id, tmp_path)
        assert len(room.turns) == 4

        # First turn should have a hash based on content + empty prev_hash
        for i in range(1, len(room.turns)):
            prev_turn = room.turns[i - 1]
            curr_turn = room.turns[i]

            # The current turn's prev_hash should match the previous turn's hash
            assert curr_turn.previous_hash is not None, f"Turn {i} should have prev_hash set"
            assert prev_turn.hash is not None, f"Turn {i-1} should have hash set"
            assert (
                curr_turn.previous_hash == prev_turn.hash
            ), f"Turn {i} prev_hash should match turn {i-1} hash"

    def test_hash_chain_survives_close(self, tmp_path: Path) -> None:
        """Hash chain remains valid after debate close."""
        result = consult(
            topic="Close hash test",
            advisor_role="TMG",
            question="Testing close",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Response for close test.",
            state_dir=tmp_path,
        )

        debate_close(
            thread_id=thread_id,
            synthesis="Consultation closed successfully.",
            state_dir=tmp_path,
            output_format="json",
        )

        room = load_debate_state(thread_id, tmp_path)
        # Hash chain should still be intact after close
        for i in range(1, len(room.turns)):
            assert room.turns[i].previous_hash == room.turns[i - 1].hash


class TestConsultGetDebateIntegration:
    """Verify get_debate returns correct session info for consultations."""

    def test_get_debate_returns_consultation_session_type(self, tmp_path: Path) -> None:
        """get_debate() returns session_type='consultation' for consult sessions."""
        result = consult(
            topic="Get debate test",
            advisor_role="TMG",
            question="Question for get_debate test?",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)

        assert debate_info["session_type"] == "consultation"
        assert debate_info["mode"] == "mediated"
        assert debate_info["status"] == "active"
        assert debate_info["turn_count"] == 1

    def test_get_debate_returns_participants(self, tmp_path: Path) -> None:
        """get_debate() returns participants list for consultation."""
        result = consult(
            topic="Participants test",
            advisor_role="CE",
            question="Test participants?",
            questioner_role="DevLead",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)

        assert debate_info["participants"] is not None
        roles = [p["role"] for p in debate_info["participants"]]
        assert "DevLead" in roles
        assert "CE" in roles

    def test_get_debate_with_transcript_shows_conversation(self, tmp_path: Path) -> None:
        """get_debate(include_transcript=True) returns full conversation."""
        result = consult(
            topic="Transcript test",
            advisor_role="TMG",
            question="Show me the transcript?",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        # Advisor responds
        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Here is the transcript.",
            state_dir=tmp_path,
        )

        debate_info = debate_get(
            thread_id=thread_id,
            include_transcript=True,
            state_dir=tmp_path,
        )

        assert "transcript" in debate_info
        # Transcript includes System OCTAVE preamble + actual turns
        transcript = debate_info["transcript"]
        assert transcript[0]["role"] == "System"  # OCTAVE literacy primer
        assert transcript[1]["role"] == "Questioner"
        assert transcript[2]["role"] == "TMG"
        assert debate_info["turn_count"] == 2

    def test_get_debate_after_close_shows_synthesis_status(self, tmp_path: Path) -> None:
        """get_debate() shows synthesis status after close."""
        result = consult(
            topic="Close status test",
            advisor_role="TMG",
            question="Test close status?",
            state_dir=tmp_path,
        )
        thread_id = result["thread_id"]

        debate_turn(
            thread_id=thread_id,
            role="TMG",
            content="Response.",
            state_dir=tmp_path,
        )

        debate_close(
            thread_id=thread_id,
            synthesis="Consultation complete.",
            state_dir=tmp_path,
            output_format="json",
        )

        debate_info = debate_get(thread_id=thread_id, state_dir=tmp_path)
        assert debate_info["status"] == "synthesis"
        assert debate_info["session_type"] == "consultation"
