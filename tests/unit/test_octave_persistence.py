from datetime import UTC, datetime

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
    load_debate_state,
    save_debate_state,
)


def test_octave_persistence_roundtrip(tmp_path):
    """Verify that a debate room can be saved to OCTAVE format and reloaded correctly."""

    # 1. Setup - Create a debate room in OCTAVE mode
    thread_id = "2026-01-01-test-persistence"
    room = DebateRoom(
        thread_id=thread_id,
        topic="Persistence Test",
        mode=DebateMode.FIXED,
        status=DebateStatus.ACTIVE,
        octave_mode=True,
    )

    # Add a turn
    turn = Turn(
        role="Wind", content="Testing persistence.", timestamp=datetime.now(UTC), cognition="PATHOS"
    )
    room.turns.append(turn)

    # 2. Action - Save
    save_debate_state(room, tmp_path)

    # Verify file exists on disk
    octave_file = tmp_path / f"{thread_id}.oct.md"
    assert octave_file.exists(), "OCTAVE file should exist"

    # Verify content looks like OCTAVE
    content = octave_file.read_text()
    assert "===DEBATE_TRANSCRIPT===" in content
    assert f'THREAD_ID::"{thread_id}"' in content

    # 3. Action - Load
    loaded_room = load_debate_state(thread_id, tmp_path)

    # 4. Assert
    assert loaded_room.thread_id == room.thread_id
    assert loaded_room.topic == room.topic
    assert loaded_room.mode == room.mode
    assert len(loaded_room.turns) == 1
    assert loaded_room.turns[0].role == "Wind"
    assert loaded_room.turns[0].content == "Testing persistence."
    # Verify hash chain was preserved (recalculated hash should match)
    assert loaded_room.turns[0].hash == turn.hash
