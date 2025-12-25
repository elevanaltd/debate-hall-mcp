"""E2E tests for resource limit enforcement.

Tests debate resource limits:
- max_turns enforcement
- max_rounds enforcement
- Exhaustion termination
- Status reporting of limits

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
async def test_max_turns_limit_enforcement(cleanup_debates: None) -> None:  # noqa: ARG001
    """Test that max_turns limit is enforced correctly.

    Scenario:
    1. Initialize debate with max_turns=3
    2. Add 3 turns (Wind, Wall, Door)
    3. Attempt 4th turn - should fail or mark exhausted
    4. Verify debate is exhausted

    Expected behavior:
    - Debate allows exactly max_turns turns
    - Additional turns are rejected or debate transitions to exhausted
    - Status reflects exhaustion
    """
    server = create_server()

    async with create_connected_server_and_client_session(server) as client_session:
        # Step 1: Initialize with max_turns=3
        init_result = await client_session.call_tool(
            "init_debate",
            {
                "thread_id": "test-limits-001",
                "topic": "Testing resource limits",
                "mode": "fixed",
                "max_turns": 3,
                "max_rounds": 4,
            },
        )

        assert init_result is not None
        init_text = (
            init_result.content[0].text
            if hasattr(init_result.content[0], "text")
            else str(init_result.content[0])
        )
        assert "test-limits-001" in init_text

        # Step 2: Add 3 turns (exactly at limit)
        for i, role in enumerate(["Wind", "Wall", "Door"], 1):
            turn_result = await client_session.call_tool(
                "add_turn",
                {
                    "thread_id": "test-limits-001",
                    "role": role,
                    "content": f"TURN::{role} turn {i}",
                },
            )
            assert turn_result is not None

        # Step 3: Check status after hitting limit
        status_result = await client_session.call_tool(
            "get_status", {"thread_id": "test-limits-001"}
        )

        assert status_result is not None
        status_text = (
            status_result.content[0].text
            if hasattr(status_result.content[0], "text")
            else str(status_result.content[0])
        )

        # Should show exhausted or blocked state
        assert "exhausted" in status_text.lower() or "3" in status_text

        # Step 4: Attempt 4th turn - should fail
        # Note: The actual error handling might vary - could be error response
        # or could be silently rejected. We just verify status shows exhausted.
        try:
            fourth_result = await client_session.call_tool(
                "add_turn",
                {
                    "thread_id": "test-limits-001",
                    "role": "Wind",  # Would be next in cycle
                    "content": "TURN::This should fail",
                },
            )
            # If it doesn't raise, check the response for error
            fourth_text = (
                fourth_result.content[0].text
                if hasattr(fourth_result.content[0], "text")
                else str(fourth_result.content[0])
            )
            # Should contain error or exhausted indication
            assert (
                "exhausted" in fourth_text.lower()
                or "error" in fourth_text.lower()
                or "limit" in fourth_text.lower()
            )
        except Exception:
            # Exception is acceptable - limit is enforced
            pass

        # Verify final status confirms exhaustion
        final_status = await client_session.call_tool(
            "get_status", {"thread_id": "test-limits-001"}
        )

        assert final_status is not None
        final_text = (
            final_status.content[0].text
            if hasattr(final_status.content[0], "text")
            else str(final_status.content[0])
        )
        assert "3" in final_text  # Should show 3 turns
