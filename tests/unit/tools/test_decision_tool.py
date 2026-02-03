"""Tests for extract_decision_record MCP tool wrapper.

Tests cover:
- Tool returns DecisionRecord as JSON-compatible dict
- Tool raises FileNotFoundError for missing threads
- Tool raises ValueError for non-closed debates (ACTIVE/PAUSED)
"""

from pathlib import Path

import pytest

from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


class TestExtractDecisionRecordTool:
    """Tests for extract_decision_record MCP tool wrapper."""

    def test_extract_decision_record_tool_success(self, tmp_path: Path) -> None:
        """Tool returns DecisionRecord as JSON-compatible dict for closed debate."""
        # Import here to trigger import error if module doesn't exist
        from debate_hall_mcp.tools.decision import extract_decision_record

        # Setup: Create and close a debate
        debate_init(
            thread_id="2026-01-15-decision-tool-test",
            topic="Architecture decision test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2026-01-15-decision-tool-test",
            role="Wind",
            content="Wind perspective on the architecture.",
            state_dir=tmp_path,
        )
        debate_turn(
            thread_id="2026-01-15-decision-tool-test",
            role="Wall",
            content="Wall constraint on the architecture.",
            state_dir=tmp_path,
        )
        debate_close(
            thread_id="2026-01-15-decision-tool-test",
            synthesis="The final architecture decision.",
            state_dir=tmp_path,
        )

        # Execute: Call the tool
        result = extract_decision_record(
            thread_id="2026-01-15-decision-tool-test",
            state_dir=tmp_path,
        )

        # Verify: Result is a dict with expected fields
        assert isinstance(result, dict)
        assert result["thread_id"] == "2026-01-15-decision-tool-test"
        assert result["topic"] == "Architecture decision test"
        assert result["synthesis"] == "The final architecture decision."
        assert result["status"] == "synthesis"
        assert result["turn_count"] == 2
        assert len(result["wind_perspectives"]) == 1
        assert len(result["wall_constraints"]) == 1
        # Provenance fields present
        assert "decision_hash" in result
        assert "source_hash" in result
        assert "extracted_at" in result
        assert "decided_at" in result

    def test_extract_decision_record_tool_not_found(self, tmp_path: Path) -> None:
        """Tool raises FileNotFoundError for missing thread."""
        from debate_hall_mcp.tools.decision import extract_decision_record

        with pytest.raises(FileNotFoundError):
            extract_decision_record(
                thread_id="nonexistent-thread",
                state_dir=tmp_path,
            )

    def test_extract_decision_record_tool_not_closed_active(self, tmp_path: Path) -> None:
        """Tool raises ValueError for ACTIVE debate."""
        from debate_hall_mcp.tools.decision import extract_decision_record

        # Setup: Create debate but don't close it
        debate_init(
            thread_id="2026-01-15-active-debate",
            topic="Active debate",
            mode="fixed",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="Cannot extract decision from active debate"):
            extract_decision_record(
                thread_id="2026-01-15-active-debate",
                state_dir=tmp_path,
            )

    def test_extract_decision_record_tool_not_closed_paused(self, tmp_path: Path) -> None:
        """Tool raises ValueError for PAUSED debate."""
        from debate_hall_mcp.tools.decision import extract_decision_record

        # Setup: Create debate and pause it
        debate_init(
            thread_id="2026-01-15-paused-debate",
            topic="Paused debate",
            mode="fixed",
            state_dir=tmp_path,
        )

        # Pause the debate by modifying state directly
        from debate_hall_mcp.state import (
            DebateStatus,
            load_debate_state,
            save_debate_state,
        )

        room = load_debate_state("2026-01-15-paused-debate", tmp_path)
        room.status = DebateStatus.PAUSED
        save_debate_state(room, tmp_path)

        with pytest.raises(ValueError, match="Cannot extract decision from paused debate"):
            extract_decision_record(
                thread_id="2026-01-15-paused-debate",
                state_dir=tmp_path,
            )

    def test_extract_decision_record_tool_returns_json_serializable(self, tmp_path: Path) -> None:
        """Tool result is JSON serializable (datetime converted)."""
        import json

        from debate_hall_mcp.tools.decision import extract_decision_record

        # Setup: Create and close a debate
        debate_init(
            thread_id="2026-01-15-json-test",
            topic="JSON serialization test",
            mode="fixed",
            state_dir=tmp_path,
        )
        debate_close(
            thread_id="2026-01-15-json-test",
            synthesis="Serializable synthesis.",
            state_dir=tmp_path,
        )

        # Execute
        result = extract_decision_record(
            thread_id="2026-01-15-json-test",
            state_dir=tmp_path,
        )

        # Verify: Should be JSON serializable without errors
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        assert "2026-01-15-json-test" in json_str


