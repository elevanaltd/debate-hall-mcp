"""run_debate and resume_debate tools - Auto-orchestration (Phase 3 & 4, ADR-0002).

This module implements:
- run_debate: MCP tool for automated Wind/Wall/Door debates
- resume_debate: MCP tool for resuming PAUSED debates

The tools wrap DebateOrchestrator, providing tier configuration loading
and state directory resolution automatically.

CE Review Mitigations (Phase 3):
- M4: Input validation at tool boundary (topic and thread_id)

Phase 4 Additions:
- resume_debate: Resumes debates from PAUSED status after failures
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.config import load_tier_config
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import create_provider  # noqa: F401 - used in patch
from debate_hall_mcp.state import (
    DebateStatus,
    _validate_thread_id_for_filesystem,
    get_state_dir,
    load_debate_state,
)

# M4: Maximum topic length (reasonable limit for debate topics)
MAX_TOPIC_LENGTH = 1000


def _validate_topic(topic: str) -> None:
    """Validate topic input (M4: CE Review mitigation).

    Args:
        topic: The debate topic to validate

    Raises:
        ValueError: If topic is empty, whitespace-only, or too long
    """
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic exceeds maximum length of {MAX_TOPIC_LENGTH} characters")


async def run_debate(
    topic: str,
    tier: str = "standard",
    thread_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Run an automated Wind/Wall/Door debate.

    This is the main entry point for auto-orchestration. It:
    1. Validates inputs (M4: CE Review)
    2. Loads tier configuration
    3. Creates an orchestrator
    4. Runs the debate loop (Wind -> Wall -> Door)
    5. Returns the result

    Args:
        topic: The debate topic to explore (1-1000 chars, non-empty)
        tier: Tier configuration name (default: "standard")
        thread_id: Optional thread ID (auto-generated if not provided)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate result:
        - thread_id: Unique debate thread identifier
        - topic: The debate topic
        - status: Final status (synthesis, stalemate, etc.)
        - turn_count: Number of turns completed
        - synthesis: Door's final synthesis (if status=synthesis)

    Raises:
        ValueError: If topic is invalid or thread_id contains unsafe chars (M4)
        KeyError: If tier configuration is not found
        Exception: If provider fails during debate
    """
    # M4: Validate inputs at tool boundary
    _validate_topic(topic)
    if thread_id is not None:
        _validate_thread_id_for_filesystem(thread_id)

    # Load tier configuration
    tier_config = load_tier_config(tier)

    # Get state directory
    if state_dir is None:
        state_dir = get_state_dir()

    # Create orchestrator
    orchestrator = DebateOrchestrator(tier_config, state_dir)

    # Run debate
    result = await orchestrator.run(topic=topic, thread_id=thread_id)

    # Return as dictionary
    return {
        "thread_id": result.thread_id,
        "topic": result.topic,
        "status": result.status,
        "turn_count": result.turn_count,
        "synthesis": result.synthesis,
    }


async def resume_debate(
    thread_id: str,
    tier: str = "standard",
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Resume a PAUSED debate from where it left off.

    This tool allows resuming debates that were paused due to failures
    (provider timeouts, errors, etc.) during auto-orchestration.

    The resume logic:
    1. Validates thread_id and loads debate state
    2. Validates debate is in PAUSED status
    3. Determines resume point from turn count
    4. Continues orchestration (consensus loop if enabled)
    5. Returns the final result

    Args:
        thread_id: The thread ID of the paused debate
        tier: Tier configuration name (default: "standard")
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with debate result (same format as run_debate):
        - thread_id: Unique debate thread identifier
        - topic: The debate topic
        - status: Final status (synthesis, stalemate, etc.)
        - turn_count: Number of turns completed
        - synthesis: Door's final synthesis (if status=synthesis)

    Raises:
        ValueError: If thread_id contains unsafe chars (M4)
        FileNotFoundError: If debate doesn't exist
        ValueError: If debate is not in PAUSED status
        KeyError: If tier configuration is not found
        Exception: If provider fails during resumption
    """
    # M4: Validate thread_id at tool boundary
    _validate_thread_id_for_filesystem(thread_id)

    # Get state directory
    if state_dir is None:
        state_dir = get_state_dir()

    # Validate debate exists and is PAUSED before creating orchestrator
    room = load_debate_state(thread_id, state_dir)
    if room.status != DebateStatus.PAUSED:
        raise ValueError(
            f"Cannot resume debate with status '{room.status.value}': "
            f"only PAUSED debates can be resumed"
        )

    # Load tier configuration
    tier_config = load_tier_config(tier)

    # Create orchestrator
    orchestrator = DebateOrchestrator(tier_config, state_dir)

    # Resume debate
    result = await orchestrator.resume(thread_id=thread_id)

    # Return as dictionary (same format as run_debate)
    return {
        "thread_id": result.thread_id,
        "topic": result.topic,
        "status": result.status,
        "turn_count": result.turn_count,
        "synthesis": result.synthesis,
    }
