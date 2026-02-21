"""Unit tests for Issue #175: Session type and participant model extensions.

Tests cover:
- SessionType enum values
- Participant model creation and validation
- CommitteeMetadata model creation and validation
- DebateRoom extensions with new optional fields
- Backward compatibility with existing serialized state
- get_debate response for new session types

TDD: RED phase — these tests are written BEFORE the implementation.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    CommitteeMetadata,
    DebateMode,
    DebateRoom,
    Participant,
    SessionType,
    load_debate_state,
    save_debate_state,
)


class TestSessionType:
    """Test SessionType enum."""

    def test_session_type_debate_value(self) -> None:
        """SessionType.DEBATE has value 'debate'."""
        assert SessionType.DEBATE.value == "debate"

    def test_session_type_consultation_value(self) -> None:
        """SessionType.CONSULTATION has value 'consultation'."""
        assert SessionType.CONSULTATION.value == "consultation"

    def test_session_type_committee_value(self) -> None:
        """SessionType.COMMITTEE has value 'committee'."""
        assert SessionType.COMMITTEE.value == "committee"

    def test_session_type_is_strenum(self) -> None:
        """SessionType values are string-compatible."""
        assert str(SessionType.DEBATE) == "debate"
        assert str(SessionType.CONSULTATION) == "consultation"
        assert str(SessionType.COMMITTEE) == "committee"


class TestParticipant:
    """Test Participant model."""

    def test_participant_creation_valid(self) -> None:
        """Participant with valid role and joined_at succeeds."""
        now = datetime.now(UTC)
        p = Participant(role="CRS", joined_at=now)
        assert p.role == "CRS"
        assert p.joined_at == now

    def test_participant_role_long_valid(self) -> None:
        """Participant role at exactly 128 chars is valid."""
        role = "A" * 128
        p = Participant(role=role, joined_at=datetime.now(UTC))
        assert p.role == role

    def test_participant_rejects_empty_role(self) -> None:
        """Participant rejects empty string role."""
        with pytest.raises(ValueError):
            Participant(role="", joined_at=datetime.now(UTC))

    def test_participant_rejects_whitespace_role(self) -> None:
        """Participant rejects whitespace-only role."""
        with pytest.raises(ValueError):
            Participant(role="   ", joined_at=datetime.now(UTC))

    def test_participant_rejects_too_long_role(self) -> None:
        """Participant rejects role > 128 chars."""
        with pytest.raises(ValueError):
            Participant(role="A" * 129, joined_at=datetime.now(UTC))

    def test_participant_rejects_non_ascii_role(self) -> None:
        """Participant rejects non-ASCII role."""
        with pytest.raises(ValueError):
            Participant(role="role\u00e9", joined_at=datetime.now(UTC))

    def test_participant_rejects_control_chars_role(self) -> None:
        """Participant rejects role with control characters."""
        with pytest.raises(ValueError):
            Participant(role="role\x00name", joined_at=datetime.now(UTC))

    def test_participant_does_not_have_authority_field(self) -> None:
        """Participant does NOT have an authority field (deferred per R1)."""
        p = Participant(role="TMG", joined_at=datetime.now(UTC))
        assert not hasattr(p, "authority")

    def test_participant_serialization_roundtrip(self) -> None:
        """Participant serializes and deserializes correctly."""
        now = datetime.now(UTC)
        p = Participant(role="CE", joined_at=now)
        data = p.model_dump()
        p2 = Participant.model_validate(data)
        assert p2.role == "CE"
        assert p2.joined_at == now


class TestCommitteeMetadata:
    """Test CommitteeMetadata model (governance committee state)."""

    def test_committee_metadata_valid_creation(self) -> None:
        """CommitteeMetadata with valid fields succeeds."""
        cm = CommitteeMetadata(
            decision_type="go_nogo",
            members=["CRS", "CE"],
            responses={"CRS": "GO"},
            awaiting=["CE"],
        )
        assert cm.decision_type == "go_nogo"
        assert cm.members == ["CRS", "CE"]
        assert cm.responses == {"CRS": "GO"}
        assert cm.awaiting == ["CE"]
        assert cm.decision is None

    def test_committee_metadata_vote_type(self) -> None:
        """CommitteeMetadata accepts decision_type='vote'."""
        cm = CommitteeMetadata(
            decision_type="vote",
            members=["A"],
            awaiting=["A"],
        )
        assert cm.decision_type == "vote"

    def test_committee_metadata_review_type(self) -> None:
        """CommitteeMetadata accepts decision_type='review'."""
        cm = CommitteeMetadata(
            decision_type="review",
            members=["A"],
            awaiting=["A"],
        )
        assert cm.decision_type == "review"

    def test_committee_metadata_rejects_invalid_decision_type(self) -> None:
        """CommitteeMetadata rejects invalid decision_type."""
        with pytest.raises(ValueError):
            CommitteeMetadata(
                decision_type="invalid",
                members=["A"],
                awaiting=["A"],
            )

    def test_committee_metadata_rejects_empty_members(self) -> None:
        """CommitteeMetadata rejects empty members list."""
        with pytest.raises(ValueError):
            CommitteeMetadata(
                decision_type="go_nogo",
                members=[],
                awaiting=[],
            )

    def test_committee_metadata_defaults_responses_empty(self) -> None:
        """CommitteeMetadata defaults responses to empty dict."""
        cm = CommitteeMetadata(
            decision_type="go_nogo",
            members=["CRS"],
            awaiting=["CRS"],
        )
        assert cm.responses == {}

    def test_committee_metadata_defaults_decision_none(self) -> None:
        """CommitteeMetadata defaults decision to None."""
        cm = CommitteeMetadata(
            decision_type="go_nogo",
            members=["CRS"],
            awaiting=["CRS"],
        )
        assert cm.decision is None

    def test_committee_metadata_with_decision(self) -> None:
        """CommitteeMetadata accepts a decision value."""
        cm = CommitteeMetadata(
            decision_type="go_nogo",
            members=["CRS", "CE"],
            responses={"CRS": "GO", "CE": "GO"},
            awaiting=[],
            decision="GO - unanimous",
        )
        assert cm.decision == "GO - unanimous"

    def test_committee_metadata_serialization_roundtrip(self) -> None:
        """CommitteeMetadata serializes and deserializes correctly."""
        cm = CommitteeMetadata(
            decision_type="vote",
            members=["A", "B"],
            responses={"A": "yes"},
            awaiting=["B"],
            decision=None,
        )
        data = cm.model_dump()
        cm2 = CommitteeMetadata.model_validate(data)
        assert cm2.decision_type == "vote"
        assert cm2.members == ["A", "B"]
        assert cm2.responses == {"A": "yes"}
        assert cm2.awaiting == ["B"]


class TestDebateRoomSessionExtensions:
    """Test DebateRoom with new session-type fields."""

    def test_debate_room_default_session_type_is_debate(self) -> None:
        """DebateRoom defaults session_type to 'debate'."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        assert room.session_type == SessionType.DEBATE

    def test_debate_room_default_participants_is_none(self) -> None:
        """DebateRoom defaults participants to None."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        assert room.participants is None

    def test_debate_room_default_committee_metadata_is_none(self) -> None:
        """DebateRoom defaults committee_metadata to None."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        assert room.committee_metadata is None

    def test_debate_room_with_consultation_type(self) -> None:
        """DebateRoom can be created with consultation session type."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-consult",
            topic="TDD guidance",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.CONSULTATION,
            participants=[
                Participant(role="Questioner", joined_at=now),
                Participant(role="TMG", joined_at=now),
            ],
        )
        assert room.session_type == SessionType.CONSULTATION
        assert room.participants is not None
        assert len(room.participants) == 2
        assert room.participants[0].role == "Questioner"
        assert room.participants[1].role == "TMG"

    def test_debate_room_with_committee_type(self) -> None:
        """DebateRoom can be created with committee session type."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-committee",
            topic="PR review",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.COMMITTEE,
            participants=[
                Participant(role="Chair", joined_at=now),
                Participant(role="CRS", joined_at=now),
                Participant(role="CE", joined_at=now),
            ],
            committee_metadata=CommitteeMetadata(
                decision_type="go_nogo",
                members=["CRS", "CE"],
                responses={},
                awaiting=["CRS", "CE"],
            ),
        )
        assert room.session_type == SessionType.COMMITTEE
        assert room.participants is not None
        assert len(room.participants) == 3
        assert room.committee_metadata is not None
        assert room.committee_metadata.decision_type == "go_nogo"

    def test_debate_room_backward_compat_serialization(self, tmp_path: Path) -> None:
        """Existing DebateRoom JSON without new fields deserializes with defaults."""
        # Simulate an existing JSON file that has NO session_type/participants/committee_metadata
        old_data = {
            "thread_id": "2025-01-01-old-debate",
            "topic": "Old topic",
            "mode": "fixed",
            "status": "active",
            "max_turns": 12,
            "max_rounds": 4,
            "strict_cognition": False,
            "octave_preamble": True,
            "octave_mode": True,
            "expected_next_role": None,
            "turns": [],
            "synthesis": None,
            "audit_log": [],
            "github_binding": None,
            "injected_context": [],
            "consensus_metadata": None,
            "turn_manifest": None,
        }

        state_file = tmp_path / "2025-01-01-old-debate.json"
        state_file.write_text(json.dumps(old_data, indent=2))

        room = load_debate_state("2025-01-01-old-debate", tmp_path)
        assert room.session_type == SessionType.DEBATE
        assert room.participants is None
        assert room.committee_metadata is None

    def test_debate_room_with_new_fields_roundtrip(self, tmp_path: Path) -> None:
        """DebateRoom with new fields serializes and deserializes correctly."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-roundtrip",
            topic="Roundtrip test",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.CONSULTATION,
            participants=[
                Participant(role="Questioner", joined_at=now),
                Participant(role="TMG", joined_at=now),
            ],
        )

        save_debate_state(room, tmp_path)
        loaded = load_debate_state("2025-01-01-roundtrip", tmp_path)

        assert loaded.session_type == SessionType.CONSULTATION
        assert loaded.participants is not None
        assert len(loaded.participants) == 2
        assert loaded.participants[0].role == "Questioner"
        assert loaded.participants[1].role == "TMG"

    def test_debate_room_committee_roundtrip(self, tmp_path: Path) -> None:
        """DebateRoom with committee metadata roundtrips correctly."""
        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-committee-rt",
            topic="Committee test",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.COMMITTEE,
            participants=[
                Participant(role="Chair", joined_at=now),
                Participant(role="CRS", joined_at=now),
            ],
            committee_metadata=CommitteeMetadata(
                decision_type="review",
                members=["CRS"],
                responses={"CRS": "Approved"},
                awaiting=[],
                decision="Approved",
            ),
        )

        save_debate_state(room, tmp_path)
        loaded = load_debate_state("2025-01-01-committee-rt", tmp_path)

        assert loaded.session_type == SessionType.COMMITTEE
        assert loaded.committee_metadata is not None
        assert loaded.committee_metadata.decision_type == "review"
        assert loaded.committee_metadata.responses == {"CRS": "Approved"}
        assert loaded.committee_metadata.decision == "Approved"


class TestGetDebateSessionFields:
    """Test get_debate response includes session-type fields."""

    def test_get_debate_includes_session_type_for_debate(self, tmp_path: Path) -> None:
        """get_debate returns session_type='debate' for standard debates."""
        from debate_hall_mcp.tools.get import debate_get
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-get-session",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-get-session", state_dir=tmp_path)
        assert result["session_type"] == "debate"

    def test_get_debate_omits_participants_for_debate(self, tmp_path: Path) -> None:
        """get_debate omits participants and committee_metadata for debate sessions."""
        from debate_hall_mcp.tools.get import debate_get
        from debate_hall_mcp.tools.init import debate_init

        debate_init(
            thread_id="2025-01-01-get-omit",
            topic="Test",
            mode="fixed",
            state_dir=tmp_path,
        )

        result = debate_get(thread_id="2025-01-01-get-omit", state_dir=tmp_path)
        # For debate sessions, participants and committee_metadata are omitted
        assert "participants" not in result
        assert "committee_metadata" not in result

    def test_get_debate_includes_fields_for_consultation(self, tmp_path: Path) -> None:
        """get_debate returns participants for consultation sessions."""
        from debate_hall_mcp.tools.get import debate_get

        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-get-consult",
            topic="Consultation",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.CONSULTATION,
            participants=[
                Participant(role="Questioner", joined_at=now),
                Participant(role="TMG", joined_at=now),
            ],
        )
        save_debate_state(room, tmp_path)

        result = debate_get(thread_id="2025-01-01-get-consult", state_dir=tmp_path)
        assert result["session_type"] == "consultation"
        assert result["participants"] is not None
        assert len(result["participants"]) == 2
        assert result["participants"][0]["role"] == "Questioner"

    def test_get_debate_includes_committee_metadata(self, tmp_path: Path) -> None:
        """get_debate returns committee_metadata for committee sessions."""
        from debate_hall_mcp.tools.get import debate_get

        now = datetime.now(UTC)
        room = DebateRoom(
            thread_id="2025-01-01-get-committee",
            topic="Committee",
            mode=DebateMode.MEDIATED,
            session_type=SessionType.COMMITTEE,
            participants=[
                Participant(role="Chair", joined_at=now),
                Participant(role="CRS", joined_at=now),
            ],
            committee_metadata=CommitteeMetadata(
                decision_type="go_nogo",
                members=["CRS"],
                responses={},
                awaiting=["CRS"],
            ),
        )
        save_debate_state(room, tmp_path)

        result = debate_get(thread_id="2025-01-01-get-committee", state_dir=tmp_path)
        assert result["session_type"] == "committee"
        assert result["participants"] is not None
        assert result["committee_metadata"] is not None
        assert result["committee_metadata"]["decision_type"] == "go_nogo"
        assert result["committee_metadata"]["awaiting"] == ["CRS"]
