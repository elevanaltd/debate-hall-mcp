"""Debate Orchestrator for auto-orchestration (Phase 3 & 4, ADR-0002).

This module implements:
- DebateOrchestrator: Core orchestration loop for automated debates
- DebateResult: Result model for completed debates

The orchestrator uses existing debate tools (init, turn, close) internally,
maintaining backward compatibility while enabling automated multi-model debates.

Architecture (per ADR-0002):
- Agents call get_debate() to access state (I1: Cognitive State Isolation)
- Events emitted at each stage for observability
- Providers created per tier configuration

CE Review Mitigations (Phase 3):
- M1: Provider timeout handling with asyncio.wait_for()
- M2: Debate marked PAUSED on failure for recovery
- M3: Event payload redaction (no content_preview, sanitized errors)

Phase 4: Consensus Loop
- Wind/Wall approval mechanism for Door's synthesis
- Refinement loop with feedback on rejection
- max_refinement_loops from TierSettings (default 3)
- Stalemate status if max loops exceeded
- CONSENSUS_VOTE events emitted
"""

import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field
from ulid import ULID

from debate_hall_mcp.config import RoleConfig, TierConfig
from debate_hall_mcp.consensus import parse_consensus_response
from debate_hall_mcp.events import EventType, append_event
from debate_hall_mcp.prompts import (
    format_door_user_prompt,
    format_wall_approval_prompt,
    format_wall_user_prompt,
    format_wind_approval_prompt,
    format_wind_user_prompt,
)
from debate_hall_mcp.prompts.loader import get_prompt
from debate_hall_mcp.providers import ModelProvider, ProviderResponse, create_provider
from debate_hall_mcp.state import DebateStatus, load_debate_state, save_debate_state
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn

# Default provider timeout in seconds (M1: CE Review)
# Increased from 120 to 300 to accommodate slower CLI providers
DEFAULT_PROVIDER_TIMEOUT = 300

