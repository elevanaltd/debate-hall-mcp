"""Decision record extraction for debate-hall-mcp Layer 3.

This module implements:
- DecisionRecord: Extracted decision from a closed debate
- extract_decision_record(): Function to create record from DebateRoom

The "Cognitive Notary" concept: Debates produce verified decision records
that can be indexed, searched, and cited by future agents.
"""

import hashlib
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from debate_hall_mcp.state import DebateRoom, DebateStatus


class DecisionRecord(BaseModel):
    """Extracted decision from a closed debate for query/search.

    The "Cognitive Notary" product - a verified record that can be
    indexed, searched, and cited by future decision-making agents.

    Fields grouped by purpose:

    Identity:
    - thread_id: Source debate ID (unique identifier)
    - topic: Original debate topic (searchable)
    - decided_at: When debate closed (temporal query)

    Outcome:
    - synthesis: Door's final synthesis (the decision/answer)
    - decision_hash: SHA-256 of synthesis for integrity verification
    - status: How the debate concluded (synthesis, stalemate, exhaustion)

    Rationale:
    - wind_perspectives: Key points from Wind turns (alternatives explored)
    - wall_constraints: Key constraints from Wall turns (boundaries applied)
    - door_refinements: Door's refinement summaries if any

    Validation:
    - consensus_reached: Whether Wind and Wall both approved
    - consensus_votes: Individual vote record {wind: bool, wall: bool}
    - refinement_count: Number of Door refinement rounds

    Provenance:
    - extracted_at: When this record was created
    - source_hash: Hash of source DebateRoom JSON for integrity
    - turn_count: Total turns in source debate
    """

    # Identity
    thread_id: str = Field(..., description="Source debate thread ID")
    topic: str = Field(..., description="Original debate topic")
    decided_at: datetime = Field(..., description="When debate was closed (UTC)")

    # Outcome
    synthesis: str = Field(..., description="Door's final synthesis")
    decision_hash: str = Field(..., description="SHA-256 hash of synthesis")
    status: str = Field(
        ..., description="How debate concluded: synthesis|stalemate|exhaustion|force_closed"
    )

    # Rationale - extracted summaries from turns
    wind_perspectives: list[str] = Field(
        default_factory=list, description="Key points from Wind turns"
    )
    wall_constraints: list[str] = Field(
        default_factory=list, description="Key constraints from Wall turns"
    )
    door_refinements: list[str] = Field(
        default_factory=list, description="Door's refinement iterations (if any)"
    )

    # Validation
    consensus_reached: bool = Field(
        default=False, description="Whether Wind and Wall both approved synthesis"
    )
    consensus_votes: dict[str, bool | None] = Field(
        default_factory=dict, description="Individual vote record"
    )
    refinement_count: int = Field(default=0, description="Number of Door refinement rounds")

    # Provenance
    extracted_at: datetime = Field(..., description="When this record was created (UTC)")
    source_hash: str = Field(..., description="Hash of source DebateRoom JSON")
    turn_count: int = Field(default=0, description="Total turns in source debate")


def calculate_decision_hash(synthesis: str) -> str:
    """Calculate SHA-256 hash of synthesis for integrity verification."""
    return hashlib.sha256(synthesis.encode("utf-8")).hexdigest()


def calculate_source_hash(room: DebateRoom) -> str:
    """Calculate SHA-256 hash of DebateRoom JSON for provenance."""
    return hashlib.sha256(room.model_dump_json().encode("utf-8")).hexdigest()


def extract_decision_record(room: DebateRoom) -> DecisionRecord:
    """Extract a DecisionRecord from a closed DebateRoom.

    Args:
        room: A closed DebateRoom (status not ACTIVE or PAUSED)

    Returns:
        DecisionRecord with extracted decision data

    Raises:
        ValueError: If room is not closed (status ACTIVE or PAUSED)
    """
    # Validate room is closed
    if room.status in (DebateStatus.ACTIVE, DebateStatus.PAUSED):
        raise ValueError(
            f"Cannot extract decision from {room.status.value} debate. "
            "Debate must be closed first."
        )

    # Extract perspectives from turns by role
    wind_perspectives = []
    wall_constraints = []
    door_refinements = []

    for turn in room.turns:
        if turn.role == "Wind":
            wind_perspectives.append(turn.content)
        elif turn.role == "Wall":
            wall_constraints.append(turn.content)
        elif turn.role == "Door":
            door_refinements.append(turn.content)

    # Get last turn timestamp as decided_at, or now if no turns
    decided_at = room.turns[-1].timestamp if room.turns else datetime.now(UTC)

    # Build consensus info from metadata if available
    consensus_reached = False
    consensus_votes: dict[str, bool | None] = {"wind": None, "wall": None}
    refinement_count = 0

    if room.consensus_metadata:
        consensus_reached = room.consensus_metadata.consensus_reached
        consensus_votes = {
            "wind": room.consensus_metadata.wind_approved,
            "wall": room.consensus_metadata.wall_approved,
        }
        refinement_count = room.consensus_metadata.refinement_count

    return DecisionRecord(
        # Identity
        thread_id=room.thread_id,
        topic=room.topic,
        decided_at=decided_at,
        # Outcome
        synthesis=room.synthesis or "",
        decision_hash=calculate_decision_hash(room.synthesis or ""),
        status=room.status.value,
        # Rationale
        wind_perspectives=wind_perspectives,
        wall_constraints=wall_constraints,
        door_refinements=door_refinements,
        # Validation
        consensus_reached=consensus_reached,
        consensus_votes=consensus_votes,
        refinement_count=refinement_count,
        # Provenance
        extracted_at=datetime.now(UTC),
        source_hash=calculate_source_hash(room),
        turn_count=len(room.turns),
    )
