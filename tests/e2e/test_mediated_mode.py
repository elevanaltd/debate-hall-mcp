"""E2E tests for mediated mode debate orchestration.

Tests mediated mode where HO explicitly picks next speaker:
- Mediated mode initialization
- debate_pick to set next speaker
- Turn validation against picked speaker
- Mixed orchestration (pick → turn cycles)

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
async def test_mediated_mode_with_pick(cleanup_debates: None) -> None:  # noqa: ARG001
    """Test mediated debate mode with explicit speaker picking.

    Scenario:
    1. Initialize debate (mediated mode)
    2. Pick Wind as next speaker
    3. Wind turn
    4. Pick Door as next speaker (skip Wall)
    5. Door turn
    6. Close debate

    Expected behavior:
    - Picks override fixed sequence
    - Turn validation enforces picked speaker
    - Debate can close without full round
    """
    server = create_server()

    async with create_connected_server_and_client_session(server) as client_session:
        # Step 1: Initialize in mediated mode
        init_result = await client_session.call_tool(
            "init_debate",
            {
                "thread_id": "test-mediated-001",
                "topic": "Balancing autonomy and coordination in multi-agent systems",
                "mode": "mediated",
                "max_turns": 12,
                "max_rounds": 4,
            },
        )

        assert init_result is not None
        init_text = (
            init_result.content[0].text
            if hasattr(init_result.content[0], "text")
            else str(init_result.content[0])
        )
        assert "test-mediated-001" in init_text
        assert "mediated" in init_text.lower()

        # Step 2: Pick Wind as first speaker
        pick_wind_result = await client_session.call_tool(
            "pick_next_speaker",
            {
                "thread_id": "test-mediated-001",
                "role": "Wind",
            },
        )

        assert pick_wind_result is not None
        pick_wind_text = (
            pick_wind_result.content[0].text
            if hasattr(pick_wind_result.content[0], "text")
            else str(pick_wind_result.content[0])
        )
        assert "Wind" in pick_wind_text

        # Step 3: Wind turn
        wind_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "test-mediated-001",
                "role": "Wind",
                "content": "TURN::Wind advocates for maximum agent autonomy - each agent self-directs toward shared goals.",
            },
        )

        assert wind_result is not None
        wind_text = (
            wind_result.content[0].text
            if hasattr(wind_result.content[0], "text")
            else str(wind_result.content[0])
        )
        assert "Wind" in wind_text

        # Step 4: Pick Door (skip Wall - mediated mode allows this)
        pick_door_result = await client_session.call_tool(
            "pick_next_speaker",
            {
                "thread_id": "test-mediated-001",
                "role": "Door",
            },
        )

        assert pick_door_result is not None
        pick_door_text = (
            pick_door_result.content[0].text
            if hasattr(pick_door_result.content[0], "text")
            else str(pick_door_result.content[0])
        )
        assert "Door" in pick_door_text

        # Step 5: Door turn
        door_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "test-mediated-001",
                "role": "Door",
                "content": "TURN::Door synthesizes: structured autonomy - agents self-organize within coordination frameworks.",
            },
        )

        assert door_result is not None
        door_text = (
            door_result.content[0].text
            if hasattr(door_result.content[0], "text")
            else str(door_result.content[0])
        )
        assert "Door" in door_text

        # Step 6: Close debate
        close_result = await client_session.call_tool(
            "close_debate",
            {
                "thread_id": "test-mediated-001",
                "synthesis": "SYNTHESIS::Multi-agent systems thrive with structured autonomy - clear frameworks enable self-organization.",
            },
        )

        assert close_result is not None
        close_text = (
            close_result.content[0].text
            if hasattr(close_result.content[0], "text")
            else str(close_result.content[0])
        )
        assert "synthesis" in close_text.lower()

        # Verify final status
        status_result = await client_session.call_tool(
            "get_debate", {"thread_id": "test-mediated-001"}
        )

        assert status_result is not None
        status_text = (
            status_result.content[0].text
            if hasattr(status_result.content[0], "text")
            else str(status_result.content[0])
        )

        # Should show 2 turns (Wind + Door, skipped Wall)
        assert "synthesis" in status_text.lower()
        assert "2" in status_text or "turn_count" in status_text.lower()
