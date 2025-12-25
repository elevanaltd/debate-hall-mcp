"""State management for debate-hall-mcp.

This module implements:
- DebateStatus and DebateMode enums (I1: Cognitive State Isolation)
- Turn model with hash chain support (I4: Verifiable Event Ledger)
- DebateRoom model with persistence
- JSON file-based persistence with hash chain integrity

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively by Hall server
- I4 (VERIFIABLE_EVENT_LEDGER): Append-only hash chain for turn history
"""

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DebateStatus(str, Enum):
    """Status of a debate room (I3: Finite Dialectic Closure)."""

    ACTIVE = "active"
    SYNTHESIS = "synthesis"
    STALEMATE = "stalemate"
    EXHAUSTION = "exhaustion"
    FORCE_CLOSED = "force_closed"


class DebateMode(str, Enum):
    """Debate orchestration mode."""

    FIXED = "fixed"  # Wind→Wall→Door→Wind...
    MEDIATED = "mediated"  # Orchestrator picks next role


class Turn(BaseModel):
    """A single turn in the debate with hash chain integrity (I4).

    Each turn is cryptographically linked to the previous turn via hash,
    creating an append-only, tamper-evident ledger.

    Speaker Identity Fields (Issue #4):
    - agent_role: Operational agent role (e.g., "implementation-lead")
    - model: AI model identifier (e.g., "claude-opus-4-5")
    - cognition: Cognitive archetype (PATHOS|ETHOS|LOGOS)

    These fields are audit metadata and are NOT included in hash calculation,
    preserving dialectic integrity while enabling speaker attribution.
    """

    role: str = Field(..., description="Agent role (Wind, Wall, Door)")
    content: str = Field(..., description="Turn content (OCTAVE format)")
    timestamp: datetime = Field(..., description="UTC timestamp of turn")
    previous_hash: str | None = Field(
        None, description="Hash of previous turn (None for first turn)"
    )
    hash: str = Field(default="", description="SHA-256 hash of this turn")

    # Speaker identity metadata (Issue #4) - excluded from hash chain
    agent_role: str | None = Field(None, description="Operational agent role")
    model: str | None = Field(None, description="AI model identifier")
    cognition: str | None = Field(None, description="Cognitive archetype: PATHOS|ETHOS|LOGOS")

    def model_post_init(self, __context: Any) -> None:
        """Calculate hash after model initialization."""
        if not self.hash:
            self.hash = calculate_turn_hash(
                self.role, self.content, self.timestamp, self.previous_hash
            )

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if isinstance(v, str):
            # Parse ISO format string
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=UTC)
        return v


class DebateRoom(BaseModel):
    """A debate room instance with state and history.

    Manages:
    - Thread identification
    - Debate topic and mode
    - Current status
    - Resource limits (I3: Finite Dialectic Closure)
    - Turn history with hash chain (I4: Verifiable Event Ledger)
    """

    thread_id: str = Field(..., description="Unique thread identifier")
    topic: str = Field(..., description="Debate topic")
    mode: DebateMode = Field(..., description="Orchestration mode")
    status: DebateStatus = Field(default=DebateStatus.ACTIVE, description="Current debate status")
    max_turns: int = Field(default=12, description="Maximum turns allowed (I3)")
    max_rounds: int = Field(default=4, description="Maximum rounds allowed (I3)")
    turns: list[Turn] = Field(default_factory=list, description="Turn history")
    synthesis: str | None = Field(
        default=None, description="Final Door synthesis (if status=SYNTHESIS)"
    )


def calculate_turn_hash(
    role: str, content: str, timestamp: datetime, previous_hash: str | None
) -> str:
    """Calculate SHA-256 hash for a turn (I4 compliance).

    Hash includes:
    - Role
    - Content
    - Timestamp (ISO format)
    - Previous hash (or empty string if None)

    This creates a cryptographic chain where each turn depends on all
    previous turns, making history tampering evident.
    """
    timestamp_str = timestamp.isoformat()
    prev_hash_str = previous_hash or ""

    data = f"{role}|{content}|{timestamp_str}|{prev_hash_str}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def save_debate_state(room: DebateRoom, state_dir: Path) -> None:
    """Save debate room state to JSON file.

    File location: {state_dir}/{thread_id}.json

    Format: Pydantic model JSON with hash chain preserved.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{room.thread_id}.json"

    # Serialize with Pydantic for proper datetime handling
    with open(state_file, "w") as f:
        f.write(room.model_dump_json(indent=2))


def load_debate_state(thread_id: str, state_dir: Path) -> DebateRoom:
    """Load debate room state from JSON file.

    Raises:
        FileNotFoundError: If state file doesn't exist.
    """
    state_file = state_dir / f"{thread_id}.json"

    if not state_file.exists():
        raise FileNotFoundError(f"No state file found for thread {thread_id}")

    with open(state_file) as f:
        data = json.load(f)

    return DebateRoom.model_validate(data)