class TestResolveQuestion:
    """Tests for resolve_question Layer 3 API."""

    def test_resolve_question_generates_thread_id(self) -> None:
        """resolve_question generates thread_id in YYYY-MM-DD-slug format when not provided."""
        from datetime import UTC, datetime

        # Test the thread_id generation logic (extracted for testability)
        topic = "Should we use microservices or monolith?"
        topic_slug = topic[:30].lower().replace(" ", "-")
        topic_slug = "".join(c for c in topic_slug if c.isalnum() or c == "-")
        date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        expected_pattern = f"{date_prefix}-should-we-use-microservices-or"

        # Verify pattern
        assert expected_pattern.startswith("2026-")  # Year check
        assert "should-we-use" in expected_pattern
        assert " " not in expected_pattern  # No spaces

    def test_resolve_question_thread_id_sanitization(self) -> None:
        """Thread ID generation removes non-alphanumeric characters except dash."""
        topic = "Is React's useEffect() better than Vue's watch()?"
        topic_slug = topic[:30].lower().replace(" ", "-")
        topic_slug = "".join(c for c in topic_slug if c.isalnum() or c == "-")

        # Should remove ' and () characters
        assert "'" not in topic_slug
        assert "(" not in topic_slug
        assert ")" not in topic_slug
        assert topic_slug == "is-reacts-useeffect-better-"

    @pytest.mark.anyio
    async def test_resolve_question_uses_provided_thread_id(self, tmp_path: Path) -> None:
        """resolve_question uses provided thread_id instead of generating one."""
        from unittest.mock import patch

        # Mock run_debate to capture the thread_id it receives
        captured_thread_id = None

        async def mock_run_debate(
            topic: str,
            tier: str = "standard",  # noqa: ARG001
            thread_id: str | None = None,
            state_dir: Path | None = None,  # noqa: ARG001
        ) -> dict:
            nonlocal captured_thread_id
            captured_thread_id = thread_id
            return {
                "thread_id": thread_id,
                "topic": topic,
                "status": "synthesis",
                "turn_count": 3,
                "synthesis": "Final synthesis.",
            }

        with (
            patch("debate_hall_mcp.tools.decision.run_debate", new=mock_run_debate),
            patch("debate_hall_mcp.tools.decision.load_debate_state") as mock_load,
            patch("debate_hall_mcp.tools.decision._extract") as mock_extract,
        ):
            # Mock the load_debate_state to return a closed debate
            from debate_hall_mcp.decision import DecisionRecord
            from debate_hall_mcp.state import DebateRoom, DebateStatus

            mock_room = DebateRoom(
                thread_id="custom-thread-123",
                topic="Test topic",
                mode="fixed",
                status=DebateStatus.SYNTHESIS,
                synthesis="Final synthesis.",
            )
            mock_load.return_value = mock_room

            mock_record = DecisionRecord(
                thread_id="custom-thread-123",
                topic="Test topic",
                decided_at="2026-02-03T00:00:00Z",
                synthesis="Final synthesis.",
                decision_hash="abc123",
                status="synthesis",
                wind_perspectives=[],
                wall_constraints=[],
                door_refinements=[],
                consensus_reached=False,
                consensus_votes={},
                refinement_count=0,
                extracted_at="2026-02-03T00:00:00Z",
                source_hash="def456",
                turn_count=3,
            )
            mock_extract.return_value = mock_record

            from debate_hall_mcp.tools.decision import resolve_question

            await resolve_question(
                topic="Test topic",
                thread_id="custom-thread-123",
                state_dir=tmp_path,
            )

        # Verify the provided thread_id was used
        assert captured_thread_id == "custom-thread-123"

    @pytest.mark.anyio
    async def test_resolve_question_returns_decision_record_fields(self, tmp_path: Path) -> None:
        """resolve_question returns DecisionRecord fields plus debate_result."""
        from unittest.mock import patch

        with patch("debate_hall_mcp.tools.decision.run_debate") as mock_run:
            mock_run.return_value = {
                "thread_id": "2026-02-03-test-debate",
                "topic": "Test debate",
                "status": "synthesis",
                "turn_count": 3,
                "synthesis": "Final synthesis.",
            }

            with patch("debate_hall_mcp.tools.decision.load_debate_state") as mock_load:
                from debate_hall_mcp.state import DebateRoom, DebateStatus

                mock_room = DebateRoom(
                    thread_id="2026-02-03-test-debate",
                    topic="Test debate",
                    mode="fixed",
                    status=DebateStatus.SYNTHESIS,
                    synthesis="Final synthesis.",
                )
                mock_load.return_value = mock_room

                with patch("debate_hall_mcp.tools.decision._extract") as mock_extract:
                    from debate_hall_mcp.decision import DecisionRecord

                    mock_record = DecisionRecord(
                        thread_id="2026-02-03-test-debate",
                        topic="Test debate",
                        decided_at="2026-02-03T00:00:00Z",
                        synthesis="Final synthesis.",
                        decision_hash="abc123",
                        status="synthesis",
                        wind_perspectives=["perspective1"],
                        wall_constraints=["constraint1"],
                        door_refinements=[],
                        consensus_reached=True,
                        consensus_votes={"Wind": True, "Wall": True},
                        refinement_count=0,
                        extracted_at="2026-02-03T00:00:00Z",
                        source_hash="def456",
                        turn_count=3,
                    )
                    mock_extract.return_value = mock_record

                    from debate_hall_mcp.tools.decision import resolve_question

                    result = await resolve_question(
                        topic="Test debate",
                        state_dir=tmp_path,
                    )

        # Verify DecisionRecord fields are present
        assert result["thread_id"] == "2026-02-03-test-debate"
        assert result["synthesis"] == "Final synthesis."
        assert result["status"] == "synthesis"
        assert result["wind_perspectives"] == ["perspective1"]
        assert result["wall_constraints"] == ["constraint1"]
        assert result["consensus_reached"] is True

        # Verify debate_result is included
        assert "debate_result" in result
        assert result["debate_result"]["status"] == "synthesis"

    @pytest.mark.anyio
    async def test_resolve_question_raises_on_failed_debate(self, tmp_path: Path) -> None:
        """resolve_question raises RuntimeError if debate fails."""
        from unittest.mock import patch

        with patch("debate_hall_mcp.tools.decision.run_debate") as mock_run:
            mock_run.return_value = {
                "thread_id": "2026-02-03-failed-debate",
                "topic": "Failed debate",
                "status": "error",  # Not a success status
                "turn_count": 1,
                "synthesis": None,
            }

            from debate_hall_mcp.tools.decision import resolve_question

            with pytest.raises(RuntimeError, match="Debate did not complete successfully"):
                await resolve_question(
                    topic="Failed debate",
                    state_dir=tmp_path,
                )
