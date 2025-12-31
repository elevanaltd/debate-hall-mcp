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

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import BaseModel, Field, field_validator

# Security: Patterns that indicate path traversal or directory injection
PATH_UNSAFE_PATTERNS = ["..", "/", "\\"]


class DebateStatus(str, Enum):
    """Status of a debate room (I3: Finite Dialectic Closure)."""

    ACTIVE = "active"
    SYNTHESIS = "synthesis"
    STALEMATE = "stalemate"
    EXHAUSTION = "exhaustion"
    FORCE_CLOSED = "force_closed"


class AuditAction(str, Enum):
    """Type of administrative action for audit trail (Issue #40)."""

    FORCE_CLOSE = "force_close"
    TOMBSTONE = "tombstone"


class AuditEvent(BaseModel):
    """An audit event recording administrative actions (Issue #40).

    Provides immutable audit trail for:
    - Force close operations (I5: Sovereign Safety Override)
    - Tombstone operations (I4: Verifiable Event Ledger)

    Fields:
    - action: Type of administrative action
    - reason: Human-readable reason for the action
    - timestamp: When the action occurred (UTC)
    - actor: Optional identifier of who/what performed the action
    - turn_index: For tombstone actions, which turn was affected
    - original_content_hash: For tombstone actions, SHA-256 of original content
    """

    action: AuditAction = Field(..., description="Type of administrative action")
    reason: str = Field(..., description="Reason for the action")
    timestamp: datetime = Field(..., description="UTC timestamp of action")
    actor: str | None = Field(default=None, description="Actor identifier (agent/admin)")
    turn_index: int | None = Field(default=None, description="Turn index (for tombstone)")
    original_content_hash: str | None = Field(
        default=None, description="SHA-256 hash of original content before tombstone"
    )


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
        default=None, description="Hash of previous turn (None for first turn)"
    )
    hash: str = Field(default="", description="SHA-256 hash of this turn")

    # Speaker identity metadata (Issue #4) - excluded from hash chain
    agent_role: str | None = Field(default=None, description="Operational agent role")
    model: str | None = Field(default=None, description="AI model identifier")
    cognition: str | None = Field(
        default=None, description="Cognitive archetype: PATHOS|ETHOS|LOGOS"
    )

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
    - Cognition enforcement policy (behavioral firewall)
    - Mediated mode role enforcement (Issue #37)
    """

    thread_id: str = Field(
        ...,
        description="Unique thread identifier in date-first format (YYYY-MM-DD-subject)",
    )
    topic: str = Field(..., description="Debate topic")
    mode: DebateMode = Field(..., description="Orchestration mode")
    status: DebateStatus = Field(default=DebateStatus.ACTIVE, description="Current debate status")
    max_turns: int = Field(default=12, description="Maximum turns allowed (I3)")
    max_rounds: int = Field(default=4, description="Maximum rounds allowed (I3)")
    strict_cognition: bool = Field(
        default=False,
        description="If True, BLOCK-level cognition violations reject turns (behavioral firewall)",
    )
    octave_preamble: bool = Field(
        default=True,
        description="If True, prepend System turn with OCTAVE format guidance to transcripts (view-layer only)",
    )
    expected_next_role: str | None = Field(
        default=None,
        description="Expected next speaker role in mediated mode (set by debate_pick, cleared after turn)",
    )
    turns: list[Turn] = Field(default_factory=list, description="Turn history")
    synthesis: str | None = Field(
        default=None, description="Final Door synthesis (if status=SYNTHESIS)"
    )
    audit_log: list[AuditEvent] = Field(
        default_factory=list,
        description="Immutable audit trail for administrative actions (Issue #40)",
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


def _validate_thread_id_for_filesystem(thread_id: str) -> None:
    """Validate thread_id is safe for filesystem operations.

    Security: Rejects path traversal sequences and directory separators
    to prevent file system injection attacks.

    Args:
        thread_id: Thread identifier to validate

    Raises:
        ValueError: If thread_id contains path-unsafe characters
    """
    for pattern in PATH_UNSAFE_PATTERNS:
        if pattern in thread_id:
            raise ValueError(f"Invalid thread_id '{thread_id}': contains path-unsafe characters")


def _get_file_lock(lock_file: Path) -> FileLock:
    """Get a cross-platform file lock (Issue #48 - Concurrency Control).

    Uses filelock library for cross-platform file locking.
    Works on POSIX (Linux, macOS) and Windows.

    Args:
        lock_file: Path to the lock file (typically {thread_id}.lock)

    Returns:
        FileLock instance that can be used as context manager

    Note:
        filelock uses exclusive locks only. For our use case this is fine
        since reads are fast and contention is expected to be low.
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_file))


def save_debate_state(room: DebateRoom, state_dir: Path) -> None:
    """Save debate room state to JSON file using atomic write pattern.

    File location: {state_dir}/{thread_id}.json

    Format: Pydantic model JSON with hash chain preserved.

    Concurrency Control (Issue #48):
    Uses file-based locking to prevent race conditions during concurrent access.

    Atomic Write Pattern (Issue #39 - Crash Recovery):
    1. Acquire exclusive file lock
    2. Write to temporary file in the same directory
    3. Call fsync() to ensure data is flushed to disk
    4. Atomically rename temp file to final location
    5. Release lock and clean up temp file on any failure

    This prevents data corruption from interrupted writes and concurrent access.

    Security: Validates thread_id to prevent path traversal attacks.

    Raises:
        ValueError: If thread_id contains path-unsafe characters
        OSError: If atomic rename fails (original file preserved)
    """
    # Security: Validate thread_id before using in file path
    _validate_thread_id_for_filesystem(room.thread_id)

    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{room.thread_id}.json"
    lock_file = state_dir / f"{room.thread_id}.lock"

    # Acquire exclusive lock for write operation (cross-platform via filelock)
    with _get_file_lock(lock_file):
        # Create temp file in same directory (required for atomic rename on same filesystem)
        fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp")
        try:
            # Write to temp file with fsync for durability
            with os.fdopen(fd, "w") as f:
                f.write(room.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk before rename

            # Atomic replace - works cross-platform (POSIX and Windows)
            # os.replace is atomic on same filesystem and overwrites existing file
            os.replace(tmp_path, str(state_file))
        except Exception:
            # Clean up temp file on any failure - preserve original file
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)  # May not exist if mkstemp failed
            raise


def load_debate_state(thread_id: str, state_dir: Path) -> DebateRoom:
    """Load debate room state from JSON file.

    Concurrency Control (Issue #48):
    Uses shared file lock to allow concurrent reads but block during writes.

    Security: Validates thread_id to prevent path traversal attacks.

    Raises:
        ValueError: If thread_id contains path-unsafe characters
        FileNotFoundError: If state file doesn't exist.
    """
    # Security: Validate thread_id before using in file path
    _validate_thread_id_for_filesystem(thread_id)

    state_file = state_dir / f"{thread_id}.json"
    lock_file = state_dir / f"{thread_id}.lock"

    if not state_file.exists():
        raise FileNotFoundError(f"No state file found for thread {thread_id}")

    # Acquire lock for read operation (cross-platform via filelock)
    # Note: filelock only supports exclusive locks, but reads are fast so this is acceptable
    with _get_file_lock(lock_file), open(state_file) as f:
        data = json.load(f)

    return DebateRoom.model_validate(data)
