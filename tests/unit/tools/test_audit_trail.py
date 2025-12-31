"""Tests for audit trail and tombstone context preservation (Issue #40).

TDD Discipline: RED phase - write failing tests first.
Immutables: I4 (Verifiable Event Ledger)

This module tests:
1. AuditEvent model existence and required fields
2. audit_log field on DebateRoom
3. force_close records audit event with reason
4. tombstone records audit event + preserves original content hash
5. Audit events are persisted and queryable
6. Backward compatibility (None/empty audit_log allowed)
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from debate_hall_mcp.state import (
    AuditAction,
    AuditEvent,
    DebateMode,
    DebateRoom,
    load_debate_state,
)
from debate_hall_mcp.tools.admin import debate_force_close, debate_tombstone
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


class TestAuditEventModel:
    """Tests for AuditEvent model structure."""

    def test_audit_event_model_exists(self) -> None:
        """Test that AuditEvent model exists with required fields."""
        event = AuditEvent(
            action=AuditAction.FORCE_CLOSE,
            reason="Test reason",
            timestamp=datetime.now(UTC),
        )
        assert event.action == AuditAction.FORCE_CLOSE
        assert event.reason == "Test reason"
        assert event.timestamp is not None

    def test_audit_event_has_optional_actor(self) -> None:
        """Test that AuditEvent has optional actor field."""
        event = AuditEvent(
            action=AuditAction.FORCE_CLOSE,
            reason="Test reason",
            timestamp=datetime.now(UTC),
            actor="admin-agent",
        )
        assert event.actor == "admin-agent"

    def test_audit_event_without_actor(self) -> None:
        """Test that AuditEvent works without actor (optional field)."""
        event = AuditEvent(
            action=AuditAction.TOMBSTONE,
            reason="Content redaction",
            timestamp=datetime.now(UTC),
        )
        assert event.actor is None

    def test_audit_event_tombstone_has_turn_index(self) -> None:
        """Test that tombstone audit events can store turn_index."""
        event = AuditEvent(
            action=AuditAction.TOMBSTONE,
            reason="Redaction",
            timestamp=datetime.now(UTC),
            turn_index=2,
        )
        assert event.turn_index == 2

    def test_audit_event_tombstone_has_original_content_hash(self) -> None:
        """Test that tombstone audit events store original content hash."""
        original_content = "This is the original content"
        content_hash = hashlib.sha256(original_content.encode()).hexdigest()

        event = AuditEvent(
            action=AuditAction.TOMBSTONE,
            reason="Redaction",
            timestamp=datetime.now(UTC),
            turn_index=1,
            original_content_hash=content_hash,
        )
        assert event.original_content_hash == content_hash


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_audit_action_has_force_close(self) -> None:
        """Test AuditAction has FORCE_CLOSE value."""
        assert AuditAction.FORCE_CLOSE.value == "force_close"

    def test_audit_action_has_tombstone(self) -> None:
        """Test AuditAction has TOMBSTONE value."""
        assert AuditAction.TOMBSTONE.value == "tombstone"


class TestDebateRoomAuditLog:
    """Tests for audit_log field on DebateRoom."""

    def test_debate_room_has_audit_log_field(self) -> None:
        """Test that DebateRoom has audit_log field."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
        )
        assert hasattr(room, "audit_log")
        assert isinstance(room.audit_log, list)

    def test_debate_room_audit_log_defaults_empty(self) -> None:
        """Test that audit_log defaults to empty list."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
        )
        assert room.audit_log == []

    def test_debate_room_can_append_audit_event(self) -> None:
        """Test that audit events can be appended to audit_log."""
        room = DebateRoom(
            thread_id="2025-01-01-test",
            topic="Test topic",
            mode=DebateMode.FIXED,
        )
        event = AuditEvent(
            action=AuditAction.FORCE_CLOSE,
            reason="Test",
            timestamp=datetime.now(UTC),
        )
        room.audit_log.append(event)
        assert len(room.audit_log) == 1
        assert room.audit_log[0].action == AuditAction.FORCE_CLOSE


class TestForceCloseAuditTrail:
    """Tests for audit trail on force_close operations."""

    def test_force_close_appends_audit_event(self, tmp_path: Path) -> None:
        """Test that force_close appends audit event to room."""
        debate_init(
            thread_id="2025-01-01-audit-fc-001",
            topic="Audit test",
            state_dir=tmp_path,
        )

        debate_force_close(
            thread_id="2025-01-01-audit-fc-001",
            reason="Emergency shutdown",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-audit-fc-001", tmp_path)
        assert len(room.audit_log) == 1
        assert room.audit_log[0].action == AuditAction.FORCE_CLOSE
        assert room.audit_log[0].reason == "Emergency shutdown"

    def test_force_close_audit_event_has_timestamp(self, tmp_path: Path) -> None:
        """Test that force_close audit event has timestamp."""
        debate_init(
            thread_id="2025-01-01-audit-fc-002",
            topic="Audit test",
            state_dir=tmp_path,
        )

        before = datetime.now(UTC)
        debate_force_close(
            thread_id="2025-01-01-audit-fc-002",
            reason="Test",
            state_dir=tmp_path,
        )
        after = datetime.now(UTC)

        room = load_debate_state("2025-01-01-audit-fc-002", tmp_path)
        event_time = room.audit_log[0].timestamp
        assert before <= event_time <= after

    def test_force_close_audit_event_persisted(self, tmp_path: Path) -> None:
        """Test that force_close audit event survives save/load cycle."""
        debate_init(
            thread_id="2025-01-01-audit-fc-003",
            topic="Persistence test",
            state_dir=tmp_path,
        )

        debate_force_close(
            thread_id="2025-01-01-audit-fc-003",
            reason="Persistence check",
            state_dir=tmp_path,
        )

        # Load state fresh from disk
        room = load_debate_state("2025-01-01-audit-fc-003", tmp_path)
        assert len(room.audit_log) == 1
        assert room.audit_log[0].reason == "Persistence check"

    def test_force_close_returns_audit_event_in_result(self, tmp_path: Path) -> None:
        """Test that force_close result includes audit reference."""
        debate_init(
            thread_id="2025-01-01-audit-fc-004",
            topic="Result test",
            state_dir=tmp_path,
        )

        result = debate_force_close(
            thread_id="2025-01-01-audit-fc-004",
            reason="Result check",
            state_dir=tmp_path,
        )

        # Result should indicate audit was recorded
        assert "audit_event_index" in result
        assert result["audit_event_index"] == 0


class TestTombstoneAuditTrail:
    """Tests for audit trail on tombstone operations."""

    def test_tombstone_appends_audit_event(self, tmp_path: Path) -> None:
        """Test that tombstone appends audit event to room."""
        debate_init(
            thread_id="2025-01-01-audit-ts-001",
            topic="Tombstone audit test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-ts-001", "Wind", "Original content", state_dir=tmp_path)

        debate_tombstone(
            thread_id="2025-01-01-audit-ts-001",
            turn_index=0,
            reason="Content policy violation",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-audit-ts-001", tmp_path)
        assert len(room.audit_log) == 1
        assert room.audit_log[0].action == AuditAction.TOMBSTONE
        assert room.audit_log[0].reason == "Content policy violation"

    def test_tombstone_audit_event_has_turn_index(self, tmp_path: Path) -> None:
        """Test that tombstone audit event records turn_index."""
        debate_init(
            thread_id="2025-01-01-audit-ts-002",
            topic="Turn index test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-ts-002", "Wind", "Turn 0", state_dir=tmp_path)
        debate_turn("2025-01-01-audit-ts-002", "Wall", "Turn 1", state_dir=tmp_path)

        debate_tombstone(
            thread_id="2025-01-01-audit-ts-002",
            turn_index=1,
            reason="Redacted",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-audit-ts-002", tmp_path)
        assert room.audit_log[0].turn_index == 1

    def test_tombstone_audit_event_preserves_original_content_hash(self, tmp_path: Path) -> None:
        """Test that tombstone audit event stores hash of original content."""
        debate_init(
            thread_id="2025-01-01-audit-ts-003",
            topic="Content hash test",
            state_dir=tmp_path,
        )
        original_content = "This is the original sensitive content"
        debate_turn("2025-01-01-audit-ts-003", "Wind", original_content, state_dir=tmp_path)

        # Calculate expected hash
        expected_hash = hashlib.sha256(original_content.encode()).hexdigest()

        debate_tombstone(
            thread_id="2025-01-01-audit-ts-003",
            turn_index=0,
            reason="Sensitive data",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-audit-ts-003", tmp_path)
        assert room.audit_log[0].original_content_hash == expected_hash

    def test_tombstone_audit_event_has_timestamp(self, tmp_path: Path) -> None:
        """Test that tombstone audit event has timestamp."""
        debate_init(
            thread_id="2025-01-01-audit-ts-004",
            topic="Timestamp test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-ts-004", "Wind", "Content", state_dir=tmp_path)

        before = datetime.now(UTC)
        debate_tombstone(
            thread_id="2025-01-01-audit-ts-004",
            turn_index=0,
            reason="Test",
            state_dir=tmp_path,
        )
        after = datetime.now(UTC)

        room = load_debate_state("2025-01-01-audit-ts-004", tmp_path)
        event_time = room.audit_log[0].timestamp
        assert before <= event_time <= after

    def test_tombstone_returns_audit_event_in_result(self, tmp_path: Path) -> None:
        """Test that tombstone result includes audit reference."""
        debate_init(
            thread_id="2025-01-01-audit-ts-005",
            topic="Result test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-ts-005", "Wind", "Content", state_dir=tmp_path)

        result = debate_tombstone(
            thread_id="2025-01-01-audit-ts-005",
            turn_index=0,
            reason="Result check",
            state_dir=tmp_path,
        )

        assert "audit_event_index" in result
        assert "original_content_hash" in result


class TestMultipleAuditEvents:
    """Tests for multiple audit events in sequence."""

    def test_multiple_tombstones_accumulate_audit_events(self, tmp_path: Path) -> None:
        """Test that multiple tombstones append multiple audit events."""
        debate_init(
            thread_id="2025-01-01-audit-multi-001",
            topic="Multi-tombstone test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-multi-001", "Wind", "Content 0", state_dir=tmp_path)
        debate_turn("2025-01-01-audit-multi-001", "Wall", "Content 1", state_dir=tmp_path)
        debate_turn("2025-01-01-audit-multi-001", "Door", "Content 2", state_dir=tmp_path)

        # Tombstone multiple turns
        debate_tombstone(
            "2025-01-01-audit-multi-001", turn_index=0, reason="First", state_dir=tmp_path
        )
        debate_tombstone(
            "2025-01-01-audit-multi-001", turn_index=2, reason="Second", state_dir=tmp_path
        )

        room = load_debate_state("2025-01-01-audit-multi-001", tmp_path)
        assert len(room.audit_log) == 2
        assert room.audit_log[0].turn_index == 0
        assert room.audit_log[0].reason == "First"
        assert room.audit_log[1].turn_index == 2
        assert room.audit_log[1].reason == "Second"

    def test_force_close_after_tombstone(self, tmp_path: Path) -> None:
        """Test that force_close after tombstone accumulates audit events."""
        debate_init(
            thread_id="2025-01-01-audit-mixed-001",
            topic="Mixed operations test",
            state_dir=tmp_path,
        )
        debate_turn("2025-01-01-audit-mixed-001", "Wind", "Content", state_dir=tmp_path)

        debate_tombstone(
            "2025-01-01-audit-mixed-001", turn_index=0, reason="Redact", state_dir=tmp_path
        )
        debate_force_close("2025-01-01-audit-mixed-001", reason="Shutdown", state_dir=tmp_path)

        room = load_debate_state("2025-01-01-audit-mixed-001", tmp_path)
        assert len(room.audit_log) == 2
        assert room.audit_log[0].action == AuditAction.TOMBSTONE
        assert room.audit_log[1].action == AuditAction.FORCE_CLOSE


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing data."""

    def test_debate_room_loads_without_audit_log(self, tmp_path: Path) -> None:
        """Test that DebateRoom loads correctly when audit_log is missing (old data)."""
        # Create a minimal state file without audit_log (simulating old format)
        state_file = tmp_path / "2025-01-01-legacy.json"
        legacy_data = {
            "thread_id": "2025-01-01-legacy",
            "topic": "Legacy topic",
            "mode": "fixed",
            "status": "active",
            "max_turns": 12,
            "max_rounds": 4,
            "strict_cognition": False,
            "octave_preamble": True,
            "expected_next_role": None,
            "turns": [],
            "synthesis": None,
            # Note: no audit_log field
        }
        with open(state_file, "w") as f:
            json.dump(legacy_data, f)

        room = load_debate_state("2025-01-01-legacy", tmp_path)
        assert room.audit_log == []  # Should default to empty list

    def test_debate_room_serializes_audit_log(self) -> None:
        """Test that audit_log is properly serialized to JSON."""
        room = DebateRoom(
            thread_id="2025-01-01-serialize",
            topic="Serialization test",
            mode=DebateMode.FIXED,
            audit_log=[
                AuditEvent(
                    action=AuditAction.FORCE_CLOSE,
                    reason="Test reason",
                    timestamp=datetime.now(UTC),
                )
            ],
        )

        # Serialize and deserialize
        json_str = room.model_dump_json()
        data = json.loads(json_str)

        assert "audit_log" in data
        assert len(data["audit_log"]) == 1
        assert data["audit_log"][0]["action"] == "force_close"
        assert data["audit_log"][0]["reason"] == "Test reason"
