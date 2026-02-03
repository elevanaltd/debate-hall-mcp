"""Layer 3 decision tools - Decision extraction and resolution.

Provides:
- extract_decision_record: Extracts DecisionRecord from a closed debate
- resolve_question: High-level API combining run_debate + extract_decision_record

Part of the "Cognitive Notary" Layer 3 query capabilities.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from debate_hall_mcp.decision import extract_decision_record as _extract
from debate_hall_mcp.state import get_state_dir, load_debate_state
from debate_hall_mcp.tools.orchestrate import run_debate


def extract_decision_record(
    thread_id: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Extract a DecisionRecord from a closed debate.

    The "Cognitive Notary" product - a verified record that can be
    indexed, searched, and cited by future decision-making agents.

    Args:
        thread_id: Thread identifier of closed debate
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with DecisionRecord fields:
        - thread_id, topic, decided_at (identity)
        - synthesis, decision_hash, status (outcome)
        - wind_perspectives, wall_constraints, door_refinements (rationale)
        - consensus_reached, consensus_votes, refinement_count (validation)
        - extracted_at, source_hash, turn_count (provenance)

    Raises:
        FileNotFoundError: If thread doesn't exist
        ValueError: If debate is not closed (ACTIVE or PAUSED status)
    """
    if state_dir is None:
        state_dir = get_state_dir()

    room = load_debate_state(thread_id, state_dir)
    record = _extract(room)

    # Convert to dict for MCP return
    return record.model_dump(mode="json")


async def resolve_question(
    topic: str,
    tier: str = "standard",
    thread_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Resolve a question through structured debate and return decision record.

    High-level Layer 3 API that combines run_debate + extract_decision_record
    into a single operation. Agents call this for quick, verified decisions.

    Process:
    1. Generate thread_id if not provided (YYYY-MM-DD-topic-slug format)
    2. Run full Wind/Wall/Door debate via run_debate
    3. Extract DecisionRecord from closed debate
    4. Return verified decision ready for use

    Args:
        topic: The question or topic to resolve
        tier: Tier configuration name (default: "standard")
        thread_id: Optional custom thread ID (auto-generated if None)
        state_dir: Directory for state files (defaults to ./debates)

    Returns:
        Dictionary with DecisionRecord fields plus debate metadata:
        - All DecisionRecord fields (identity, outcome, rationale, validation, provenance)
        - debate_result: The raw run_debate result for reference

    Raises:
        RuntimeError: If debate fails or cannot be closed
        ValueError: If tier configuration is invalid
    """
    if state_dir is None:
        state_dir = get_state_dir()

    # Generate thread_id if not provided
    if thread_id is None:
        # Create slug from topic (first 30 chars, lowercase, spaces to dashes)
        topic_slug = topic[:30].lower().replace(" ", "-")
        # Remove any non-alphanumeric chars except dash
        topic_slug = "".join(c for c in topic_slug if c.isalnum() or c == "-")
        date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        thread_id = f"{date_prefix}-{topic_slug}"

    # Run the debate
    debate_result = await run_debate(
        topic=topic,
        tier=tier,
        thread_id=thread_id,
        state_dir=state_dir,
    )

    # Check if debate succeeded (status should be synthesis or stalemate)
    status = debate_result.get("status", "")
    if status not in ("synthesis", "stalemate", "exhaustion"):
        raise RuntimeError(
            f"Debate did not complete successfully. Status: {status}. " f"Thread ID: {thread_id}"
        )

    # Extract decision record
    room = load_debate_state(thread_id, state_dir)
    record = _extract(room)

    # Combine record with debate metadata
    result = record.model_dump(mode="json")
    result["debate_result"] = debate_result

    return result
