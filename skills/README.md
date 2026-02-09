# Debate Hall Skills

This directory contains skills for AI agents to orchestrate Wind/Wall/Door debates using debate-hall-mcp.

## Architecture (ADR-0005)

Skills follow the **Router + Focused Skills** pattern for token efficiency:

```
debate-hall (router) - ~50 lines
├── "Running automated debates" → MUST load /debate-hall-auto
├── "Manual turn-by-turn control" → MUST load /debate-hall-manual
├── "GitHub sync/ratification" → MUST load /debate-hall-github
└── "Admin operations" → MUST load /debate-hall-admin
```

## Skills

### debate-hall (Router)
**Purpose**: Routes to focused skills based on task
**Load**: Always loaded first, routes to specific skill

### debate-hall-auto
**Purpose**: Automated debate orchestration
**Tools**: `run_debate`, `resolve_question`, `resume_debate`, `search_decisions`
**Triggers**: "run debate", "resolve question", "tier selection"

### debate-hall-manual
**Purpose**: Manual turn-by-turn control
**Tools**: `init_debate`, `add_turn`, `get_debate`, `close_debate`, `pick_next_speaker`
**Triggers**: "manual debate", "turn by turn", "init debate"

### debate-hall-github
**Purpose**: GitHub integration
**Tools**: `github_sync_debate`, `ratify_rfc`, `human_interject`
**Triggers**: "github sync", "ratify rfc", "adr pr"

### debate-hall-admin
**Purpose**: Safety overrides and redaction
**Tools**: `force_close_debate`, `tombstone_turn`
**Triggers**: "force close", "tombstone", "admin"

## Token Savings

| Scenario | Old (monolith) | New (router + focused) | Savings |
|----------|----------------|------------------------|---------|
| Run debate | 336 lines | 51 + 80 = 131 lines | ~61% |
| Manual flow | 336 lines | 51 + 71 = 122 lines | ~64% |
| GitHub sync | 336 lines | 51 + 48 = 99 lines | ~71% |
| Admin ops | 336 lines | 51 + 33 = 84 lines | ~75% |

## Installation

### Claude Code

Copy skills to your Claude Code skills directory:

```bash
cp -r skills/debate-hall* ~/.claude/skills/
```

### Codex / Gemini CLI

Skills use standard YAML frontmatter format. Copy to your platform's skills directory.

## Migration from v3.0

The monolithic skill (v3.0) is preserved in `debate-hall/SKILL.md.deprecated` for reference during transition. New agents should use the router pattern.

## See Also

- **ADR-0005**: `docs/adr/adr-0005-skill-hierarchy-architecture.md`
- **Agents**: `agents/README.md` for Wind/Wall/Door definitions
- **Patterns**: `docs/examples/multi-model-debate-patterns.md`
