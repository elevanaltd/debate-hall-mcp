"""Unit tests for token counting/observability per turn in VTP injection (#135).

Tests cover:
- Token counts appear in formatted transcript when available and enabled
- Token counts are omitted when not available (None/0)
- Token counts can be disabled via show_token_counts config setting
- Formatting is correct: [Role/COGNITION] (N tokens): content
- Backward compatibility: existing transcript format still works
"""

from pathlib import Path

from debate_hall_mcp.config import RoleConfig, TierConfig, TierSettings
from debate_hall_mcp.orchestrator import DebateOrchestrator


class TestFormatDebateStateTokenCounts:
    """Test token count display in _format_debate_state VTP injection (#135)."""

    def _make_orchestrator(
        self, tmp_path: Path, show_token_counts: bool = True
    ) -> DebateOrchestrator:
        """Create an orchestrator with specified show_token_counts setting."""
        tier_config = TierConfig(
            wind=RoleConfig(provider="cli", cli="claude"),
            wall=RoleConfig(provider="cli", cli="codex"),
            door=RoleConfig(provider="cli", cli="gemini"),
            settings=TierSettings(show_token_counts=show_token_counts),
        )
        return DebateOrchestrator(tier_config, tmp_path)

    def test_token_counts_appear_when_available_and_enabled(self, tmp_path: Path) -> None:
        """Token counts appear in transcript when token_output is set and show_token_counts is True."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 3,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind explores possibilities",
                    "token_output": 238,
                },
                {
                    "role": "Wall",
                    "cognition": "ETHOS",
                    "content": "Wall validates constraints",
                    "token_output": 567,
                },
                {
                    "role": "Door",
                    "cognition": "LOGOS",
                    "content": "Door synthesizes resolution",
                    "token_output": 1024,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS] (238 tokens)::" in result
        assert "[Wall/ETHOS] (567 tokens)::" in result
        assert "[Door/LOGOS] (1024 tokens)::" in result

    def test_token_counts_omitted_when_none(self, tmp_path: Path) -> None:
        """Token counts are omitted when token_output is None."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind explores possibilities",
                    "token_output": None,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS]::" in result
        assert "tokens" not in result

    def test_token_counts_omitted_when_zero(self, tmp_path: Path) -> None:
        """Token counts are omitted when token_output is 0."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind explores possibilities",
                    "token_output": 0,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS]::" in result
        assert "tokens" not in result

    def test_token_counts_omitted_when_missing(self, tmp_path: Path) -> None:
        """Token counts are omitted when token_output key is missing from transcript entry."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind explores possibilities",
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS]::" in result
        assert "tokens" not in result

    def test_token_counts_disabled_via_config(self, tmp_path: Path) -> None:
        """Token counts are NOT shown when show_token_counts is False."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=False)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 3,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind explores possibilities",
                    "token_output": 238,
                },
                {
                    "role": "Wall",
                    "cognition": "ETHOS",
                    "content": "Wall validates constraints",
                    "token_output": 567,
                },
                {
                    "role": "Door",
                    "cognition": "LOGOS",
                    "content": "Door synthesizes resolution",
                    "token_output": 1024,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        # Token counts should NOT appear
        assert "tokens" not in result
        # But role/cognition formatting should still work
        assert "[Wind/PATHOS]::" in result
        assert "[Wall/ETHOS]::" in result
        assert "[Door/LOGOS]::" in result

    def test_cognition_included_in_role_format(self, tmp_path: Path) -> None:
        """Role formatting includes cognition archetype as [Role/COGNITION]."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "test content",
                    "token_output": 100,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS]" in result

    def test_cognition_missing_falls_back_to_role_only(self, tmp_path: Path) -> None:
        """When cognition is not in transcript, format falls back to [Role] only."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "content": "test content",
                    "token_output": 100,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        # Should fall back to role-only format
        assert "[Wind] (100 tokens)::" in result

    def test_mixed_token_availability_in_transcript(self, tmp_path: Path) -> None:
        """Some turns with tokens, some without - each formatted correctly."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 3,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": "Wind content",
                    "token_output": 238,
                },
                {
                    "role": "Wall",
                    "cognition": "ETHOS",
                    "content": "Wall content",
                    # No token_output - omitted
                },
                {
                    "role": "Door",
                    "cognition": "LOGOS",
                    "content": "Door content",
                    "token_output": 1024,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert "[Wind/PATHOS] (238 tokens)::" in result
        assert "[Wall/ETHOS]::" in result
        assert "[Door/LOGOS] (1024 tokens)::" in result

    def test_backward_compatibility_no_cognition_no_tokens(self, tmp_path: Path) -> None:
        """Backward compatible: transcript entries without cognition or token_output still work."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "content": "test content",
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        # Should produce the fallback format with role only
        assert "[Wind]::" in result
        assert "test content" in result

    def test_content_still_preserved_with_token_counts(self, tmp_path: Path) -> None:
        """Full turn content is preserved when token counts are added."""
        orchestrator = self._make_orchestrator(tmp_path, show_token_counts=True)
        long_content = "x" * 1000
        state = {
            "thread_id": "test-thread",
            "topic": "test topic",
            "status": "active",
            "turn_count": 1,
            "transcript": [
                {
                    "role": "Wind",
                    "cognition": "PATHOS",
                    "content": long_content,
                    "token_output": 500,
                },
            ],
        }

        result = orchestrator._format_debate_state(state)

        assert long_content in result
        assert "[Wind/PATHOS] (500 tokens)::" in result


class TestShowTokenCountsConfig:
    """Test show_token_counts field on TierSettings."""

    def test_show_token_counts_defaults_to_true(self) -> None:
        """show_token_counts defaults to True (observability opt-out)."""
        settings = TierSettings()
        assert settings.show_token_counts is True

    def test_show_token_counts_can_be_set_false(self) -> None:
        """show_token_counts can be explicitly set to False."""
        settings = TierSettings(show_token_counts=False)
        assert settings.show_token_counts is False

    def test_show_token_counts_can_be_set_true(self) -> None:
        """show_token_counts can be explicitly set to True."""
        settings = TierSettings(show_token_counts=True)
        assert settings.show_token_counts is True


class TestDebateGetTokenOutput:
    """Test that debate_get includes token_output in transcript entries."""

    def test_transcript_includes_token_output(self, tmp_path: Path) -> None:
        """debate_get transcript entries include token_output from Turn model."""
        from datetime import UTC, datetime

        from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn
        from debate_hall_mcp.tools.get import debate_get

        # Create a debate with turns that have token_output
        turn1 = Turn(
            role="Wind",
            content="Wind content",
            timestamp=datetime.now(UTC),
            token_output=238,
            cognition="PATHOS",
        )
        turn2 = Turn(
            role="Wall",
            content="Wall content",
            timestamp=datetime.now(UTC),
            previous_hash=turn1.hash,
            token_output=567,
            cognition="ETHOS",
        )
        room = DebateRoom(
            thread_id="test-token-get",
            topic="Token test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            turns=[turn1, turn2],
        )

        from debate_hall_mcp.state import save_debate_state

        save_debate_state(room, tmp_path)

        result = debate_get(
            thread_id="test-token-get",
            include_transcript=True,
            state_dir=tmp_path,
        )

        # Find non-System transcript entries
        actual_turns = [t for t in result["transcript"] if t["role"] != "System"]
        assert len(actual_turns) == 2
        assert actual_turns[0]["token_output"] == 238
        assert actual_turns[1]["token_output"] == 567

    def test_transcript_includes_cognition(self, tmp_path: Path) -> None:
        """debate_get transcript entries include cognition from Turn model."""
        from datetime import UTC, datetime

        from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn
        from debate_hall_mcp.tools.get import debate_get

        room = DebateRoom(
            thread_id="test-cognition-get",
            topic="Cognition test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            turns=[
                Turn(
                    role="Wind",
                    content="Wind content",
                    timestamp=datetime.now(UTC),
                    cognition="PATHOS",
                ),
            ],
        )

        from debate_hall_mcp.state import save_debate_state

        save_debate_state(room, tmp_path)

        result = debate_get(
            thread_id="test-cognition-get",
            include_transcript=True,
            state_dir=tmp_path,
        )

        actual_turns = [t for t in result["transcript"] if t["role"] != "System"]
        assert len(actual_turns) == 1
        assert actual_turns[0]["cognition"] == "PATHOS"

    def test_transcript_token_output_none_when_not_set(self, tmp_path: Path) -> None:
        """debate_get transcript entries have token_output=None when Turn has no token data."""
        from datetime import UTC, datetime

        from debate_hall_mcp.state import DebateMode, DebateRoom, DebateStatus, Turn
        from debate_hall_mcp.tools.get import debate_get

        room = DebateRoom(
            thread_id="test-no-token",
            topic="No token test",
            mode=DebateMode.FIXED,
            status=DebateStatus.ACTIVE,
            turns=[
                Turn(
                    role="Wind",
                    content="Wind content",
                    timestamp=datetime.now(UTC),
                ),
            ],
        )

        from debate_hall_mcp.state import save_debate_state

        save_debate_state(room, tmp_path)

        result = debate_get(
            thread_id="test-no-token",
            include_transcript=True,
            state_dir=tmp_path,
        )

        actual_turns = [t for t in result["transcript"] if t["role"] != "System"]
        assert len(actual_turns) == 1
        assert actual_turns[0]["token_output"] is None
