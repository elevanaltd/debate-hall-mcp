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
