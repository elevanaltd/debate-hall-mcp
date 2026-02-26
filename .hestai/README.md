# .hestai/ - Three-Tier Architecture

This directory implements the three-tier `.hestai` architecture for debate-hall-mcp.

## Tier Overview

| Tier | Path | Purpose | Git Status |
|------|------|---------|------------|
| 1 | `.hestai-sys/` | System governance (MCP-delivered, read-only) | Gitignored |
| 2 | `.hestai/` | Project governance (north-star, decisions, rules) | Committed, PR-controlled |
| 3 | `.hestai/state/` | Working state (context, reports, sessions) | Gitignored (symlink) |

## Tier 1: System Governance (`.hestai-sys/`)

Delivered by the HestAI MCP server at session startup. Contains:
- `CONSTITUTION.md` - System-wide governance rules
- `library/skills/` - Agent skills and templates
- System configuration

**Not committed to git.** Read-only, managed by MCP infrastructure.

## Tier 2: Project Governance (`.hestai/`)

Committed to the repository. Changes require a PR. Contains:
- `north-star/` - Canonical North Star documents only (`000-*-NORTH-STAR*`)
- `rules/` - Project standards, methodology, workflow guidance, implementation specs
- `issues/` - Project issue tracking documents
- `octave-validation-tests/` - OCTAVE format test fixtures
- `README.md` - This file

## Tier 3: Working State (`.hestai/state/`)

Symlinked to the shared `.hestai-state/` directory in the main repo root:

```
.hestai/state/ -> /path/to/debate-hall-mcp/.hestai-state/
```

This allows all worktrees to share the same working state. Contains:

- `context/` - Project context dashboards (PROJECT-CONTEXT.oct.md, project-ideas.oct.md)
- `reports/` - Investigation reports, briefings, audit logs
- `sessions/` - Session archives (pending, active, archived)

**Not committed to git.** The symlink is created by the session startup hook.

## Session Startup Hook

The session startup hook creates the symlink automatically:

```bash
ln -sfn /path/to/debate-hall-mcp/.hestai-state .hestai/state
```

This ensures `.hestai/state/` is available in every worktree without duplicating
working state files.
