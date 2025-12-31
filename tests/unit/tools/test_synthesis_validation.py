"""Tests for synthesis semantics validation (Issue #38).

TDD Discipline: RED phase - these tests should FAIL until implementation.

Issue #38 Requirements:
- Synthesis content validated against LOGOS rules (numbered steps, synthesis markers)
- Non-strict mode: WARN on invalid synthesis structure
- Strict mode: BLOCK on invalid synthesis structure
- Backward compatibility: short synthesis allowed (pragmatic leniency)

Immutables: I1 (state isolation), I3 (finite dialectic closure)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.state import load_debate_state
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.init import debate_init


class TestSynthesisValidationNonStrict:
    """Test synthesis LOGOS validation in non-strict mode (default).

    Non-strict mode should WARN on invalid synthesis but still allow close.
    """

    def test_valid_synthesis_with_logos_structure_passes(self, tmp_path: Path) -> None:
        """Valid synthesis with numbered steps and synthesis markers passes."""
        debate_init(
            thread_id="2025-01-01-synth-valid-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # LOGOS-compliant synthesis: numbered steps + synthesis markers
        valid_synthesis = """
[TENSION]
Speed vs. verification quality

[PATTERN]
1. We analyzed the tension between immediate action and thorough verification
2. We identified that quality gates provide the synthesis
3. We concluded that sequential verification creates emergent assurance

[CLARITY]
The debate resolved through structured synthesis: quality emerges from constraint.
"""
        result = debate_close(
            thread_id="2025-01-01-synth-valid-001",
            synthesis=valid_synthesis,
            state_dir=tmp_path,
        )

        assert result["status"] == "synthesis"
        assert result["synthesis"] == valid_synthesis

    def test_invalid_synthesis_missing_steps_warns(self, tmp_path: Path) -> None:
        """Synthesis without numbered steps triggers WARN in non-strict mode.

        Non-strict mode should still close but return warning in response.
        """
        debate_init(
            thread_id="2025-01-01-synth-warn-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # Invalid synthesis: missing numbered steps (LOGOS violation)
        invalid_synthesis = """
[TENSION]
Speed vs. quality

[PATTERN]
We should just proceed immediately without structure.

[CLARITY]
Done.
"""
        result = debate_close(
            thread_id="2025-01-01-synth-warn-001",
            synthesis=invalid_synthesis,
            state_dir=tmp_path,
        )

        # Should still close in non-strict mode
        assert result["status"] == "synthesis"
        # Should include validation warning
        assert "validation_warnings" in result
        assert len(result["validation_warnings"]) > 0
        assert any(
            "numbered" in w.lower() or "step" in w.lower() for w in result["validation_warnings"]
        )

    def test_invalid_synthesis_missing_markers_warns(self, tmp_path: Path) -> None:
        """Synthesis without synthesis markers triggers WARN in non-strict mode."""
        debate_init(
            thread_id="2025-01-01-synth-warn-002",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # Invalid synthesis: missing synthesis markers but has steps
        invalid_synthesis = """
Analysis complete:

1. First we analyzed the problem
2. Then we found a solution
3. Finally we verified correctness

All done.
"""
        result = debate_close(
            thread_id="2025-01-01-synth-warn-002",
            synthesis=invalid_synthesis,
            state_dir=tmp_path,
        )

        # Should still close in non-strict mode
        assert result["status"] == "synthesis"
        # Should include validation warning about markers
        assert "validation_warnings" in result
        assert len(result["validation_warnings"]) > 0
        assert any(
            "marker" in w.lower() or "synthesis" in w.lower() for w in result["validation_warnings"]
        )

    def test_short_synthesis_allowed_backward_compat(self, tmp_path: Path) -> None:
        """Short synthesis (<100 chars) is allowed for backward compatibility.

        Many existing closes use brief synthesis. Validation should be lenient.
        """
        debate_init(
            thread_id="2025-01-01-synth-short-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # Short synthesis - backward compat
        short_synthesis = "Debate concluded: consensus reached."

        result = debate_close(
            thread_id="2025-01-01-synth-short-001",
            synthesis=short_synthesis,
            state_dir=tmp_path,
        )

        # Should close without warnings for short synthesis
        assert result["status"] == "synthesis"
        assert (
            result.get("validation_warnings") is None
            or len(result.get("validation_warnings", [])) == 0
        )


class TestSynthesisValidationStrict:
    """Test synthesis LOGOS validation in strict_cognition mode.

    Strict mode should BLOCK on invalid synthesis structure.
    """

    def test_valid_synthesis_passes_strict_mode(self, tmp_path: Path) -> None:
        """Valid LOGOS synthesis passes in strict mode."""
        debate_init(
            thread_id="2025-01-01-synth-strict-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=True,
        )

        valid_synthesis = """
[TENSION]
Competing priorities identified

1. Analysis of system constraints
2. Evaluation of proposed solutions
3. Synthesis of final approach

[STRUCTURE]
The pattern emerges from constraint.

[CLARITY]
Resolution achieved through structured convergence.
"""
        result = debate_close(
            thread_id="2025-01-01-synth-strict-001",
            synthesis=valid_synthesis,
            state_dir=tmp_path,
        )

        assert result["status"] == "synthesis"

    def test_invalid_synthesis_missing_steps_blocks_strict(self, tmp_path: Path) -> None:
        """Synthesis without numbered steps BLOCKS in strict mode."""
        debate_init(
            thread_id="2025-01-01-synth-strict-002",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=True,
        )

        # Invalid synthesis: missing numbered steps
        invalid_synthesis = """
[TENSION]
Speed vs. quality

[PATTERN]
We concluded without structured reasoning.

