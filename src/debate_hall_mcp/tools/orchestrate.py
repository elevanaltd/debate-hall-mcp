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

Issue #133 Security Hardening (CRS+CE review):
- Root directory restriction to prevent arbitrary file read
- Bounded memory read (stream-read only needed chars)
- Aggregate limits (MAX_CONTEXT_FILES, MAX_TOTAL_CONTEXT_CHARS)
- XML attribute escaping in FILE path tags
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
from debate_hall_mcp.tools.topic_validation import validate_topic

logger = logging.getLogger(__name__)


def _validate_topic(topic: str) -> None:
    """Validate topic input (M4: CE Review mitigation).

    Delegates to shared validate_topic for consistent validation
    across init_debate and run_debate.

    Args:
        topic: The debate topic to validate

    Raises:
        ValueError: If topic is empty, whitespace-only, or too long
    """
    validate_topic(topic)


# Default max characters per context file (to prevent prompt explosion)
MAX_CHARS_PER_FILE = 10000

# Aggregate limits for context files (Issue #133 security hardening)
MAX_CONTEXT_FILES = 20
MAX_TOTAL_CONTEXT_CHARS = 100_000


def _escape_xml_attr(value: str) -> str:
    """Escape a string for safe use in an XML attribute value.

    Replaces &, ", <, > with their XML entity equivalents.

    Args:
        value: The raw string to escape

    Returns:
        XML-safe string suitable for attribute values
    """
    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _validate_context_file_path(file_path: str, root_dir: Path | None = None) -> Path:
    """Validate a context file path for security (Issue #133).

    Security checks:
    - No path traversal sequences (..)
    - Must be an absolute path
    - Must resolve to a real location (no symlink escape)
    - If root_dir is provided, resolved path must be contained within it

    Args:
        file_path: The file path to validate
        root_dir: Optional root directory to restrict file access scope.
            If provided, the resolved path must be relative to this directory.
            Symlinks that resolve outside the root are rejected.

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path contains traversal sequences, is not absolute,
            or resolves outside the allowed root directory
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

    # Resolve to handle symlinks - this follows symlinks to their real target
    resolved = path.resolve()

    # Root directory containment check
    if root_dir is not None:
        resolved_root = root_dir.resolve()
        if not resolved.is_relative_to(resolved_root):
            raise ValueError(
                f"Invalid context_file path '{file_path}': "
                f"resolves outside allowed root '{root_dir}'"
            )

    return resolved


def _read_context_files(
    context_files: list[str],
    max_chars_per_file: int = MAX_CHARS_PER_FILE,
    root_dir: Path | None = None,
) -> str:
    """Read and format context files for injection into debate prompts (Issue #133).

    Validates each file path for security, reads contents with bounded I/O,
    and formats them as a <CODEBASE_CONTEXT> block. Missing files emit a
    warning but do not cause failure (graceful degradation).

    Security hardening (CRS+CE review):
    - Root directory restriction via root_dir parameter
    - Bounded memory read: only reads max_chars_per_file + 1 bytes per file
    - Aggregate file count limit: MAX_CONTEXT_FILES (20)
    - Aggregate content size limit: MAX_TOTAL_CONTEXT_CHARS (100,000)
    - XML attribute escaping for file paths

    Args:
        context_files: List of absolute file paths to read
        max_chars_per_file: Maximum characters per file (default 10000).
            Files exceeding this limit are truncated with a notice.
        root_dir: Optional root directory to restrict file access scope.
            If provided, only files within this directory are allowed.

    Returns:
        Formatted string with CODEBASE_CONTEXT tags, or empty string if no
        files could be read.

    Raises:
        ValueError: If len(context_files) exceeds MAX_CONTEXT_FILES.
    """
    if not context_files:
        return ""

    # Aggregate limit: reject if too many files requested
    if len(context_files) > MAX_CONTEXT_FILES:
        raise ValueError(
            f"context_files count ({len(context_files)}) exceeds maximum " f"of {MAX_CONTEXT_FILES}"
        )

    file_blocks: list[str] = []
    total_chars_read = 0

    for file_path in context_files:
        # Check aggregate content limit before reading next file
        if total_chars_read >= MAX_TOTAL_CONTEXT_CHARS:
            logger.warning(
                "context_files: stopping - aggregate content limit reached " "(%d >= %d chars)",
                total_chars_read,
                MAX_TOTAL_CONTEXT_CHARS,
            )
            break

        try:
            validated_path = _validate_context_file_path(file_path, root_dir=root_dir)

            if not validated_path.is_file():
                logger.warning("context_files: skipping missing file: %s", file_path)
                continue

            # Bounded memory read: only read max_chars_per_file + 1 to detect
            # truncation without loading the entire file into memory
            with open(validated_path, encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars_per_file + 1)

            truncated = False
            if len(content) > max_chars_per_file:
                content = content[:max_chars_per_file]
                truncated = True

            total_chars_read += len(content)

            # XML attribute escaping for file path (prevent syntax breakage)
            escaped_path = _escape_xml_attr(file_path)
            block = f'<FILE path="{escaped_path}">\n{content}'
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
    mode: Literal["standard", "speed", "raci"] = "standard",
    context_files: list[str] | None = None,
    raci_config: dict[str, Any] | None = None,
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
        topic: The debate topic to explore (1-12000 chars, non-empty)
        tier: Tier configuration name (default: "standard")
        thread_id: Optional thread ID (auto-generated if not provided)
        state_dir: Directory for state files (defaults to ./debates)
        compression_tier: Override compression tier (None = use tier default)
        primer_tier: Override primer tier (None = use tier default)
        mode: Debate mode - "standard" for full debate, "speed" for lightweight
            Speed Dialogue Mode (Issue #139), "raci" for RACI governance mode.
            Speed completes in exactly 3 turns with no consensus loop.
            RACI uses a compiled turn manifest for deterministic governance.
        context_files: Optional list of absolute file paths to inject as codebase
            context into debate prompts (Issue #133). Files are read and injected
            as a <CODEBASE_CONTEXT> block before <DEBATE_STATE>. Missing files
            are skipped with a warning. Each file is truncated at 10000 chars.
        raci_config: Required when mode="raci". Dictionary with RACI assignments:
            - responsible: Role name for Responsible agent (required)
            - accountable: Role name for Accountable agent (required)
            - consulted: List of Consulted role names (optional, max 5)
            - informed: List of Informed role names (optional, max 3, post-verdict OBSERVATION turns)

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

    # Run debate - dispatch to appropriate mode
    if mode == "raci":
        # RACI mode requires raci_config
        if raci_config is None:
            raise ValueError("raci_config is required when mode='raci'")
        from debate_hall_mcp.raci import RACIConfig

        raci_config_obj = RACIConfig(**raci_config)
        result = await orchestrator.run_raci(
            topic=topic, raci_config=raci_config_obj, thread_id=thread_id
        )
    elif mode == "speed":
        result = await orchestrator.run_speed(topic=topic, thread_id=thread_id)
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
    # NOTE: context_files are NOT persisted across resume. The original
    # context_block from run_debate is lost when a debate is paused and
    # later resumed. A proper fix would require adding context_files to
    # DebateRoom state, which is a larger design change (Issue #133).
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
