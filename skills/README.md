# Debate Hall Skills

This directory contains skills for AI agents to orchestrate Wind/Wall/Door debates using debate-hall-mcp.

## Quick Start

One skill for comprehensive debate orchestration:

1. **debate-hall** – Complete workflow for multi-perspective debate orchestration

## Skill Overview

### debate-hall
**Domain**: Orchestration (LOGOS)
**Purpose**: Wind/Wall/Door debate workflow, patterns, and integration

Enables agents to:
- Initialize and run structured debates
- Use fixed or mediated mode
- Apply Flash Debate pattern for quick decisions
- Apply Socratic pattern for premise clarification
- Integrate with multi-model specialist debates (Claude Wind, GPT Wall, Gemini Door per M019)
- Know when to escalate to debate-hall from orchestration workflows

**Triggers**: `debate`, `wind wall door`, `dialectic`, `multi-perspective`, `structured decision`, `architecture decision`

## Installation

### Claude Code

Copy the skill to your Claude Code skills directory:

```bash
cp -r skills/debate-hall ~/.claude/skills/
```

### Codex / Gemini CLI

Skills use standard YAML frontmatter format. Copy to your platform's skills directory or reference directly.

### Other Systems

Each skill is in `skill-name/SKILL.md` format with YAML frontmatter. Adapt to your platform's skill loading mechanism.

## For Developers

Skills follow the OCTAVE skills specification:

- **Name**: `debate-hall`
- **Description**: Includes triggers and use cases
- **Format**: YAML frontmatter + Markdown body
- **Tools**: `mcp__debate-hall__*` for MCP tool access
- **Size**: Under 500 lines (skill constraint)

## See Also

- **Agents**: `agents/README.md` for Wind/Wall/Door agent definitions
- **Patterns**: `docs/examples/multi-model-debate-patterns.md` for real debate examples
- **Contracts**: `docs/architecture/wall-content-contract.oct.md` for Wall semantic structure
