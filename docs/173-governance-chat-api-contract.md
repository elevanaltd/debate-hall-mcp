# Issue #173: Headless Governance Chat API — Contract-First Specification

**Status**: DRAFT (D3 reviewed, conditions resolved)
**D3 Review**: APPROVE_WITH_CONDITIONS → conditions C1-C4 resolved, recommendations R1-R3 addressed
**Branch**: `headless-governance-chat-api`
**Epic**: Governance Chat — Headless API Surface
**Cross-repo**: workbench#16, HestAI-MCP#262

---

## Architectural Constraints

- **P5**: debate-hall is HEADLESS — no UI, workbench owns that
- **P6**: debate-hall is STANDALONE — no dependency on hestai-core
- **Provider ownership**: workbench picks provider/model; debate-hall records turns
- **Human-mediated first-class**: operator IS the facilitator, controls turn order
- **I1**: All state in DebateRoom server-side (cognitive state isolation)
- **I3**: All sessions enforce finite closure (max_turns, max_rounds)
- **I4**: Hash-chain transcript integrity maintained

---

## API Surface: New MCP Tools

### Tool 1: `consult`

**Purpose**: Create an advisory consultation session where an agent asks an expert for guidance.

```
consult(
    topic: str,                      # What the consultation is about
    advisor_role: str,               # Who to consult (any role name, e.g. "TMG", "CE")
    question: str,                   # The specific question being asked
    questioner_role: str = "Questioner",  # Who is asking (default: "Questioner")
    thread_id: str | None = None,    # Custom thread ID (auto-generated if omitted)
    context: str | None = None,      # Additional context for the advisor
    max_turns: int = 6,              # Consultation limit (I3 enforcement)
) -> dict
```

**Returns**:
```json
{
    "thread_id": "2026-02-21-tdd-guidance-consult-abc123",
    "status": "active",
    "session_type": "consultation",
    "question": "Best TDD pattern for async providers?",
    "advisor_role": "TMG",
    "questioner_role": "Questioner",
    "awaiting": "TMG",
    "turn_count": 1
}
```

**Validation** (C1):
- `advisor_role`: non-empty, non-whitespace, printable ASCII, max 128 chars (consistent with `Turn.validate_identity_string`)
- `questioner_role`: same constraints as `advisor_role`
- `advisor_role != questioner_role` (must be distinct participants)
- `topic`: non-empty string
- `question`: non-empty string

**Context handling** (C3): If `context` is provided, it is prepended to the question turn content as a clearly delimited block:
```
[CONTEXT]
{context}
[/CONTEXT]

{question}
```
This keeps context visible in the transcript (I4 auditability) and available to the advisor via `get_debate`.

**Behavior**:
1. Creates DebateRoom: `mode=mediated`, `session_type=consultation`
2. Records the question (with optional context prefix) as first turn (role=questioner_role)
3. Sets `expected_next_role = advisor_role`
4. Advisor responds via `add_turn(thread_id, role="TMG", content="...")`
5. Follow-up questions allowed via additional turns
6. Close with `close_debate()` when done

**Raises** (R2):
- `ValueError`: if `advisor_role` or `questioner_role` fail validation (empty, whitespace, non-ASCII, >128 chars)
- `ValueError`: if `advisor_role == questioner_role`
- `ValueError`: if `thread_id` already exists (duplicate session)
- `ValueError`: if `topic` or `question` is empty

**Conversation flow**:
```
Questioner: "Best TDD pattern for async providers?"
  ↓ (add_turn by workbench-dispatched advisor agent)
TMG: "For async providers, use the AAA pattern with..."
  ↓ (optional follow-up)
Questioner: "What about error cases?"
  ↓
TMG: "Error cases should use..."
  ↓
close_debate(synthesis="TMG advised AAA pattern with error boundaries...")
```

---

### Tool 2: `convene`

**Purpose**: Assemble a committee of agents for a group decision.

```
convene(
    topic: str,                      # What the committee is deciding
    members: list[str],              # Committee member roles (e.g. ["CRS", "CE"])
    brief: str,                      # The brief/description for the committee
    chair_role: str = "Chair",       # Who chairs the committee
    decision_type: str = "review",   # "go_nogo" | "vote" | "review"
    thread_id: str | None = None,    # Custom thread ID
    context: str | None = None,      # Additional context
    max_turns: int = 12,             # Committee limit (I3 enforcement)
) -> dict
```

