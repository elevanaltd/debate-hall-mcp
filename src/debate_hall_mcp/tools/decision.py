"""extract_decision_record tool - Layer 3 decision extraction.

Extracts a DecisionRecord from a closed debate for indexing and search.
Part of the "Cognitive Notary" Layer 3 query capabilities.
"""

from pathlib import Path
from typing import Any

from debate_hall_mcp.decision import extract_decision_record as _extract
from debate_hall_mcp.state import get_state_dir, load_debate_state


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
