"""Debate Orchestrator for auto-orchestration (Phase 3, ADR-0002).

This module implements:
- DebateOrchestrator: Core orchestration loop for automated debates
- DebateResult: Result model for completed debates

The orchestrator uses existing debate tools (init, turn, close) internally,
maintaining backward compatibility while enabling automated multi-model debates.

Architecture (per ADR-0002):
- Agents call get_debate() to access state (I1: Cognitive State Isolation)
- Events emitted at each stage for observability
- Providers created per tier configuration
"""

import contextlib
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field
from ulid import ULID

from debate_hall_mcp.config import TierConfig
from debate_hall_mcp.events import EventType, append_event
from debate_hall_mcp.prompts import (
    DOOR_PROMPT,
    WALL_PROMPT,
    WIND_PROMPT,
    format_door_user_prompt,
    format_wall_user_prompt,
    format_wind_user_prompt,
)
from debate_hall_mcp.providers import ProviderResponse, create_provider
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn


class DebateResult(BaseModel):
    """Result of a completed debate orchestration.

    Fields:
    - thread_id: Unique debate thread identifier
    - topic: The debate topic
    - status: Final debate status (synthesis, stalemate, exhaustion, etc.)
    - turn_count: Total number of turns in the debate
    - synthesis: Door's final synthesis (if status=synthesis)
    """

    thread_id: str = Field(..., description="Debate thread identifier")
    topic: str = Field(..., description="The debate topic")
    status: str = Field(..., description="Final debate status")
    turn_count: int = Field(..., description="Total turns in debate")
    synthesis: str | None = Field(default=None, description="Door's final synthesis")


class DebateOrchestrator:
    """Orchestrates automated Wind/Wall/Door debates.

    Uses tier configuration to create providers for each role, then runs
    the debate loop: init -> Wind -> Wall -> Door -> close.

    Per ADR-0002:
    - Agents fetch state via get_debate() (not injected)
    - Events emitted at each stage
    - Uses existing debate tools internally
    """

    def __init__(self, tier_config: TierConfig, state_dir: Path) -> None:
        """Initialize orchestrator with tier configuration.

        Args:
            tier_config: Configuration for Wind/Wall/Door providers
            state_dir: Directory for debate state persistence
        """
        self.tier_config = tier_config
        self.state_dir = state_dir

    def _generate_thread_id(self, topic: str) -> str:
        """Generate a thread ID in date-first format.

        Format: YYYY-MM-DD-subject-ulid

        Args:
            topic: The debate topic (used to derive subject)

        Returns:
            Thread ID string in date-first format
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        # Create a safe subject from the topic (lowercase, replace spaces with hyphens)
        subject = topic.lower().replace(" ", "-")
        # Keep only alphanumeric and hyphens, limit length
        safe_subject = "".join(c for c in subject if c.isalnum() or c == "-")[:30]
        # Add ULID suffix for uniqueness
        ulid_suffix = str(ULID())[:8].lower()
        return f"{today}-{safe_subject}-{ulid_suffix}"

    async def run(self, topic: str, thread_id: str | None = None) -> DebateResult:
        """Run a complete debate orchestration.

        Flow:
        1. Generate thread_id if not provided
        2. Initialize debate via init_debate
        3. Create providers for Wind, Wall, Door
        4. Wind turn: expand possibilities
        5. Wall turn: validate constraints
        6. Door turn: synthesize resolution
        7. Close debate with Door's synthesis
        8. Return DebateResult

        Args:
            topic: The debate topic
            thread_id: Optional thread ID (generated if not provided)

        Returns:
            DebateResult with debate outcome

        Raises:
            Exception: If provider fails or debate cannot be completed
        """
        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = self._generate_thread_id(topic)

        try:
            # 1. Initialize debate
            debate_init(
                thread_id=thread_id,
                topic=topic,
                mode="fixed",
                state_dir=self.state_dir,
            )

            # Emit debate_started event
            append_event(
                thread_id=thread_id,
                event_type=EventType.DEBATE_STARTED,
                payload={"topic": topic, "tier": "auto-orchestrated"},
                state_dir=self.state_dir,
            )

            # 2. Create providers
            wind_provider = create_provider(self.tier_config.wind)
            wall_provider = create_provider(self.tier_config.wall)
            door_provider = create_provider(self.tier_config.door)

            # 3. Wind turn (PATHOS - Ideation)
            wind_user_prompt = format_wind_user_prompt(topic, thread_id)
            wind_response: ProviderResponse = await wind_provider.complete(
                system_prompt=WIND_PROMPT,
                user_prompt=wind_user_prompt,
            )
            debate_turn(
                thread_id=thread_id,
                role="Wind",
                content=wind_response.content,
                cognition="PATHOS",
                model=wind_response.model,
                token_input=wind_response.token_input,
                token_output=wind_response.token_output,
                state_dir=self.state_dir,
            )
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Wind",
                    "content_preview": wind_response.content[:100],
                },
                state_dir=self.state_dir,
            )

            # 4. Wall turn (ETHOS - Validation)
            wall_user_prompt = format_wall_user_prompt(topic, thread_id)
            wall_response: ProviderResponse = await wall_provider.complete(
                system_prompt=WALL_PROMPT,
                user_prompt=wall_user_prompt,
            )
            debate_turn(
                thread_id=thread_id,
                role="Wall",
                content=wall_response.content,
                cognition="ETHOS",
                model=wall_response.model,
                token_input=wall_response.token_input,
                token_output=wall_response.token_output,
                state_dir=self.state_dir,
            )
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Wall",
                    "content_preview": wall_response.content[:100],
                },
                state_dir=self.state_dir,
            )

            # 5. Door turn (LOGOS - Synthesis)
            door_user_prompt = format_door_user_prompt(topic, thread_id)
            door_response: ProviderResponse = await door_provider.complete(
                system_prompt=DOOR_PROMPT,
                user_prompt=door_user_prompt,
            )
            debate_turn(
                thread_id=thread_id,
                role="Door",
                content=door_response.content,
                cognition="LOGOS",
                model=door_response.model,
                token_input=door_response.token_input,
                token_output=door_response.token_output,
                state_dir=self.state_dir,
            )
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Door",
                    "content_preview": door_response.content[:100],
                },
                state_dir=self.state_dir,
            )

            # 6. Close debate with Door's synthesis
            debate_close(
                thread_id=thread_id,
                synthesis=door_response.content,
                state_dir=self.state_dir,
                output_format="json",
            )

            # Emit debate_closed event
            append_event(
                thread_id=thread_id,
                event_type=EventType.DEBATE_CLOSED,
                payload={
                    "status": "synthesis",
                    "synthesis_preview": door_response.content[:100],
                },
                state_dir=self.state_dir,
            )

            # 7. Return result
            return DebateResult(
                thread_id=thread_id,
                topic=topic,
                status="synthesis",
                turn_count=3,
                synthesis=door_response.content,
            )

        except Exception as e:
            # Emit error event (suppress any failure to emit)
            with contextlib.suppress(Exception):
                append_event(
                    thread_id=thread_id,
                    event_type=EventType.ERROR,
                    payload={
                        "error_type": type(e).__name__,
                        "message": str(e),
                    },
                    state_dir=self.state_dir,
                )
            raise
