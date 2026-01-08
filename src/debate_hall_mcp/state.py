"""State management for debate-hall-mcp.

This module implements:
- DebateStatus and DebateMode enums (I1: Cognitive State Isolation)
- Turn model with hash chain support (I4: Verifiable Event Ledger)
- DebateRoom model with persistence
- JSON file-based persistence with hash chain integrity
- OCTAVE file-based persistence (Universal OCTAVE Storage)

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

# Environment variable for state directory (Issue #33)
STATE_DIR_ENV_VAR = "DEBATE_HALL_STATE_DIR"
DEFAULT_STATE_DIR = Path("./debates")

try:
    import octave_mcp
except ImportError:
    # Optional dependency handled where used
    octave_mcp: Any = None  # type: ignore[no-redef]


def find_project_root(start_path: Path | None = None) -> Path:
    """Find project root by searching for .git or pyproject.toml markers.

    Searches upward from start_path (or cwd) through parent directories
    until finding a .git directory or pyproject.toml file, which indicates
    the project root.

    This enables project-relative debate storage regardless of where the
    MCP server process starts.

    Args:
        start_path: Starting path for search (defaults to cwd)

    Returns:
        Path to project root, or start_path if no markers found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search current directory and all parents
    for directory in [current] + list(current.parents):
        if (directory / ".git").exists() or (directory / "pyproject.toml").exists():
            return directory

    # No project markers found, return starting path
    return start_path


def get_state_dir() -> Path:
    """Get state directory for debate persistence.

    Resolution order (Issue #33):
    1. DEBATE_HALL_STATE_DIR env var (if set and non-empty)
    2. Project root / "debates" (auto-detected via .git or pyproject.toml)
    3. ./debates (fallback for backwards compatibility)

    The project-relative detection (option 2) ensures debates live with
    the project they relate to, supporting version control and organization,
    while working consistently across different MCP clients.

    Returns:
        Path to state directory
    """
    # Priority 1: Explicit env var configuration
    env_value = os.environ.get(STATE_DIR_ENV_VAR, "")
    if env_value:
        return Path(env_value)

    # Priority 2: Project-relative detection
    try:
        project_root = find_project_root()
        return project_root / "debates"
    except Exception:
        # Fallback if project detection fails
        pass

    # Priority 3: Backwards-compatible default
    return DEFAULT_STATE_DIR


# Forward declaration via string type hint
def _parse_turn_from_octave(turn_str: str, _index: int) -> dict[str, Any]:
    """Parse a single turn string from OCTAVE format.

    Expected format: T{i}::{Role}[{Cognition}]@{Timestamp}::"{Content}"
    Or legacy: T{i}::{Role}[{Cognition}]::"{Content}"
    """
    # Simple regex parsing or string splitting
    # T1::Wind[PATHOS]@2024-01-01T00:00:00+00:00::"Content"
    try:
        parts = turn_str.split("::", 2)
        if len(parts) < 3:
            raise ValueError("Invalid turn format")

        role_part = parts[1]  # Role[Cognition]@Timestamp or Role[Cognition]
        content = parts[2].strip(",").strip('"')  # "Content", -> Content

        hash_val = ""  # Default to empty hash
        timestamp_str = None
        meta_part = role_part

        # Unescape content safely using custom logic to handle escape sequences
        # Naive replace chain fails on edge cases like "\\n" vs "\n"
        # We process backslashes from left to right.

        chars = []
        i = 0
        n = len(content)
        while i < n:
            c = content[i]
            if c == '\\' and i + 1 < n:
                next_c = content[i + 1]
                if next_c == '\\':
                    chars.append('\\')
                    i += 2
                elif next_c == '"':
                    chars.append('"')
                    i += 2
                elif next_c == 'n':
                    chars.append('\n')
                    i += 2
                elif next_c == 'r':
                    chars.append('\r')
                    i += 2
                elif next_c == 't':
                    chars.append('\t')
                    i += 2
                else:
                    # Unknown escape, keep literal
                    chars.append('\\')
                    i += 1
            else:
                chars.append(c)
                i += 1

        content = "".join(chars)

        # Parse Role[Cognition] and Timestamp and Hash
        # Format: Role[Cognition]...#Hash@Timestamp

        # Check for Timestamp @
        if "@" in role_part:
            meta_part, timestamp_str = role_part.split("@", 1)
            # Ensure ISO format upper case T (robustness against case normalization)
            timestamp_str = timestamp_str.replace("t", "T")

        # Check for Hash #
        if "#" in meta_part:
            meta_part, hash_val = meta_part.split("#", 1)

        # Parse Role[Cognition] or Role[Cognition|Agent|Model]
        if "[" in meta_part and "]" in meta_part:
            role = meta_part.split("[")[0]
            bracket_content = meta_part.split("[")[1].strip("]")

            # Handle Extended Identity: Cognition|Agent|Model
            if "|" in bracket_content:
                parts_identity = bracket_content.split("|")
                cognition = parts_identity[0] if parts_identity else None
                agent_role = parts_identity[1] if len(parts_identity) > 1 else None
                model = parts_identity[2] if len(parts_identity) > 2 else None

                # Treat empty strings as None
                if agent_role == "":
                    agent_role = None
                if model == "":
                    model = None
            else:
                cognition = bracket_content
                agent_role = None
                model = None
        else:
            role = meta_part
            cognition = None
            agent_role = None
            model = None

        # Clean up
        if cognition == "UNKNOWN":
            cognition = None

        # Timestamp fallback (should be present for valid chain reconstruction)
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(UTC)

        return {
            "role": role,
            "content": content,
            "cognition": cognition,
            "agent_role": agent_role,
            "model": model,
            "timestamp": timestamp,
            "hash": hash_val,  # Explicit hash from file
            "previous_hash": None,  # Will be linked
        }
    except Exception as e:
        raise ValueError(f"Failed to parse turn: {turn_str} | Error: {str(e)}") from e


