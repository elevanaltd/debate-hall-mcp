"""OCTAVE storage adapter for debate persistence.

Provides .oct.md file storage for DebateRoom objects.
Bridges between DebateRoom models and OCTAVE parser/serializer.
"""

import contextlib
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .octave_parser import parse_octave
from .octave_serializer import serialize_octave
from .state import (
    PATH_UNSAFE_PATTERNS,
    DebateMode,
    DebateRoom,
    DebateStatus,
    Turn,
)


class OctaveStorage:
    """Storage adapter for OCTAVE format debate files.

    Handles:
    - Save DebateRoom as .oct.md file
    - Load DebateRoom from .oct.md file
    - Atomic write pattern (temp file → rename)
    - Thread ID validation for filesystem safety
    """

    def __init__(self, state_dir: Path):
        """Initialize storage with state directory.

        Args:
            state_dir: Directory where .oct.md files will be stored
        """
        self.state_dir = state_dir

    def _validate_thread_id(self, thread_id: str) -> None:
        """Validate thread_id is safe for filesystem operations.

        Reuses validation logic from state.py to ensure consistency.

        Args:
            thread_id: Thread identifier to validate

        Raises:
            ValueError: If thread_id contains path-unsafe characters
        """
        for pattern in PATH_UNSAFE_PATTERNS:
            if pattern in thread_id:
                raise ValueError(
                    f"Invalid thread_id '{thread_id}': contains path-unsafe characters"
                )

    def _get_octave_path(self, thread_id: str) -> Path:
        """Get path to .oct.md file for thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Path to .oct.md file
        """
        return self.state_dir / f"{thread_id}.oct.md"

    def _room_to_dict(self, room: DebateRoom) -> dict[str, Any]:
        """Convert DebateRoom to dictionary for OCTAVE serialization.

        Args:
            room: DebateRoom to convert

        Returns:
            Dictionary with meta, turns, and synthesis sections

        Note:
            Speaker identity metadata (agent_role, model) are stored in META
            section to preserve them across save/load cycles, even though they're
            not part of the core OCTAVE turn format.
        """
        # META section
        meta = {
            "thread_id": room.thread_id,
            "topic": room.topic,
            "mode": room.mode.value,
            "status": room.status.value,
            "max_turns": room.max_turns,
            "max_rounds": room.max_rounds,
            "strict_cognition": room.strict_cognition,
            "octave_preamble": room.octave_preamble,
            "octave_mode": room.octave_mode,
        }

        if room.expected_next_role is not None:
            meta["expected_next_role"] = room.expected_next_role

        # Store speaker identity metadata in META section for preservation
        # Format: turn_N_agent_role, turn_N_model
        for i, turn in enumerate(room.turns):
            if turn.agent_role:
                meta[f"turn_{i}_agent_role"] = turn.agent_role
            if turn.model:
                meta[f"turn_{i}_model"] = turn.model

        # TURNS section - convert Turn objects to dicts
        turns = []
        for turn in room.turns:
            # Cognition defaults to "PATHOS" if not set (must be valid value)
            cognition = turn.cognition if turn.cognition else "PATHOS"

            turn_dict = {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
                "content_hash": turn.hash,  # Use turn.hash as content_hash for OCTAVE
                "cognition": cognition,
            }
            turns.append(turn_dict)

        # SYNTHESIS section (optional)
        synthesis = None
        if room.synthesis:
            synthesis = {
                "content": room.synthesis,
                "status": room.status.value,
            }

        return {
            "meta": meta,
            "turns": turns,
            "synthesis": synthesis,
        }

    def _dict_to_room(self, data: dict[str, Any]) -> DebateRoom:
        """Convert parsed OCTAVE dictionary to DebateRoom.

        Args:
            data: Parsed OCTAVE data with meta, turns, synthesis

        Returns:
            DebateRoom instance

        Note:
            Restores speaker identity metadata (agent_role, model) from META
            section where they were stored during serialization.
        """
        meta = data["meta"]
        turns_data = data.get("turns", [])
        synthesis_data = data.get("synthesis")

        # Convert turn dicts to Turn objects
        turns: list[Turn] = []
        for i, turn_dict in enumerate(turns_data):
            # Parse timestamp
            timestamp_str = turn_dict["timestamp"]
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Determine previous_hash (None for first turn, previous turn's hash otherwise)
            previous_hash = None if i == 0 else turns[i - 1].hash

            # Restore speaker identity metadata from META section
            agent_role = meta.get(f"turn_{i}_agent_role")
            model = meta.get(f"turn_{i}_model")

            # Create Turn object
            turn = Turn(
                role=turn_dict["role"],
                content=turn_dict["content"],
                timestamp=timestamp,
                previous_hash=previous_hash,
                hash=turn_dict["content_hash"],  # Preserve original hash from OCTAVE
                agent_role=agent_role,
                model=model,
                cognition=turn_dict.get("cognition"),
            )
            turns.append(turn)

        # Extract synthesis if present
        synthesis = None
        if synthesis_data:
            synthesis = synthesis_data.get("content")

        # Create DebateRoom
        # Note: audit_log, github_binding, and injected_context are NOT preserved
        # in OCTAVE format as they're operational metadata, not dialectic content.
        # This is an intentional design decision - OCTAVE focuses on debate structure.
        return DebateRoom(
            thread_id=meta["thread_id"],
            topic=meta["topic"],
            mode=DebateMode(meta["mode"]),
            status=DebateStatus(meta["status"]),
            max_turns=meta["max_turns"],
            max_rounds=meta["max_rounds"],
            strict_cognition=meta.get("strict_cognition", False),
            octave_preamble=meta.get("octave_preamble", True),
            octave_mode=meta.get("octave_mode", True),
            expected_next_role=meta.get("expected_next_role"),
            turns=turns,
            synthesis=synthesis,
            # Operational metadata intentionally excluded from OCTAVE format:
            # audit_log=[], github_binding=None, injected_context=[]
        )

    def exists(self, thread_id: str) -> bool:
        """Check if .oct.md file exists for thread.

        Args:
            thread_id: Thread identifier

        Returns:
            True if .oct.md file exists, False otherwise
        """
        self._validate_thread_id(thread_id)
        return self._get_octave_path(thread_id).exists()

    def save(self, room: DebateRoom) -> None:
        """Save DebateRoom as .oct.md file using atomic write pattern.

        Write pattern:
        1. Validate thread_id for filesystem safety
        2. Convert DebateRoom to dictionary
        3. Serialize to OCTAVE format
        4. Write to temporary file
        5. fsync() to ensure data is on disk
        6. Atomically rename temp file to final location

        This prevents corruption from interrupted writes.

        Args:
            room: DebateRoom to save

        Raises:
            ValueError: If thread_id contains path-unsafe characters
            OSError: If atomic rename fails
        """
        # Security: Validate thread_id
        self._validate_thread_id(room.thread_id)

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict and serialize
        data = self._room_to_dict(room)
        octave_content = serialize_octave(data)

        # Get target file path
        octave_file = self._get_octave_path(room.thread_id)

        # Atomic write: temp file → rename
        fd, tmp_path = tempfile.mkstemp(dir=self.state_dir, suffix=".tmp")
        try:
            # Write to temp file with fsync for durability
            with os.fdopen(fd, "w") as f:
                f.write(octave_content)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk

            # Atomic replace - overwrites existing file
            os.replace(tmp_path, str(octave_file))
        except Exception:
            # Clean up temp file on failure
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def load(self, thread_id: str) -> DebateRoom:
        """Load DebateRoom from .oct.md file.

        Args:
            thread_id: Thread identifier

        Returns:
            DebateRoom instance

        Raises:
            ValueError: If thread_id contains path-unsafe characters
            FileNotFoundError: If .oct.md file doesn't exist
        """
        # Security: Validate thread_id
        self._validate_thread_id(thread_id)

        # Get file path
        octave_file = self._get_octave_path(thread_id)

        # Check file exists
        if not octave_file.exists():
            raise FileNotFoundError(f"No OCTAVE file found for thread {thread_id}")

        # Read and parse OCTAVE content
        content = octave_file.read_text()
        data = parse_octave(content)

        # Convert to DebateRoom
        return self._dict_to_room(data)
