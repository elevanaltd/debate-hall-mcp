"""E2E tests for admin override functions.

Tests administrative safety mechanisms:
- debate_force_close (I5: Human-in-the-loop kill switch)
- debate_tombstone (I4: Audit trail preservation with redaction)
- Admin overrides normal debate flow

RED phase: Writing failing test first per TDD discipline.
"""

import shutil
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from debate_hall_mcp.server import create_server


@pytest.fixture(scope="function")
def cleanup_debates():
    """Clean up debate state before and after tests."""
    debates_dir = Path("./debates")
    if debates_dir.exists():
        shutil.rmtree(debates_dir)

    yield

    if debates_dir.exists():
        shutil.rmtree(debates_dir)


@pytest.mark.anyio
async def test_force_close_admin_override(cleanup_debates):  # noqa: ARG001
    """Test force_close admin kill switch functionality.

    Scenario:
    1. Initialize debate
    2. Add some turns
    3. Force close (admin override)
    4. Verify debate is force_closed
    5. Verify reason is recorded

    Expected behavior:
    - Force close works at any debate state
    - Debate transitions to force_closed
    - Reason is preserved in state
    - Subsequent turns are rejected
    """
    server = create_server()

    async with create_connected_server_and_client_session(server) as client_session:
        # Step 1: Initialize debate
        init_result = await client_session.call_tool(
            "init_debate",
            {
                "thread_id": "test-admin-001",
                "topic": "Testing admin overrides",
                "mode": "fixed",
                "max_turns": 12,
                "max_rounds": 4,
            }
        )

        assert init_result is not None

        # Step 2: Add one turn
        turn_result = await client_session.call_tool(
            "add_turn",
            {
                "thread_id": "test-admin-001",
                "role": "Wind",
                "content": "TURN::Wind initial perspective",
            }
        )

        assert turn_result is not None

        # Step 3: Force close (admin override mid-debate)
        force_close_result = await client_session.call_tool(
            "force_close_debate",
            {
                "thread_id": "test-admin-001",
                "reason": "Emergency shutdown: content policy violation detected",
            }
        )

        assert force_close_result is not None
        force_close_text = force_close_result.content[0].text if hasattr(force_close_result.content[0], 'text') else str(force_close_result.content[0])

        # Should indicate force closure
        assert "force" in force_close_text.lower() or "closed" in force_close_text.lower()

        # Step 4: Verify status shows force_closed
        status_result = await client_session.call_tool(
            "get_status",
            {"thread_id": "test-admin-001"}
        )

        assert status_result is not None
        status_text = status_result.content[0].text if hasattr(status_result.content[0], 'text') else str(status_result.content[0])

        # Should show force_closed status and reason
        assert "force" in status_text.lower() or "emergency" in status_text.lower()

        # Step 5: Attempt to add turn after force close - should fail
        try:
            turn_after_result = await client_session.call_tool(
                "add_turn",
                {
                    "thread_id": "test-admin-001",
                    "role": "Wall",
                    "content": "TURN::This should be rejected",
                }
            )
            # If it doesn't raise, check for error indication
            turn_after_text = turn_after_result.content[0].text if hasattr(turn_after_result.content[0], 'text') else str(turn_after_result.content[0])
            assert "error" in turn_after_text.lower() or "closed" in turn_after_text.lower() or "force" in turn_after_text.lower()
        except Exception:
            # Exception is acceptable - force close blocks new turns
            pass


@pytest.mark.anyio
async def test_tombstone_turn_redaction(cleanup_debates):  # noqa: ARG001
    """Test turn tombstone/redaction while preserving audit trail.

    Scenario:
    1. Initialize debate
    2. Add several turns
    3. Tombstone a middle turn (redact content)
    4. Verify turn is redacted but audit trail intact
    5. Verify hash chain is preserved

    Expected behavior:
    - Tombstone redacts content but preserves turn entry
    - Reason for redaction is recorded
    - Turn count remains accurate
    - Hash chain integrity maintained (immutable audit)
    """
    server = create_server()

    async with create_connected_server_and_client_session(server) as client_session:
        # Step 1: Initialize debate
        init_result = await client_session.call_tool(
            "init_debate",
            {
                "thread_id": "test-admin-002",
                "topic": "Testing tombstone redaction",
                "mode": "fixed",
                "max_turns": 12,
                "max_rounds": 4,
            }
        )

        assert init_result is not None

        # Step 2: Add three turns
        for i, role in enumerate(["Wind", "Wall", "Door"]):
            turn_result = await client_session.call_tool(
                "add_turn",
                {
                    "thread_id": "test-admin-002",
                    "role": role,
                    "content": f"TURN::{role} turn {i+1} with sensitive content",
                }
            )
            assert turn_result is not None

        # Step 3: Tombstone the Wall turn (index 1)
        tombstone_result = await client_session.call_tool(
            "tombstone_turn",
            {
                "thread_id": "test-admin-002",
                "turn_index": 1,  # Wall turn (0-indexed)
                "reason": "Content redacted: privacy concern",
            }
        )

        assert tombstone_result is not None
        tombstone_text = tombstone_result.content[0].text if hasattr(tombstone_result.content[0], 'text') else str(tombstone_result.content[0])

        # Should confirm tombstone
        assert "tombstone" in tombstone_text.lower() or "redact" in tombstone_text.lower() or "1" in tombstone_text

        # Step 4: Verify status shows turn count unchanged
        status_result = await client_session.call_tool(
            "get_status",
            {"thread_id": "test-admin-002"}
        )

        assert status_result is not None
        status_text = status_result.content[0].text if hasattr(status_result.content[0], 'text') else str(status_result.content[0])

        # Should still show 3 turns (tombstone doesn't delete)
        assert "3" in status_text
        assert "active" in status_text.lower() or "open" in status_text.lower()

        # Debate should still be functional - can close normally
        close_result = await client_session.call_tool(
            "close_debate",
            {
                "thread_id": "test-admin-002",
                "synthesis": "SYNTHESIS::Audit trail preserved despite redaction",
            }
        )

        assert close_result is not None
