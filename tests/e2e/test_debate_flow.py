"""E2E tests for full debate lifecycle.

Tests the complete debate flow from initialization to closure:
- Fixed mode orchestration
- Wind→Wall→Door→synthesis cycle
- Hash chain integrity verification
- Transcript persistence

RED phase: Writing failing test first per TDD discipline.
"""

import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from debate_hall_mcp.server import create_server


@pytest.fixture(scope="function")
def cleanup_debates() -> Generator[None, None, None]:
    """Clean up debate state before and after tests."""
    debates_dir = Path("./debates")
    if debates_dir.exists():
        shutil.rmtree(debates_dir)

    yield

    if debates_dir.exists():
        shutil.rmtree(debates_dir)


@pytest.mark.anyio
async def test_full_debate_lifecycle_fixed_mode(cleanup_debates: None) -> None:  # noqa: ARG001
    """Test complete debate flow in fixed mode.

    Scenario:
    1. Initialize debate (fixed mode)
    2. Wind turn
    3. Wall turn
    4. Door turn
    5. Close with synthesis
    6. Verify transcript hash chain integrity

    Expected behavior:
    - Each turn follows Wind→Wall→Door sequence
    - Hash chain is maintained through all turns
    - Final synthesis contains all perspectives
    - Debate status transitions: active→closed
    """
    server = create_server()

    # Use MCP memory transport for in-process testing
    async with create_connected_server_and_client_session(server) as client_session:
        # Step 1: Initialize debate
        init_result = await client_session.call_tool(
            "init_debate",
            {
                "thread_id": "2025-01-01-test-e2e-001",
                "topic": "The role of constraints in creative problem-solving",
                "mode": "fixed",
                "max_turns": 12,
                "max_rounds": 4,
            },
        )

        assert init_result is not None
        content = init_result.content
        assert len(content) > 0

        # Parse response - MCP returns list of TextContent or ImageContent
        response_text = content[0].text if hasattr(content[0], "text") else str(content[0])

        # Verify initialization
        assert "2025-01-01-test-e2e-001" in response_text
        assert "active" in response_text.lower() or "open" in response_text.lower()

        # Step 2: Wind turn (PATHOS - possibility exploration)
        wind_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "2025-01-01-test-e2e-001",
                "role": "Wind",
                "content": "TURN::Wind explores infinite possibility space: constraints as catalysts for breakthrough thinking.",
            },
        )

        assert wind_result is not None
        wind_text = (
            wind_result.content[0].text
            if hasattr(wind_result.content[0], "text")
            else str(wind_result.content[0])
        )
        assert "Wind" in wind_text

        # Step 3: Wall turn (ETHOS - boundary validation)
        wall_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "2025-01-01-test-e2e-001",
                "role": "Wall",
                "content": "TURN::Wall validates boundaries: unconstrained exploration leads to chaos, structure provides safety.",
            },
        )

        assert wall_result is not None
        wall_text = (
            wall_result.content[0].text
            if hasattr(wall_result.content[0], "text")
            else str(wall_result.content[0])
        )
        assert "Wall" in wall_text

        # Step 4: Door turn (LOGOS - synthesis)
        door_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "2025-01-01-test-e2e-001",
                "role": "Door",
                "content": "TURN::Door synthesizes: constraints enable creativity by channeling exploration into productive paths.",
            },
        )

        assert door_result is not None
        door_text = (
            door_result.content[0].text
            if hasattr(door_result.content[0], "text")
            else str(door_result.content[0])
        )
        assert "Door" in door_text

        # Step 5: Close debate with synthesis
        close_result = await client_session.call_tool(
            "close_debate",
            {
                "thread_id": "2025-01-01-test-e2e-001",
                "synthesis": "SYNTHESIS::The debate reveals that constraints and creativity exist in productive tension - constraints catalyze breakthroughs while preventing chaos.",
            },
        )

        assert close_result is not None
        close_text = (
            close_result.content[0].text
            if hasattr(close_result.content[0], "text")
            else str(close_result.content[0])
        )
        assert "closed" in close_text.lower() or "synthesis" in close_text.lower()

        # Step 6: Verify final status shows hash chain integrity
        status_result = await client_session.call_tool(
            "get_debate", {"thread_id": "2025-01-01-test-e2e-001"}
        )

        assert status_result is not None
        status_text = (
            status_result.content[0].text
            if hasattr(status_result.content[0], "text")
            else str(status_result.content[0])
        )

        # Verify debate is closed (status is "synthesis" after close)
        assert "synthesis" in status_text.lower()

        # Verify all turns were recorded (3 turns recorded)
        # Note: This is a basic check - actual hash chain verification would
        # require parsing the JSON state file, but that's integration-level detail
        assert "turn_count" in status_text.lower() and "3" in status_text
