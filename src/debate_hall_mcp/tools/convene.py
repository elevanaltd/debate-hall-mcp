"""convene tool — Assemble a committee for group decisions (Issue #178).

Phase 3 of the governance chat API epic (#173).

Creates a committee session where multiple agents deliberate on a topic.
Reuses existing debate_init and debate_turn for room creation and turn recording.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): max_turns enforced via DebateRoom
- I4 (VERIFIABLE_EVENT_LEDGER): Hash chain maintained via debate_turn

Contract: docs/173-governance-chat-api-contract.md — Tool 2: convene
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ulid import ULID

from debate_hall_mcp.state import (
    CommitteeMetadata,
    Participant,
    SessionType,
    get_state_dir,
    load_debate_state,
    save_debate_state,
)
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import _validate_role_string
from debate_hall_mcp.tools.turn import debate_turn

# Valid decision types for committee sessions
VALID_DECISION_TYPES = {"go_nogo", "vote", "review"}


def _generate_thread_id(topic: str) -> str:
    """Generate a thread ID in date-first format.

    Format: YYYY-MM-DD-safe-topic-slug-ulid8

    Same pattern as DebateOrchestrator._generate_thread_id.

    Args:
        topic: The committee topic (used to derive subject slug)

    Returns:
        Thread ID string in date-first format
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    subject = topic.lower().replace(" ", "-")
    safe_subject = "".join(c for c in subject if c.isalnum() or c == "-")[:30]
    ulid_suffix = str(ULID())[:8].lower()
    return f"{today}-{safe_subject}-{ulid_suffix}"


def convene(
    topic: str,
    members: list[str],
    brief: str,
    chair_role: str = "Chair",
    decision_type: str = "review",
    thread_id: str | None = None,
    context: str | None = None,
    max_turns: int = 12,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Assemble a committee of agents for a group decision.

    Creates a mediated committee session, registers participants,
    sets up committee metadata for tracking, and records the brief
    as the first turn.

    Args:
        topic: What the committee is deciding
        members: Committee member roles (at least 1, no duplicates)
        brief: The brief/description for the committee
        chair_role: Who chairs the committee (default: "Chair")
        decision_type: "go_nogo" | "vote" | "review" (default: "review")
        thread_id: Custom thread ID (auto-generated if omitted)
        context: Additional context for the committee
        max_turns: Committee turn limit (I3 enforcement, default: 12)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with committee session summary:
        - thread_id: Unique thread identifier
        - status: "active"
        - session_type: "committee"
        - decision_type: The decision type
        - chair_role: Who chairs
        - members: List of member roles
        - awaiting: Members who haven't responded
        - turn_count: Current turn count (1 after brief)

    Raises:
        ValueError: If validation fails (see contract for rules)
        FileExistsError: If thread_id already exists
    """
    # Default state directory
    if state_dir is None:
        state_dir = get_state_dir()

    # --- Validation ---

    # Validate topic
    if not topic or not topic.strip():
        raise ValueError("Topic must be a non-empty string")

    # Validate brief
    if not brief or not brief.strip():
        raise ValueError("Brief must be a non-empty string")

    # Validate decision_type
    if decision_type not in VALID_DECISION_TYPES:
        raise ValueError(
            f"Invalid decision_type '{decision_type}': "
            f"must be one of {sorted(VALID_DECISION_TYPES)}"
        )

    # Validate chair_role
    _validate_role_string(chair_role)

    # Validate members
    if not members:
        raise ValueError("Committee must have at least 1 member")

    for member in members:
        _validate_role_string(member)

    # Check for duplicate members
    if len(members) != len(set(members)):
        raise ValueError("Duplicate members are not allowed")

    # Chair must not appear in members
    if chair_role in members:
        raise ValueError(f"Chair role '{chair_role}' must not appear in members list")

    # --- Generate thread_id if not provided ---
    if thread_id is None:
        thread_id = _generate_thread_id(topic)

    # --- Create room via debate_init ---
    debate_init(
        thread_id=thread_id,
        topic=topic,
        mode="mediated",
        max_turns=max_turns,
        state_dir=state_dir,
    )

    # --- Load room to set committee-specific fields ---
    room = load_debate_state(thread_id, state_dir)

    # Set session type
    room.session_type = SessionType.COMMITTEE

    # Set participants (chair + all members)
    now = datetime.now(UTC)
    room.participants = [Participant(role=chair_role, joined_at=now)]
    for member in members:
        room.participants.append(Participant(role=member, joined_at=now))

    # Set committee metadata
    room.committee_metadata = CommitteeMetadata(
        decision_type=decision_type,
        members=list(members),
        responses={},
        awaiting=list(members),
    )

    # Save updated room state before recording turn
    save_debate_state(room, state_dir)

    # --- Record brief as first turn ---
    # Build turn content with optional context prefix
    turn_content = brief
    if context:
        turn_content = f"[CONTEXT]\n{context}\n[/CONTEXT]\n\n{brief}"

    # Use debate_pick + debate_turn to record the brief
    # In mediated mode, we need to pick the chair first
    from debate_hall_mcp.tools.pick import debate_pick

    debate_pick(thread_id=thread_id, role=chair_role, state_dir=state_dir)
    debate_turn(
        thread_id=thread_id,
        role=chair_role,
        content=turn_content,
        state_dir=state_dir,
    )

    # --- Build response ---
    return {
        "thread_id": thread_id,
        "status": "active",
        "session_type": "committee",
        "decision_type": decision_type,
        "chair_role": chair_role,
        "members": list(members),
        "awaiting": list(members),
        "turn_count": 1,
    }
