"""Unit tests for RACI Turn Manifest Compiler.

Tests for the RACI governance mode compiler that produces deterministic
TurnManifest objects from RACIConfig input.

Sequence: R(proposal) -> C*(advice) -> R(rebuttal) -> A(verdict) -> I*(observation)
If no consulted agents: R(proposal) -> A(verdict) -> I*(observation)

TDD: These tests are written first (RED phase) before implementation.
"""

import pytest

from debate_hall_mcp.raci import MAX_INFORMED, RACIConfig, compile_raci_manifest
from debate_hall_mcp.state import TurnManifest, TurnType


class TestRACIConfig:
    """Tests for RACIConfig validation."""

    def test_valid_config_with_consulted(self) -> None:
        """RACIConfig should accept valid R, A, C, I values."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["security-reviewer", "ux-designer"],
            informed=["product-manager"],
        )
        assert config.responsible == "architect"
        assert config.accountable == "tech-lead"
        assert len(config.consulted) == 2
        assert len(config.informed) == 1

    def test_valid_config_without_consulted(self) -> None:
        """RACIConfig should accept empty consulted list."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
        )
        assert config.consulted == []
        assert config.informed == []

    def test_responsible_cannot_be_empty(self) -> None:
        """RACIConfig should reject empty responsible."""
        with pytest.raises(ValueError, match="responsible"):
            RACIConfig(
                responsible="",
                accountable="tech-lead",
            )

    def test_accountable_cannot_be_empty(self) -> None:
        """RACIConfig should reject empty accountable."""
        with pytest.raises(ValueError, match="accountable"):
            RACIConfig(
                responsible="architect",
                accountable="",
            )

    def test_responsible_cannot_be_whitespace(self) -> None:
        """RACIConfig should reject whitespace-only responsible."""
        with pytest.raises(ValueError, match="responsible"):
            RACIConfig(
                responsible="   ",
                accountable="tech-lead",
            )

    def test_accountable_cannot_be_whitespace(self) -> None:
        """RACIConfig should reject whitespace-only accountable."""
        with pytest.raises(ValueError, match="accountable"):
            RACIConfig(
                responsible="architect",
                accountable="  ",
            )

    def test_responsible_must_differ_from_accountable(self) -> None:
        """RACIConfig should reject R == A (separation of concerns)."""
        with pytest.raises(ValueError, match="responsible.*accountable|separation"):
            RACIConfig(
                responsible="architect",
                accountable="architect",
            )

    def test_consulted_max_5_entries(self) -> None:
        """RACIConfig should reject more than 5 consulted agents."""
        with pytest.raises(ValueError, match="consulted|5"):
            RACIConfig(
                responsible="architect",
                accountable="tech-lead",
                consulted=["a", "b", "c", "d", "e", "f"],
            )

    def test_consulted_entries_must_be_non_empty(self) -> None:
        """RACIConfig should reject empty strings in consulted list."""
        with pytest.raises(ValueError, match="consulted|empty"):
            RACIConfig(
                responsible="architect",
                accountable="tech-lead",
                consulted=["valid", ""],
            )

    def test_informed_entries_must_be_non_empty(self) -> None:
        """RACIConfig should reject empty strings in informed list."""
        with pytest.raises(ValueError, match="informed|empty"):
            RACIConfig(
                responsible="architect",
                accountable="tech-lead",
                informed=["valid", ""],
            )

    def test_consulted_exactly_5_allowed(self) -> None:
        """RACIConfig should allow exactly 5 consulted (the max)."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["a", "b", "c", "d", "e"],
        )
        assert len(config.consulted) == 5


class TestCompileRACIManifest:
    """Tests for compile_raci_manifest() function."""

    def test_manifest_with_consulted_agents(self) -> None:
        """Manifest with C+I: R(proposal) -> C1(advice) -> C2(advice) -> R(rebuttal) -> A(verdict) -> I(observation)."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["security", "ux"],
            informed=["pm"],
        )
        manifest = compile_raci_manifest(config)

        assert isinstance(manifest, TurnManifest)
        assert len(manifest.specs) == 6  # R + C1 + C2 + R(rebuttal) + A + I

        # Verify sequence
        assert manifest.specs[0].role == "architect"
        assert manifest.specs[0].turn_type == TurnType.PROPOSAL
        assert manifest.specs[0].raci_designation == "R"

        assert manifest.specs[1].role == "security"
        assert manifest.specs[1].turn_type == TurnType.ADVICE
        assert manifest.specs[1].raci_designation == "C"

        assert manifest.specs[2].role == "ux"
        assert manifest.specs[2].turn_type == TurnType.ADVICE
        assert manifest.specs[2].raci_designation == "C"

        assert manifest.specs[3].role == "architect"
        assert manifest.specs[3].turn_type == TurnType.REBUTTAL
        assert manifest.specs[3].raci_designation == "R"

        assert manifest.specs[4].role == "tech-lead"
        assert manifest.specs[4].turn_type == TurnType.VERDICT
        assert manifest.specs[4].raci_designation == "A"

        assert manifest.specs[5].role == "pm"
        assert manifest.specs[5].turn_type == TurnType.OBSERVATION
        assert manifest.specs[5].raci_designation == "I"

    def test_manifest_without_consulted(self) -> None:
        """Manifest without C agents: R(proposal) -> A(verdict)."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
        )
        manifest = compile_raci_manifest(config)

        assert len(manifest.specs) == 2  # R(proposal) + A(verdict)

        assert manifest.specs[0].role == "architect"
        assert manifest.specs[0].turn_type == TurnType.PROPOSAL
        assert manifest.specs[0].raci_designation == "R"

        assert manifest.specs[1].role == "tech-lead"
        assert manifest.specs[1].turn_type == TurnType.VERDICT
        assert manifest.specs[1].raci_designation == "A"

    def test_manifest_stores_raci_assignments(self) -> None:
        """Manifest should store RACI role assignments as metadata."""
        config = RACIConfig(
            responsible="architect",
            accountable="tech-lead",
            consulted=["security"],
            informed=["pm", "stakeholder"],
        )
        manifest = compile_raci_manifest(config)

        assert manifest.responsible == "architect"
        assert manifest.accountable == "tech-lead"
        assert manifest.consulted == ["security"]
        assert manifest.informed == ["pm", "stakeholder"]

    def test_manifest_single_consulted(self) -> None:
        """Manifest with one C: R(proposal) -> C(advice) -> R(rebuttal) -> A(verdict)."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["reviewer"],
        )
        manifest = compile_raci_manifest(config)

        assert len(manifest.specs) == 4
        assert manifest.specs[0].turn_type == TurnType.PROPOSAL
        assert manifest.specs[1].turn_type == TurnType.ADVICE
        assert manifest.specs[2].turn_type == TurnType.REBUTTAL
        assert manifest.specs[3].turn_type == TurnType.VERDICT

    def test_manifest_max_consulted(self) -> None:
        """Manifest with 5 C agents: R + C*5 + R(rebuttal) + A = 8 turns."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["c1", "c2", "c3", "c4", "c5"],
        )
        manifest = compile_raci_manifest(config)

        assert len(manifest.specs) == 8  # 1 + 5 + 1 + 1

    def test_manifest_informed_get_observation_turns(self) -> None:
        """Informed agents should get OBSERVATION turns after verdict."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm", "stakeholder", "ceo"],
        )
        manifest = compile_raci_manifest(config)

        # R(proposal) + A(verdict) + 3 I(observation) = 5 turns
        assert len(manifest.specs) == 5

        # Informed agents appear in manifest as OBSERVATION turns
        roles_in_manifest = [spec.role for spec in manifest.specs]
        assert "pm" in roles_in_manifest
        assert "stakeholder" in roles_in_manifest
        assert "ceo" in roles_in_manifest

        # Verify they are all OBSERVATION type
        observation_specs = [s for s in manifest.specs if s.turn_type == TurnType.OBSERVATION]
        assert len(observation_specs) == 3
        for obs_spec in observation_specs:
            assert obs_spec.raci_designation == "I"

    def test_manifest_is_deterministic(self) -> None:
        """Same config should always produce the same manifest."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["c1", "c2"],
            informed=["pm"],
        )

        manifest1 = compile_raci_manifest(config)
        manifest2 = compile_raci_manifest(config)

        assert len(manifest1.specs) == len(manifest2.specs)
        for s1, s2 in zip(manifest1.specs, manifest2.specs, strict=True):
            assert s1.role == s2.role
            assert s1.turn_type == s2.turn_type
            assert s1.raci_designation == s2.raci_designation


class TestTurnTypeEnum:
    """Tests for TurnType enum values."""

    def test_turn_type_proposal(self) -> None:
        assert TurnType.PROPOSAL.value == "proposal"

    def test_turn_type_advice(self) -> None:
        assert TurnType.ADVICE.value == "advice"

    def test_turn_type_rebuttal(self) -> None:
        assert TurnType.REBUTTAL.value == "rebuttal"

    def test_turn_type_verdict(self) -> None:
        assert TurnType.VERDICT.value == "verdict"

    def test_turn_type_observation(self) -> None:
        assert TurnType.OBSERVATION.value == "observation"

    def test_turn_type_is_str_enum(self) -> None:
        assert str(TurnType.PROPOSAL) == "proposal"


class TestMaxInformedValidation:
    """Tests for MAX_INFORMED=3 validation in RACIConfig."""

    def test_max_informed_constant_is_3(self) -> None:
        """MAX_INFORMED should be 3 (hard cap from debate mandate)."""
        assert MAX_INFORMED == 3

    def test_informed_max_3_allowed(self) -> None:
        """RACIConfig should allow exactly 3 informed agents (the max)."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["a", "b", "c"],
        )
        assert len(config.informed) == 3

    def test_informed_exceeds_max_3_rejected(self) -> None:
        """RACIConfig should reject more than 3 informed agents."""
        with pytest.raises(ValueError, match="informed|3"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["a", "b", "c", "d"],
            )

    def test_informed_zero_allowed(self) -> None:
        """RACIConfig should allow empty informed list."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=[],
        )
        assert config.informed == []


class TestRACIDisjointnessValidation:
    """Tests for RACI role disjointness validation (V1-V5).

    Each role must have exactly one RACI designation.
    All comparisons are case-insensitive.
    """

    def test_v1_duplicate_informed_rejected(self) -> None:
        """V1: Duplicate entries in informed list should be rejected."""
        with pytest.raises(ValueError, match="duplicate in informed.*appears more than once"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["ops", "ops"],
            )

    def test_v2_duplicate_consulted_rejected(self) -> None:
        """V2: Duplicate entries in consulted list should be rejected."""
        with pytest.raises(ValueError, match="duplicate in consulted.*appears more than once"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                consulted=["arch", "arch"],
            )

    def test_v3_informed_overlaps_responsible_rejected(self) -> None:
        """V3: Informed agent that is also Responsible should be rejected."""
        with pytest.raises(ValueError, match="role 'dev'.*responsible.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["dev"],
            )

    def test_v4_informed_overlaps_accountable_rejected(self) -> None:
        """V4: Informed agent that is also Accountable should be rejected."""
        with pytest.raises(ValueError, match="role 'lead'.*accountable.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["lead"],
            )

    def test_v5_informed_overlaps_consulted_rejected(self) -> None:
        """V5: Informed agent that is also Consulted should be rejected."""
        with pytest.raises(ValueError, match="role 'arch'.*consulted.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                consulted=["arch"],
                informed=["arch"],
            )

    def test_case_insensitive_disjointness(self) -> None:
        """Case differences should be treated as same role (e.g., 'Dev' and 'dev')."""
        # V3: case-insensitive R vs I
        with pytest.raises(ValueError, match="role 'Dev'.*responsible.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["Dev"],
            )

    def test_case_insensitive_r_equals_a(self) -> None:
        """R==A check should also be case-insensitive."""
        with pytest.raises(ValueError, match="responsible.*accountable|separation"):
            RACIConfig(
                responsible="Dev",
                accountable="dev",
            )

    def test_valid_config_all_unique_roles(self) -> None:
        """Config with all unique roles across R/A/C/I should pass validation."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["arch", "security"],
            informed=["pm", "ops"],
        )
        assert config.responsible == "dev"
        assert config.accountable == "lead"
        assert config.consulted == ["arch", "security"]
        assert config.informed == ["pm", "ops"]

    def test_consulted_same_as_responsible_allowed(self) -> None:
        """Consulted == Responsible is a valid pattern (R appears in proposal + rebuttal).

        This is by design: consulted agents advise, then R synthesizes feedback.
        Do NOT block this pattern.
        """
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["dev"],
        )
        assert config.consulted == ["dev"]

    def test_v1_duplicate_informed_case_insensitive(self) -> None:
        """V1: Duplicate detection in informed should be case-insensitive."""
        with pytest.raises(ValueError, match="duplicate in informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["Ops", "ops"],
            )

    def test_v2_duplicate_consulted_case_insensitive(self) -> None:
        """V2: Duplicate detection in consulted should be case-insensitive."""
        with pytest.raises(ValueError, match="duplicate in consulted"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                consulted=["Arch", "arch"],
            )

    def test_v4_case_insensitive_accountable_informed(self) -> None:
        """V4: Case-insensitive check for accountable vs informed."""
        with pytest.raises(ValueError, match="role 'LEAD'.*accountable.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                informed=["LEAD"],
            )

    def test_v5_case_insensitive_consulted_informed(self) -> None:
        """V5: Case-insensitive check for consulted vs informed overlap."""
        with pytest.raises(ValueError, match="role 'ARCH'.*consulted.*informed"):
            RACIConfig(
                responsible="dev",
                accountable="lead",
                consulted=["arch"],
                informed=["ARCH"],
            )