**Returns**:
```json
{
    "thread_id": "2026-02-21-pr-review-committee-xyz789",
    "status": "active",
    "session_type": "committee",
    "decision_type": "go_nogo",
    "chair_role": "Chair",
    "members": ["CRS", "CE"],
    "awaiting": ["CRS", "CE"],
    "turn_count": 1
}
```

**Validation** (C1, C2):
- `members`: must contain at least 1 entry; each member must be non-empty, non-whitespace, printable ASCII, max 128 chars
- `chair_role`: same constraints; must NOT appear in `members` list (chair is distinct)
- `members` must not contain duplicates
- `decision_type`: must be one of `"go_nogo"`, `"vote"`, `"review"`
- `brief`: non-empty string
- `topic`: non-empty string

**Context handling** (C3): Same as `consult` — if `context` is provided, prepended to the brief turn as `[CONTEXT]...[/CONTEXT]` block.

**Behavior**:
1. Creates DebateRoom: `mode=mediated`, `session_type=committee`
2. Registers `participants` list (chair + members)
3. Records the brief (with optional context prefix) as first turn (role=chair_role)
4. Committee metadata tracks: `decision_type`, `members`, `votes`, `awaiting`
5. Chair manages order via `pick_next_speaker()`
6. Members respond via `add_turn()`
7. For `go_nogo`: each member's turn is parsed for GO/NO-GO
8. For `vote`: close triggers vote tally
9. Close with `close_debate()` when decision reached

**Raises** (R2):
- `ValueError`: if `members` is empty
- `ValueError`: if any member fails role validation (empty, whitespace, non-ASCII, >128 chars)
- `ValueError`: if `members` contains duplicates
- `ValueError`: if `chair_role` appears in `members`
- `ValueError`: if `decision_type` not in `("go_nogo", "vote", "review")`
- `ValueError`: if `thread_id` already exists

**Open question** (R3): Vote tally algorithm for `decision_type="vote"` is TBD. Will be specified in Phase 3. Options: simple majority, unanimous, configurable threshold. The `CommitteeMetadata.responses` dict captures raw votes; tally logic will be added to `close_debate` or a new `tally_votes` helper.

**Conversation flow (go_nogo)**:
```
Chair: "Review PR #491 implementation for production readiness"
  ↓ pick_next_speaker("CRS")
CRS: "GO — code quality meets standards, coverage at 92%"
  ↓ pick_next_speaker("CE")
CE: "NO-GO — security concern in auth module line 47"
  ↓ (committee has split decision)
Chair can: pick another member, request clarification, or close
  ↓
close_debate(synthesis="NO-GO: CE identified security concern...")
```

---

---

### Existing Tool Enhancement: `get_debate` Response Contract (C4)

When `get_debate` is called on a consultation or committee session, the response includes the new fields:

**For `session_type=consultation`**:
```json
{
    "thread_id": "...",
    "topic": "...",
    "mode": "mediated",
    "status": "active",
    "session_type": "consultation",
    "participants": [
        {"role": "Questioner", "joined_at": "2026-02-21T..."},
        {"role": "TMG", "joined_at": "2026-02-21T..."}
    ],
    "turn_count": 2,
    "expected_next_role": "Questioner"
}
```

**For `session_type=committee`**:
```json
{
    "thread_id": "...",
    "topic": "...",
    "mode": "mediated",
    "status": "active",
    "session_type": "committee",
    "participants": [
        {"role": "Chair", "joined_at": "2026-02-21T..."},
        {"role": "CRS", "joined_at": "2026-02-21T..."},
        {"role": "CE", "joined_at": "2026-02-21T..."}
    ],
    "committee_metadata": {
        "decision_type": "go_nogo",
        "members": ["CRS", "CE"],
        "responses": {"CRS": "GO"},
        "awaiting": ["CE"],
        "decision": null
    },
    "turn_count": 3,
    "expected_next_role": null
}
```

**For `session_type=debate`** (existing behavior): `session_type` field is included as `"debate"`. `participants` and `committee_metadata` are omitted (null). No change to existing response shape beyond the new field.

