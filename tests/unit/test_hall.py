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

    def test_hall_event_type_count(self) -> None:
        from debate_hall_mcp.hall import HallEventType

        assert len(HallEventType) == 10


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
