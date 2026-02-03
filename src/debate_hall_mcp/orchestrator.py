"""Debate Orchestrator for auto-orchestration (Phase 3 & 4, ADR-0002).

This module implements:
- DebateOrchestrator: Core orchestration loop for automated debates
- DebateResult: Result model for completed debates

The orchestrator uses existing debate tools (init, turn, close) internally,
maintaining backward compatibility while enabling automated multi-model debates.

Architecture (per ADR-0002 + VTP):
- VTP (Virtual Tool Preload): Orchestrator pre-fetches state via debate_get()
  and injects it into prompts. Agents receive state passively.
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
from typing import Any

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
from debate_hall_mcp.state import (
    ConsensusMetadata,
    DebateStatus,
    load_debate_state,
    save_debate_state,
)
from debate_hall_mcp.tools.close import debate_close
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn
from debate_hall_mcp.utils.primers import load_primer

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

    def _format_debate_state(self, debate_state: dict[str, Any]) -> str:
        """Format debate state as a structured block for prompt injection (VTP).

        Virtual Tool Preload (VTP) pattern: Pre-fetches debate state and injects
        it into the prompt so agents receive state passively instead of needing
        to call get_debate() themselves. This enables provider-agnostic design
        since OpenRouter/API models cannot execute tool calls.

        Args:
            debate_state: Result from debate_get()

        Returns:
            Formatted string with DEBATE_STATE tags
        """
        lines = ["<DEBATE_STATE>"]
        lines.append(f"THREAD_ID::{debate_state['thread_id']}")
        lines.append(f"TOPIC::{debate_state['topic']}")
        lines.append(f"STATUS::{debate_state['status']}")
        lines.append(f"TURN_COUNT::{debate_state['turn_count']}")

        if debate_state.get("synthesis"):
            lines.append(f"SYNTHESIS::{debate_state['synthesis']}")

        if debate_state.get("transcript"):
            lines.append("\nTRANSCRIPT::")
            for turn in debate_state["transcript"]:
                role = turn.get("role", "Unknown")
                content = turn.get("content", "")
                lines.append(f"  [{role}]:: {content}")

        lines.append("</DEBATE_STATE>")
        return "\n".join(lines)

    def _get_primer_content(self) -> str:
        """Get primer content based on primer_tier setting (VTP).

        Primer mapping:
        - none: No primers (empty string)
        - literacy: octave-literacy-primer only
        - standard: octave-literacy-primer + octave-compression-primer
        - advanced: literacy + compression + octave-ultra-mythic-primer

        Returns:
            Combined primer content string, or empty string for 'none' tier
        """
        primer_tier = self.tier_config.settings.primer_tier
        if primer_tier == "none":
            return ""

        primers: list[str] = []

        # All non-none tiers include literacy primer
        if primer_tier in ("literacy", "standard", "advanced"):
            primers.append(load_primer("octave-literacy-primer"))

        # Standard and advanced include compression primer
        if primer_tier in ("standard", "advanced"):
            primers.append(load_primer("octave-compression-primer"))

        # Advanced includes ultra-mythic primer
        if primer_tier == "advanced":
            primers.append(load_primer("octave-ultra-mythic-primer"))

        return "\n\n".join(primers)

    def _get_compression_directive(self) -> str:
        """Get compression directive based on compression_tier setting (VTP).

        Directive mapping:
        - none: No directive (empty string)
        - basic: "Use OCTAVE structure while preserving nuance"
        - aggressive: "Use OCTAVE compression. Drop nuance, preserve core meaning."
        - ultra: "Use ULTRA compression. Drop all narrative, preserve protocol only."

        Returns:
            Compression directive string, or empty string for 'none' tier
        """
        compression_tier = self.tier_config.settings.compression_tier

        directives = {
            "none": "",
            "basic": "Use OCTAVE structure while preserving nuance",
            "aggressive": "Use OCTAVE compression. Drop nuance, preserve core meaning.",
            "ultra": "Use ULTRA compression. Drop all narrative, preserve protocol only.",
        }

        return directives.get(compression_tier, "")

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

The current debate state is provided above in <DEBATE_STATE> tags.

{rejector} has REJECTED your synthesis with the following feedback:
{feedback_text}

Your task: Refine your synthesis to address {rejector}'s concerns.

As Door (LOGOS), create a refined synthesis that:
- Addresses the specific feedback from {rejector}
- Maintains integration of Wind's possibilities and Wall's constraints
- Demonstrates how this refinement improves the emergent solution
- Preserves concrete, actionable implementation steps

Respond with your refined synthesis using the OCTAVE response format."""

    async def _execute_role_turn(
        self,
        role: str,
        provider: ModelProvider,
        thread_id: str,
        user_prompt: str,
        timeout: int,
    ) -> ProviderResponse:
        """Execute a single role turn with provider call, recording, and event emission.

        This helper consolidates the common pattern of:
        1. Pre-fetching debate state (VTP: Virtual Tool Preload)
        2. Injecting state into prompt
        3. Calling the provider with timeout
        4. Recording the debate turn
        5. Emitting TURN_ADDED event

        VTP enables provider-agnostic design: agents receive state passively
        instead of needing to call get_debate() themselves (which OpenRouter/API
        models cannot do).

        Args:
            role: The debate role (Wind, Wall, Door)
            provider: The provider instance for this role
            thread_id: Thread ID for the debate
            user_prompt: The formatted user prompt to send
            timeout: Provider timeout in seconds

        Returns:
            ProviderResponse from the provider
        """
        # Role-specific cognition mapping
        cognition_map = {"Wind": "PATHOS", "Wall": "ETHOS", "Door": "LOGOS"}
        cognition = cognition_map.get(role, "LOGOS")

        # VTP: Pre-fetch debate state and inject into prompt
        context_turns = self.tier_config.settings.context_turns
        debate_state = debate_get(
            thread_id=thread_id,
            include_transcript=True,
            context_turns=context_turns,
            state_dir=self.state_dir,
        )

        # Format state as structured block
        state_block = self._format_debate_state(debate_state)

        # VTP: Build enhanced prompt with primers, compression directive, and state
        # Order: primers -> compression directive -> state block -> user prompt
        primer_content = self._get_primer_content()
        compression_directive = self._get_compression_directive()

        enhanced_prompt = ""
        if primer_content:
            enhanced_prompt += f"{primer_content}\n\n"
        if compression_directive:
            enhanced_prompt += (
                f"<COMPRESSION_DIRECTIVE>\n{compression_directive}\n</COMPRESSION_DIRECTIVE>\n\n"
            )
        enhanced_prompt += f"{state_block}\n\n{user_prompt}"

        # Call provider with timeout (M1: CE Review mitigation)
        response: ProviderResponse = await asyncio.wait_for(
            provider.complete(
                system_prompt=self._get_prompt(role.lower()),
                user_prompt=enhanced_prompt,
            ),
            timeout=timeout,
        )

        # Record the debate turn
        debate_turn(
            thread_id=thread_id,
            role=role,
            content=response.content,
            cognition=cognition,
            model=response.model,
            token_input=response.token_input,
            token_output=response.token_output,
            state_dir=self.state_dir,
        )

        # M3: Emit TURN_ADDED event (redact content_preview)
        append_event(
            thread_id=thread_id,
            event_type=EventType.TURN_ADDED,
            payload={
                "role": role,
                "model": response.model,
            },
            state_dir=self.state_dir,
        )

        return response

    async def _execute_consensus_loop(
        self,
        thread_id: str,
        topic: str,
        current_synthesis: str,
        turn_count: int,
        wind_provider: ModelProvider,
        wall_provider: ModelProvider,
        door_provider: ModelProvider,
        initial_refinement_count: int = 0,
    ) -> tuple[str, int, str, ConsensusMetadata]:
        """Execute the consensus loop where Wind and Wall approve Door's synthesis.

        This helper consolidates the consensus approval pattern used by both
        run() and resume() methods. It handles:
        1. Wind approval -> reject triggers Door refinement
        2. Wall approval -> reject triggers Door refinement
        3. Stalemate detection when max loops exceeded

        Args:
            thread_id: Thread ID for the debate
            topic: The debate topic
            current_synthesis: Door's current synthesis content
            turn_count: Current turn count
            wind_provider: Provider for Wind role
            wall_provider: Provider for Wall role
            door_provider: Provider for Door role
            initial_refinement_count: Starting refinement count (for resume scenarios
                where refinements may have already occurred before pause)

        Returns:
            Tuple of (final_status, final_turn_count, final_synthesis, consensus_metadata)
            where status is "synthesis" or "stalemate"
        """
        max_refinement_loops = self.tier_config.settings.max_refinement_loops
        timeout = self._get_provider_timeout()
        refinement_count = initial_refinement_count

        # Track vote states for ConsensusMetadata
        final_wind_approved: bool | None = None
        final_wall_approved: bool | None = None

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
            final_wind_approved = wind_vote.approved

            # Emit CONSENSUS_VOTE event for Wind
            append_event(
                thread_id=thread_id,
                event_type=EventType.CONSENSUS_VOTE,
                payload={"role": "Wind", "approved": wind_vote.approved},
                state_dir=self.state_dir,
            )

            # If Wind rejects, refine immediately
            if not wind_vote.approved:
                refinement_count += 1
                # Reset Wall vote since we're starting a new consensus round
                final_wall_approved = None
                if refinement_count > max_refinement_loops:
                    break

                # Door refines based on Wind's feedback
                refinement_prompt = self._create_refinement_prompt(
                    topic, thread_id, "Wind", wind_vote.feedback
                )
                door_response = await self._execute_role_turn(
                    "Door", door_provider, thread_id, refinement_prompt, timeout
                )
                turn_count += 1
                current_synthesis = door_response.content
                continue

            # Wall approval (only if Wind approved)
            wall_approval_prompt = format_wall_approval_prompt(topic, thread_id)
            wall_approval_response: ProviderResponse = await asyncio.wait_for(
                wall_provider.complete(
                    system_prompt=self._get_prompt("wall"),
                    user_prompt=wall_approval_prompt,
                ),
                timeout=timeout,
            )
            wall_vote = parse_consensus_response(wall_approval_response.content)
            final_wall_approved = wall_vote.approved

            # Emit CONSENSUS_VOTE event for Wall
            append_event(
                thread_id=thread_id,
                event_type=EventType.CONSENSUS_VOTE,
                payload={"role": "Wall", "approved": wall_vote.approved},
                state_dir=self.state_dir,
            )

            # If Wall rejects, refine
            if not wall_vote.approved:
                refinement_count += 1
                if refinement_count > max_refinement_loops:
                    break

                # Door refines based on Wall's feedback
                refinement_prompt = self._create_refinement_prompt(
                    topic, thread_id, "Wall", wall_vote.feedback
                )
                door_response = await self._execute_role_turn(
                    "Door", door_provider, thread_id, refinement_prompt, timeout
                )
                turn_count += 1
                current_synthesis = door_response.content
                continue

            # Both approved - consensus achieved
            break

        # Determine final status and create consensus metadata
        max_reached = refinement_count > max_refinement_loops
        consensus_reached = not max_reached and final_wind_approved and final_wall_approved

        consensus_metadata = ConsensusMetadata(
            consensus_reached=consensus_reached is True,
            wind_approved=final_wind_approved,
            wall_approved=final_wall_approved,
            refinement_count=refinement_count,
            max_refinements_reached=max_reached,
        )

        if max_reached:
            return ("stalemate", turn_count, current_synthesis, consensus_metadata)
        return ("synthesis", turn_count, current_synthesis, consensus_metadata)

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

            # 3. Wind turn (PATHOS - Ideation)
            wind_user_prompt = format_wind_user_prompt(topic, thread_id)
            await self._execute_role_turn(
                "Wind", wind_provider, thread_id, wind_user_prompt, timeout
            )

            # 4. Wall turn (ETHOS - Validation)
            wall_user_prompt = format_wall_user_prompt(topic, thread_id)
            await self._execute_role_turn(
                "Wall", wall_provider, thread_id, wall_user_prompt, timeout
            )

            # 5. Door turn (LOGOS - Synthesis)
            door_user_prompt = format_door_user_prompt(topic, thread_id)
            door_response = await self._execute_role_turn(
                "Door", door_provider, thread_id, door_user_prompt, timeout
            )

            # Track turn count (3 initial turns: Wind, Wall, Door)
            turn_count = 3
            current_synthesis = door_response.content
            final_status = "synthesis"

            # 6. Consensus loop (Phase 4) - if consensus_required
            consensus_metadata: ConsensusMetadata | None = None
            if self.tier_config.settings.consensus_required:
                (
                    final_status,
                    turn_count,
                    current_synthesis,
                    consensus_metadata,
                ) = await self._execute_consensus_loop(
                    thread_id=thread_id,
                    topic=topic,
                    current_synthesis=current_synthesis,
                    turn_count=turn_count,
                    wind_provider=wind_provider,
                    wall_provider=wall_provider,
                    door_provider=door_provider,
                )

                # Handle stalemate from consensus loop
                if final_status == "stalemate":
                    # Set consensus_metadata on room before closing
                    room = load_debate_state(thread_id, self.state_dir)
                    room.consensus_metadata = consensus_metadata
                    save_debate_state(room, self.state_dir)

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

            # 7. Set consensus_metadata on room before closing (if consensus was executed)
            if consensus_metadata is not None:
                room = load_debate_state(thread_id, self.state_dir)
                room.consensus_metadata = consensus_metadata
                save_debate_state(room, self.state_dir)

            # 8. Close debate with Door's synthesis (consensus achieved or not required)
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

            # 9. Return result
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
                    await self._execute_role_turn(
                        "Wind", wind_provider, thread_id, wind_user_prompt, timeout
                    )
                    turn_count += 1

                # Complete missing Wall turn if needed
                if "Wall" not in existing_roles:
                    wall_user_prompt = format_wall_user_prompt(topic, thread_id)
                    await self._execute_role_turn(
                        "Wall", wall_provider, thread_id, wall_user_prompt, timeout
                    )
                    turn_count += 1

                # Complete missing Door turn if needed (always needed if we're here)
                if "Door" not in existing_roles:
                    door_user_prompt = format_door_user_prompt(topic, thread_id)
                    door_response = await self._execute_role_turn(
                        "Door", door_provider, thread_id, door_user_prompt, timeout
                    )
                    turn_count += 1
                    current_synthesis = door_response.content

            # If we have Wind, Wall, Door turns (>=3), resume from consensus
            final_status = "synthesis"
            consensus_metadata: ConsensusMetadata | None = None
            if turn_count >= 3 and self.tier_config.settings.consensus_required:
                # Estimate refinements already done before pause
                initial_refinement_count = max(0, turn_count - 3)

                (
                    final_status,
                    turn_count,
                    current_synthesis,
                    consensus_metadata,
                ) = await self._execute_consensus_loop(
                    thread_id=thread_id,
                    topic=topic,
                    current_synthesis=current_synthesis,
                    turn_count=turn_count,
                    wind_provider=wind_provider,
                    wall_provider=wall_provider,
                    door_provider=door_provider,
                    initial_refinement_count=initial_refinement_count,
                )

                # Handle stalemate from consensus loop
                if final_status == "stalemate":
                    # Set consensus_metadata on room before closing
                    room = load_debate_state(thread_id, self.state_dir)
                    room.consensus_metadata = consensus_metadata
                    save_debate_state(room, self.state_dir)

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

            # Set consensus_metadata on room before closing (if consensus was executed)
            if consensus_metadata is not None:
                room = load_debate_state(thread_id, self.state_dir)
                room.consensus_metadata = consensus_metadata
                save_debate_state(room, self.state_dir)

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
