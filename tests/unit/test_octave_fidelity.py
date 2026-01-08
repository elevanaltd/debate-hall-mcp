
from datetime import UTC, datetime

import pytest

from debate_hall_mcp.state import (
    DebateMode,
    DebateRoom,
    Turn,
    load_debate_state,
    save_debate_state,
)


class TestOctaveFidelity:
    """Critical fidelity tests for OCTAVE persistence."""

    def test_literal_escape_sequence_fidelity(self, tmp_path):
        """Regression test: literal \\n in content should not become a newline."""
        thread_id = "fidelity-escape-001"
        room = DebateRoom(
            thread_id=thread_id,
            topic="Escape Test",
            mode=DebateMode.FIXED,
            octave_mode=True
        )

        # Content with literal backslash-n (common in code snippets)
        # In Python: "\\n" is a string containing \ and n (2 chars)
        original_content = "Here is a regex: \\n and a backslash: \\"

        room.turns.append(Turn(
            role="Wind",
            content=original_content,
            timestamp=datetime.now(UTC)
        ))

        save_debate_state(room, tmp_path)
        loaded = load_debate_state(thread_id, tmp_path)

        # FAIL: Current implementation converts \\n to \n (newline)
        assert loaded.turns[0].content == original_content

    def test_hash_tampering_detection(self, tmp_path):
        """Regression test: Modifying content without updating hash should fail load."""
        thread_id = "fidelity-hash-001"
        room = DebateRoom(
            thread_id=thread_id,
            topic="Hash Test",
            mode=DebateMode.FIXED,
            octave_mode=True
        )

        room.turns.append(Turn(
            role="Wind",
            content="Original content",
            timestamp=datetime.now(UTC)
        ))

        save_debate_state(room, tmp_path)

        # Tamper with the file
        octave_file = tmp_path / f"{thread_id}.oct.md"
        content = octave_file.read_text()
        # Replace content but keep hash/timestamp intact
        tampered = content.replace("Original content", "Tampered content")
        octave_file.write_text(tampered)

        # FAIL: Current implementation only checks links, not content-hash match
        with pytest.raises(ValueError, match="Hash mismatch"):
            load_debate_state(thread_id, tmp_path)
