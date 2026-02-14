"""Unit tests for RACI state models and serialization.

Tests for TurnManifest, TurnSpec, TurnType persistence on DebateRoom,
and round-trip serialization through JSON.

TDD: These tests are written first (RED phase) before implementation.
"""

from pathlib import Path

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    TurnManifest,
    TurnSpec,
    TurnType,
    load_debate_state,
    save_debate_state,
)


class TestTurnSpecModel:
    """Tests for TurnSpec Pydantic model."""

    def test_turnspec_creation(self) -> None:
        """TurnSpec should accept role, turn_type, and raci_designation."""
        spec = TurnSpec(
            role="architect",
            turn_type=TurnType.PROPOSAL,
            raci_designation="R",
        )
        assert spec.role == "architect"
        assert spec.turn_type == TurnType.PROPOSAL
        assert spec.raci_designation == "R"

    def test_turnspec_serialization(self) -> None:
        """TurnSpec should serialize to and from JSON."""
        spec = TurnSpec(
            role="reviewer",
            turn_type=TurnType.ADVICE,
            raci_designation="C",
        )
        json_data = spec.model_dump()
        restored = TurnSpec.model_validate(json_data)

        assert restored.role == "reviewer"
        assert restored.turn_type == TurnType.ADVICE
        assert restored.raci_designation == "C"

    def test_turnspec_json_roundtrip(self) -> None:
        """TurnSpec should survive JSON string roundtrip."""
        spec = TurnSpec(
            role="tech-lead",
            turn_type=TurnType.VERDICT,
            raci_designation="A",
        )
        json_str = spec.model_dump_json()
        restored = TurnSpec.model_validate_json(json_str)

        assert restored.role == spec.role
        assert restored.turn_type == spec.turn_type
        assert restored.raci_designation == spec.raci_designation


