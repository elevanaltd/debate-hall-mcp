"""Unit tests for debate_hall_mcp.decision module.

Tests cover:
- DecisionRecord Pydantic model validation
- calculate_decision_hash() for synthesis integrity
- calculate_source_hash() for provenance
- extract_decision_record() from closed DebateRoom
- Rejection of active/paused debates
- Consensus metadata integration
"""

from datetime import UTC, datetime

import pytest

from debate_hall_mcp.decision import (
    DecisionRecord,
    calculate_decision_hash,
    calculate_source_hash,
    extract_decision_record,
)
from debate_hall_mcp.state import (
    ConsensusMetadata,
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
)


class TestDecisionRecordModel:
    """Test DecisionRecord Pydantic model validation."""

    def test_decision_record_required_fields(self) -> None:
        """DecisionRecord requires thread_id, topic, decided_at, synthesis, decision_hash, status, extracted_at, source_hash."""
        record = DecisionRecord(
            thread_id="2026-01-15-test-decision",
            topic="Test topic",
            decided_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
            synthesis="The final synthesis.",
            decision_hash="abc123",
            status="synthesis",
            extracted_at=datetime(2026, 1, 15, 12, 5, 0, tzinfo=UTC),
            source_hash="def456",
        )
        assert record.thread_id == "2026-01-15-test-decision"
        assert record.topic == "Test topic"
        assert record.synthesis == "The final synthesis."
        assert record.status == "synthesis"

    def test_decision_record_default_values(self) -> None:
        """DecisionRecord has sensible defaults for optional fields."""
        record = DecisionRecord(
            thread_id="test-thread",
            topic="Test",
            decided_at=datetime.now(UTC),
            synthesis="Synthesis",
            decision_hash="hash",
            status="synthesis",
            extracted_at=datetime.now(UTC),
            source_hash="source",
        )
        # Default lists should be empty
        assert record.wind_perspectives == []
        assert record.wall_constraints == []
        assert record.door_refinements == []
        # Default validation fields
        assert record.consensus_reached is False
        assert record.consensus_votes == {}
        assert record.refinement_count == 0
        assert record.turn_count == 0

    def test_decision_record_serialization(self) -> None:
        """DecisionRecord can be serialized to and from JSON."""
        now = datetime.now(UTC)
        record = DecisionRecord(
            thread_id="test-thread",
            topic="Test topic",
            decided_at=now,
            synthesis="Final synthesis",
            decision_hash="abc123",
            status="synthesis",
            wind_perspectives=["Explored option A", "Considered alternative B"],
            wall_constraints=["Budget constraint", "Timeline limit"],
            extracted_at=now,
            source_hash="def456",
            turn_count=6,
        )

        # Serialize and deserialize
        json_str = record.model_dump_json()
        restored = DecisionRecord.model_validate_json(json_str)

        assert restored.thread_id == record.thread_id
        assert restored.synthesis == record.synthesis
        assert restored.wind_perspectives == record.wind_perspectives
        assert restored.wall_constraints == record.wall_constraints


class TestCalculateDecisionHash:
    """Test calculate_decision_hash() function."""

    def test_hash_is_sha256(self) -> None:
        """Hash is a valid SHA-256 hex string (64 characters)."""
        result = calculate_decision_hash("Test synthesis")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_is_deterministic(self) -> None:
        """Same synthesis produces same hash."""
        synthesis = "The final decision was to proceed with option B."
        hash1 = calculate_decision_hash(synthesis)
        hash2 = calculate_decision_hash(synthesis)
        assert hash1 == hash2

    def test_different_synthesis_different_hash(self) -> None:
        """Different synthesis produces different hash."""
        hash1 = calculate_decision_hash("Option A")
        hash2 = calculate_decision_hash("Option B")
        assert hash1 != hash2

    def test_empty_synthesis_has_hash(self) -> None:
        """Empty synthesis still produces a valid hash."""
        result = calculate_decision_hash("")
        assert len(result) == 64


