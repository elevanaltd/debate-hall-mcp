"""run_debate tool - Auto-orchestration entry point (Phase 3, ADR-0002).

This module implements:
- run_debate: MCP tool for automated Wind/Wall/Door debates

The tool wraps DebateOrchestrator, providing tier configuration loading
and state directory resolution automatically.
"""

from typing import Any

from debate_hall_mcp.config import load_tier_config
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import create_provider  # noqa: F401 - used in patch
from debate_hall_mcp.state import get_state_dir


async def run_debate(
    topic: str,
    tier: str = "standard",
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Run an automated Wind/Wall/Door debate.

    This is the main entry point for auto-orchestration. It:
    1. Loads tier configuration
    2. Creates an orchestrator
    3. Runs the debate loop (Wind -> Wall -> Door)
    4. Returns the result

    Args:
        topic: The debate topic to explore
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
        KeyError: If tier configuration is not found
        Exception: If provider fails during debate
    """
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