def _load_from_octave(thread_id: str, state_dir: Path) -> "DebateRoom":
    """Load debate state from OCTAVE file."""
    octave_file = state_dir / f"{thread_id}.oct.md"
    lock_file = state_dir / f"{thread_id}.oct.lock"

    with _get_file_lock(lock_file), open(octave_file) as f:
        content = f.read()

    if octave_mcp is None:
        raise ImportError("octave-mcp required for OCTAVE storage")

    doc = octave_mcp.parse(content)

    # Extract Metadata
    meta = doc.meta or {}
    topic = meta.get("TOPIC", "Unknown Topic").strip('"')
    mode_str = meta.get("MODE", "fixed").lower()
    status_str = meta.get("STATUS", "active").lower()

    # Optional operational fields
    max_turns = int(meta.get("MAX_TURNS", 12))
    max_rounds = int(meta.get("MAX_ROUNDS", 4))
    strict_cognition = str(meta.get("STRICT_COGNITION", "false")).lower() == "true"
    octave_mode = str(meta.get("OCTAVE_MODE", "true")).lower() == "true"
    expected_next_role = meta.get("EXPECTED_NEXT_ROLE")
    if expected_next_role:
        expected_next_role = expected_next_role.strip('"')

    # Extract Turns
    turns_list = []
    # Find TURNS section
    turns_section = next((s for s in doc.sections if getattr(s, "key", "") == "TURNS"), None)

    if turns_section and hasattr(turns_section, "value"):
        # Handle ListValue (AST node) or raw list
        value = getattr(turns_section, "value", [])
        items = []
        if isinstance(value, list):
            items = value
        elif hasattr(value, "items"):
            items = getattr(value, "items", [])

        for i, item in enumerate(items):
            # Item might be "T1::Role...::Content" string
            turn_data = _parse_turn_from_octave(str(item), i)
            turns_list.append(turn_data)

    # Reconstruct Hash Chain and Verify Content Integrity
    prev_hash = None
    reconstructed_turns = []

    for i, turn_data in enumerate(turns_list):
        # 1. Create turn with calculated hash (model_post_init does this)
        turn = Turn(
            role=turn_data["role"],
            content=turn_data["content"],
            timestamp=turn_data["timestamp"],
            cognition=turn_data["cognition"],
            agent_role=turn_data.get("agent_role"),
            model=turn_data.get("model"),
            previous_hash=prev_hash
            # Note: We do NOT pass 'hash' here yet, so Turn calculates it from content
        )

        # 2. Verify calculated hash matches stored hash (Tamper Detection)
        stored_hash = turn_data.get("hash", "")
        if stored_hash and turn.hash != stored_hash:
            # DEBUG: Print inputs to hash calculation to identify mismatch
            # calc_inputs = f"{turn.role}|{turn.content}|{turn.timestamp.isoformat()}|{prev_hash or ''}"
            # print(f"DEBUG MISMATCH: Stored={stored_hash}, Calc={turn.hash}")
            # print(f"DEBUG INPUTS: {calc_inputs}")
            # print(f"DEBUG CONTENT: {turn.content!r}")

            raise ValueError(
                f"Hash mismatch at turn {i+1} ({turn.role}). "
                f"Content/Timestamp modified? "
                f"Stored: {stored_hash[:8]}..., Calculated: {turn.hash[:8]}... "
                f"(Check content escaping or timestamp precision)"
            )

        # 3. Use the valid hash for the next link
        prev_hash = turn.hash
        reconstructed_turns.append(turn)

    # Extract Synthesis
    synthesis = None
    synthesis_section = next(
        (s for s in doc.sections if getattr(s, "key", "") == "SYNTHESIS"), None
    )
    if synthesis_section:
        # Value might be string "Synthesis..." or null
        val = str(getattr(synthesis_section, "value", "null")).strip('"')
        if val.lower() != "null":
            synthesis = val

    # Extract Internal State Sections
    audit_log = []
    github_binding = None
    injected_context = []

    def get_field_content(key: str) -> str | None:
        # Check META first (octave-mcp usually merges top-level assignments here)
        if key in meta:
            val = meta[key]
            if isinstance(val, str):
                return val.strip('"')
            return str(val)

        # Check sections/assignments in body
        # octave-mcp v0.4+ puts assignments in doc.sections if they appear in body
        # We need to find Assignment node with key matching
        for section in doc.sections:
            # Check if it's an Assignment (has key and value)
            # Use getattr to be safe across versions or node types
            k = getattr(section, "key", None)
            if k == key:
                val = getattr(section, "value", None)
                if val is not None:
                    # Value might be StringValue, ListValue, or primitive
                    # If it's a quoted string, we want the raw content
                    return str(val).strip('"')
        return None

    audit_str = get_field_content("AUDIT_LOG")
    if audit_str:
        try:
            data = json.loads(audit_str)
            audit_log = [AuditEvent.model_validate(a) for a in data]
        except Exception:
            pass

    github_str = get_field_content("GITHUB_BINDING")
    if github_str:
        try:
            data = json.loads(github_str)
            github_binding = GitHubBinding.model_validate(data)
        except Exception:
            pass

    context_str = get_field_content("INJECTED_CONTEXT")
    if context_str:
        try:
            data = json.loads(context_str)
            injected_context = [InjectedContext.model_validate(c) for c in data]
        except Exception:
            pass

    return DebateRoom(
        thread_id=thread_id,
        topic=topic,
        mode=DebateMode(mode_str),
        status=DebateStatus(status_str),
        max_turns=max_turns,
        max_rounds=max_rounds,
        strict_cognition=strict_cognition,
        octave_mode=octave_mode,
        expected_next_role=expected_next_role,
        turns=reconstructed_turns,
        synthesis=synthesis,
        audit_log=audit_log,
        github_binding=github_binding,
        injected_context=injected_context,
    )


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

    FIXED = "fixed"  # Wind->Wall->Door->Wind...
    MEDIATED = "mediated"  # Orchestrator picks next role