**Note for workbench#16**: The workbench renders the chat UI by polling `get_debate(include_transcript=True)`. The `session_type` field determines which UI layout to use. The `committee_metadata.awaiting` list drives the "waiting for..." indicator. The `participants` list drives avatar/role display.

---

### Foundation Change: Flexible Roles in Mediated Mode

**Current limitation**: `pick_next_speaker` only accepts `("Wind", "Wall", "Door")`.

**Required change**: Accept any valid role string in mediated mode (replacing the `("Wind", "Wall", "Door")` restriction).

**Role validation rule** (C1): Roles must be non-empty, non-whitespace, printable ASCII strings, max 128 chars. This matches the existing `Turn.validate_identity_string` pattern used for `agent_role` and `model` fields.

**Impact**:
- `tools/pick.py`: Replace `VALID_ROLES = ("Wind", "Wall", "Door")` with general string validation. Accept any valid role string in mediated mode.
- `tools/turn.py`: Cognition validation (PATHOS/ETHOS/LOGOS) applies only when `role in ("Wind", "Wall", "Door")`. Non-triad roles skip cognition validation — the `cognition` field is accepted as-is (including `None`).
- `engine.py`: `get_next_speaker()` unchanged (mediated already returns `None`)
- Backward compatible: Wind/Wall/Door still work exactly as before, including cognition enforcement

---

## State Model Extensions

### DebateRoom additions

```python
# New fields on DebateRoom
session_type: SessionType = SessionType.DEBATE  # debate | consultation | committee
participants: list[Participant] | None = None   # Registered participant roles
committee_metadata: CommitteeMetadata | None = None  # Committee-specific tracking
```

### New models

```python
class SessionType(StrEnum):
    DEBATE = "debate"
    CONSULTATION = "consultation"
    COMMITTEE = "committee"

class Participant(BaseModel):
    role: str                    # Role name (e.g. "CRS", "TMG") — validated: non-empty, printable ASCII, max 128 chars
    joined_at: datetime          # When registered
    # NOTE (R1): `authority` field (RACI designation) is deferred to future phase.
    # Rationale: neither consult nor convene tool behavior references authority in any
    # conditional logic. Adding it now would be an unvalidated, unused field. When RACI
    # integration is needed, add AuthorityType enum with enforcement.

class CommitteeMetadata(BaseModel):
    decision_type: str           # "go_nogo" | "vote" | "review"
    members: list[str]           # Expected member roles
    responses: dict[str, str]    # role -> "GO" | "NO-GO" | vote content
    awaiting: list[str]          # Members who haven't responded
    decision: str | None = None  # Final decision when closed
```

---

## Backward Compatibility

All changes are ADDITIVE:
- Existing tools (`init_debate`, `add_turn`, etc.) unchanged
- New `session_type` field defaults to `"debate"` — existing rooms unaffected
- Wind/Wall/Door roles continue to work in all modes
- RACI mode unchanged (uses TurnManifest)
- New tools are NEW registrations, not modifications

---

## What debate-hall Does NOT Own

Per P5/P6 and cross-repo boundaries:

| Concern | Owner | NOT debate-hall |
|---------|-------|----------------|
| Which model/provider per role | workbench agent registry | |
| Agent identity/constitution | hestai-core-mcp | |
| UI for governance chat | workbench panel | |
| CLI spawning | workbench dispatch | |
| Persistent agent registry | workbench | |

debate-hall owns: **session lifecycle, turn validation, transcript integrity, committee tracking, finite closure**.

---

## Phase Ordering

### Phase 1: Foundation (MUST exist before consult/convene)
- Flexible roles in mediated mode
- SessionType enum and Participant model
- State model extensions to DebateRoom

### Phase 2: consult tool
- `tools/consult.py` implementation
- Server registration
- TDD: unit tests + integration

### Phase 3: convene tool
- CommitteeMetadata model
- `tools/convene.py` implementation
- Vote/GO-NO-GO tracking
- Server registration
- TDD: unit tests + integration

### Phase 4: Integration
- End-to-end test: full consult flow
- End-to-end test: full committee flow
- Cross-tool interaction tests (consult → add_turn → close)

### Phase 5: Housekeeping
- Close/relabel #112 (absorbed into workbench per P5)
- Update PROJECT-CONTEXT.oct.md
