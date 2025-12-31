# Wind/Wall/Door Agents

Canonical agent definitions for structured debate using the Wind/Wall/Door methodology.

## Agent Configuration Tiers

Evidence from replication studies shows specialist agents search **different solution spaces** than basic agents. Choose your tier based on debate complexity:

### Tier 1: Basic (Included)
| Agent | Cognition | Behavior |
|-------|-----------|----------|
| `wind-agent.oct.md` | PATHOS | Explores obvious paths |
| `wall-agent.oct.md` | ETHOS | Balanced judgment |
| `door-agent.oct.md` | LOGOS | Balanced integration |

**Use for:** Quick decisions, standard debates

### Tier 2: Specialist (Recommended for complex debates)
| Specialist | Maps to | Behavioral Difference |
|------------|---------|----------------------|
| `ideator` | Wind | Converges to minimal elegant solutions |
| `edge-optimizer` | Wind | Discovers hidden vectors others miss |
| `validator` | Wall | Cold truth, uncompromising reality |
| `critical-engineer` | Wall | Production readiness focus |
| `synthesizer` | Door | Breakthrough transcendence (1+1=3) |

**Use for:** Architectural decisions, security reviews, innovation

### Tier 3: Domain Mix
Combine specialists based on the topic:
- **Security:** edge-optimizer + critical-engineer + technical-architect
- **Innovation:** ideator + validator + synthesizer
- **Architecture:** ideator + critical-engineer + holistic-orchestrator

### Using Specialists in Debates

Specialists map to their cognition's debate role:
- **PATHOS specialists** → speak as **Wind**
- **ETHOS specialists** → speak as **Wall**
- **LOGOS specialists** → speak as **Door**

Pass identity via `agent_role` metadata in `debate_turn()` for audit trails.

See [multi-model-debate-patterns.md](../docs/examples/multi-model-debate-patterns.md) for evidence and recipes.

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
