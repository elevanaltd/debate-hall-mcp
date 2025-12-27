# Wind/Wall/Door Agents

Canonical agent definitions for structured debate using the Wind/Wall/Door methodology.

## Files

| File | Purpose |
|------|---------|
| `wind-agent.oct.md` | PATHOS - The Explorer (divergent thinking) |
| `wall-agent.oct.md` | ETHOS - The Guardian (constraint validation) |
| `door-agent.oct.md` | LOGOS - The Synthesizer (integration) |
| `cognitions/` | Behavioral contracts (reference) |

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