class TestObservationTurnOrdering:
    """Tests for OBSERVATION turn ordering in compiled manifests."""

    def test_observation_turns_appear_after_verdict(self) -> None:
        """OBSERVATION turns must appear strictly after VERDICT."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["reviewer"],
            informed=["pm", "ops"],
        )
        manifest = compile_raci_manifest(config)

        # Find indices
        verdict_index = next(
            i for i, s in enumerate(manifest.specs) if s.turn_type == TurnType.VERDICT
        )
        observation_indices = [
            i for i, s in enumerate(manifest.specs) if s.turn_type == TurnType.OBSERVATION
        ]

        # All observation indices must be after verdict index
        assert len(observation_indices) == 2
        for obs_idx in observation_indices:
            assert obs_idx > verdict_index

    def test_manifest_total_turns_with_all_raci_roles(self) -> None:
        """Manifest with R, 2C, A, 2I should have 7 turns."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["c1", "c2"],
            informed=["i1", "i2"],
        )
        manifest = compile_raci_manifest(config)

        # R(proposal) + C1(advice) + C2(advice) + R(rebuttal) + A(verdict) + I1(obs) + I2(obs) = 7
        assert len(manifest.specs) == 7

    def test_manifest_without_consulted_with_informed(self) -> None:
        """Manifest without C but with I: R(proposal) -> A(verdict) -> I(observation)."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            informed=["pm"],
        )
        manifest = compile_raci_manifest(config)

        # R(proposal) + A(verdict) + I(observation) = 3
        assert len(manifest.specs) == 3
        assert manifest.specs[0].turn_type == TurnType.PROPOSAL
        assert manifest.specs[1].turn_type == TurnType.VERDICT
        assert manifest.specs[2].turn_type == TurnType.OBSERVATION
        assert manifest.specs[2].role == "pm"

    def test_manifest_without_informed_has_no_observation_turns(self) -> None:
        """Manifest without I agents should have no OBSERVATION turns."""
        config = RACIConfig(
            responsible="dev",
            accountable="lead",
            consulted=["reviewer"],
        )
        manifest = compile_raci_manifest(config)

        observation_specs = [s for s in manifest.specs if s.turn_type == TurnType.OBSERVATION]
        assert len(observation_specs) == 0
