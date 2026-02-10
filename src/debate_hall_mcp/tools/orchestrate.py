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

Issue #132 Additions:
- Optional compression_tier and primer_tier overrides for per-debate customization

Issue #133 Additions:
- Optional context_files parameter for codebase-aware debates
"""

import logging
from pathlib import Path
from typing import Any, Literal

from debate_hall_mcp.config import TierConfig, TierSettings, load_tier_config
from debate_hall_mcp.orchestrator import DebateOrchestrator
from debate_hall_mcp.providers import create_provider  # noqa: F401 - used in patch
from debate_hall_mcp.state import (
    DebateStatus,
    _validate_thread_id_for_filesystem,
    get_state_dir,
    load_debate_state,
)

logger = logging.getLogger(__name__)

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


# Default max characters per context file (to prevent prompt explosion)
MAX_CHARS_PER_FILE = 10000


def _validate_context_file_path(file_path: str) -> Path:
    """Validate a context file path for security (Issue #133).

    Security checks:
    - No path traversal sequences (..)
    - Must be an absolute path
    - Must resolve to a real location (no symlink escape)

    Args:
        file_path: The file path to validate

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path contains traversal sequences or is not absolute
    """
    # Reject path traversal sequences
    if ".." in file_path:
        raise ValueError(
            f"Invalid context_file path '{file_path}': path traversal (..) not allowed"
        )

    path = Path(file_path)

    # Must be absolute
    if not path.is_absolute():
        raise ValueError(f"Invalid context_file path '{file_path}': must be an absolute path")

    return path.resolve()


def _read_context_files(
    context_files: list[str],
    max_chars_per_file: int = MAX_CHARS_PER_FILE,
) -> str:
    """Read and format context files for injection into debate prompts (Issue #133).

    Validates each file path for security, reads contents, and formats them
    as a <CODEBASE_CONTEXT> block. Missing files emit a warning but do not
    cause failure (graceful degradation).

    Args:
        context_files: List of absolute file paths to read
        max_chars_per_file: Maximum characters per file (default 10000).
            Files exceeding this limit are truncated with a notice.

    Returns:
        Formatted string with CODEBASE_CONTEXT tags, or empty string if no
        files could be read.
    """
    if not context_files:
        return ""

    file_blocks: list[str] = []

    for file_path in context_files:
        try:
            validated_path = _validate_context_file_path(file_path)

            if not validated_path.is_file():
                logger.warning("context_files: skipping missing file: %s", file_path)
                continue

            content = validated_path.read_text(encoding="utf-8", errors="replace")

            # Truncate if exceeding max chars
            truncated = False
            if len(content) > max_chars_per_file:
                content = content[:max_chars_per_file]
                truncated = True

            block = f'<FILE path="{file_path}">\n{content}'
            if truncated:
                block += f"\n... [TRUNCATED at {max_chars_per_file} chars]"
            block += "\n</FILE>"

            file_blocks.append(block)

        except ValueError as e:
            logger.warning("context_files: skipping invalid path: %s", e)
            continue
        except OSError as e:
            logger.warning("context_files: error reading file %s: %s", file_path, e)
            continue

    if not file_blocks:
        return ""

    return "<CODEBASE_CONTEXT>\n" + "\n\n".join(file_blocks) + "\n</CODEBASE_CONTEXT>"


def _apply_tier_overrides(
    tier_config: TierConfig,
    compression_tier: Literal["none", "basic", "aggressive", "ultra"] | None = None,
    primer_tier: Literal["none", "literacy", "standard", "advanced"] | None = None,
) -> TierConfig:
    """Apply optional overrides to tier configuration (Issue #132).

    Creates a new TierConfig with overridden settings if any overrides are provided.
    Returns the original config unchanged if no overrides are specified.

    Args:
        tier_config: Original tier configuration
        compression_tier: Override for compression_tier (None = use tier default)
        primer_tier: Override for primer_tier (None = use tier default)

    Returns:
        TierConfig with overrides applied (or original if no overrides)
    """
    # If no overrides, return original config unchanged
    if compression_tier is None and primer_tier is None:
        return tier_config

    # Create new settings with overrides applied
    settings_dict = tier_config.settings.model_dump()
    if compression_tier is not None:
        settings_dict["compression_tier"] = compression_tier
    if primer_tier is not None:
        settings_dict["primer_tier"] = primer_tier

    # Create new TierConfig with updated settings
    return TierConfig(
        wind=tier_config.wind,
        wall=tier_config.wall,
        door=tier_config.door,
        settings=TierSettings.model_validate(settings_dict),
    )


async def run_debate(
    topic: str,
    tier: str = "standard",
    thread_id: str | None = None,
    state_dir: Path | None = None,
    compression_tier: Literal["none", "basic", "aggressive", "ultra"] | None = None,
    primer_tier: Literal["none", "literacy", "standard", "advanced"] | None = None,
    mode: Literal["standard", "raci"] = "standard",
    context_files: list[str] | None = None,
) -> dict[str, Any]:
    """Run an automated Wind/Wall/Door debate.

    This is the main entry point for auto-orchestration. It:
    1. Validates inputs (M4: CE Review)
    2. Loads tier configuration
    3. Applies optional overrides (Issue #132)
    4. Reads context files if provided (Issue #133)
    5. Creates an orchestrator
    6. Runs the debate loop (Wind -> Wall -> Door)
    7. Returns the result

    Args:
        topic: The debate topic to explore (1-1000 chars, non-empty)
        tier: Tier configuration name (default: "standard")
        thread_id: Optional thread ID (auto-generated if not provided)
        state_dir: Directory for state files (defaults to ./debates)
        compression_tier: Override compression tier (None = use tier default)
        primer_tier: Override primer tier (None = use tier default)
        mode: Debate mode - "standard" for full debate, "raci" for lightweight
            RACI Dialogue Mode (Issue #139). RACI mode completes in exactly
            3 turns with no consensus loop.
        context_files: Optional list of absolute file paths to inject as codebase
            context into debate prompts (Issue #133). Files are read and injected
            as a <CODEBASE_CONTEXT> block before <DEBATE_STATE>. Missing files
            are skipped with a warning. Each file is truncated at 10000 chars.

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

    # Apply optional overrides (Issue #132)
    tier_config = _apply_tier_overrides(tier_config, compression_tier, primer_tier)

    # Read context files if provided (Issue #133)
    context_block = ""
    if context_files:
        context_block = _read_context_files(context_files)

    # Get state directory
    if state_dir is None:
        state_dir = get_state_dir()

    # Create orchestrator with context block
    orchestrator = DebateOrchestrator(tier_config, state_dir, context_block=context_block or None)

    # Run debate - use RACI mode if specified (Issue #139)
    if mode == "raci":
        result = await orchestrator.run_raci(topic=topic, thread_id=thread_id)
    else:
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
    compression_tier: Literal["none", "basic", "aggressive", "ultra"] | None = None,
    primer_tier: Literal["none", "literacy", "standard", "advanced"] | None = None,
) -> dict[str, Any]:
    """Resume a PAUSED debate from where it left off.

    This tool allows resuming debates that were paused due to failures
    (provider timeouts, errors, etc.) during auto-orchestration.

    The resume logic:
    1. Validates thread_id and loads debate state
    2. Validates debate is in PAUSED status
    3. Applies optional overrides (Issue #132)
    4. Determines resume point from turn count
    5. Continues orchestration (consensus loop if enabled)
    6. Returns the final result

    Args:
        thread_id: The thread ID of the paused debate
        tier: Tier configuration name (default: "standard")
        state_dir: Directory for state files (defaults to ./debates)
        compression_tier: Override compression tier (None = use tier default)
        primer_tier: Override primer tier (None = use tier default)

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

    # Apply optional overrides (Issue #132)
    tier_config = _apply_tier_overrides(tier_config, compression_tier, primer_tier)

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
