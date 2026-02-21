"""consult tool — Create advisory consultation sessions (Issue #177).

Phase 2 of the headless governance chat API (Issue #173).

Creates a two-party consultation session where a questioner asks an
advisor for guidance. Reuses existing tool functions (debate_init,
debate_turn, debate_pick) to avoid logic duplication.

Immutables Compliance:
- I1 (COGNITIVE_STATE_ISOLATION): State managed exclusively in Hall server
- I3 (FINITE_DIALECTIC_CLOSURE): max_turns enforced
- I4 (VERIFIABLE_EVENT_LEDGER): Hash chain maintained via debate_turn
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ulid import ULID

from debate_hall_mcp.state import (
    Participant,
    SessionType,
    get_state_dir,
    load_debate_state,
    save_debate_state,
)
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn

# Maximum length for role strings (consistent with tools/pick.py)
MAX_ROLE_LENGTH = 128


def _validate_role_string(role: str, field_name: str) -> None:
    """Validate a role string: non-empty, non-whitespace, printable ASCII, max 128 chars.

    Args:
        role: Role string to validate
        field_name: Name of the field for error messages

    Raises:
        ValueError: If role fails validation
    """
    if not role or role.strip() == "":
        raise ValueError(f"Invalid {field_name}: must be a non-empty, non-whitespace string")
    if len(role) > MAX_ROLE_LENGTH:
        raise ValueError(
            f"Invalid {field_name}: exceeds maximum length of {MAX_ROLE_LENGTH} characters"
        )
    if (not role.isascii()) or (not role.isprintable()):
        raise ValueError(f"Invalid {field_name}: must be printable ASCII (no control characters)")


def _generate_consult_thread_id(topic: str) -> str:
    """Generate a thread ID for a consultation session.

    Format: YYYY-MM-DD-{safe-topic-slug}-consult-{ulid8}

    Uses the same pattern as orchestrator._generate_thread_id but adds
    a 'consult' marker for identifiability.

    Args:
        topic: The consultation topic

    Returns:
        Thread ID string in date-first format
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    # Create a safe subject from the topic (lowercase, replace spaces with hyphens)
    subject = topic.lower().replace(" ", "-")
    # Keep only alphanumeric and hyphens, limit length
    safe_subject = "".join(c for c in subject if c.isalnum() or c == "-")[:30]
    # Add consult marker and ULID suffix for uniqueness
    ulid_suffix = str(ULID())[:8].lower()
    return f"{today}-{safe_subject}-consult-{ulid_suffix}"


def consult(
    topic: str,
    advisor_role: str,
    question: str,
    questioner_role: str = "Questioner",
    thread_id: str | None = None,
    context: str | None = None,
    max_turns: int = 6,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Create an advisory consultation session.

    Creates a two-party mediated session where a questioner asks an advisor
    for guidance. The question is recorded as the first turn, and the
    expected next speaker is set to the advisor.

    Args:
        topic: What the consultation is about
        advisor_role: Who to consult (e.g. "TMG", "CE")
        question: The specific question being asked
        questioner_role: Who is asking (default: "Questioner")
        thread_id: Custom thread ID (auto-generated if omitted)
        context: Additional context for the advisor
        max_turns: Consultation limit (I3 enforcement, default: 6)
        state_dir: Directory for state files (defaults to env/project detection)

    Returns:
        Dictionary with consultation session summary:
        - thread_id: Unique session identifier
        - status: "active"
        - session_type: "consultation"
        - question: The question asked
        - advisor_role: The advisor's role
        - questioner_role: The questioner's role
        - awaiting: The advisor_role (next expected speaker)
        - turn_count: 1 (the question turn)

    Raises:
        ValueError: If roles fail validation, roles are identical,
            topic/question empty, or thread_id already exists
    """
    # --- Validation ---
    _validate_role_string(advisor_role, "advisor_role")
    _validate_role_string(questioner_role, "questioner_role")

    if advisor_role == questioner_role:
        raise ValueError(
            f"advisor_role and questioner_role must be distinct (both are '{advisor_role}')"
        )

    if not topic or not topic.strip():
        raise ValueError("topic must be a non-empty string")

    if not question or not question.strip():
        raise ValueError("question must be a non-empty string")

    # --- Resolve state_dir ---
    if state_dir is None:
        state_dir = get_state_dir()

    # --- Generate thread_id if not provided ---
    if thread_id is None:
        thread_id = _generate_consult_thread_id(topic)

    # --- Create room via debate_init (reuse existing logic) ---
    # debate_init validates thread_id format and checks for duplicates
    try:
        debate_init(
            thread_id=thread_id,
            topic=topic,
            mode="mediated",
            max_turns=max_turns,
            state_dir=state_dir,
        )
    except FileExistsError as e:
        raise ValueError(f"thread_id already exists: {thread_id}") from e

    # --- Set session_type and participants on the room ---
    now = datetime.now(UTC)
    room = load_debate_state(thread_id, state_dir)
    room.session_type = SessionType.CONSULTATION
    room.participants = [
        Participant(role=questioner_role, joined_at=now),
        Participant(role=advisor_role, joined_at=now),
    ]
    save_debate_state(room, state_dir)

    # --- Build turn content (with optional context prefix) ---
    if context and context.strip():
        turn_content = f"[CONTEXT]\n{context}\n[/CONTEXT]\n\n{question}"
    else:
        turn_content = question

    # --- Record question as first turn ---
    # Need to pick the questioner first so debate_turn accepts the role
    debate_pick(thread_id=thread_id, role=questioner_role, state_dir=state_dir)
    debate_turn(
        thread_id=thread_id,
        role=questioner_role,
        content=turn_content,
        state_dir=state_dir,
    )

    # --- Set expected_next_role to advisor ---
    debate_pick(thread_id=thread_id, role=advisor_role, state_dir=state_dir)

    # --- Return response dict per contract ---
    return {
        "thread_id": thread_id,
        "status": "active",
        "session_type": "consultation",
        "question": question,
        "advisor_role": advisor_role,
        "questioner_role": questioner_role,
        "awaiting": advisor_role,
        "turn_count": 1,
    }