class GitHubTargetType(str, Enum):
    """Valid GitHub target types for debate sync (Issue #15)."""

    DISCUSSION = "discussion"
    ISSUE = "issue"


class InjectionType(str, Enum):
    """Valid injection types for human interjection context (Issue #17)."""

    PATHOS = "pathos"  # Wind-related: emotion/intuition expansion
    ETHOS = "ethos"  # Wall-related: ethics/evidence addition
    LOGOS = "logos"  # Door-related: synthesis/clarification
    GENERAL = "general"  # Discussion body or general context


class InjectedContext(BaseModel):
    """Context injected from human GitHub comments into active debates (Issue #17).

    Enables human-in-the-loop participation by capturing GitHub comments
    and injecting them as context for debate agents.

    Fields:
    - source: Origin of the context (e.g., "github_comment")
    - comment_id: Unique identifier for the comment (node_id or issue comment id)
    - content: The comment body text
    - injection_type: Type of injection (pathos, ethos, logos, general)
    - processed_at: When the injection was processed (UTC)
    - author: Optional username of comment author
    - replied_to_turn: Optional turn index if this is a reply to a debate comment
    """

    source: str = Field(..., description="Origin of the context")
    comment_id: str = Field(..., description="Unique identifier for idempotency")
    content: str = Field(..., description="The comment body text")
    injection_type: str = Field(..., description="Type: pathos|ethos|logos|general")
    processed_at: datetime = Field(..., description="UTC timestamp of processing")
    author: str | None = Field(default=None, description="Username of comment author")
    replied_to_turn: int | None = Field(
        default=None, description="Turn index if reply to debate comment"
    )

    @field_validator("injection_type")
    @classmethod
    def validate_injection_type(cls, v: str) -> str:
        """Validate injection_type is a valid type."""
        valid_types = {t.value for t in InjectionType}
        if v not in valid_types:
            raise ValueError(f"Invalid injection_type '{v}': must be one of {sorted(valid_types)}")
        return v


