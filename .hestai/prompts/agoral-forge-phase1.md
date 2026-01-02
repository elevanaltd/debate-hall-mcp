# Agoral Forge Phase 1 - HO Orchestration Prompt

## Initialization

```
/bind ho "Agoral Forge Phase 1 - GitHub Integration Tools"
```

Then load orchestration skill:
```
Skill(ho-orchestrate)
```

---

## Mission

Implement the Agoral Forge GitHub Integration Tools (Issues #15, #16, #17) following HestAI methodology with enforced quality gates.

**Vision**: Transform GitHub Discussions/Issues into AI-assisted debate surfaces where:
> "The Discussion IS the Draft. The Synthesis IS the Law."

---

## Context

### Repository
- **Repo**: elevanaltd/debate-hall-mcp
- **Branch**: Create `agoral-forge-phase1` from `main`
- **Reference**: Issue #28 (umbrella), Issues #15, #16, #17

### Architecture Decision
Per ADR-0001 (Skills-Based OCTAVE Compression), debate-hall-mcp owns debate orchestration. The Agoral Forge tools extend this to GitHub as an external debate surface.

### Current State
- debate-hall-mcp has full debate orchestration (init, turn, get, close)
- OCTAVE output format implemented with security sanitization
- No GitHub integration exists yet

---

## Implementation Order (Strict Dependencies)

```
#15 github_sync_debate ─────────────────────┐
     │                                       │
     └──► #16 ratify_rfc ◄──────────────────┤
     │                                       │
     └──► #17 human_interject ◄─────────────┘
```

**CRITICAL**: #15 MUST be complete before starting #16 or #17.

---

## Issue #15: github_sync_debate

### Tool Specification
```python
@server.tool()
def github_sync_debate(
    thread_id: str,
    repo: str,
    target_id: str,
    target_type: str = "discussion"  # or "issue"
) -> dict[str, Any]:
    """
    Sync debate turns to GitHub Discussion/Issue comments.

    Posts new turns as formatted comments with cognition headers.
    Idempotent: tracks synced turns to avoid duplicates.
    """
```

### Implementation Tasks

1. **State Extension** - Add `github_binding` field to DebateRoom model:
   ```python
   github_binding: GitHubBinding | None = Field(
       default=None,
       description="GitHub Discussion/Issue binding for sync"
   )

   class GitHubBinding(BaseModel):
       repo: str
       target_id: str
       target_type: str  # "discussion" | "issue"
       last_synced_turn: int = 0
       comment_ids: dict[int, str] = {}  # turn_index -> comment_node_id
   ```

2. **GitHub API Client** - Create `src/debate_hall_mcp/github.py`:
   - GraphQL client for Discussions API
   - REST client for Issues API
   - Token via `GITHUB_TOKEN` env var
   - Rate limit handling

3. **Comment Formatting** - Each turn as:
   ```markdown
   ## 💨 Wind (PATHOS)
   **Model**: gemini-3-pro-preview | **Turn**: 1/12

   [Content from debate turn...]

   ---
   *Posted via [debate-hall-mcp](https://github.com/elevanaltd/debate-hall-mcp)*
   ```

4. **Tool Implementation** - `src/debate_hall_mcp/tools/github_sync.py`

5. **Tests** - Unit tests with mocked GitHub API

### Acceptance Criteria
- [ ] Posts new turns as formatted comments
- [ ] Tracks synced turns (no duplicates)
- [ ] Works with both Discussions and Issues
- [ ] Handles rate limits gracefully
- [ ] Stores comment node IDs for reference

---

## Issue #16: ratify_rfc

### Tool Specification
```python
@server.tool()
def ratify_rfc(
    thread_id: str,
    repo: str,
    target_id: str,
    adr_path: str = "docs/adr/"
) -> dict[str, Any]:
    """
    Generate ADR from Door synthesis and create PR.

    Requires: Debate must be closed with synthesis.
    """
```

### Implementation Tasks

1. **ADR Generator** - Extract Door synthesis, format as ADR:
   ```markdown
   # ADR-{number}: {title}

   ## Status
   Accepted

   ## Context
   {extracted from discussion body}

   ## Decision
   {Door synthesis content}

   ## Consequences
   {extracted from Wall constraints + Wind opportunities}

   ## References
   - Discussion: {discussion_url}
   - Debate transcript: {thread_id}
   ```

2. **PR Creation** - Via GitHub API:
   - Create branch `adr/{number}-{slug}`
   - Commit ADR file
   - Create PR with description

3. **Optional: Lock Discussion** - Mark as answered/resolved

4. **Tests** - Unit tests for ADR generation and mocked PR creation

### Acceptance Criteria
- [ ] Extracts Door synthesis from closed debate
- [ ] Generates well-formatted ADR
- [ ] Creates PR via GitHub API
- [ ] Handles edge cases (no Door turn, debate not closed)

---

## Issue #17: human_interject

### Tool Specification
```python
@server.tool()
def human_interject(
    thread_id: str,
    repo: str,
    target_id: str,
    comment_id: str
) -> dict[str, Any]:
    """
    Inject human GitHub comment into active debate as context.

    Detects which role was replied to and injects accordingly.
    """
```

### Implementation Tasks

1. **Comment Fetcher** - Fetch specific comment via GitHub API

2. **Parent Detection** - Determine injection context:
   | Reply To | Injection As |
   |----------|--------------|
   | Wind comment | PATHOS expansion/challenge |
   | Wall comment | Additional evidence |
   | Door comment | Clarification request |
   | Discussion body | General context |

3. **State Extension** - Add `injected_context` to DebateRoom:
   ```python
   injected_context: list[InjectedContext] = Field(default_factory=list)

   class InjectedContext(BaseModel):
       source: str  # "github_comment"
       comment_id: str
       content: str
       injection_type: str  # "pathos", "ethos", "logos", "general"
       processed_at: datetime
   ```

4. **Tests** - Unit tests for comment parsing and injection logic

### Acceptance Criteria
- [ ] Fetches comment from GitHub
- [ ] Detects parent comment for context
- [ ] Injects into debate state
- [ ] Marks as processed (idempotency)

---

## Quality Gates (MANDATORY)

Per ho-orchestrate skill, ALL implementation must pass:

### 1. Implementation Lead Delegation
```octave
Task(implementation-lead):
  GOVERNANCE::TRACED[T+R+A+C+E+D]
  PHASE::B2[FEATURE_IMPLEMENTATION]
  SKILLS::[
    "Load: Skill(build-execution)",
    "Read: ~/.claude/skills/build-execution/tdd-discipline.oct.md"
  ]
  TDD_MANDATE::failing_test->BEFORE->implementation[NO_EXCEPTIONS]
  TASK::{detailed_task}
  SUCCESS::{criteria}
```

### 2. CRS Review (Codex)
```python
mcp__pal__clink(
    cli_name="codex",
    role="code-review-specialist",
    prompt="Review {feature} for quality, security, architecture"
)
```
- Capture `continuation_id` for signoff
- On BLOCKING: Return to IL with rework guidance

### 3. CE Review (Gemini)
```python
mcp__pal__clink(
    cli_name="gemini",
    role="critical-engineer",
    prompt="Review {feature} for production readiness, scalability, security"
)
```
- Capture `continuation_id` for signoff
- On BLOCKING: Return to IL with rework guidance

### 4. Merge Only When
- CRS: GO
- CE: GO
- All tests pass
- ruff/mypy/black clean

---

## HO Constraints (NEVER VIOLATE)

```octave
NEVER::[
  write_src_code_directly,
  fix_implementation_bugs_directly,
  bypass_quality_gates,
  skip_TDD_in_IL_delegation,
  merge_without_CRS+CE_signoff
]

ALWAYS::[
  delegate_to_IL_with_build_execution_skill,
  capture_agent_ids_and_continuation_ids,
  require_CRS_then_CE_review_chain,
  maintain_pure_orchestration
]
```

---

## Debate Escalation (If Needed)

For complex architectural decisions, use debate-hall:

```python
# 1. Initialize
mcp__debate-hall__init_debate(
    thread_id="ho-agoral-{decision}-{timestamp}",
    topic="{decision_point}",
    mode="mediated",
    strict_cognition=True
)

# 2. Wind (Ideator) - Gemini
mcp__pal__clink(cli_name="gemini", role="ideator-catalyst", ...)

# 3. Wall (Validator) - Codex
mcp__pal__clink(cli_name="codex", role="validator", ...)

# 4. Door (Synthesizer) - Claude
# Synthesize and close

# 5. Apply synthesis to task
```

---

## File Structure (Expected)

```
src/debate_hall_mcp/
├── github.py                    # GitHub API client
├── tools/
│   ├── github_sync.py           # github_sync_debate tool
│   ├── ratify.py                # ratify_rfc tool
│   └── interject.py             # human_interject tool
├── state.py                     # Extended with GitHubBinding
└── server.py                    # Register new tools

tests/unit/
├── test_github.py               # GitHub client tests
└── tools/
    ├── test_github_sync.py
    ├── test_ratify.py
    └── test_interject.py
```

---

## Commit Convention

All commits must follow:
```
feat|fix|test|docs|chore: {description} (Issue #{number})

{body}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Success Criteria

Phase 1 is complete when:
- [ ] Issue #15 merged with CRS+CE approval
- [ ] Issue #16 merged with CRS+CE approval
- [ ] Issue #17 merged with CRS+CE approval
- [ ] All tests pass (including new integration tests)
- [ ] Documentation updated
- [ ] Issue #28 updated with Phase 1 completion status

---

## References

- [Issue #28 - Agoral Forge Umbrella](https://github.com/elevanaltd/debate-hall-mcp/issues/28)
- [Issue #15 - github_sync_debate](https://github.com/elevanaltd/debate-hall-mcp/issues/15)
- [Issue #16 - ratify_rfc](https://github.com/elevanaltd/debate-hall-mcp/issues/16)
- [Issue #17 - human_interject](https://github.com/elevanaltd/debate-hall-mcp/issues/17)
- [ADR-0001 - Skills-Based OCTAVE Compression](https://github.com/elevanaltd/debate-hall-mcp/blob/main/docs/adr/adr-0001-skills-based-octave-compression.md)
- [HestAI-MCP Issue #60 - Agoral Forge Vision](https://github.com/elevanaltd/HestAI-MCP/issues/60)
