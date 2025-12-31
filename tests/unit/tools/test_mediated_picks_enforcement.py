"""Tests for mediated picks enforcement (Issue #37).

TDD Discipline: RED->GREEN->REFACTOR
Immutables: I1 (state isolation)

Tests that mediated mode ENFORCES the picked role, not just records it.
This ensures orchestration integrity - picks are not "informational only".

Test sequence:
1. expected_next_role field exists in DebateRoom
2. debate_pick persists the expected role
3. debate_turn rejects wrong role in mediated mode
4. debate_turn accepts correct role in mediated mode
5. Backward compat (None expected_next_role allowed - no prior pick)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import DebateMode, DebateRoom, load_debate_state
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn


class TestExpectedNextRoleField:
    """Tests for expected_next_role field on DebateRoom model."""

    def test_debate_room_has_expected_next_role_field(self) -> None:
        """Test that DebateRoom model has expected_next_role field."""
        room = DebateRoom(
            thread_id="2025-01-01-test-field",
            topic="Test field existence",
            mode=DebateMode.MEDIATED,
        )
        # Field should exist and default to None
        assert hasattr(room, "expected_next_role")
        assert room.expected_next_role is None

    def test_debate_room_expected_next_role_can_be_set(self) -> None:
        """Test that expected_next_role can be set to a valid role."""
        room = DebateRoom(
            thread_id="2025-01-01-test-field-set",
            topic="Test field setting",
            mode=DebateMode.MEDIATED,
            expected_next_role="Wind",
        )
        assert room.expected_next_role == "Wind"

    def test_debate_room_expected_next_role_persists(self, tmp_path: Path) -> None:
        """Test that expected_next_role persists through save/load cycle."""
        from debate_hall_mcp.state import save_debate_state

        room = DebateRoom(
            thread_id="2025-01-01-test-persist",
            topic="Test persistence",
            mode=DebateMode.MEDIATED,
            expected_next_role="Door",
        )
        save_debate_state(room, tmp_path)

        loaded = load_debate_state("2025-01-01-test-persist", tmp_path)
        assert loaded.expected_next_role == "Door"


class TestDebatePickPersistence:
    """Tests for debate_pick persisting the expected role."""

    def test_debate_pick_persists_expected_role(self, tmp_path: Path) -> None:
        """Test that debate_pick saves expected_next_role to state."""
        debate_init(
            thread_id="2025-01-01-test-pick-persist",
            topic="Test pick persistence",
            mode="mediated",
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2025-01-01-test-pick-persist",
            role="Wall",
            state_dir=tmp_path,
        )

        # Load state and verify expected_next_role was persisted
        room = load_debate_state("2025-01-01-test-pick-persist", tmp_path)
        assert room.expected_next_role == "Wall"

    def test_debate_pick_updates_expected_role(self, tmp_path: Path) -> None:
        """Test that subsequent picks update expected_next_role."""
        debate_init(
            thread_id="2025-01-01-test-pick-update",
            topic="Test pick update",
            mode="mediated",
            state_dir=tmp_path,
        )

        # First pick
        debate_pick(
            thread_id="2025-01-01-test-pick-update",
            role="Wind",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-test-pick-update", tmp_path)
        assert room.expected_next_role == "Wind"

        # Second pick overwrites
        debate_pick(
            thread_id="2025-01-01-test-pick-update",
            role="Door",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-test-pick-update", tmp_path)
        assert room.expected_next_role == "Door"


class TestMediatedModeEnforcement:
    """Tests for debate_turn enforcing expected role in mediated mode."""

    def test_mediated_turn_rejects_wrong_role_after_pick(self, tmp_path: Path) -> None:
        """Test that mediated mode rejects turn if role doesn't match pick."""
        debate_init(
            thread_id="2025-01-01-test-enforce-reject",
            topic="Test enforcement rejection",
            mode="mediated",
            state_dir=tmp_path,
        )

        # Pick Wind
        debate_pick(
            thread_id="2025-01-01-test-enforce-reject",
            role="Wind",
            state_dir=tmp_path,
        )

        # Attempt Wall turn (should fail)
        with pytest.raises(ValueError, match="Expected role 'Wind' but got 'Wall'"):
            debate_turn(
                thread_id="2025-01-01-test-enforce-reject",
                role="Wall",
                content="COUNTER::This should be rejected",
                state_dir=tmp_path,
            )

    def test_mediated_turn_accepts_correct_role_after_pick(self, tmp_path: Path) -> None:
        """Test that mediated mode accepts turn if role matches pick."""
        debate_init(
            thread_id="2025-01-01-test-enforce-accept",
            topic="Test enforcement acceptance",
            mode="mediated",
            state_dir=tmp_path,
        )

        # Pick Door
        debate_pick(
            thread_id="2025-01-01-test-enforce-accept",
            role="Door",
            state_dir=tmp_path,
        )

        # Door turn should succeed
        result = debate_turn(
            thread_id="2025-01-01-test-enforce-accept",
            role="Door",
            content="SYNTHESIS::This should be accepted",
            state_dir=tmp_path,
        )

        assert result["role"] == "Door"
        assert result["turn_count"] == 1

    def test_mediated_turn_clears_expected_role_after_valid_turn(self, tmp_path: Path) -> None:
        """Test that successful turn clears expected_next_role."""
        debate_init(
            thread_id="2025-01-01-test-clear",
            topic="Test clear after turn",
            mode="mediated",
            state_dir=tmp_path,
        )

        # Pick and execute
        debate_pick(
            thread_id="2025-01-01-test-clear",
            role="Wind",
            state_dir=tmp_path,
        )

        debate_turn(
            thread_id="2025-01-01-test-clear",
            role="Wind",
            content="POSITION::Turn executed",
            state_dir=tmp_path,
        )

        # expected_next_role should be cleared
        room = load_debate_state("2025-01-01-test-clear", tmp_path)
        assert room.expected_next_role is None


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing debates."""

    def test_mediated_turn_allows_any_role_without_prior_pick(self, tmp_path: Path) -> None:
        """Test backward compat: mediated mode allows any role if no pick was made."""
        debate_init(
            thread_id="2025-01-01-test-backward-compat",
            topic="Test backward compatibility",
            mode="mediated",
            state_dir=tmp_path,
        )

        # No pick made - any role should work
        result = debate_turn(
            thread_id="2025-01-01-test-backward-compat",
            role="Door",
            content="SYNTHESIS::Any role should work",
            state_dir=tmp_path,
        )

        assert result["role"] == "Door"
        assert result["turn_count"] == 1

    def test_existing_debate_without_field_is_handled(self, tmp_path: Path) -> None:
        """Test that existing debates without expected_next_role field work."""
        import json

        # Create a debate state file WITHOUT expected_next_role field
        # (simulates pre-upgrade debate)
        state_file = tmp_path / "2025-01-01-legacy-debate.json"
        legacy_state = {
            "thread_id": "2025-01-01-legacy-debate",
            "topic": "Legacy debate",
            "mode": "mediated",
            "status": "active",
            "max_turns": 12,
            "max_rounds": 4,
            "strict_cognition": False,
            "octave_preamble": True,
            "turns": [],
            "synthesis": None,
            # NOTE: expected_next_role field is MISSING
        }
        with open(state_file, "w") as f:
            json.dump(legacy_state, f)

        # Should load successfully (field defaults to None)
        room = load_debate_state("2025-01-01-legacy-debate", tmp_path)
        assert room.expected_next_role is None

        # Should allow any turn (backward compatible)
        result = debate_turn(
            thread_id="2025-01-01-legacy-debate",
            role="Wall",
            content="COUNTER::Legacy support",
            state_dir=tmp_path,
        )

        assert result["role"] == "Wall"


class TestPickTurnCycles:
    """Tests for complete pick->turn cycle behavior."""

    def test_multiple_pick_turn_cycles(self, tmp_path: Path) -> None:
        """Test multiple pick->turn cycles enforce correctly."""
        debate_init(
            thread_id="2025-01-01-test-cycles",
            topic="Test multiple cycles",
            mode="mediated",
            state_dir=tmp_path,
        )

        # Cycle 1: Pick Wind, Wind speaks
        debate_pick(thread_id="2025-01-01-test-cycles", role="Wind", state_dir=tmp_path)
        debate_turn(
            thread_id="2025-01-01-test-cycles",
            role="Wind",
            content="POSITION::Wind speaks",
            state_dir=tmp_path,
        )

        # Cycle 2: Pick Door (skip Wall), Door speaks
        debate_pick(thread_id="2025-01-01-test-cycles", role="Door", state_dir=tmp_path)
        debate_turn(
            thread_id="2025-01-01-test-cycles",
            role="Door",
            content="SYNTHESIS::Door speaks",
            state_dir=tmp_path,
        )

        # Cycle 3: Pick Wall, Wall speaks
        debate_pick(thread_id="2025-01-01-test-cycles", role="Wall", state_dir=tmp_path)
        debate_turn(
            thread_id="2025-01-01-test-cycles",
            role="Wall",
            content="COUNTER::Wall speaks",
            state_dir=tmp_path,
        )

        room = load_debate_state("2025-01-01-test-cycles", tmp_path)
        assert len(room.turns) == 3
        assert room.turns[0].role == "Wind"
        assert room.turns[1].role == "Door"
        assert room.turns[2].role == "Wall"

    def test_pick_without_turn_then_new_pick(self, tmp_path: Path) -> None:
        """Test that new pick overwrites previous pick without turn."""
        debate_init(
            thread_id="2025-01-01-test-overwrite",
            topic="Test pick overwrite",
            mode="mediated",
            state_dir=tmp_path,
        )

        # Pick Wind
        debate_pick(thread_id="2025-01-01-test-overwrite", role="Wind", state_dir=tmp_path)

        # Pick Door without Wind turn (changes mind)
        debate_pick(thread_id="2025-01-01-test-overwrite", role="Door", state_dir=tmp_path)

        # Wind should now be rejected
        with pytest.raises(ValueError, match="Expected role 'Door' but got 'Wind'"):
            debate_turn(
                thread_id="2025-01-01-test-overwrite",
                role="Wind",
                content="POSITION::Should fail",
                state_dir=tmp_path,
            )

        # Door should succeed
        result = debate_turn(
            thread_id="2025-01-01-test-overwrite",
            role="Door",
            content="SYNTHESIS::Door succeeds",
            state_dir=tmp_path,
        )
        assert result["role"] == "Door"
