"""Tests for hall.py — Stateful RACI Hall models and infrastructure (#163).

Phase 1 tests covering:
- P1T01: Enums (HallStatus, ParticipantKind, HallEventType) and exceptions
- P1T02: Participant and RaciMatrix models
- P1T03: HallEvent and HallState models with security validators
- P1T04: apply_hall_event reducer
- P1T05: Event ledger functions
- P1T06: Smart Loader (load_hall) and save_hall
- P1T07: G1 benchmark (replay latency)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

# ── P1T01: Enums + Error Taxonomy ────────────────────────────────────


class TestHallStatusEnum:
    """Test HallStatus enum values and membership."""

    def test_hall_status_values(self) -> None:
        from debate_hall_mcp.hall import HallStatus

        assert HallStatus.OPEN == "open"
        assert HallStatus.ACTIVE == "active"
        assert HallStatus.REVIEWING == "reviewing"
        assert HallStatus.ARCHIVED == "archived"
        assert HallStatus.FORCE_CLOSED == "force_closed"

    def test_hall_status_is_str_enum(self) -> None:
        from debate_hall_mcp.hall import HallStatus

        assert isinstance(HallStatus.OPEN, str)
        assert len(HallStatus) == 5


class TestParticipantKindEnum:
    """Test ParticipantKind enum values."""

    def test_participant_kind_values(self) -> None:
        from debate_hall_mcp.hall import ParticipantKind

        assert ParticipantKind.AGENT == "agent"
        assert ParticipantKind.HUMAN == "human"
        assert ParticipantKind.SYSTEM == "system"

    def test_participant_kind_is_str_enum(self) -> None:
        from debate_hall_mcp.hall import ParticipantKind

        assert isinstance(ParticipantKind.AGENT, str)
        assert len(ParticipantKind) == 3


class TestHallEventTypeEnum:
    """Test HallEventType enum values."""

    def test_hall_event_type_values(self) -> None:
        from debate_hall_mcp.hall import HallEventType

        assert HallEventType.HALL_OPENED == "hall_opened"
        assert HallEventType.PARTICIPANT_REGISTERED == "participant_registered"
        assert HallEventType.PARTICIPANT_UNREGISTERED == "participant_unregistered"
        assert HallEventType.RACI_ASSIGNED == "raci_assigned"
        assert HallEventType.DEBATE_SPAWNED == "debate_spawned"
        assert HallEventType.DEBATE_COMPLETED == "debate_completed"
        assert HallEventType.CONSULTATION_COMPLETED == "consultation_completed"
        assert HallEventType.CONTEXT_COMPRESSED == "context_compressed"
        assert HallEventType.HALL_CLOSED == "hall_closed"
        assert HallEventType.HALL_FORCE_CLOSED == "hall_force_closed"
        assert HallEventType.CHECKPOINT_RESTORED == "checkpoint_restored"

    def test_hall_event_type_count(self) -> None:
        from debate_hall_mcp.hall import HallEventType

        assert len(HallEventType) == 11  # Phase 2 added CHECKPOINT_RESTORED


class TestCustomExceptions:
    """Test custom exception classes from S14."""

    def test_hall_not_found_error(self) -> None:
        from debate_hall_mcp.hall import HallNotFoundError

        err = HallNotFoundError("test-hall")
        assert err.hall_id == "test-hall"
        assert "test-hall" in str(err)
        assert isinstance(err, FileNotFoundError)

    def test_hall_status_error(self) -> None:
        from debate_hall_mcp.hall import HallStatusError

        err = HallStatusError("h1", "archived", ["open", "active"])
        assert err.hall_id == "h1"
        assert err.current_status == "archived"
        assert err.required == ["open", "active"]
        assert isinstance(err, ValueError)

    def test_participant_not_found_error(self) -> None:
        from debate_hall_mcp.hall import ParticipantNotFoundError

        err = ParticipantNotFoundError("h1", "alice")
        assert err.hall_id == "h1"
        assert err.participant_id == "alice"
        assert isinstance(err, ValueError)

    def test_participant_active_error(self) -> None:
        from debate_hall_mcp.hall import ParticipantActiveError

        err = ParticipantActiveError("h1", "alice")
        assert "alice" in str(err)
        assert "active" in str(err)
        assert isinstance(err, ValueError)

    def test_depth_limit_exceeded(self) -> None:
        from debate_hall_mcp.hall import DepthLimitExceeded

        err = DepthLimitExceeded("h1", 4, 3)
        assert "4" in str(err)
        assert "3" in str(err)
        assert isinstance(err, ValueError)

    def test_debate_limit_exceeded(self) -> None:
        from debate_hall_mcp.hall import DebateLimitExceeded

        err = DebateLimitExceeded("h1", 20, 20)
        assert "20/20" in str(err)
        assert isinstance(err, ValueError)

    def test_active_debates_exist_error(self) -> None:
        from debate_hall_mcp.hall import ActiveDebatesExistError

        err = ActiveDebatesExistError("h1", ["d1", "d2"])
        assert "2 active debate(s)" in str(err)
        assert isinstance(err, ValueError)


# ── P1T02: Participant + RaciMatrix Models ─────────────────────────────


class TestParticipantModel:
    """Test Participant Pydantic model with validators."""

    def test_valid_participant_creation(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        p = Participant(id="alice", name="Alice", kind=ParticipantKind.AGENT)
        assert p.id == "alice"
        assert p.name == "Alice"
        assert p.kind == ParticipantKind.AGENT
        assert p.status == "on_call"
        assert p.raci_designation is None
        assert p.provider_config is None
        assert p.capabilities == []

    def test_participant_id_with_hyphens_and_underscores(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        p = Participant(id="impl-lead_01", name="Impl Lead", kind=ParticipantKind.AGENT)
        assert p.id == "impl-lead_01"

    def test_participant_id_rejects_spaces(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        with pytest.raises(ValueError, match="invalid characters"):
            Participant(id="bad id", name="Bad", kind=ParticipantKind.AGENT)

    def test_participant_id_rejects_special_chars(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        with pytest.raises(ValueError, match="invalid characters"):
            Participant(id="bad/id", name="Bad", kind=ParticipantKind.AGENT)

    def test_participant_id_rejects_empty(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        with pytest.raises(ValueError):
            Participant(id="", name="Bad", kind=ParticipantKind.AGENT)

    def test_raci_designation_valid_values(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        for designation in ("R", "A", "C", "I"):
            p = Participant(
                id="alice",
                name="Alice",
                kind=ParticipantKind.AGENT,
                raci_designation=designation,
            )
            assert p.raci_designation == designation

    def test_raci_designation_rejects_invalid(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        with pytest.raises(ValueError, match="raci_designation must be"):
            Participant(
                id="alice",
                name="Alice",
                kind=ParticipantKind.AGENT,
                raci_designation="X",
            )

    def test_participant_serialization_roundtrip(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind

        p = Participant(id="alice", name="Alice", kind=ParticipantKind.AGENT)
        data = p.model_dump()
        p2 = Participant.model_validate(data)
        assert p2.id == p.id
        assert p2.name == p.name


class TestRaciMatrix:
    """Test RaciMatrix model with cross-validation."""

    def test_valid_raci_matrix(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        m = RaciMatrix(responsible="alice", accountable="bob")
        assert m.responsible == "alice"
        assert m.accountable == "bob"
        assert m.consulted == []
        assert m.informed == []

    def test_raci_matrix_with_consulted_and_informed(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        m = RaciMatrix(
            responsible="alice",
            accountable="bob",
            consulted=["charlie"],
            informed=["dave"],
        )
        assert m.consulted == ["charlie"]
        assert m.informed == ["dave"]

    def test_same_responsible_and_accountable_rejected(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        with pytest.raises(ValueError, match="responsible and accountable must be different"):
            RaciMatrix(responsible="alice", accountable="alice")

    def test_consulted_exceeds_max_rejected(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        with pytest.raises(ValueError, match="consulted exceeds max 5"):
            RaciMatrix(
                responsible="r",
                accountable="a",
                consulted=["c1", "c2", "c3", "c4", "c5", "c6"],
            )

    def test_informed_exceeds_max_rejected(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        with pytest.raises(ValueError, match="informed exceeds max 3"):
            RaciMatrix(
                responsible="r",
                accountable="a",
                informed=["i1", "i2", "i3", "i4"],
            )

    def test_duplicate_across_roles_rejected(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        with pytest.raises(ValueError, match="exactly one RACI designation"):
            RaciMatrix(
                responsible="alice",
                accountable="bob",
                consulted=["alice"],
            )

    def test_duplicate_within_consulted_rejected(self) -> None:
        from debate_hall_mcp.hall import RaciMatrix

        with pytest.raises(ValueError, match="exactly one RACI designation"):
            RaciMatrix(
                responsible="r",
                accountable="a",
                consulted=["c1", "c1"],
            )


# ── P1T03: HallEvent + HallState Models ───────────────────────────────


class TestHallEvent:
    """Test HallEvent model with ULID and timestamp handling."""

    def test_hall_event_creation(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallEvent, HallEventType

        now = datetime.now(UTC)
        ev = HallEvent(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            hall_id="test-hall",
            event_type=HallEventType.HALL_OPENED,
            timestamp=now,
            data={"topic": "Test"},
        )
        assert ev.event_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert ev.hall_id == "test-hall"
        assert ev.event_type == HallEventType.HALL_OPENED
        assert ev.data == {"topic": "Test"}

    def test_hall_event_timestamp_from_iso_string(self) -> None:
        from debate_hall_mcp.hall import HallEvent, HallEventType

        ev = HallEvent(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            hall_id="h1",
            event_type=HallEventType.HALL_OPENED,
            timestamp="2026-01-15T10:30:00+00:00",
        )
        assert ev.timestamp.tzinfo is not None

    def test_hall_event_timestamp_naive_becomes_utc(self) -> None:
        from datetime import datetime

        from debate_hall_mcp.hall import HallEvent, HallEventType

        naive_dt = datetime(2026, 1, 15, 10, 30, 0)  # noqa: DTZ001
        ev = HallEvent(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            hall_id="h1",
            event_type=HallEventType.HALL_OPENED,
            timestamp=naive_dt,
        )
        assert ev.timestamp.tzinfo is not None

    def test_hall_event_serialization_roundtrip(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallEvent, HallEventType

        ev = HallEvent(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            hall_id="h1",
            event_type=HallEventType.HALL_OPENED,
            timestamp=datetime.now(UTC),
            data={"key": "value"},
        )
        json_str = ev.model_dump_json()
        ev2 = HallEvent.model_validate_json(json_str)
        assert ev2.event_id == ev.event_id
        assert ev2.event_type == ev.event_type


class TestHallState:
    """Test HallState model with validators for H-001 and M-001."""

    def test_hall_state_creation_with_defaults(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState, HallStatus

        now = datetime.now(UTC)
        state = HallState(
            hall_id="test-hall",
            topic="Test topic",
            created_at=now,
            updated_at=now,
        )
        assert state.hall_id == "test-hall"
        assert state.status == HallStatus.OPEN
        assert state.max_depth == 3
        assert state.max_context_tokens == 4096
        assert state.max_debates == 20
        assert state.participants == {}
        assert state.active_debates == []
        assert state.completed_debates == []
        assert state.compressed_log == ""

    def test_hall_id_rejects_invalid_chars_m001(self) -> None:
        """M-001: Strict regex for hall_id."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="invalid characters"):
            HallState(
                hall_id="bad/hall",
                topic="T",
                created_at=now,
                updated_at=now,
            )

    def test_hall_id_rejects_spaces_m001(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="invalid characters"):
            HallState(
                hall_id="bad hall",
                topic="T",
                created_at=now,
                updated_at=now,
            )

    def test_hall_id_rejects_empty_m001(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="must be non-empty"):
            HallState(
                hall_id="",
                topic="T",
                created_at=now,
                updated_at=now,
            )

    def test_hall_id_accepts_valid_m001(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        state = HallState(
            hall_id="hall-2026-01-15-my_topic",
            topic="T",
            created_at=now,
            updated_at=now,
        )
        assert state.hall_id == "hall-2026-01-15-my_topic"

    def test_context_files_max_count_h001(self) -> None:
        """H-001: Max 10 context files."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="exceeds maximum of 10"):
            HallState(
                hall_id="h1",
                topic="T",
                created_at=now,
                updated_at=now,
                context_files=[f"/tmp/f{i}" for i in range(11)],  # noqa: S108
            )

    def test_context_files_rejects_relative_paths_h001(self) -> None:
        """H-001: All paths must be absolute."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="must be absolute"):
            HallState(
                hall_id="h1",
                topic="T",
                created_at=now,
                updated_at=now,
                context_files=["relative/path.py"],
            )

    def test_context_files_rejects_traversal_h001(self) -> None:
        """H-001: Reject path traversal."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="traversal"):
            HallState(
                hall_id="h1",
                topic="T",
                created_at=now,
                updated_at=now,
                context_files=["/home/user/../etc/passwd"],
            )

    def test_context_files_rejects_sensitive_dirs_h001(self) -> None:
        """H-001: Block sensitive directories."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="restricted directory"):
            HallState(
                hall_id="h1",
                topic="T",
                created_at=now,
                updated_at=now,
                context_files=["/etc/passwd"],
            )

    def test_context_files_accepts_valid_paths_h001(self) -> None:
        """H-001: Valid absolute paths accepted."""
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import HallState

        now = datetime.now(UTC)
        state = HallState(
            hall_id="h1",
            topic="T",
            created_at=now,
            updated_at=now,
            context_files=["/tmp/valid.py"],  # noqa: S108
        )
        assert state.context_files == ["/tmp/valid.py"]

    def test_hall_state_max_constants(self) -> None:
        from debate_hall_mcp.hall import HallState

        assert HallState.MAX_CONTEXT_FILES == 10
        assert HallState.MAX_CONTEXT_FILE_SIZE == 65536


# ── P1T04: apply_hall_event Reducer ────────────────────────────────────


def _make_hall_state(
    hall_id: str = "test-hall",
    topic: str = "Test",
    status: str = "open",
) -> HallState:  # noqa: F821
    """Helper to create a HallState for reducer tests."""
    from datetime import UTC, datetime

    from debate_hall_mcp.hall import HallState, HallStatus

    return HallState(
        hall_id=hall_id,
        topic=topic,
        status=HallStatus(status),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_event(
    event_type: str,
    data: dict[str, object] | None = None,
    hall_id: str = "test-hall",
) -> HallEvent:  # noqa: F821
    """Helper to create a HallEvent for reducer tests."""
    from datetime import UTC, datetime

    from debate_hall_mcp.hall import HallEvent, HallEventType

    return HallEvent(
        event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        hall_id=hall_id,
        event_type=HallEventType(event_type),
        timestamp=datetime.now(UTC),
        data=data or {},
    )


class TestApplyHallEvent:
    """Test apply_hall_event pure reducer for all 10 event types."""

    def test_hall_opened(self) -> None:
        from debate_hall_mcp.hall import HallStatus, apply_hall_event

        state = _make_hall_state()
        event = _make_event("hall_opened")
        result = apply_hall_event(state, event)
        assert result.status == HallStatus.OPEN
        assert result.last_event_id == event.event_id

    def test_participant_registered(self) -> None:
        from debate_hall_mcp.hall import apply_hall_event

        state = _make_hall_state()
        event = _make_event(
            "participant_registered",
            {
                "id": "alice",
                "name": "Alice",
                "kind": "agent",
            },
        )
        result = apply_hall_event(state, event)
        assert "alice" in result.participants
        assert result.participants["alice"].name == "Alice"

    def test_participant_unregistered(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind, apply_hall_event

        state = _make_hall_state()
        state.participants["alice"] = Participant(
            id="alice",
            name="Alice",
            kind=ParticipantKind.AGENT,
        )
        event = _make_event("participant_unregistered", {"participant_id": "alice"})
        result = apply_hall_event(state, event)
        assert "alice" not in result.participants

    def test_raci_assigned(self) -> None:
        from debate_hall_mcp.hall import Participant, ParticipantKind, apply_hall_event

        state = _make_hall_state()
        state.participants["alice"] = Participant(
            id="alice",
            name="Alice",
            kind=ParticipantKind.AGENT,
        )
        state.participants["bob"] = Participant(
            id="bob",
            name="Bob",
            kind=ParticipantKind.AGENT,
        )
        event = _make_event(
            "raci_assigned",
            {
                "raci_matrix": {"responsible": "alice", "accountable": "bob"},
            },
        )
        result = apply_hall_event(state, event)
        assert result.raci_matrix is not None
        assert result.raci_matrix.responsible == "alice"
        assert result.participants["alice"].raci_designation == "R"
        assert result.participants["bob"].raci_designation == "A"

    def test_debate_spawned(self) -> None:
        from debate_hall_mcp.hall import HallStatus, apply_hall_event

        state = _make_hall_state()
        event = _make_event(
            "debate_spawned",
            {
                "thread_id": "thread-001",
                "participant_ids": [],
            },
        )
        result = apply_hall_event(state, event)
        assert "thread-001" in result.active_debates
        assert result.status == HallStatus.ACTIVE

    def test_debate_completed_moves_to_completed(self) -> None:
        from debate_hall_mcp.hall import HallStatus, apply_hall_event

        state = _make_hall_state(status="active")
        state.active_debates = ["thread-001"]
        event = _make_event(
            "debate_completed",
            {
                "thread_id": "thread-001",
                "compressed_log": "summary",
                "participant_ids": [],
            },
        )
        result = apply_hall_event(state, event)
        assert "thread-001" not in result.active_debates
        assert "thread-001" in result.completed_debates
        assert result.compressed_log == "summary"
        # Auto-transition to REVIEWING when no active debates
        assert result.status == HallStatus.REVIEWING

    def test_debate_completed_raci_reset(self) -> None:
        from debate_hall_mcp.hall import (
            Participant,
            ParticipantKind,
            apply_hall_event,
        )

        state = _make_hall_state(status="active")
        state.active_debates = ["thread-001"]
        state.participants["alice"] = Participant(
            id="alice",
            name="Alice",
            kind=ParticipantKind.AGENT,
            raci_designation="R",
        )
        event = _make_event(
            "debate_completed",
            {
                "thread_id": "thread-001",
                "participant_ids": ["alice"],
            },
        )
        result = apply_hall_event(state, event)
        assert result.participants["alice"].raci_designation is None
        assert result.raci_matrix is None

    def test_consultation_completed(self) -> None:
        from debate_hall_mcp.hall import apply_hall_event

        state = _make_hall_state(status="active")
        event = _make_event(
            "consultation_completed",
            {
                "thread_id": "consult-001",
                "compressed_log": "consult summary",
            },
        )
        result = apply_hall_event(state, event)
        assert "consult-001" in result.completed_debates
        assert result.compressed_log == "consult summary"

    def test_context_compressed(self) -> None:
        from debate_hall_mcp.hall import apply_hall_event

        state = _make_hall_state()
        event = _make_event(
            "context_compressed",
            {
                "compressed_log": "new compressed log",
            },
        )
        result = apply_hall_event(state, event)
        assert result.compressed_log == "new compressed log"

    def test_hall_closed(self) -> None:
        from debate_hall_mcp.hall import HallStatus, apply_hall_event

        state = _make_hall_state(status="reviewing")
        event = _make_event(
            "hall_closed",
            {
                "compressed_log": "final log",
            },
        )
        result = apply_hall_event(state, event)
        assert result.status == HallStatus.ARCHIVED
        assert result.compressed_log == "final log"

    def test_hall_force_closed(self) -> None:
        from debate_hall_mcp.hall import HallStatus, apply_hall_event

        state = _make_hall_state(status="active")
        event = _make_event("hall_force_closed")
        result = apply_hall_event(state, event)
        assert result.status == HallStatus.FORCE_CLOSED

    def test_malformed_event_data_skipped_w_ce_3(self) -> None:
        """W-CE-3: Malformed event data is logged and skipped."""
        from debate_hall_mcp.hall import apply_hall_event

        state = _make_hall_state()
        # Malformed: participant_registered with missing required fields
        event = _make_event("participant_registered", {"bad_field": True})
        # Should not crash — should log warning and skip
        result = apply_hall_event(state, event)
        # State should be updated (last_event_id/updated_at) but no participant added
        assert len(result.participants) == 0
        assert result.last_event_id == event.event_id

    def test_last_event_id_always_updated(self) -> None:
        from debate_hall_mcp.hall import apply_hall_event

        state = _make_hall_state()
        event = _make_event("hall_opened")
        result = apply_hall_event(state, event)
        assert result.last_event_id == event.event_id
        assert result.updated_at == event.timestamp


# ── P1T05: Event Ledger Functions ──────────────────────────────────────


class TestEventLedgerHelpers:
    """Test helper functions for file layout."""

    def test_get_halls_dir_creates_directory(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import _get_halls_dir

        halls_dir = _get_halls_dir(tmp_path)
        assert halls_dir.exists()
        assert halls_dir == tmp_path / "halls"

    def test_validate_hall_id_for_filesystem_accepts_valid(self) -> None:
        from debate_hall_mcp.hall import _validate_hall_id_for_filesystem

        # Should not raise
        _validate_hall_id_for_filesystem("hall-2026-01-15-my_topic")

    def test_validate_hall_id_for_filesystem_rejects_invalid(self) -> None:
        from debate_hall_mcp.hall import _validate_hall_id_for_filesystem

        with pytest.raises(ValueError, match="Invalid hall_id"):
            _validate_hall_id_for_filesystem("bad/id")


class TestAppendHallEvent:
    """Test append_hall_event persistence function."""

    def test_append_returns_hall_event_with_ulid(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event

        event = append_hall_event(
            "test-hall",
            HallEventType.HALL_OPENED,
            {"topic": "Test"},
            tmp_path,
        )
        assert len(event.event_id) == 26  # ULID length
        assert event.hall_id == "test-hall"
        assert event.event_type == HallEventType.HALL_OPENED

    def test_append_creates_events_file(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event

        append_hall_event(
            "test-hall",
            HallEventType.HALL_OPENED,
            {"topic": "Test"},
            tmp_path,
        )
        events_file = tmp_path / "halls" / "test-hall.events.jsonl"
        assert events_file.exists()

    def test_append_multiple_events(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event

        e1 = append_hall_event(
            "test-hall",
            HallEventType.HALL_OPENED,
            {},
            tmp_path,
        )
        e2 = append_hall_event(
            "test-hall",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        assert e1.event_id != e2.event_id
        events_file = tmp_path / "halls" / "test-hall.events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 2


class TestLoadHallEvents:
    """Test load_hall_events with after-filter and corrupt handling."""

    def test_load_events_returns_in_order(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event, load_hall_events

        append_hall_event("h1", HallEventType.HALL_OPENED, {}, tmp_path)
        append_hall_event(
            "h1",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        events, corrupt_count = load_hall_events("h1", tmp_path)
        assert len(events) == 2
        assert corrupt_count == 0
        assert events[0].event_type == HallEventType.HALL_OPENED
        assert events[1].event_type == HallEventType.PARTICIPANT_REGISTERED

    def test_load_events_after_filter(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event, load_hall_events

        e1 = append_hall_event("h1", HallEventType.HALL_OPENED, {}, tmp_path)
        append_hall_event(
            "h1",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        events, corrupt_count = load_hall_events("h1", tmp_path, after=e1.event_id)
        assert len(events) == 1
        assert corrupt_count == 0
        assert events[0].event_type == HallEventType.PARTICIPANT_REGISTERED

    def test_load_events_empty_file_returns_empty(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import load_hall_events

        # No events file -> empty list
        events, corrupt_count = load_hall_events("nonexistent", tmp_path)
        assert events == []
        assert corrupt_count == 0

    def test_load_events_corrupt_line_skipped(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, append_hall_event, load_hall_events

        append_hall_event("h1", HallEventType.HALL_OPENED, {}, tmp_path)
        # Inject a corrupt line
        events_file = tmp_path / "halls" / "h1.events.jsonl"
        with open(events_file, "a") as f:
            f.write("THIS IS NOT VALID JSON\n")
        append_hall_event(
            "h1",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "bob", "name": "Bob", "kind": "agent"},
            tmp_path,
        )
        events, corrupt_count = load_hall_events("h1", tmp_path)
        # Should have 2 valid events, corrupt line skipped
        assert len(events) == 2
        # CE-B1: corrupt_count should report the corrupt line
        assert corrupt_count == 1


# ── P1T06: Smart Loader + Save Hall ────────────────────────────────────


def _seed_hall(tmp_path: Path, hall_id: str = "test-hall") -> None:
    """Create a hall with one HALL_OPENED event for testing."""
    from debate_hall_mcp.hall import HallEventType, append_hall_event

    append_hall_event(
        hall_id,
        HallEventType.HALL_OPENED,
        {"topic": "Test Topic", "max_depth": 3, "max_context_tokens": 4096},
        tmp_path,
    )


class TestLoadHall:
    """Test load_hall Smart Loader with self-healing."""

    def test_load_from_events_only(self, tmp_path: Path) -> None:
        """No snapshot: full reconstruction from events."""
        from debate_hall_mcp.hall import HallStatus, load_hall

        _seed_hall(tmp_path)
        state = load_hall("test-hall", tmp_path)
        assert state.hall_id == "test-hall"
        assert state.topic == "Test Topic"
        assert state.status == HallStatus.OPEN

    def test_load_creates_snapshot(self, tmp_path: Path) -> None:
        """load_hall should flush snapshot after replay."""
        from debate_hall_mcp.hall import _get_hall_state_file, load_hall

        _seed_hall(tmp_path)
        load_hall("test-hall", tmp_path)
        snapshot = _get_hall_state_file("test-hall", tmp_path)
        assert snapshot.exists()

    def test_load_from_current_snapshot(self, tmp_path: Path) -> None:
        """When snapshot is up-to-date, no replay needed."""
        from debate_hall_mcp.hall import load_hall

        _seed_hall(tmp_path)
        # First load creates snapshot
        state1 = load_hall("test-hall", tmp_path)
        # Second load reads from snapshot (no new events)
        state2 = load_hall("test-hall", tmp_path)
        assert state2.hall_id == state1.hall_id
        assert state2.last_event_id == state1.last_event_id

    def test_load_with_delta_replay(self, tmp_path: Path) -> None:
        """Snapshot is stale, delta events replayed."""
        from debate_hall_mcp.hall import HallEventType, append_hall_event, load_hall

        _seed_hall(tmp_path)
        load_hall("test-hall", tmp_path)  # Create snapshot
        # Add more events after snapshot
        append_hall_event(
            "test-hall",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        state = load_hall("test-hall", tmp_path)
        assert "alice" in state.participants

    def test_load_not_found(self, tmp_path: Path) -> None:
        """No events + no snapshot = FileNotFoundError."""
        from debate_hall_mcp.hall import load_hall

        with pytest.raises(FileNotFoundError, match="not found"):
            load_hall("nonexistent", tmp_path)

    def test_load_corrupt_snapshot_falls_back_to_events_w_ce_1(
        self,
        tmp_path: Path,
    ) -> None:
        """W-CE-1: Corrupt snapshot triggers events-only reconstruction."""
        from debate_hall_mcp.hall import _get_hall_state_file, load_hall

        _seed_hall(tmp_path)
        load_hall("test-hall", tmp_path)  # Creates valid snapshot
        # Corrupt the snapshot
        snapshot = _get_hall_state_file("test-hall", tmp_path)
        snapshot.write_text("THIS IS NOT VALID JSON")
        # Should fall back to events-only reconstruction
        state = load_hall("test-hall", tmp_path)
        assert state.hall_id == "test-hall"
        assert state.topic == "Test Topic"


class TestSaveHall:
    """Test save_hall event-first write path."""

    def test_save_hall_appends_event_and_updates_state(
        self,
        tmp_path: Path,
    ) -> None:
        from debate_hall_mcp.hall import HallEventType, load_hall, save_hall

        _seed_hall(tmp_path)
        state = load_hall("test-hall", tmp_path)
        event = save_hall(
            state,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "bob", "name": "Bob", "kind": "agent"},
            tmp_path,
        )
        assert event.event_type == HallEventType.PARTICIPANT_REGISTERED
        assert "bob" in state.participants

    def test_save_hall_snapshot_updated(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import HallEventType, load_hall, save_hall

        _seed_hall(tmp_path)
        state = load_hall("test-hall", tmp_path)
        save_hall(
            state,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "bob", "name": "Bob", "kind": "agent"},
            tmp_path,
        )
        # Reload and verify
        state2 = load_hall("test-hall", tmp_path)
        assert "bob" in state2.participants

    def test_snapshot_excludes_provider_config_h002(self, tmp_path: Path) -> None:
        """H-002: provider_config must NOT appear in snapshot."""
        import json

        from debate_hall_mcp.hall import (
            HallEventType,
            _get_hall_state_file,
            load_hall,
            save_hall,
        )

        _seed_hall(tmp_path)
        state = load_hall("test-hall", tmp_path)
        save_hall(
            state,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        snapshot_file = _get_hall_state_file("test-hall", tmp_path)
        data = json.loads(snapshot_file.read_text())
        # Check that provider_config is not in any participant
        for pid, pdata in data.get("participants", {}).items():
            assert "provider_config" not in pdata, f"provider_config found in participant {pid}"

    def test_snapshot_file_permissions(self, tmp_path: Path) -> None:
        """Snapshot file should have 0o600 permissions."""
        import stat

        from debate_hall_mcp.hall import _get_hall_state_file, load_hall

        _seed_hall(tmp_path)
        load_hall("test-hall", tmp_path)
        snapshot = _get_hall_state_file("test-hall", tmp_path)
        mode = stat.S_IMODE(snapshot.stat().st_mode)
        assert mode == 0o600


# ── B-001: Concurrent Debate Reducer Logic ──────────────────────────────


class TestConcurrentDebateReducer:
    """B-001: Verify participants in other active debates are not reset."""

    def test_completing_one_debate_preserves_other_debate_participants(self) -> None:
        """Two debates active, complete one: participants in the other stay active."""
        from debate_hall_mcp.hall import (
            Participant,
            ParticipantKind,
            RaciMatrix,
            apply_hall_event,
        )

        state = _make_hall_state(status="active")
        # Register participants
        state.participants["alice"] = Participant(
            id="alice",
            name="Alice",
            kind=ParticipantKind.AGENT,
            status="active",
            raci_designation="R",
        )
        state.participants["bob"] = Participant(
            id="bob",
            name="Bob",
            kind=ParticipantKind.AGENT,
            status="active",
            raci_designation="A",
        )
        state.participants["charlie"] = Participant(
            id="charlie",
            name="Charlie",
            kind=ParticipantKind.AGENT,
            status="active",
            raci_designation="C",
        )
        # Two active debates
        state.active_debates = ["debate-1", "debate-2"]
        state.raci_matrix = RaciMatrix(
            responsible="alice",
            accountable="bob",
            consulted=["charlie"],
        )

        # Complete debate-1, with alice and charlie as participants
        event = _make_event(
            "debate_completed",
            {
                "thread_id": "debate-1",
                "participant_ids": ["alice", "charlie"],
            },
        )
        result = apply_hall_event(state, event)

        # debate-1 moved to completed, debate-2 still active
        assert "debate-1" not in result.active_debates
        assert "debate-1" in result.completed_debates
        assert "debate-2" in result.active_debates

        # B-001: Participants should STILL be active because debate-2 is running
        assert result.participants["alice"].status == "active"
        assert result.participants["alice"].raci_designation == "R"
        assert result.participants["bob"].status == "active"
        assert result.participants["charlie"].status == "active"

        # B-001: RACI matrix should be preserved while debates are active
        assert result.raci_matrix is not None

        # Status should remain ACTIVE (not REVIEWING)
        from debate_hall_mcp.hall import HallStatus

        assert result.status == HallStatus.ACTIVE

    def test_completing_last_debate_resets_participants_and_raci(self) -> None:
        """When the last debate completes, participants and RACI are reset."""
        from debate_hall_mcp.hall import (
            HallStatus,
            Participant,
            ParticipantKind,
            RaciMatrix,
            apply_hall_event,
        )

        state = _make_hall_state(status="active")
        state.participants["alice"] = Participant(
            id="alice",
            name="Alice",
            kind=ParticipantKind.AGENT,
            status="active",
            raci_designation="R",
        )
        state.participants["bob"] = Participant(
            id="bob",
            name="Bob",
            kind=ParticipantKind.AGENT,
            status="active",
            raci_designation="A",
        )
        state.active_debates = ["debate-only"]
        state.raci_matrix = RaciMatrix(responsible="alice", accountable="bob")

        event = _make_event(
            "debate_completed",
            {
                "thread_id": "debate-only",
                "participant_ids": ["alice", "bob"],
            },
        )
        result = apply_hall_event(state, event)

        # All debates done: participants reset, RACI cleared
        assert result.participants["alice"].status == "on_call"
        assert result.participants["alice"].raci_designation is None
        assert result.participants["bob"].status == "on_call"
        assert result.participants["bob"].raci_designation is None
        assert result.raci_matrix is None
        assert result.status == HallStatus.REVIEWING


# ── CE-B1: Corrupt Event Silent Skip Policy ────────────────────────────


class TestCorruptEventPolicy:
    """CE-B1: Corrupt events must not cause silent snapshot advancement."""

    def test_corrupt_event_prevents_snapshot_update(self, tmp_path: Path) -> None:
        """Load with corrupt events succeeds but does NOT update snapshot."""
        from debate_hall_mcp.hall import (
            HallEventType,
            _get_hall_state_file,
            append_hall_event,
            load_hall,
        )

        # Create hall and build initial snapshot
        _seed_hall(tmp_path, hall_id="corrupt-test")
        load_hall("corrupt-test", tmp_path)
        snapshot_file = _get_hall_state_file("corrupt-test", tmp_path)
        assert snapshot_file.exists()
        snapshot_mtime_before = snapshot_file.stat().st_mtime

        # Add a valid event after snapshot
        append_hall_event(
            "corrupt-test",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "alice", "name": "Alice", "kind": "agent"},
            tmp_path,
        )
        # Inject a corrupt line into the events file
        events_file = tmp_path / "halls" / "corrupt-test.events.jsonl"
        with open(events_file, "a") as f:
            f.write("CORRUPT LINE HERE\n")

        # Load should succeed (availability)
        state2 = load_hall("corrupt-test", tmp_path)
        assert "alice" in state2.participants

        # CE-B1: Snapshot should NOT have been updated
        # (mtime should be unchanged because we didn't re-save)
        snapshot_mtime_after = snapshot_file.stat().st_mtime
        assert snapshot_mtime_after == snapshot_mtime_before

    def test_corrupt_event_count_returned_by_load_hall_events(
        self,
        tmp_path: Path,
    ) -> None:
        """load_hall_events returns accurate corrupt count."""
        from debate_hall_mcp.hall import HallEventType, append_hall_event, load_hall_events

        append_hall_event("h-corrupt", HallEventType.HALL_OPENED, {}, tmp_path)
        events_file = tmp_path / "halls" / "h-corrupt.events.jsonl"
        with open(events_file, "a") as f:
            f.write("BAD LINE 1\n")
            f.write("BAD LINE 2\n")
        append_hall_event(
            "h-corrupt",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "x", "name": "X", "kind": "agent"},
            tmp_path,
        )
        events, corrupt_count = load_hall_events("h-corrupt", tmp_path)
        assert len(events) == 2
        assert corrupt_count == 2

    def test_clean_events_still_update_snapshot(self, tmp_path: Path) -> None:
        """When there are no corrupt events, snapshot IS updated normally."""
        import json

        from debate_hall_mcp.hall import (
            HallEventType,
            _get_hall_state_file,
            append_hall_event,
            load_hall,
        )

        _seed_hall(tmp_path, hall_id="clean-test")
        load_hall("clean-test", tmp_path)  # Creates initial snapshot

        append_hall_event(
            "clean-test",
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "bob", "name": "Bob", "kind": "agent"},
            tmp_path,
        )
        state = load_hall("clean-test", tmp_path)
        assert "bob" in state.participants

        # Snapshot should be updated (contains bob)
        snapshot_file = _get_hall_state_file("clean-test", tmp_path)
        snap_data = json.loads(snapshot_file.read_text())
        assert "bob" in snap_data["participants"]

    def test_save_hall_blocks_with_corrupt_events(self, tmp_path: Path) -> None:
        """CE-B1 write-path: save_hall should refuse to write when corruption exists."""
        from debate_hall_mcp.hall import (
            HallCorruptionError,
            HallEventType,
            append_hall_event,
            load_hall,
            save_hall,
        )

        hall_id = "test-write-corruption"

        # Create hall using append_hall_event
        append_hall_event(
            hall_id, HallEventType.HALL_OPENED, {"topic": "Write Corruption Test"}, tmp_path
        )

        # Load the hall state
        state = load_hall(hall_id, tmp_path)

        # Manually corrupt an event line in the ledger
        events_file = tmp_path / "halls" / f"{hall_id}.events.jsonl"
        with open(events_file, "a") as f:
            f.write("CORRUPT_JSON_LINE\n")

        # Attempt to save should raise HallCorruptionError
        with pytest.raises(HallCorruptionError) as exc:
            save_hall(
                state,
                HallEventType.PARTICIPANT_REGISTERED,
                {"participant_id": "bob", "role": "Wind"},
                tmp_path,
            )

        assert "corrupt events" in str(exc.value)
        assert "Cannot advance snapshot" in str(exc.value)


# ── W-001: Events-Only Reconstruction Validation ───────────────────────


class TestEventsOnlyValidation:
    """W-001: Validate first event type during events-only reconstruction."""

    def test_non_hall_opened_first_event_uses_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        """If first event is not HALL_OPENED, use default init values."""
        from datetime import UTC, datetime

        from ulid import ULID

        from debate_hall_mcp.hall import (
            HallEvent,
            HallEventType,
            _get_hall_events_file,
            _get_halls_dir,
            load_hall,
        )

        # Manually write an events file where first event is NOT HALL_OPENED
        _get_halls_dir(tmp_path)  # ensure dir exists
        events_file = _get_hall_events_file("bad-start", tmp_path)

        event = HallEvent(
            event_id=str(ULID()),
            hall_id="bad-start",
            event_type=HallEventType.PARTICIPANT_REGISTERED,
            timestamp=datetime.now(UTC),
            data={"id": "alice", "name": "Alice", "kind": "agent"},
        )
        with open(events_file, "w") as f:
            f.write(event.model_dump_json() + "\n")

        # Should load successfully with defaults (not crash)
        state = load_hall("bad-start", tmp_path)
        assert state.hall_id == "bad-start"
        assert state.topic == "(unknown)"  # Default, not from event data
        assert state.max_depth == 3  # Default
        # The participant event was still applied by the reducer
        assert "alice" in state.participants

    def test_hall_opened_first_event_uses_its_data(self, tmp_path: Path) -> None:
        """Normal case: HALL_OPENED first event provides init data."""
        from debate_hall_mcp.hall import load_hall

        _seed_hall(tmp_path, hall_id="good-start")
        state = load_hall("good-start", tmp_path)
        assert state.topic == "Test Topic"
        assert state.max_depth == 3
        assert state.max_context_tokens == 4096


# ── P1T07: DebateRoom Extension + G1 Benchmark ─────────────────────────


class TestDebateRoomExtension:
    """Test parent_hall_id and parent_thread_id fields on DebateRoom."""

    def test_debate_room_new_fields_default_to_none(self) -> None:
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="test-2026-01-15-my-topic",
            topic="Test",
            mode=DebateMode.FIXED,
        )
        assert room.parent_hall_id is None
        assert room.parent_thread_id is None

    def test_debate_room_with_parent_fields(self) -> None:
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="test-thread",
            topic="Test",
            mode=DebateMode.RACI,
            parent_hall_id="hall-2026-01-15-topic",
            parent_thread_id="parent-thread",
        )
        assert room.parent_hall_id == "hall-2026-01-15-topic"
        assert room.parent_thread_id == "parent-thread"

    def test_old_json_roundtrip_without_parent_fields(self) -> None:
        """Backward compat: old JSON without parent fields deserializes OK."""
        import json

        from debate_hall_mcp.state import DebateRoom

        old_json = json.dumps(
            {
                "thread_id": "old-thread",
                "topic": "Old topic",
                "mode": "fixed",
                "status": "active",
            }
        )
        room = DebateRoom.model_validate_json(old_json)
        assert room.parent_hall_id is None
        assert room.parent_thread_id is None


class TestG1Benchmark:
    """G1: 200 event replay < 200ms."""

    def _generate_events(self, tmp_path: Path, count: int) -> None:
        """Generate N hall events for benchmarking."""
        from debate_hall_mcp.hall import HallEventType, append_hall_event

        hall_id = f"bench-{count}"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": f"Benchmark {count} events"},
            tmp_path,
        )
        for i in range(count - 1):
            append_hall_event(
                hall_id,
                HallEventType.PARTICIPANT_REGISTERED,
                {"id": f"p{i}", "name": f"Participant {i}", "kind": "agent"},
                tmp_path,
            )

    def test_g1_50_events(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import load_hall

        self._generate_events(tmp_path, 50)
        start = time.monotonic()
        load_hall("bench-50", tmp_path)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"50 events took {elapsed_ms:.1f}ms (limit: 200ms)"

    def test_g1_100_events(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import load_hall

        self._generate_events(tmp_path, 100)
        start = time.monotonic()
        load_hall("bench-100", tmp_path)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"100 events took {elapsed_ms:.1f}ms (limit: 200ms)"

    def test_g1_200_events(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import load_hall

        self._generate_events(tmp_path, 200)
        start = time.monotonic()
        load_hall("bench-200", tmp_path)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"200 events took {elapsed_ms:.1f}ms (limit: 200ms)"


# ── P2T01: Checkpoint/Restore Lifecycle (Phase 2) ────────────────────


class TestCheckpointMetadata:
    """Test CheckpointMetadata model."""

    def test_checkpoint_metadata_creation(self) -> None:
        from datetime import UTC, datetime

        from debate_hall_mcp.hall import CheckpointMetadata

        now = datetime.now(UTC)
        metadata = CheckpointMetadata(
            checkpoint_id="01HN1234567890ABCDEFGHJ",
            hall_id="test-hall",
            timestamp=now,
            description="Test checkpoint",
            event_count=5,
            state_hash="abc123def456",
        )

        assert metadata.checkpoint_id == "01HN1234567890ABCDEFGHJ"
        assert metadata.hall_id == "test-hall"
        assert metadata.timestamp == now
        assert metadata.description == "Test checkpoint"
        assert metadata.event_count == 5
        assert metadata.state_hash == "abc123def456"


class TestCreateCheckpoint:
    """Test create_checkpoint function."""

    def test_create_checkpoint_success(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
        )

        # Setup: Create a hall with some events
        hall_id = "cp-test-1"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test Hall", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p1", "name": "Participant 1", "kind": "agent"},
            tmp_path,
        )

        # Action: Create checkpoint
        checkpoint_id = create_checkpoint(hall_id, "Before debate start", tmp_path)

        # Assert: Checkpoint ID is a ULID
        assert len(checkpoint_id) == 26
        assert checkpoint_id.startswith("01")

        # Assert: Checkpoint file exists
        checkpoints_dir = tmp_path / "halls" / hall_id / ".checkpoints"
        checkpoint_file = checkpoints_dir / f"checkpoint_{checkpoint_id}.json"
        assert checkpoint_file.exists()

    def test_create_checkpoint_stores_metadata(self, tmp_path: Path) -> None:
        import json

        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
        )

        # Setup
        hall_id = "cp-test-2"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Action
        checkpoint_id = create_checkpoint(hall_id, "Test checkpoint", tmp_path)

        # Assert: Read checkpoint file and verify metadata
        checkpoints_dir = tmp_path / "halls" / hall_id / ".checkpoints"
        checkpoint_file = checkpoints_dir / f"checkpoint_{checkpoint_id}.json"
        with open(checkpoint_file) as f:
            data = json.load(f)

        assert data["checkpoint_id"] == checkpoint_id
        assert data["hall_id"] == hall_id
        assert data["description"] == "Test checkpoint"
        assert "timestamp" in data
        assert "event_count" in data
        assert "state_hash" in data
        assert "state" in data

    def test_create_checkpoint_nonexistent_hall(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import create_checkpoint

        with pytest.raises(FileNotFoundError):
            create_checkpoint("nonexistent-hall", "Test", tmp_path)


class TestListCheckpoints:
    """Test list_checkpoints function."""

    def test_list_checkpoints_empty(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            list_checkpoints,
        )

        # Setup: Create hall with no checkpoints
        hall_id = "lc-test-1"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Action
        checkpoints = list_checkpoints(hall_id, tmp_path)

        # Assert
        assert checkpoints == []

    def test_list_checkpoints_multiple(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
            list_checkpoints,
        )

        # Setup
        hall_id = "lc-test-2"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Create multiple checkpoints
        cp1 = create_checkpoint(hall_id, "First checkpoint", tmp_path)
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p1", "name": "P1", "kind": "agent"},
            tmp_path,
        )
        cp2 = create_checkpoint(hall_id, "Second checkpoint", tmp_path)

        # Action
        checkpoints = list_checkpoints(hall_id, tmp_path)

        # Assert: Returns sorted list (most recent first)
        assert len(checkpoints) == 2
        assert checkpoints[0].checkpoint_id == cp2
        assert checkpoints[0].description == "Second checkpoint"
        assert checkpoints[1].checkpoint_id == cp1
        assert checkpoints[1].description == "First checkpoint"


class TestRestoreFromCheckpoint:
    """Test restore_from_checkpoint function."""

    def test_restore_from_checkpoint_success(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
            load_hall,
            restore_from_checkpoint,
        )

        # Setup: Create hall, add events, checkpoint, add more events
        hall_id = "restore-test-1"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p1", "name": "P1", "kind": "agent"},
            tmp_path,
        )

        # Create checkpoint
        checkpoint_id = create_checkpoint(hall_id, "Before p2", tmp_path)

        # Add more events after checkpoint
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p2", "name": "P2", "kind": "agent"},
            tmp_path,
        )

        # Verify current state has both participants
        current = load_hall(hall_id, tmp_path)
        assert len(current.participants) == 2

        # Action: Restore from checkpoint
        restored = restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)

        # Assert: Restored state has only first participant
        assert len(restored.participants) == 1
        assert "p1" in restored.participants
        assert "p2" not in restored.participants

    def test_restore_creates_checkpoint_restored_event(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
            load_hall_events,
            restore_from_checkpoint,
        )

        # Setup
        hall_id = "restore-test-2"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )
        checkpoint_id = create_checkpoint(hall_id, "Test", tmp_path)
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p1", "name": "P1", "kind": "agent"},
            tmp_path,
        )

        # Action: Restore
        restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)

        # Assert: Check event ledger contains CHECKPOINT_RESTORED event
        events, _ = load_hall_events(hall_id, tmp_path)
        restored_events = [e for e in events if e.event_type == HallEventType.CHECKPOINT_RESTORED]
        assert len(restored_events) == 1
        assert restored_events[0].data["checkpoint_id"] == checkpoint_id

    def test_restore_preserves_append_only_ledger(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
            load_hall_events,
            restore_from_checkpoint,
        )

        # Setup
        hall_id = "restore-test-3"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )
        checkpoint_id = create_checkpoint(hall_id, "Test", tmp_path)
        append_hall_event(
            hall_id,
            HallEventType.PARTICIPANT_REGISTERED,
            {"id": "p1", "name": "P1", "kind": "agent"},
            tmp_path,
        )

        # Record event count before restore
        events_before, _ = load_hall_events(hall_id, tmp_path)
        count_before = len(events_before)

        # Action: Restore
        restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)

        # Assert: Events after checkpoint are NOT deleted (append-only I4)
        events_after, _ = load_hall_events(hall_id, tmp_path)
        # Should have original events + CHECKPOINT_RESTORED event
        assert len(events_after) > count_before

    def test_restore_nonexistent_checkpoint(self, tmp_path: Path) -> None:
        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            restore_from_checkpoint,
        )

        hall_id = "restore-test-4"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        with pytest.raises(FileNotFoundError):
            restore_from_checkpoint(hall_id, "01HN1234567890FAKE", tmp_path)