class GitHubBinding(BaseModel):
    """GitHub binding for syncing debate turns to Discussion/Issue comments (Issue #15).

    Enables syncing debate turns to GitHub as formatted comments, supporting
    both Discussions (GraphQL API) and Issues (REST API).

    Fields:
    - repo: Repository in "owner/repo" format
    - target_id: GitHub node ID (Discussions) or issue number (Issues)
    - target_type: Type of target ("discussion" or "issue")
    - last_synced_turn: Index of last synced turn (0 = no turns synced)
    - comment_ids: List of posted comment node IDs for reference
    - discussion_number: For discussions, the human-readable discussion number for deep linking
    """

    repo: str = Field(..., description="Repository in owner/repo format")
    target_id: str = Field(..., description="GitHub node ID or issue number")
    target_type: str = Field(..., description="Target type: discussion or issue")
    last_synced_turn: int = Field(
        default=0, description="Index of last synced turn (0 = no turns synced)"
    )
    comment_ids: list[str] = Field(default_factory=list, description="Posted comment node IDs")
    discussion_number: int | None = Field(
        default=None,
        description="For discussions, the human-readable number for deep linking (e.g., 15 for discussions/15)",
    )

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        """Validate target_type is a valid GitHub target type."""
        valid_types = {t.value for t in GitHubTargetType}
        if v not in valid_types:
            raise ValueError(f"Invalid target_type '{v}': must be one of {sorted(valid_types)}")
        return v


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
    # Note: These fields are persisted and returned via get_debate(include_transcript=True).
    # Keep them bounded and simple to reduce accidental leakage / log injection risk.
    agent_role: str | None = Field(
        default=None, description="Operational agent role", max_length=128
    )
    model: str | None = Field(default=None, description="AI model identifier", max_length=128)
    cognition: str | None = Field(
        default=None, description="Cognitive archetype: PATHOS|ETHOS|LOGOS", max_length=16
    )

    @field_validator("agent_role", "model")
    @classmethod
    def validate_identity_string(cls, v: str | None) -> str | None:
        """Reject control characters and normalize empty strings."""
        if v is None:
            return None
        if v.strip() == "":
            return None
        # Keep metadata printable and ASCII-only to reduce formatting/log injection risk.
        # (This also rejects C0/C1 controls and other non-printable characters.)
        if (not v.isascii()) or (not v.isprintable()):
            raise ValueError("Identity metadata must be printable ASCII (no control characters)")
        return v

    @field_validator("cognition")
    @classmethod
    def validate_cognition(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v.strip() == "":
            return None
        allowed = {"PATHOS", "ETHOS", "LOGOS"}
        if v not in allowed:
            raise ValueError(f"Invalid cognition '{v}': must be one of {sorted(allowed)}")
        return v

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
    octave_mode: bool = Field(
        default=True,
        description="Enable OCTAVE-mode debates with skills-based compression and OCTAVE output default on close (Issue #26). Set False for JSON output.",
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
    github_binding: GitHubBinding | None = Field(
        default=None,
        description="Optional GitHub binding for syncing turns to Discussion/Issue (Issue #15)",
    )
    injected_context: list[InjectedContext] = Field(
        default_factory=list,
        description="Human-injected context from GitHub comments (Issue #17)",
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

    # Storage Strategy: OCTAVE vs JSON (Issue #29)
    # If octave_mode is enabled, save as OCTAVE format (.oct.md)
    # Otherwise, fallback to JSON (.json)

    if room.octave_mode:
        from debate_hall_mcp.octave_formatter import OutputMode, format_debate_as_octave

        # Determine file paths for OCTAVE
        state_file = state_dir / f"{room.thread_id}.oct.md"
        lock_file = state_dir / f"{room.thread_id}.oct.lock"

        # Generate content
        content = format_debate_as_octave(room, output_mode=OutputMode.FULL)

        # Acquire exclusive lock
        with _get_file_lock(lock_file):
            fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(state_file))
            except Exception:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise
        return

    # Fallback to JSON Persistence
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


def _verify_hash_chain_links(turns: list[Turn]) -> None:
    """Verify hash chain link integrity (Issue #58).

    Checks that each turn's previous_hash matches the prior turn's hash.
    This is a LINK verification only - does NOT re-compute content hashes.

    Critical for tombstone compatibility: Tombstoned turns have different
    content but preserve their original hash. Re-computing would break
    the chain for redacted turns.

    Args:
        turns: List of Turn objects to verify

    Raises:
        ValueError: If hash chain is broken with clear diagnostic message
    """
    if not turns:
        return  # Empty chain is valid

    # First turn must have null/empty previous_hash
    first_turn = turns[0]
    if first_turn.previous_hash is not None and first_turn.previous_hash != "":
        raise ValueError(
            f"Hash chain integrity error: First turn (index 0) has non-null previous_hash. "
            f"Expected: None/empty, Found: {first_turn.previous_hash[:16]}..."
        )

    # Verify each subsequent turn links to prior turn
    for i in range(1, len(turns)):
        current_turn = turns[i]
        prior_turn = turns[i - 1]

        if current_turn.previous_hash != prior_turn.hash:
            raise ValueError(
                f"Hash chain integrity error at turn index {i}: "
                f"previous_hash does not match prior turn's hash. "
                f"Expected: {prior_turn.hash[:16]}..., "
                f"Found: {current_turn.previous_hash[:16] if current_turn.previous_hash else 'None'}..."
            )


def load_debate_state(thread_id: str, state_dir: Path) -> DebateRoom:
    """Load debate room state from file (OCTAVE preferred, then JSON).

    Concurrency Control (Issue #48):
    Uses shared file lock to allow concurrent reads but block during writes.

    Hash Chain Verification (Issue #58):
    Verifies hash chain link integrity on load. Fails fast with clear error
    if chain is broken. Only verifies LINKS (previous_hash continuity),
    does NOT re-compute content hashes (tombstone compatibility).

    Security: Validates thread_id to prevent path traversal attacks.

    Raises:
        ValueError: If thread_id contains path-unsafe characters or hash chain broken
        FileNotFoundError: If state file doesn't exist.
    """
    # Security: Validate thread_id before using in file path
    _validate_thread_id_for_filesystem(thread_id)

    # Try loading OCTAVE format first (if present)
    octave_file = state_dir / f"{thread_id}.oct.md"

    if octave_file.exists():
        return _load_from_octave(thread_id, state_dir)

    # Fallback to JSON
    state_file = state_dir / f"{thread_id}.json"
    lock_file = state_dir / f"{thread_id}.lock"

    if not state_file.exists():
        # If explicitly checking for OCTAVE-only future
        if octave_file.exists():
            return _load_from_octave(thread_id, state_dir)
        raise FileNotFoundError(f"No state file found for thread {thread_id}")

    # Acquire lock for read operation (cross-platform via filelock)
    # Note: filelock only supports exclusive locks, but reads are fast so this is acceptable
    with _get_file_lock(lock_file), open(state_file) as f:
        data = json.load(f)

    room = DebateRoom.model_validate(data)

    # Verify hash chain integrity (Issue #58)
    _verify_hash_chain_links(room.turns)

    return room
