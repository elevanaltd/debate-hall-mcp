"""Tests for hash chain link verification on load (Issue #58).

TDD Discipline: RED phase - write failing tests first.
Immutables: I4 (Verifiable Event Ledger)

This module tests:
1. Valid hash chain loads successfully
2. Broken chain (previous_hash mismatch) fails with clear error
3. Empty debate (no turns) loads successfully
4. Single turn debate loads successfully
5. Tombstoned turns preserve chain validity (hash not recomputed)

IMPORTANT: Verification checks LINKS only (previous_hash -> prior content_hash).
Does NOT re-compute content hashes (would break tombstone compatibility).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    Turn,
    load_debate_state,
    save_debate_state,
)
from debate_hall_mcp.tools.admin import debate_tombstone
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


class TestHashChainVerificationOnLoad:
    """Tests for hash chain link verification during load_debate_state."""

    def test_load_valid_chain_succeeds(self, tmp_path: Path) -> None:
        """Load debate with valid hash chain succeeds."""
        # Create room with valid chain
        room = DebateRoom(
            thread_id="valid-chain-001",
            topic="Valid Chain Test",
            mode=DebateMode.FIXED,
        )

        turn1 = Turn(
            role="Wind",
            content="First turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second turn",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        turn3 = Turn(
            role="Door",
            content="Third turn",
            timestamp=datetime.now(UTC),
            previous_hash=turn2.hash,
        )
        room.turns.append(turn3)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Load should succeed - chain is valid
        loaded = load_debate_state("valid-chain-001", state_dir)
        assert len(loaded.turns) == 3
        assert loaded.turns[0].previous_hash is None
        assert loaded.turns[1].previous_hash == loaded.turns[0].hash
        assert loaded.turns[2].previous_hash == loaded.turns[1].hash

    def test_load_broken_chain_fails_with_clear_error(self, tmp_path: Path) -> None:
        """Load debate with broken hash chain raises ValueError with clear message."""
        # Create valid room first
        room = DebateRoom(
            thread_id="broken-chain-001",
            topic="Broken Chain Test",
            mode=DebateMode.FIXED,
        )

        turn1 = Turn(
            role="Wind",
            content="First turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second turn",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Corrupt the chain by modifying the JSON directly
        state_file = state_dir / "broken-chain-001.json"
        with open(state_file) as f:
            data = json.load(f)

        # Break the chain: set wrong previous_hash on turn 1 (index 1)
        data["turns"][1]["previous_hash"] = "corrupted_hash_value"

        with open(state_file, "w") as f:
            json.dump(data, f)

        # Load should fail with ValueError
        with pytest.raises(ValueError) as exc_info:
            load_debate_state("broken-chain-001", state_dir)

        # Error message should be clear about the issue
        error_msg = str(exc_info.value)
        assert "hash chain" in error_msg.lower() or "chain" in error_msg.lower()
        assert "1" in error_msg  # Turn index
        # Should mention expected vs actual or similar diagnostic info

    def test_load_empty_debate_succeeds(self, tmp_path: Path) -> None:
        """Load debate with no turns succeeds (no chain to verify)."""
        room = DebateRoom(
            thread_id="empty-001",
            topic="Empty Debate",
            mode=DebateMode.FIXED,
        )
        # No turns added

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Load should succeed
        loaded = load_debate_state("empty-001", state_dir)
        assert len(loaded.turns) == 0

    def test_load_single_turn_succeeds(self, tmp_path: Path) -> None:
        """Load debate with single turn succeeds (no chain link to verify)."""
        room = DebateRoom(
            thread_id="single-001",
            topic="Single Turn",
            mode=DebateMode.FIXED,
        )

        turn = Turn(
            role="Wind",
            content="Only turn",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Load should succeed
        loaded = load_debate_state("single-001", state_dir)
        assert len(loaded.turns) == 1
        assert loaded.turns[0].previous_hash is None

    def test_tombstoned_turn_chain_remains_valid(self, tmp_path: Path) -> None:
        """Tombstoned turn preserves hash chain validity.

        Critical: Tombstoning changes content but NOT the hash.
        Verification must only check links (previous_hash -> prior hash),
        NOT re-compute hashes from content.
        """
        state_dir = tmp_path / "debates"
        thread_id = "2025-01-01-tombstone-chain-001"

        # Create debate with turns using tools
        debate_init(
            thread_id=thread_id,
            topic="Tombstone Chain Test",
            state_dir=state_dir,
        )
        debate_turn(thread_id, "Wind", "Original content", state_dir=state_dir)
        debate_turn(thread_id, "Wall", "Second turn", state_dir=state_dir)
        debate_turn(thread_id, "Door", "Third turn", state_dir=state_dir)

        # Record hashes before tombstone
        room_before = load_debate_state(thread_id, state_dir)
        hash_before = room_before.turns[0].hash

        # Tombstone first turn
        debate_tombstone(
            thread_id=thread_id,
            turn_index=0,
            reason="Test redaction",
            state_dir=state_dir,
        )

        # Load should succeed - chain links are still valid
        # (even though turn 0 content changed, hash was preserved)
        loaded = load_debate_state(thread_id, state_dir)

        # Verify tombstoned turn has different content but same hash
        assert loaded.turns[0].content == "[REDACTED: Test redaction]"
        assert loaded.turns[0].hash == hash_before

        # Verify chain links are intact
        assert loaded.turns[1].previous_hash == loaded.turns[0].hash
        assert loaded.turns[2].previous_hash == loaded.turns[1].hash


class TestHashChainVerificationEdgeCases:
    """Edge case tests for hash chain verification."""

    def test_first_turn_with_non_null_previous_hash_fails(self, tmp_path: Path) -> None:
        """First turn must have null/empty previous_hash."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir(parents=True)

        # Create state file with first turn having non-null previous_hash
        state_file = state_dir / "bad-first-001.json"
        data = {
            "thread_id": "bad-first-001",
            "topic": "Bad First Turn",
            "mode": "fixed",
            "status": "active",
            "max_turns": 12,
            "max_rounds": 4,
            "strict_cognition": False,
            "octave_preamble": True,
            "expected_next_role": None,
            "turns": [
                {
                    "role": "Wind",
                    "content": "First turn",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "previous_hash": "should_be_null_for_first_turn",  # INVALID
                    "hash": "abc123",
                    "agent_role": None,
                    "model": None,
                    "cognition": None,
                }
            ],
            "synthesis": None,
            "audit_log": [],
        }
        with open(state_file, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            load_debate_state("bad-first-001", state_dir)

        error_msg = str(exc_info.value)
        assert "first" in error_msg.lower() or "0" in error_msg

    def test_chain_break_at_third_turn_identifies_correct_index(self, tmp_path: Path) -> None:
        """Chain break at turn 3 should identify turn index 2 in error."""
        room = DebateRoom(
            thread_id="break-at-third-001",
            topic="Break at Third",
            mode=DebateMode.FIXED,
        )

        turn1 = Turn(
            role="Wind",
            content="First",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        turn3 = Turn(
            role="Door",
            content="Third",
            timestamp=datetime.now(UTC),
            previous_hash=turn2.hash,
        )
        room.turns.append(turn3)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Corrupt chain at turn 3 (index 2)
        state_file = state_dir / "break-at-third-001.json"
        with open(state_file) as f:
            data = json.load(f)

        data["turns"][2]["previous_hash"] = "wrong_hash_value"

        with open(state_file, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            load_debate_state("break-at-third-001", state_dir)

        error_msg = str(exc_info.value)
        # Should identify the broken turn (index 2)
        assert "2" in error_msg

    def test_error_message_includes_hash_values(self, tmp_path: Path) -> None:
        """Error message should include expected and actual hash values."""
        room = DebateRoom(
            thread_id="hash-in-error-001",
            topic="Hash in Error",
            mode=DebateMode.FIXED,
        )

        turn1 = Turn(
            role="Wind",
            content="First",
            timestamp=datetime.now(UTC),
            previous_hash=None,
        )
        room.turns.append(turn1)

        turn2 = Turn(
            role="Wall",
            content="Second",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
        )
        room.turns.append(turn2)

        state_dir = tmp_path / "debates"
        save_debate_state(room, state_dir)

        # Record expected hash for verification
        expected_hash = turn1.hash

        # Corrupt the chain
        state_file = state_dir / "hash-in-error-001.json"
        with open(state_file) as f:
            data = json.load(f)

        corrupted_hash = "0" * 64  # Obviously wrong hash
        data["turns"][1]["previous_hash"] = corrupted_hash

        with open(state_file, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            load_debate_state("hash-in-error-001", state_dir)

        error_msg = str(exc_info.value)
        # Should include some hash info for debugging
        # Either the expected hash or the actual (corrupted) hash
        assert corrupted_hash[:8] in error_msg or expected_hash[:8] in error_msg