class TestCalculateSourceHash:
    """Test calculate_source_hash() function."""

    def test_source_hash_is_sha256(self) -> None:
        """Source hash is a valid SHA-256 hex string."""
        room = DebateRoom(
            thread_id="test-thread",
            topic="Test topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        result = calculate_source_hash(room)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_source_hash_is_deterministic(self) -> None:
        """Same DebateRoom produces same hash."""
        room = DebateRoom(
            thread_id="test-thread",
            topic="Test topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Final answer",
        )
        hash1 = calculate_source_hash(room)
        hash2 = calculate_source_hash(room)
        assert hash1 == hash2

    def test_different_rooms_different_hash(self) -> None:
        """Different DebateRooms produce different hashes."""
        room1 = DebateRoom(
            thread_id="thread-1",
            topic="Topic A",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        room2 = DebateRoom(
            thread_id="thread-2",
            topic="Topic B",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
        )
        assert calculate_source_hash(room1) != calculate_source_hash(room2)


class TestExtractDecisionRecord:
    """Test extract_decision_record() function."""

    def test_extract_from_closed_synthesis_debate(self) -> None:
        """Extract decision record from a debate closed with synthesis."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2026-01-15-architecture-decision",
            topic="Should we use microservices or monolith?",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="After careful consideration, a modular monolith is recommended.",
            turns=[
                Turn(
                    role="Wind",
                    content="Microservices offer scalability and team independence.",
                    timestamp=now,
                    previous_hash=None,
                ),
            ],
        )

        record = extract_decision_record(room)

        assert record.thread_id == "2026-01-15-architecture-decision"
        assert record.topic == "Should we use microservices or monolith?"
        assert record.synthesis == "After careful consideration, a modular monolith is recommended."
        assert record.status == "synthesis"
        assert record.turn_count == 1
        assert len(record.wind_perspectives) == 1
        assert "Microservices offer scalability" in record.wind_perspectives[0]

    def test_extract_rejects_active_debate(self) -> None:
        """Cannot extract decision from ACTIVE debate."""
        room = DebateRoom(
            thread_id="active-debate",
            topic="Ongoing discussion",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
        )

        with pytest.raises(ValueError, match="Cannot extract decision from active debate"):
            extract_decision_record(room)

    def test_extract_rejects_paused_debate(self) -> None:
        """Cannot extract decision from PAUSED debate."""
        room = DebateRoom(
            thread_id="paused-debate",
            topic="Paused discussion",
            mode=DebateMode.FIXED,
            status=DebateStatus.PAUSED,
        )

        with pytest.raises(ValueError, match="Cannot extract decision from paused debate"):
            extract_decision_record(room)

    def test_extract_from_stalemate(self) -> None:
        """Extract from debate closed due to stalemate."""
        room = DebateRoom(
            thread_id="stalemate-debate",
            topic="Contentious topic",
            mode=DebateMode.FIXED,
            status=DebateStatus.STALEMATE,
            synthesis="No consensus was reached.",
        )

        record = extract_decision_record(room)

        assert record.status == "stalemate"
        assert record.synthesis == "No consensus was reached."

    def test_extract_from_exhaustion(self) -> None:
        """Extract from debate closed due to resource exhaustion."""
        room = DebateRoom(
            thread_id="exhaustion-debate",
            topic="Long debate",
            mode=DebateMode.FIXED,
            status=DebateStatus.EXHAUSTION,
            synthesis="Debate ended due to turn limit.",
        )

        record = extract_decision_record(room)

        assert record.status == "exhaustion"

    def test_extract_from_force_closed(self) -> None:
        """Extract from debate that was force closed."""
        room = DebateRoom(
            thread_id="force-closed-debate",
            topic="Interrupted debate",
            mode=DebateMode.FIXED,
            status=DebateStatus.FORCE_CLOSED,
            synthesis="Administratively closed.",
        )

        record = extract_decision_record(room)

        assert record.status == "force_closed"

    def test_extract_with_all_role_turns(self) -> None:
        """Extract correctly categorizes turns by role."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="full-debate",
            topic="Architecture review",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Final decision made.",
            turns=[
                Turn(role="Wind", content="Wind perspective 1", timestamp=now, previous_hash=None),
                Turn(
                    role="Wall", content="Wall constraint 1", timestamp=now, previous_hash="hash1"
                ),
                Turn(
                    role="Door", content="Door refinement 1", timestamp=now, previous_hash="hash2"
                ),
                Turn(
                    role="Wind", content="Wind perspective 2", timestamp=now, previous_hash="hash3"
                ),
                Turn(
                    role="Wall", content="Wall constraint 2", timestamp=now, previous_hash="hash4"
                ),
                Turn(
                    role="Door", content="Door refinement 2", timestamp=now, previous_hash="hash5"
                ),
            ],
        )

        record = extract_decision_record(room)

        assert len(record.wind_perspectives) == 2
        assert len(record.wall_constraints) == 2
        assert len(record.door_refinements) == 2
        assert record.turn_count == 6

    def test_extract_decision_hash_computed(self) -> None:
        """Decision hash is computed from synthesis."""
        room = DebateRoom(
            thread_id="hash-test",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Test synthesis for hashing.",
        )

        record = extract_decision_record(room)

        expected_hash = calculate_decision_hash("Test synthesis for hashing.")
        assert record.decision_hash == expected_hash

    def test_extract_source_hash_computed(self) -> None:
        """Source hash is computed from DebateRoom."""
        room = DebateRoom(
            thread_id="source-hash-test",
            topic="Test",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Test",
        )

        record = extract_decision_record(room)

        expected_hash = calculate_source_hash(room)
        assert record.source_hash == expected_hash


class TestExtractDecisionRecordWithConsensus:
    """Test extract_decision_record() with consensus metadata."""

    def test_extract_with_consensus_reached(self) -> None:
        """Extract includes consensus metadata when Wind and Wall approved."""
        room = DebateRoom(
            thread_id="consensus-debate",
            topic="Important decision",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Approved synthesis.",
            consensus_metadata=ConsensusMetadata(
                consensus_reached=True,
                wind_approved=True,
                wall_approved=True,
                refinement_count=0,
                max_refinements_reached=False,
            ),
        )

        record = extract_decision_record(room)

        assert record.consensus_reached is True
        assert record.consensus_votes == {"wind": True, "wall": True}
        assert record.refinement_count == 0

    def test_extract_with_refinements(self) -> None:
        """Extract includes refinement count from consensus metadata."""
        room = DebateRoom(
            thread_id="refined-debate",
            topic="Refined decision",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Refined synthesis after 2 iterations.",
            consensus_metadata=ConsensusMetadata(
                consensus_reached=True,
                wind_approved=True,
                wall_approved=True,
                refinement_count=2,
                max_refinements_reached=False,
            ),
        )

        record = extract_decision_record(room)

        assert record.refinement_count == 2

    def test_extract_without_consensus_metadata(self) -> None:
        """Extract works without consensus metadata (non-orchestrated debates)."""
        room = DebateRoom(
            thread_id="manual-debate",
            topic="Manual debate",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Manually closed.",
            consensus_metadata=None,
        )

        record = extract_decision_record(room)

        assert record.consensus_reached is False
        assert record.consensus_votes == {
            "wind": None,
            "wall": None,
        }  # extract provides explicit None values
        assert record.refinement_count == 0

    def test_extract_with_partial_consensus(self) -> None:
        """Extract handles partial consensus (one role rejected)."""
        room = DebateRoom(
            thread_id="partial-consensus",
            topic="Contested decision",
            mode=DebateMode.FIXED,
            status=DebateStatus.SYNTHESIS,
            synthesis="Synthesis despite Wall rejection.",
            consensus_metadata=ConsensusMetadata(
                consensus_reached=False,
                wind_approved=True,
                wall_approved=False,
                refinement_count=3,
                max_refinements_reached=True,
            ),
        )

        record = extract_decision_record(room)

        assert record.consensus_reached is False
        assert record.consensus_votes == {"wind": True, "wall": False}
        assert record.refinement_count == 3
