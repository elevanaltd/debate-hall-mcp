# Wind/Wall/Door Agents

Canonical agent definitions for structured debate using the Wind/Wall/Door methodology.

## Layered Identity Architecture

Agent identity is composed from three layers. Use as much depth as you need:

| Layer | Purpose | Size | Files |
|-------|---------|------|-------|
| **Cognitions** | Universal behavioral contracts | ~50 lines | `cognitions/*.oct.md` |
| **Agents** | Complete debate-ready implementations | ~130 lines | `*.oct.md` |
| **Specialists** | Full HestAI methodology binding | 200+ lines | Bring your own |

### Composition Patterns

```
MINIMAL:   Cognition only     → "Wind acts as PATHOS explorer"
STANDARD:  Full agent file    → "Wind with response format and boundaries"
ADVANCED:  Your own agents    → Custom specialists mapped to Wind/Wall/Door roles
```

### Using Specialists

Specialist agents (ideator, validator, synthesizer, etc.) can participate in debates by mapping to their cognition's role:

- **PATHOS specialists** (ideator, edge-optimizer) → speak as **Wind**
- **ETHOS specialists** (validator, critical-engineer) → speak as **Wall**
- **LOGOS specialists** (synthesizer, technical-architect) → speak as **Door**

Pass specialist identity via `agent_role` metadata in `debate_turn()` for audit trails.

## Files

| File | Purpose |
|------|---------|
| `wind-agent.oct.md` | PATHOS - The Explorer (divergent thinking) |
| `wall-agent.oct.md` | ETHOS - The Guardian (constraint validation) |
| `door-agent.oct.md` | LOGOS - The Synthesizer (integration) |
| `cognitions/` | Minimal behavioral contracts (standalone) |

## Installation

### GitHub Copilot

Copy agent files to your repository's `.github/agents/` directory:

```bash
# From this repo
cp agents/*.oct.md /path/to/your-repo/.github/agents/

# Rename to .agent.md format
cd /path/to/your-repo/.github/agents/
mv wind-agent.oct.md wind.agent.md
mv wall-agent.oct.md wall.agent.md
mv door-agent.oct.md door.agent.md
```

See [GitHub Copilot Custom Agents Configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration) for customization options.

### Claude Code

Copy agent files to your Claude Code agents directory:

```bash
cp agents/*.oct.md ~/.claude/agents/
```

### Other Systems

Copy and adapt the agent files as needed for your AI system. The `.oct.md` files are standard Markdown with YAML frontmatter.

## Usage

Once installed, agents can be invoked in debates:
- **Wind**: Expands possibility space, generates options
- **Wall**: Validates against constraints, identifies blockers
- **Door**: Synthesizes transcendent solutions from Wind/Wall tension

## Related

- [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp) - MCP server for debate orchestration
- Issue #20 - Distribution strategy decision