class TestCheckpointHashVerification:
    """Test checkpoint hash verification for integrity."""

    def test_checkpoint_includes_state_hash(self, tmp_path: Path) -> None:
        import json

        from debate_hall_mcp.hall import (
            HallEventType,
            append_hall_event,
            create_checkpoint,
        )

        hall_id = "hash-test-1"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        checkpoint_id = create_checkpoint(hall_id, "Test", tmp_path)

        # Read checkpoint and verify hash field exists
        checkpoints_dir = tmp_path / "halls" / hall_id / ".checkpoints"
        checkpoint_file = checkpoints_dir / f"checkpoint_{checkpoint_id}.json"
        with open(checkpoint_file) as f:
            data = json.load(f)

        assert "state_hash" in data
        assert len(data["state_hash"]) == 64  # SHA-256 hex digest

    def test_restore_detects_tampered_checkpoint(self, tmp_path: Path) -> None:
        """Test that restore detects and rejects tampered checkpoint data.

        Security requirement: CRS blocking finding #1
        Verify that restore_from_checkpoint validates the state_hash
        and raises HallCorruptionError when hash doesn't match.
        """
        import json

        from debate_hall_mcp.hall import (
            HallCorruptionError,
            HallEventType,
            append_hall_event,
            create_checkpoint,
            restore_from_checkpoint,
        )

        hall_id = "tamper-test"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Create checkpoint
        checkpoint_id = create_checkpoint(hall_id, "Before tampering", tmp_path)

        # Tamper with checkpoint by modifying state data
        checkpoints_dir = tmp_path / "halls" / hall_id / ".checkpoints"
        checkpoint_file = checkpoints_dir / f"checkpoint_{checkpoint_id}.json"

        with open(checkpoint_file) as f:
            data = json.load(f)

        # Tamper: Change state data without updating hash
        # Modify description field which won't trigger validation error
        data["state"]["description"] = "TAMPERED DATA"

        with open(checkpoint_file, "w") as f:
            json.dump(data, f)

        # Attempt restore - should detect hash mismatch
        with pytest.raises(HallCorruptionError, match="integrity check failed"):
            restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)

    def test_restore_blocks_with_corrupted_ledger(self, tmp_path: Path) -> None:
        """Test that restore blocks when event ledger has corrupt events.

        Security requirement: CE blocking finding #2 (CE-B1 gate bypass)
        Verify that restore_from_checkpoint checks for ledger corruption
        before restoring and raises HallCorruptionError.
        """
        from debate_hall_mcp.hall import (
            HallCorruptionError,
            HallEventType,
            append_hall_event,
            create_checkpoint,
            restore_from_checkpoint,
        )

        hall_id = "corrupt-ledger-test"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Create checkpoint
        checkpoint_id = create_checkpoint(hall_id, "Before corruption", tmp_path)

        # Corrupt the event ledger by writing invalid JSON
        events_file = tmp_path / "halls" / f"{hall_id}.events.jsonl"
        with open(events_file, "a") as f:
            f.write('{"invalid": "json" missing brace\n')

        # Attempt restore - should detect corruption and block
        with pytest.raises(HallCorruptionError, match="corrupt events in ledger"):
            restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)

    def test_checkpoint_hash_mismatch_raises_error(self, tmp_path: Path) -> None:
        """Test that hash validation logic correctly detects mismatches.

        Security requirement: CRS blocking finding #1
        Verify the hash verification algorithm itself works correctly
        by manually creating a checkpoint with wrong hash.
        """
        import json

        from debate_hall_mcp.hall import (
            HallCorruptionError,
            HallEventType,
            append_hall_event,
            restore_from_checkpoint,
        )

        hall_id = "hash-mismatch-test"
        append_hall_event(
            hall_id,
            HallEventType.HALL_OPENED,
            {"topic": "Test", "max_depth": 3, "tier_name": "standard"},
            tmp_path,
        )

        # Manually create a checkpoint with incorrect hash
        from ulid import ULID

        from debate_hall_mcp.hall import _get_checkpoints_dir, load_hall

        checkpoint_id = str(ULID())
        checkpoints_dir = _get_checkpoints_dir(hall_id, tmp_path)
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        state = load_hall(hall_id, tmp_path)
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "description": "Fake checkpoint",
            "state": state.model_dump(mode="json"),
            "state_hash": "0" * 64,  # Wrong hash
        }

        checkpoint_file = checkpoints_dir / f"checkpoint_{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)

        # Attempt restore - should detect hash mismatch
        with pytest.raises(HallCorruptionError, match="integrity check failed"):
            restore_from_checkpoint(hall_id, checkpoint_id, tmp_path)