class TestTurnManifestModel:
    """Tests for TurnManifest Pydantic model."""

    def test_manifest_creation(self) -> None:
        """TurnManifest should accept specs and RACI assignments."""
        specs = [
            TurnSpec(role="dev", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="lead", turn_type=TurnType.VERDICT, raci_designation="A"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="dev",
            accountable="lead",
            consulted=[],
            informed=[],
        )
        assert len(manifest.specs) == 2
        assert manifest.responsible == "dev"
        assert manifest.accountable == "lead"

    def test_manifest_serialization(self) -> None:
        """TurnManifest should serialize to and from dict."""
        specs = [
            TurnSpec(role="dev", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="reviewer", turn_type=TurnType.ADVICE, raci_designation="C"),
            TurnSpec(role="dev", turn_type=TurnType.REBUTTAL, raci_designation="R"),
            TurnSpec(role="lead", turn_type=TurnType.VERDICT, raci_designation="A"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="dev",
            accountable="lead",
            consulted=["reviewer"],
            informed=["pm"],
        )
        data = manifest.model_dump()
        restored = TurnManifest.model_validate(data)

        assert len(restored.specs) == 4
        assert restored.consulted == ["reviewer"]
        assert restored.informed == ["pm"]

    def test_manifest_json_roundtrip(self) -> None:
        """TurnManifest should survive full JSON string roundtrip."""
        specs = [
            TurnSpec(role="dev", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="lead", turn_type=TurnType.VERDICT, raci_designation="A"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="dev",
            accountable="lead",
            consulted=[],
            informed=["stakeholder"],
        )
        json_str = manifest.model_dump_json()
        restored = TurnManifest.model_validate_json(json_str)

        assert restored.specs[0].role == "dev"
        assert restored.specs[1].role == "lead"
        assert restored.informed == ["stakeholder"]


class TestDebateRoomWithManifest:
    """Tests for DebateRoom.turn_manifest field."""

    def test_debate_room_accepts_turn_manifest(self) -> None:
        """DebateRoom should accept optional turn_manifest field."""
        specs = [
            TurnSpec(role="dev", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="lead", turn_type=TurnType.VERDICT, raci_designation="A"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="dev",
            accountable="lead",
            consulted=[],
            informed=[],
        )
        room = DebateRoom(
            thread_id="2026-02-13-raci-test",
            topic="RACI test",
            mode=DebateMode.RACI,
            turn_manifest=manifest,
        )
        assert room.turn_manifest is not None
        assert len(room.turn_manifest.specs) == 2

    def test_debate_room_manifest_defaults_to_none(self) -> None:
        """DebateRoom.turn_manifest should default to None."""
        room = DebateRoom(
            thread_id="2026-02-13-no-manifest-test",
            topic="No manifest test",
            mode=DebateMode.FIXED,
        )
        assert room.turn_manifest is None

    def test_debate_room_with_raci_mode(self) -> None:
        """DebateRoom should accept RACI as a valid DebateMode."""
        room = DebateRoom(
            thread_id="2026-02-13-raci-mode-test",
            topic="RACI mode test",
            mode=DebateMode.RACI,
        )
        assert room.mode == DebateMode.RACI
        assert room.mode.value == "raci"


class TestDebateRoomManifestPersistence:
    """Tests for DebateRoom with manifest persistence through save/load."""

    def test_save_and_load_room_with_manifest(self, tmp_path: Path) -> None:
        """DebateRoom with turn_manifest should survive save/load cycle."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir()

        specs = [
            TurnSpec(role="architect", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="security", turn_type=TurnType.ADVICE, raci_designation="C"),
            TurnSpec(role="architect", turn_type=TurnType.REBUTTAL, raci_designation="R"),
            TurnSpec(role="tech-lead", turn_type=TurnType.VERDICT, raci_designation="A"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="architect",
            accountable="tech-lead",
            consulted=["security"],
            informed=["pm"],
        )
        room = DebateRoom(
            thread_id="2026-02-13-persist-manifest-test",
            topic="Persistence test",
            mode=DebateMode.RACI,
            turn_manifest=manifest,
        )

        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-02-13-persist-manifest-test", state_dir)

        assert loaded.turn_manifest is not None
        assert len(loaded.turn_manifest.specs) == 4
        assert loaded.turn_manifest.responsible == "architect"
        assert loaded.turn_manifest.accountable == "tech-lead"
        assert loaded.turn_manifest.consulted == ["security"]
        assert loaded.turn_manifest.informed == ["pm"]

        # Verify full spec details survived
        assert loaded.turn_manifest.specs[0].role == "architect"
        assert loaded.turn_manifest.specs[0].turn_type == TurnType.PROPOSAL
        assert loaded.turn_manifest.specs[3].role == "tech-lead"
        assert loaded.turn_manifest.specs[3].turn_type == TurnType.VERDICT

    def test_save_and_load_room_without_manifest(self, tmp_path: Path) -> None:
        """DebateRoom without turn_manifest should load with None manifest."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir()

        room = DebateRoom(
            thread_id="2026-02-13-no-manifest-persist-test",
            topic="No manifest persistence test",
            mode=DebateMode.FIXED,
        )

        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-02-13-no-manifest-persist-test", state_dir)

        assert loaded.turn_manifest is None


class TestTurnTypeObservation:
    """Tests for TurnType.OBSERVATION serialization."""

    def test_observation_turnspec_creation(self) -> None:
        """TurnSpec with OBSERVATION type should be valid."""
        spec = TurnSpec(
            role="solution-steward",
            turn_type=TurnType.OBSERVATION,
            raci_designation="I",
        )
        assert spec.role == "solution-steward"
        assert spec.turn_type == TurnType.OBSERVATION
        assert spec.raci_designation == "I"

    def test_observation_turnspec_serialization(self) -> None:
        """TurnSpec with OBSERVATION should serialize to and from JSON."""
        spec = TurnSpec(
            role="ops-team",
            turn_type=TurnType.OBSERVATION,
            raci_designation="I",
        )
        json_str = spec.model_dump_json()
        restored = TurnSpec.model_validate_json(json_str)

        assert restored.role == "ops-team"
        assert restored.turn_type == TurnType.OBSERVATION
        assert restored.raci_designation == "I"

    def test_manifest_with_observation_persistence(self, tmp_path: Path) -> None:
        """Manifest with OBSERVATION turns should survive save/load."""
        state_dir = tmp_path / "debates"
        state_dir.mkdir()

        specs = [
            TurnSpec(role="dev", turn_type=TurnType.PROPOSAL, raci_designation="R"),
            TurnSpec(role="lead", turn_type=TurnType.VERDICT, raci_designation="A"),
            TurnSpec(role="pm", turn_type=TurnType.OBSERVATION, raci_designation="I"),
        ]
        manifest = TurnManifest(
            specs=specs,
            responsible="dev",
            accountable="lead",
            consulted=[],
            informed=["pm"],
        )
        room = DebateRoom(
            thread_id="2026-02-14-observation-persist-test",
            topic="Observation persistence",
            mode=DebateMode.RACI,
            turn_manifest=manifest,
        )

        save_debate_state(room, state_dir)
        loaded = load_debate_state("2026-02-14-observation-persist-test", state_dir)

        assert loaded.turn_manifest is not None
        assert len(loaded.turn_manifest.specs) == 3
        assert loaded.turn_manifest.specs[2].turn_type == TurnType.OBSERVATION
        assert loaded.turn_manifest.specs[2].role == "pm"
        assert loaded.turn_manifest.specs[2].raci_designation == "I"
