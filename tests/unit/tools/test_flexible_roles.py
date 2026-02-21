"""Tests for flexible roles in mediated mode (Issue #174).

Foundation change: pick_next_speaker accepts arbitrary named roles
in mediated mode, replacing the Wind/Wall/Door restriction.

Cognition validation is conditional on Wind/Wall/Door roles only.
Non-triad roles skip cognition validation.

TDD Discipline: RED phase - these tests should FAIL before implementation.
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn

# --- pick_next_speaker: flexible role acceptance ---


class TestPickFlexibleRoles:
    """Tests for pick_next_speaker accepting arbitrary role strings."""

    def test_pick_arbitrary_role_crs(self, tmp_path: Path) -> None:
        """pick_next_speaker('CRS') succeeds in mediated mode."""
        debate_init(
            thread_id="2026-02-21-flex-role-001",
            topic="Flexible role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        result = debate_pick(
            thread_id="2026-02-21-flex-role-001",
            role="CRS",
            state_dir=tmp_path,
        )

        assert result["next_role"] == "CRS"
        assert result["mode"] == "mediated"

    def test_pick_arbitrary_role_ce(self, tmp_path: Path) -> None:
        """pick_next_speaker('CE') succeeds in mediated mode."""
        debate_init(
            thread_id="2026-02-21-flex-role-002",
            topic="Flexible role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        result = debate_pick(
            thread_id="2026-02-21-flex-role-002",
            role="CE",
            state_dir=tmp_path,
        )

        assert result["next_role"] == "CE"
        assert result["mode"] == "mediated"

    def test_pick_then_turn_with_arbitrary_role(self, tmp_path: Path) -> None:
        """pick_next_speaker('CE') then add_turn(role='CE') succeeds."""
        debate_init(
            thread_id="2026-02-21-flex-role-003",
            topic="Pick-then-turn test",
            mode="mediated",
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-flex-role-003",
            role="CE",
            state_dir=tmp_path,
        )

        result = debate_turn(
            thread_id="2026-02-21-flex-role-003",
            role="CE",
            content="Review complete. No critical issues found.",
            state_dir=tmp_path,
        )

        assert result["role"] == "CE"
        assert result["turn_count"] == 1

    def test_pick_empty_role_raises(self, tmp_path: Path) -> None:
        """pick_next_speaker('') raises ValueError for empty role."""
        debate_init(
            thread_id="2026-02-21-flex-role-004",
            topic="Empty role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="[Rr]ole.*empty|[Ii]nvalid role"):
            debate_pick(
                thread_id="2026-02-21-flex-role-004",
                role="",
                state_dir=tmp_path,
            )

    def test_pick_whitespace_role_raises(self, tmp_path: Path) -> None:
        """pick_next_speaker('  ') raises ValueError for whitespace-only role."""
        debate_init(
            thread_id="2026-02-21-flex-role-005",
            topic="Whitespace role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="[Rr]ole.*empty|[Ii]nvalid role"):
            debate_pick(
                thread_id="2026-02-21-flex-role-005",
                role="   ",
                state_dir=tmp_path,
            )

    def test_pick_role_exceeds_max_length_raises(self, tmp_path: Path) -> None:
        """Role with >128 chars raises ValueError."""
        debate_init(
            thread_id="2026-02-21-flex-role-006",
            topic="Long role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        long_role = "A" * 129
        with pytest.raises(ValueError, match="[Rr]ole.*128|[Ii]nvalid role|exceed"):
            debate_pick(
                thread_id="2026-02-21-flex-role-006",
                role=long_role,
                state_dir=tmp_path,
            )

    def test_pick_role_at_max_length_succeeds(self, tmp_path: Path) -> None:
        """Role with exactly 128 chars succeeds."""
        debate_init(
            thread_id="2026-02-21-flex-role-007",
            topic="Max length role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        role_128 = "A" * 128
        result = debate_pick(
            thread_id="2026-02-21-flex-role-007",
            role=role_128,
            state_dir=tmp_path,
        )

        assert result["next_role"] == role_128

    def test_pick_non_ascii_role_raises(self, tmp_path: Path) -> None:
        """Non-ASCII role raises ValueError."""
        debate_init(
            thread_id="2026-02-21-flex-role-008",
            topic="Non-ASCII role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="[Pp]rintable ASCII|[Ii]nvalid role"):
            debate_pick(
                thread_id="2026-02-21-flex-role-008",
                role="Rolle\u00e9",
                state_dir=tmp_path,
            )

    def test_pick_control_char_role_raises(self, tmp_path: Path) -> None:
        """Role with control characters raises ValueError."""
        debate_init(
            thread_id="2026-02-21-flex-role-009",
            topic="Control char role test",
            mode="mediated",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="[Pp]rintable ASCII|[Ii]nvalid role"):
            debate_pick(
                thread_id="2026-02-21-flex-role-009",
                role="Role\x00Name",
                state_dir=tmp_path,
            )

    def test_pick_wind_wall_door_still_work(self, tmp_path: Path) -> None:
        """Wind/Wall/Door roles still work exactly as before."""
        for role in ("Wind", "Wall", "Door"):
            tid = f"2026-02-21-flex-role-triad-{role.lower()}"
            debate_init(
                thread_id=tid,
                topic=f"Triad {role} test",
                mode="mediated",
                state_dir=tmp_path,
            )

            result = debate_pick(thread_id=tid, role=role, state_dir=tmp_path)
            assert result["next_role"] == role
            assert result["mode"] == "mediated"

    def test_pick_fixed_mode_still_rejects(self, tmp_path: Path) -> None:
        """FIXED mode behavior unchanged: pick_next_speaker still rejects."""
        debate_init(
            thread_id="2026-02-21-flex-role-fixed",
            topic="Fixed mode test",
            mode="fixed",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="only valid for mediated mode"):
            debate_pick(
                thread_id="2026-02-21-flex-role-fixed",
                role="CRS",
                state_dir=tmp_path,
            )


# --- Cognition validation: conditional on Wind/Wall/Door ---


class TestCognitionValidationConditional:
    """Cognition validation enforced for triad roles, skipped for non-triad."""

    def test_cognition_enforced_for_wind_strict(self, tmp_path: Path) -> None:
        """Cognition validation still enforced for Wind in strict mode."""
        debate_init(
            thread_id="2026-02-21-cog-wind",
            topic="Cognition enforcement test",
            mode="mediated",
            strict_cognition=True,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-wind",
            role="Wind",
            state_dir=tmp_path,
        )

        # Wind with no cognition should BLOCK in strict mode
        with pytest.raises(ValueError, match="No cognition specified"):
            debate_turn(
                thread_id="2026-02-21-cog-wind",
                role="Wind",
                content="This is a statement.",
                cognition=None,
                state_dir=tmp_path,
            )

    def test_cognition_enforced_for_wall_strict(self, tmp_path: Path) -> None:
        """Cognition validation still enforced for Wall in strict mode."""
        debate_init(
            thread_id="2026-02-21-cog-wall",
            topic="Cognition enforcement test",
            mode="mediated",
            strict_cognition=True,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-wall",
            role="Wall",
            state_dir=tmp_path,
        )

        # Wall with no cognition should BLOCK in strict mode
        with pytest.raises(ValueError, match="No cognition specified"):
            debate_turn(
                thread_id="2026-02-21-cog-wall",
                role="Wall",
                content="[VERDICT] APPROVED\n[EVIDENCE] All good.",
                cognition=None,
                state_dir=tmp_path,
            )

    def test_cognition_enforced_for_door_strict(self, tmp_path: Path) -> None:
        """Cognition validation still enforced for Door in strict mode."""
        debate_init(
            thread_id="2026-02-21-cog-door",
            topic="Cognition enforcement test",
            mode="mediated",
            strict_cognition=True,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-door",
            role="Door",
            state_dir=tmp_path,
        )

        # Door with no cognition should BLOCK in strict mode
        with pytest.raises(ValueError, match="No cognition specified"):
            debate_turn(
                thread_id="2026-02-21-cog-door",
                role="Door",
                content="1. Step one\n2. Step two",
                cognition=None,
                state_dir=tmp_path,
            )

    def test_cognition_skipped_for_non_triad_role(self, tmp_path: Path) -> None:
        """Non-triad role (CRS) with cognition=None works even in strict mode."""
        debate_init(
            thread_id="2026-02-21-cog-crs",
            topic="Non-triad cognition skip test",
            mode="mediated",
            strict_cognition=True,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-crs",
            role="CRS",
            state_dir=tmp_path,
        )

        # CRS with cognition=None should succeed (no cognition validation)
        result = debate_turn(
            thread_id="2026-02-21-cog-crs",
            role="CRS",
            content="Code review complete. No critical issues found.",
            cognition=None,
            state_dir=tmp_path,
        )

        assert result["role"] == "CRS"
        assert result["turn_count"] == 1

    def test_cognition_skipped_for_non_triad_with_arbitrary_cognition(self, tmp_path: Path) -> None:
        """Non-triad role with arbitrary cognition value works in strict mode."""
        debate_init(
            thread_id="2026-02-21-cog-arb",
            topic="Arbitrary cognition test",
            mode="mediated",
            strict_cognition=True,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-arb",
            role="TMG",
            state_dir=tmp_path,
        )

        # TMG with unknown cognition should succeed (non-triad skips validation)
        result = debate_turn(
            thread_id="2026-02-21-cog-arb",
            role="TMG",
            content="Test methodology guidance provided.",
            cognition="ANALYTICAL",
            state_dir=tmp_path,
        )

        assert result["role"] == "TMG"
        assert result["turn_count"] == 1

    def test_cognition_not_enforced_for_non_triad_non_strict(self, tmp_path: Path) -> None:
        """Non-triad role with cognition=None works in non-strict mode too."""
        debate_init(
            thread_id="2026-02-21-cog-nonstrict",
            topic="Non-strict non-triad test",
            mode="mediated",
            strict_cognition=False,
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-nonstrict",
            role="CE",
            state_dir=tmp_path,
        )

        result = debate_turn(
            thread_id="2026-02-21-cog-nonstrict",
            role="CE",
            content="Critical engineering review.",
            cognition=None,
            state_dir=tmp_path,
        )

        assert result["role"] == "CE"
        assert result["turn_count"] == 1

    def test_content_length_still_enforced_for_non_triad(self, tmp_path: Path) -> None:
        """DoS protection (content length) still enforced for non-triad roles."""
        debate_init(
            thread_id="2026-02-21-cog-dos",
            topic="DoS protection test",
            mode="mediated",
            state_dir=tmp_path,
        )

        debate_pick(
            thread_id="2026-02-21-cog-dos",
            role="CRS",
            state_dir=tmp_path,
        )

        # Content exceeding 32KB should still be rejected
        huge_content = "x" * 33000
        with pytest.raises(ValueError, match="exceeds maximum length"):
            debate_turn(
                thread_id="2026-02-21-cog-dos",
                role="CRS",
                content=huge_content,
                state_dir=tmp_path,
            )