[CLARITY]
Done.
"""
        with pytest.raises(ValueError, match="synthesis.*validation|numbered.*step"):
            debate_close(
                thread_id="2025-01-01-synth-strict-002",
                synthesis=invalid_synthesis,
                state_dir=tmp_path,
            )

    def test_short_synthesis_blocks_strict_mode(self, tmp_path: Path) -> None:
        """Short synthesis also BLOCKS in strict mode - no backward compat exception."""
        debate_init(
            thread_id="2025-01-01-synth-strict-003",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=True,
        )

        # Short synthesis in strict mode should block
        short_synthesis = "Done."

        with pytest.raises(ValueError, match="synthesis.*validation|numbered.*step"):
            debate_close(
                thread_id="2025-01-01-synth-strict-003",
                synthesis=short_synthesis,
                state_dir=tmp_path,
            )


class TestSynthesisValidationEdgeCases:
    """Test edge cases for synthesis validation."""

    def test_synthesis_validation_uses_logos_rules(self, tmp_path: Path) -> None:
        """Synthesis validation specifically uses LOGOS/Door rules.

        LOGOS requires: numbered steps (BLOCK), synthesis markers (WARN)
        """
        debate_init(
            thread_id="2025-01-01-synth-logos-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # Content that would pass PATHOS but not LOGOS
        pathos_style_synthesis = """
1. Should we merge now?
2. Should we wait for more validation?
3. What if we need more time?

Which approach is best?
"""
        result = debate_close(
            thread_id="2025-01-01-synth-logos-001",
            synthesis=pathos_style_synthesis,
            state_dir=tmp_path,
        )

        # Should close but warn about missing synthesis markers
        assert result["status"] == "synthesis"
        # PATHOS-style content with questions should trigger LOGOS warning
        # (numbered steps present, but missing LOGOS synthesis markers)
        assert "validation_warnings" in result

    def test_synthesis_validation_result_in_room_state(self, tmp_path: Path) -> None:
        """Synthesis validation warnings should be accessible from room state."""
        debate_init(
            thread_id="2025-01-01-synth-state-001",
            topic="Test topic",
            state_dir=tmp_path,
            strict_cognition=False,
        )

        # Synthesis with WARN-level issues
        warn_synthesis = """
Analysis complete:

1. First step
2. Second step
3. Third step

Conclusion reached.
"""
        debate_close(
            thread_id="2025-01-01-synth-state-001",
            synthesis=warn_synthesis,
            state_dir=tmp_path,
        )

        # Load state and check for warnings
        room = load_debate_state("2025-01-01-synth-state-001", tmp_path)
        # Should have synthesis validation result accessible
        # (Implementation may store this in room or return only)
        assert room.synthesis == warn_synthesis


class TestSynthesisValidationIntegration:
    """Integration tests for synthesis validation with engine."""

    def test_engine_close_validates_synthesis(self) -> None:
        """Engine.close_debate should validate synthesis content.

        This tests that the engine itself has awareness of closure semantics,
        not just the tool layer.
        """
        from debate_hall_mcp.engine import DebateEngine, TerminationReason
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="2025-01-01-engine-synth-001",
            topic="Test topic",
            mode=DebateMode.FIXED,
            strict_cognition=True,
        )

        engine = DebateEngine(room)

        # Invalid synthesis should trigger validation in engine
        invalid_synthesis = "No structure whatsoever."

        with pytest.raises(ValueError, match="synthesis.*validation|numbered.*step"):
            engine.close_debate(TerminationReason.SYNTHESIS, synthesis=invalid_synthesis)

    def test_engine_close_valid_synthesis_passes(self) -> None:
        """Engine.close_debate passes with valid LOGOS synthesis."""
        from debate_hall_mcp.engine import DebateEngine, TerminationReason
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="2025-01-01-engine-synth-002",
            topic="Test topic",
            mode=DebateMode.FIXED,
            strict_cognition=True,
        )

        engine = DebateEngine(room)

        valid_synthesis = """
[TENSION]
Speed vs quality

1. Analyzed constraints
2. Evaluated options
3. Synthesized approach

[CLARITY]
Resolution achieved.
"""
        # Should not raise
        engine.close_debate(TerminationReason.SYNTHESIS, synthesis=valid_synthesis)

        assert room.synthesis == valid_synthesis

    def test_engine_non_synthesis_termination_no_validation(self) -> None:
        """Engine.close_debate with non-SYNTHESIS reason skips validation."""
        from debate_hall_mcp.engine import DebateEngine, TerminationReason
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="2025-01-01-engine-force-001",
            topic="Test topic",
            mode=DebateMode.FIXED,
            strict_cognition=True,
        )

        engine = DebateEngine(room)

        # Force close with reason - no synthesis validation needed
        engine.close_debate(TerminationReason.FORCE_CLOSE, synthesis=None)

        assert room.status.value == "force_closed"

    def test_engine_synthesis_termination_requires_synthesis(self) -> None:
        """Engine.close_debate with SYNTHESIS reason requires synthesis content (Issue #49)."""
        from debate_hall_mcp.engine import DebateEngine, TerminationReason
        from debate_hall_mcp.state import DebateMode, DebateRoom

        room = DebateRoom(
            thread_id="2025-01-01-engine-synth-req-001",
            topic="Test topic",
            mode=DebateMode.FIXED,
            strict_cognition=False,
        )

        engine = DebateEngine(room)

        # Closing with SYNTHESIS reason but no synthesis should raise
        with pytest.raises(ValueError, match="Synthesis content is required"):
            engine.close_debate(TerminationReason.SYNTHESIS, synthesis=None)
