"""run_debate tool - Auto-orchestration entry point (Phase 3, ADR-0002).

This module implements:
- run_debate: MCP tool for automated Wind/Wall/Door debates

The tool wraps DebateOrchestrator, providing tier configuration loading
and state directory resolution automatically.

CE Review Mitigations (Phase 3):
- M4: Input validation at tool boundary (topic and thread_id)
"""

from typing import Any

from debate_hall_mcp.config import load_tier_config
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import create_provider  # noqa: F401 - used in patch
from debate_hall_mcp.state import _validate_thread_id_for_filesystem, get_state_dir

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
