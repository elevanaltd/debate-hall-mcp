"""Agent templates for Wind/Wall/Door debates.

This subpackage contains the agent definition files that are bundled with
the debate-hall-mcp package. These files can be synced to a project's
.github/agents/ directory using the CLI.

Agent files:
    - wind.agent.md: Wind (PATHOS) - The Explorer
    - wall.agent.md: Wall (ETHOS) - The Guardian
    - door.agent.md: Door (LOGOS) - The Synthesizer
"""

from __future__ import annotations

__all__ = ["AGENT_NAMES"]

# Agent names available in this package
AGENT_NAMES = ["wind", "wall", "door"]
