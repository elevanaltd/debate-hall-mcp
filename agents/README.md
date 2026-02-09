# Wind/Wall/Door Agents

Canonical agent definitions for structured debate using the Wind/Wall/Door methodology.

## Understanding the Three-Layer Identity Model

Debates involve three distinct identity concepts that should not be confused:

### 1. Position (Structural Role in Debate)

**What it is:** The structural turn order in a debate sequence.

| Position | Function | Sequence |
|----------|----------|----------|
| **Wind** | Explores possibilities, expands solution space | 1st |
| **Wall** | Validates against constraints, grounds proposals | 2nd |
| **Door** | Synthesizes a third-way resolution from tension | 3rd |

Positions are **fixed structural elements** of the Wind/Wall/Door dialectic. Every debate follows: Wind -> Wall -> Door (repeated until synthesis).

### 2. Cognition (Thinking Mode)

**What it is:** The cognitive style or reasoning approach.

| Cognition | Mode | Mapped Position |
|-----------|------|-----------------|
| **PATHOS** | Divergent thinking - intuition, possibility, emotion | Wind |
| **ETHOS** | Convergent thinking - evidence, standards, constraints | Wall |
| **LOGOS** | Integrative thinking - synthesis, logic, resolution | Door |

Cognition modes are **mapped to positions** but conceptually distinct. PATHOS agents think divergently (suited for Wind position), ETHOS agents think convergently (suited for Wall position), LOGOS agents think integratively (suited for Door position).

### 3. Agent Role (Expertise Identity)

**What it is:** The operational identity with domain expertise and behavioral contracts.

| Role | Cognition | Position | Expertise |
|------|-----------|----------|-----------|
| `ideator` | PATHOS | Wind | Innovation, minimal elegant solutions |
| `edge-optimizer` | PATHOS | Wind | Hidden vectors, attack surfaces |
| `validator` | ETHOS | Wall | Cold truth, uncompromising validation |
| `critical-engineer` | ETHOS | Wall | Production readiness, system impact |
| `synthesizer` | LOGOS | Door | Breakthrough transcendence (1+1=3) |

Agent roles are **configured in tiers.yaml** and provide domain expertise beyond basic cognition. The `role` field in tier configuration specifies which agent identity speaks for each position.

### How They Connect

```
Position (Wind)  <-- speaks in -->  Cognition (PATHOS)  <-- embodied by -->  Role (ideator)
    |                                    |                                      |
 Structural                          Thinking                              Expertise
 turn order                          style                                 identity
```

**Example:** In a security-focused debate:
- **Wind position** uses **PATHOS cognition** embodied by **edge-optimizer role**
- **Wall position** uses **ETHOS cognition** embodied by **critical-engineer role**
- **Door position** uses **LOGOS cognition** embodied by **synthesizer role**

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