# Type alias for provider factory function (injectable for testing)
ProviderFactory = Callable[[RoleConfig], ModelProvider]


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

    def __init__(
        self,
        tier_config: TierConfig,
        state_dir: Path,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        """Initialize orchestrator with tier configuration.

        Args:
            tier_config: Configuration for Wind/Wall/Door providers
            state_dir: Directory for debate state persistence
            provider_factory: Optional factory for creating providers.
                Enables dependency injection for testing (VirtualProvider).
                Defaults to create_provider for backward compatibility.
        """
        self.tier_config = tier_config
        self.state_dir = state_dir
        self._provider_factory = provider_factory or create_provider

    def _get_provider_timeout(self) -> int:
        """Get provider timeout in seconds (M1: CE Review mitigation).

        Returns:
            Timeout in seconds from TierSettings.provider_timeout,
            or DEFAULT_PROVIDER_TIMEOUT (300s) if not configured.
        """
        # Use tier_config setting if available, otherwise default
        settings = self.tier_config.settings
        provider_timeout = getattr(settings, "provider_timeout", None)
        if provider_timeout is not None and isinstance(provider_timeout, int):
            return int(provider_timeout)  # Explicit cast for mypy
        return DEFAULT_PROVIDER_TIMEOUT

    def _get_prompt(self, role: str) -> str:
        """Get prompt for a role, using custom file if configured.

        Uses the Layered Discovery pattern from prompts.loader:
        1. If prompt_file is set in tier config -> load from file/variant
        2. If prompt_file is null -> use embedded default

        Args:
            role: The debate role (wind, wall, door)

        Returns:
            Prompt string (OCTAVE format)
        """
        # Get the role config for this role
        role_config = getattr(self.tier_config, role.lower())
        # Get prompt using loader (handles file resolution and defaults)
        return get_prompt(role, role_config.prompt_file)

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

    def _create_refinement_prompt(
        self, topic: str, thread_id: str, rejector: str, feedback: str | None
    ) -> str:
        """Create a prompt for Door to refine synthesis based on feedback.

        Args:
            topic: The debate topic
            thread_id: Thread ID for state access
            rejector: The role that rejected (Wind or Wall)
            feedback: Feedback from the rejector (may be None)

        Returns:
            Formatted prompt for Door to refine synthesis
        """
        feedback_text = feedback if feedback else "No specific feedback provided."
        return f"""You are participating in a Wind/Wall/Door debate REFINEMENT PHASE.

Topic: {topic}
Thread ID: {thread_id}
Your Role: Door (LOGOS) - Synthesis Refiner

To see prior turns and your previous synthesis, call: get_debate("{thread_id}", include_transcript=true)

{rejector} has REJECTED your synthesis with the following feedback:
{feedback_text}

Your task: Refine your synthesis to address {rejector}'s concerns.

As Door (LOGOS), create a refined synthesis that:
- Addresses the specific feedback from {rejector}
- Maintains integration of Wind's possibilities and Wall's constraints
- Demonstrates how this refinement improves the emergent solution
- Preserves concrete, actionable implementation steps

Respond with your refined synthesis using the OCTAVE response format."""

    async def run(self, topic: str, thread_id: str | None = None) -> DebateResult:
        """Run a complete debate orchestration.

        Flow:
        1. Generate thread_id if not provided
        2. Initialize debate via init_debate
        3. Create providers for Wind, Wall, Door
        4. Wind turn: expand possibilities (with timeout - M1)
        5. Wall turn: validate constraints (with timeout - M1)
        6. Door turn: synthesize resolution (with timeout - M1)
        7. Close debate with Door's synthesis
        8. Return DebateResult

        CE Review Mitigations:
        - M1: Provider calls wrapped with asyncio.wait_for() timeout
        - M2: On failure, debate is marked PAUSED for recovery
        - M3: Event payloads redact sensitive content

        Args:
            topic: The debate topic
            thread_id: Optional thread ID (generated if not provided)

        Returns:
            DebateResult with debate outcome

        Raises:
            asyncio.TimeoutError: If provider times out (M1)
            Exception: If provider fails or debate cannot be completed
        """
        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = self._generate_thread_id(topic)

        # Track if debate was initialized (for M2: PAUSED on failure)
        debate_initialized = False
        timeout = self._get_provider_timeout()

        try:
            # 1. Initialize debate (use mediated mode for orchestrator control of turn sequence)
            # Mediated mode allows Door to add refinement turns out of normal sequence
            debate_init(
                thread_id=thread_id,
                topic=topic,
                mode="mediated",
                state_dir=self.state_dir,
            )
            debate_initialized = True

            # Emit debate_started event
            append_event(
                thread_id=thread_id,
                event_type=EventType.DEBATE_STARTED,
                payload={"topic": topic, "tier": "auto-orchestrated"},
                state_dir=self.state_dir,
            )

            # 2. Create providers
            wind_provider = self._provider_factory(self.tier_config.wind)
            wall_provider = self._provider_factory(self.tier_config.wall)
            door_provider = self._provider_factory(self.tier_config.door)

            # 3. Wind turn (PATHOS - Ideation) with timeout (M1)
            wind_user_prompt = format_wind_user_prompt(topic, thread_id)
            wind_response: ProviderResponse = await asyncio.wait_for(
                wind_provider.complete(
                    system_prompt=self._get_prompt("wind"),
                    user_prompt=wind_user_prompt,
                ),
                timeout=timeout,
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
            # M3: Redact content_preview from TURN_ADDED events
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Wind",
                    "model": wind_response.model,
                },
                state_dir=self.state_dir,
            )

            # 4. Wall turn (ETHOS - Validation) with timeout (M1)
            wall_user_prompt = format_wall_user_prompt(topic, thread_id)
            wall_response: ProviderResponse = await asyncio.wait_for(
                wall_provider.complete(
                    system_prompt=self._get_prompt("wall"),
                    user_prompt=wall_user_prompt,
                ),
                timeout=timeout,
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
            # M3: Redact content_preview from TURN_ADDED events
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Wall",
                    "model": wall_response.model,
                },
                state_dir=self.state_dir,
            )

            # 5. Door turn (LOGOS - Synthesis) with timeout (M1)
            door_user_prompt = format_door_user_prompt(topic, thread_id)
            door_response: ProviderResponse = await asyncio.wait_for(
                door_provider.complete(
                    system_prompt=self._get_prompt("door"),
                    user_prompt=door_user_prompt,
                ),
                timeout=timeout,
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
            # M3: Redact content_preview from TURN_ADDED events
            append_event(
                thread_id=thread_id,
                event_type=EventType.TURN_ADDED,
                payload={
                    "role": "Door",
                    "model": door_response.model,
                },
                state_dir=self.state_dir,
            )

            # Track turn count (3 initial turns: Wind, Wall, Door)
            turn_count = 3
            current_synthesis = door_response.content

            # 6. Consensus loop (Phase 4) - if consensus_required
            if self.tier_config.settings.consensus_required:
                max_refinement_loops = self.tier_config.settings.max_refinement_loops
                refinement_count = 0

                while refinement_count <= max_refinement_loops:
                    # 6a. Wind approval
                    wind_approval_prompt = format_wind_approval_prompt(topic, thread_id)
                    wind_approval_response: ProviderResponse = await asyncio.wait_for(
                        wind_provider.complete(
                            system_prompt=self._get_prompt("wind"),
                            user_prompt=wind_approval_prompt,
                        ),
                        timeout=timeout,
                    )
                    wind_vote = parse_consensus_response(wind_approval_response.content)

                    # Emit CONSENSUS_VOTE event for Wind
                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.CONSENSUS_VOTE,
                        payload={
                            "role": "Wind",
                            "approved": wind_vote.approved,
                        },
                        state_dir=self.state_dir,
                    )

                    # If Wind rejects, refine immediately
                    if not wind_vote.approved:
                        refinement_count += 1
                        if refinement_count > max_refinement_loops:
                            # Max loops exceeded - stalemate
                            break

                        # Door refines based on Wind's feedback
                        refinement_prompt = self._create_refinement_prompt(
                            topic, thread_id, "Wind", wind_vote.feedback
                        )
                        door_response = await asyncio.wait_for(
                            door_provider.complete(
                                system_prompt=self._get_prompt("door"),
                                user_prompt=refinement_prompt,
                            ),
                            timeout=timeout,
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
                                "model": door_response.model,
                            },
                            state_dir=self.state_dir,
                        )
                        turn_count += 1
                        current_synthesis = door_response.content
                        continue  # Start consensus loop again

                    # 6b. Wall approval (only if Wind approved)
                    wall_approval_prompt = format_wall_approval_prompt(topic, thread_id)
                    wall_approval_response: ProviderResponse = await asyncio.wait_for(
                        wall_provider.complete(
                            system_prompt=self._get_prompt("wall"),
                            user_prompt=wall_approval_prompt,
                        ),
                        timeout=timeout,
                    )
                    wall_vote = parse_consensus_response(wall_approval_response.content)

                    # Emit CONSENSUS_VOTE event for Wall
                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.CONSENSUS_VOTE,
                        payload={
                            "role": "Wall",
                            "approved": wall_vote.approved,
                        },
                        state_dir=self.state_dir,
                    )

                    # If Wall rejects, refine
                    if not wall_vote.approved:
                        refinement_count += 1
                        if refinement_count > max_refinement_loops:
                            # Max loops exceeded - stalemate
                            break

                        # Door refines based on Wall's feedback
                        refinement_prompt = self._create_refinement_prompt(
                            topic, thread_id, "Wall", wall_vote.feedback
                        )
                        door_response = await asyncio.wait_for(
                            door_provider.complete(
                                system_prompt=self._get_prompt("door"),
                                user_prompt=refinement_prompt,
                            ),
                            timeout=timeout,
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
                                "model": door_response.model,
                            },
                            state_dir=self.state_dir,
                        )
                        turn_count += 1
                        current_synthesis = door_response.content
                        continue  # Start consensus loop again

                    # Both approved - exit consensus loop
                    break

                # Check if we exceeded max loops (stalemate)
                if refinement_count > max_refinement_loops:
                    # Close with stalemate status
                    debate_close(
                        thread_id=thread_id,
                        synthesis=current_synthesis,
                        status="stalemate",
                        state_dir=self.state_dir,
                        output_format="json",
                    )
                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.DEBATE_CLOSED,
                        payload={
                            "status": "stalemate",
                            "synthesis_preview": current_synthesis[:100],
                        },
                        state_dir=self.state_dir,
                    )
                    return DebateResult(
                        thread_id=thread_id,
                        topic=topic,
                        status="stalemate",
                        turn_count=turn_count,
                        synthesis=current_synthesis,
                    )

            # 7. Close debate with Door's synthesis (consensus achieved or not required)
            debate_close(
                thread_id=thread_id,
                synthesis=current_synthesis,
                state_dir=self.state_dir,
                output_format="json",
            )

            # Emit debate_closed event (synthesis_preview is allowed - intended output)
            append_event(
                thread_id=thread_id,
                event_type=EventType.DEBATE_CLOSED,
                payload={
                    "status": "synthesis",
                    "synthesis_preview": current_synthesis[:100],
                },
                state_dir=self.state_dir,
            )

            # 8. Return result
            return DebateResult(
                thread_id=thread_id,
                topic=topic,
                status="synthesis",
                turn_count=turn_count,
                synthesis=current_synthesis,
            )

        except Exception as e:
            # M3: Emit error event with only error_type (no message - may contain secrets)
            with contextlib.suppress(Exception):
                append_event(
                    thread_id=thread_id,
                    event_type=EventType.ERROR,
                    payload={
                        "error_type": type(e).__name__,
                    },
                    state_dir=self.state_dir,
                )

            # M2: Mark debate as PAUSED on failure (for recovery via resume_debate)
            if debate_initialized:
                with contextlib.suppress(Exception):
                    room = load_debate_state(thread_id, self.state_dir)
                    room.status = DebateStatus.PAUSED
                    save_debate_state(room, self.state_dir)

            raise

    async def resume(self, thread_id: str) -> DebateResult:
        """Resume a PAUSED debate from where it left off.

        This method loads the debate state, validates it's PAUSED, and continues
        the orchestration from the appropriate point based on the turn count.

        Args:
            thread_id: The thread ID of the paused debate

        Returns:
            DebateResult with debate outcome

        Raises:
            FileNotFoundError: If debate doesn't exist
            ValueError: If debate is not in PAUSED status
        """
        # Load debate state
        room = load_debate_state(thread_id, self.state_dir)

        # Validate status is PAUSED
        if room.status != DebateStatus.PAUSED:
            raise ValueError(
                f"Cannot resume debate with status '{room.status.value}': "
                f"only PAUSED debates can be resumed"
            )

        topic = room.topic
        turn_count = len(room.turns)
        timeout = self._get_provider_timeout()

        # Mark as active for resumption
        room.status = DebateStatus.ACTIVE
        save_debate_state(room, self.state_dir)

        try:
            # Create providers
            wind_provider = self._provider_factory(self.tier_config.wind)
            wall_provider = self._provider_factory(self.tier_config.wall)
            door_provider = self._provider_factory(self.tier_config.door)

            # Determine existing turns by role
            existing_roles = {t.role for t in room.turns}
            door_turns = [t for t in room.turns if t.role == "Door"]
            current_synthesis = door_turns[-1].content if door_turns else ""

            # CE Blocking Fix #1 & #2: Complete missing Wind/Wall/Door turns before close
            # If turn_count < 3, we need to complete the missing turns first
            # Fix #2: Handle turn_count=0 case where Wind failed immediately after init
            if turn_count < 3:
                # Complete missing Wind turn if needed (CE Fix #2)
                if "Wind" not in existing_roles:
                    wind_user_prompt = format_wind_user_prompt(topic, thread_id)
                    wind_response: ProviderResponse = await asyncio.wait_for(
                        wind_provider.complete(
                            system_prompt=self._get_prompt("wind"),
                            user_prompt=wind_user_prompt,
                        ),
                        timeout=timeout,
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
                        payload={"role": "Wind", "model": wind_response.model},
                        state_dir=self.state_dir,
                    )
                    turn_count += 1

                # Complete missing Wall turn if needed
                if "Wall" not in existing_roles:
                    wall_user_prompt = format_wall_user_prompt(topic, thread_id)
                    wall_response: ProviderResponse = await asyncio.wait_for(
                        wall_provider.complete(
                            system_prompt=self._get_prompt("wall"),
                            user_prompt=wall_user_prompt,
                        ),
                        timeout=timeout,
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
                        payload={"role": "Wall", "model": wall_response.model},
                        state_dir=self.state_dir,
                    )
                    turn_count += 1

                # Complete missing Door turn if needed (always needed if we're here)
                if "Door" not in existing_roles:
                    door_user_prompt = format_door_user_prompt(topic, thread_id)
                    door_response: ProviderResponse = await asyncio.wait_for(
                        door_provider.complete(
                            system_prompt=self._get_prompt("door"),
                            user_prompt=door_user_prompt,
                        ),
                        timeout=timeout,
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
                        payload={"role": "Door", "model": door_response.model},
                        state_dir=self.state_dir,
                    )
                    turn_count += 1
                    current_synthesis = door_response.content

            # If we have Wind, Wall, Door turns (>=3), resume from consensus
            if turn_count >= 3 and self.tier_config.settings.consensus_required:
                max_refinement_loops = self.tier_config.settings.max_refinement_loops
                refinement_count = max(0, turn_count - 3)  # Estimate refinements done

                while refinement_count <= max_refinement_loops:
                    # Wind approval
                    wind_approval_prompt = format_wind_approval_prompt(topic, thread_id)
                    wind_approval_response: ProviderResponse = await asyncio.wait_for(
                        wind_provider.complete(
                            system_prompt=self._get_prompt("wind"),
                            user_prompt=wind_approval_prompt,
                        ),
                        timeout=timeout,
                    )
                    wind_vote = parse_consensus_response(wind_approval_response.content)

                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.CONSENSUS_VOTE,
                        payload={"role": "Wind", "approved": wind_vote.approved},
                        state_dir=self.state_dir,
                    )

                    if not wind_vote.approved:
                        refinement_count += 1
                        if refinement_count > max_refinement_loops:
                            break

                        refinement_prompt = self._create_refinement_prompt(
                            topic, thread_id, "Wind", wind_vote.feedback
                        )
                        door_response = await asyncio.wait_for(
                            door_provider.complete(
                                system_prompt=self._get_prompt("door"),
                                user_prompt=refinement_prompt,
                            ),
                            timeout=timeout,
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
                            payload={"role": "Door", "model": door_response.model},
                            state_dir=self.state_dir,
                        )
                        turn_count += 1
                        current_synthesis = door_response.content
                        continue

                    # Wall approval
                    wall_approval_prompt = format_wall_approval_prompt(topic, thread_id)
                    wall_approval_response: ProviderResponse = await asyncio.wait_for(
                        wall_provider.complete(
                            system_prompt=self._get_prompt("wall"),
                            user_prompt=wall_approval_prompt,
                        ),
                        timeout=timeout,
                    )
                    wall_vote = parse_consensus_response(wall_approval_response.content)

                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.CONSENSUS_VOTE,
                        payload={"role": "Wall", "approved": wall_vote.approved},
                        state_dir=self.state_dir,
                    )

                    if not wall_vote.approved:
                        refinement_count += 1
                        if refinement_count > max_refinement_loops:
                            break

                        refinement_prompt = self._create_refinement_prompt(
                            topic, thread_id, "Wall", wall_vote.feedback
                        )
                        door_response = await asyncio.wait_for(
                            door_provider.complete(
                                system_prompt=self._get_prompt("door"),
                                user_prompt=refinement_prompt,
                            ),
                            timeout=timeout,
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
                            payload={"role": "Door", "model": door_response.model},
                            state_dir=self.state_dir,
                        )
                        turn_count += 1
                        current_synthesis = door_response.content
                        continue

                    # Both approved
                    break

                # Check for stalemate
                if refinement_count > max_refinement_loops:
                    debate_close(
                        thread_id=thread_id,
                        synthesis=current_synthesis,
                        status="stalemate",
                        state_dir=self.state_dir,
                        output_format="json",
                    )
                    append_event(
                        thread_id=thread_id,
                        event_type=EventType.DEBATE_CLOSED,
                        payload={
                            "status": "stalemate",
                            "synthesis_preview": current_synthesis[:100],
                        },
                        state_dir=self.state_dir,
                    )
                    return DebateResult(
                        thread_id=thread_id,
                        topic=topic,
                        status="stalemate",
                        turn_count=turn_count,
                        synthesis=current_synthesis,
                    )

            # Close with synthesis
            debate_close(
                thread_id=thread_id,
                synthesis=current_synthesis,
                state_dir=self.state_dir,
                output_format="json",
            )
            append_event(
                thread_id=thread_id,
                event_type=EventType.DEBATE_CLOSED,
                payload={
                    "status": "synthesis",
                    "synthesis_preview": current_synthesis[:100],
                },
                state_dir=self.state_dir,
            )
            return DebateResult(
                thread_id=thread_id,
                topic=topic,
                status="synthesis",
                turn_count=turn_count,
                synthesis=current_synthesis,
            )

        except Exception as e:
            with contextlib.suppress(Exception):
                append_event(
                    thread_id=thread_id,
                    event_type=EventType.ERROR,
                    payload={"error_type": type(e).__name__},
                    state_dir=self.state_dir,
                )
            with contextlib.suppress(Exception):
                room = load_debate_state(thread_id, self.state_dir)
                room.status = DebateStatus.PAUSED
                save_debate_state(room, self.state_dir)
            raise
