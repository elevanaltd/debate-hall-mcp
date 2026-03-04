---
version: "0.2.0"
status: "active"
created: "2026-01-29"
adr: "adr-0002"
issue: "111"
---

# Auto-Orchestration Build Plan

## Overview

This build plan decomposes Issue #111 (run_debate auto-orchestration) into atomic, testable phases per ADR-0002.

**Branch**: `issue-111`
**ADR**: [ADR-0002](../adr/adr-0002-latent-async-auto-orchestration.md)

## Phase Structure

| Phase | Name | Description | Dependencies |
|-------|------|-------------|--------------|
| P1 | Foundation | Event schema, PAUSED status, tier config loading | None |
| P2 | Providers | ModelProvider protocol, CliProvider, OpenRouterProvider | P1 |
| P3 | Orchestrator | run_debate core loop, agent prompt generation | P1, P2 |
| P4 | Consensus | Wind/Wall approval turns, refinement loops | P3 |
| P5 | Event Delivery | get_events MCP tool, polling interface | P1 |
| P6 | Integration | End-to-end testing, documentation | P1-P5 |

---

## Phase 1: Foundation

**Goal**: Event schema, new PAUSED status, tier configuration loading

### Tasks

#### P1.1: Add PAUSED Status to DebateStatus Enum
- **File**: `src/debate_hall_mcp/state.py`
- **Change**: Add `PAUSED = "paused"` to DebateStatus enum
- **Test**: Unit test for new status value
- **TDD**: Write test first that expects PAUSED status

#### P1.2: Create DebateEvent Model
- **File**: `src/debate_hall_mcp/events.py` (new)
- **Schema**:
  ```python
  class DebateEvent(BaseModel):
      id: str                    # ULID for monotonic ordering
      thread_id: str
      event_type: EventType      # Enum: debate_started, turn_added, consensus_vote, error, debate_closed
      timestamp: datetime
      payload: dict
  ```
- **Test**: Model validation, serialization/deserialization
- **TDD**: Write tests for event creation and validation first

#### P1.3: Create Event Persistence Layer
- **File**: `src/debate_hall_mcp/events.py`
- **Functions**:
  - `append_event(thread_id, event) -> DebateEvent`
  - `load_events(thread_id, after=None, limit=50) -> list[DebateEvent]`
- **Storage**: `{state_dir}/{thread_id}.events.jsonl` (append-only JSONL)
- **Test**: Append, load, cursor-based pagination
- **TDD**: Write tests for append/load cycle first

#### P1.4: Create Tier Configuration Schema
- **File**: `src/debate_hall_mcp/config.py` (new)
- **Schema**:
  ```python
  class RoleConfig(BaseModel):
      provider: Literal["cli", "openrouter"]
      cli: str | None = None        # For cli provider
      model: str | None = None
      role: str | None = None       # System prompt role name
      prompt_file: str | None = None

  class TierSettings(BaseModel):
      consensus_required: bool = True
      max_turns: int = 12
      max_refinement_loops: int = 3

  class TierConfig(BaseModel):
      wind: RoleConfig
      wall: RoleConfig
      door: RoleConfig
      settings: TierSettings
  ```
- **Test**: YAML parsing, validation, defaults
- **TDD**: Write tests for valid/invalid tier configs first

#### P1.5: Create Tier Configuration Loader
- **File**: `src/debate_hall_mcp/config.py`
- **Function**: `load_tier_config(tier_name: str) -> TierConfig`
- **Resolution order**:
  1. `DEBATE_HALL_TIERS_FILE` env var
  2. `~/.debate-hall/tiers.yaml`
  3. Built-in defaults
- **Test**: Env override, file loading, defaults
- **TDD**: Write tests for resolution order first

### P1 Success Criteria
- [ ] PAUSED status added with tests
- [ ] DebateEvent model with validation tests
- [ ] Event persistence (append/load) with tests
- [ ] Tier config schema with validation tests
- [ ] Tier loader with resolution order tests
- [ ] All tests pass, ruff/mypy clean

---

## Phase 2: Providers

**Goal**: ModelProvider protocol with CLI and OpenRouter implementations

### Tasks

#### P2.1: Create ModelProvider Protocol
- **File**: `src/debate_hall_mcp/providers/__init__.py` (new package)
- **Protocol**:
  ```python
  class ModelProvider(Protocol):
      async def complete(
          self,
          system_prompt: str,
          user_prompt: str,
          model: str | None = None
      ) -> ProviderResponse

  class ProviderResponse(BaseModel):
      content: str
      model: str
      token_input: int | None = None
      token_output: int | None = None
  ```
- **Test**: Protocol conformance tests
- **TDD**: Write protocol test fixtures first

#### P2.2: Implement CliProvider
- **File**: `src/debate_hall_mcp/providers/cli.py`
- **Supported CLIs**: claude, codex, gemini
- **Implementation**:
  - `claude --print --system-prompt <prompt> --model <model> "<user>"`
  - `codex exec --model <model> "<combined_prompt>"`
  - `gemini --model <model> "<combined_prompt>"`
- **Test**: Mock subprocess, output parsing
- **TDD**: Write tests with mocked CLI responses first

#### P2.3: Implement OpenRouterProvider
- **File**: `src/debate_hall_mcp/providers/openrouter.py`
- **API**: POST to `https://openrouter.ai/api/v1/chat/completions`
- **Auth**: `OPENROUTER_API_KEY` env var
- **Test**: Mock HTTP responses, error handling
- **TDD**: Write tests with mocked API responses first

#### P2.4: Create Provider Factory
- **File**: `src/debate_hall_mcp/providers/__init__.py`
- **Function**: `create_provider(role_config: RoleConfig) -> ModelProvider`
- **Logic**: Route to CliProvider or OpenRouterProvider based on config
- **Test**: Factory routing logic
- **TDD**: Write tests for provider selection first

### P2 Success Criteria
- [ ] ModelProvider protocol defined
- [ ] CliProvider with subprocess handling and tests
- [ ] OpenRouterProvider with HTTP client and tests
- [ ] Provider factory with routing tests
- [ ] All tests pass, ruff/mypy clean

---

## Phase 3: Orchestrator

**Goal**: Core run_debate loop with agent prompt generation

### Tasks

#### P3.1: Create Agent Prompt Templates
- **File**: `src/debate_hall_mcp/prompts.py` (new)
- **Templates**:
  - Wind (PATHOS): Ideation, possibility expansion
  - Wall (ETHOS): Validation, constraint identification
  - Door (LOGOS): Synthesis, resolution
- **Include**: Thread ID and get_debate() instruction per ADR-0002
- **Test**: Template rendering with variables
- **TDD**: Write tests for prompt generation first

#### P3.2: Create Orchestrator Core
- **File**: `src/debate_hall_mcp/orchestrator.py` (new)
- **Class**: `DebateOrchestrator`
- **Methods**:
  - `__init__(tier_config: TierConfig)`
  - `async run(topic: str, thread_id: str | None = None) -> DebateResult`
- **Flow**: init_debate → Wind → Wall → Door → close_debate
- **Test**: Orchestration flow with mocked providers
- **TDD**: Write tests for full flow with mocks first

#### P3.3: Create run_debate MCP Tool
- **File**: `src/debate_hall_mcp/mcp/tools.py` (modify)
- **Tool**:
  ```python
  @tool
  async def run_debate(
      topic: str,
      tier: str = "standard",
      thread_id: str | None = None
  ) -> DebateResult
  ```
- **Integration**: Load tier, create orchestrator, run
- **Test**: MCP tool invocation
- **TDD**: Write tool integration test first

#### P3.4: Add Event Emission to Orchestrator
- **File**: `src/debate_hall_mcp/orchestrator.py`
- **Events**:
  - `debate_started` on init
  - `turn_added` on each turn
  - `debate_closed` on close
  - `error` on failures
- **Test**: Event emission at each stage
- **TDD**: Write tests verifying events emitted first

### P3 Success Criteria
- [ ] Agent prompts with get_debate() instruction
- [ ] Orchestrator core with mocked providers
- [ ] run_debate MCP tool registered
- [ ] Events emitted at each stage
- [ ] All tests pass, ruff/mypy clean

---

## Phase 4: Consensus

**Goal**: Wind/Wall approval mechanism with refinement loops

### Tasks

#### P4.1: Create Consensus Prompts
- **File**: `src/debate_hall_mcp/prompts.py`
- **Templates**:
  - Wind approval: Review Door's synthesis, APPROVE or REJECT
  - Wall approval: Review Door's synthesis, APPROVE or REJECT
- **Response format**: Structured APPROVE/REJECT with feedback
- **Test**: Prompt generation for consensus
- **TDD**: Write tests for approval prompt generation first

#### P4.2: Create Consensus Response Parser
- **File**: `src/debate_hall_mcp/consensus.py` (new)
- **Function**: `parse_consensus_response(content: str) -> ConsensusResult`
- **Result**: `{approved: bool, feedback: str | None}`
- **Test**: Parse various response formats
- **TDD**: Write tests for approval/rejection parsing first

#### P4.3: Implement Consensus Loop in Orchestrator
- **File**: `src/debate_hall_mcp/orchestrator.py`
- **Flow**:
  1. Door produces synthesis
  2. Wind reviews → APPROVE/REJECT
  3. Wall reviews → APPROVE/REJECT
  4. If both approve → close
  5. If reject → Door refines (up to max_refinement_loops)
  6. If max loops → STALEMATE
- **Events**: `consensus_vote` for each approval turn
- **Test**: Full consensus flow with various outcomes
- **TDD**: Write tests for approval/rejection/refinement paths first

#### P4.4: Add resume_debate Tool
- **File**: `src/debate_hall_mcp/mcp/tools.py`
- **Tool**:
  ```python
  @tool
  async def resume_debate(thread_id: str) -> DebateResult
  ```
- **Logic**: Resume from PAUSED status
- **Test**: Resume after simulated failure
- **TDD**: Write tests for resume from PAUSED first

### P4 Success Criteria
- [ ] Consensus prompts for Wind/Wall approval
- [ ] Response parser for APPROVE/REJECT
- [ ] Refinement loop with max iterations
- [ ] resume_debate tool for PAUSED recovery
- [ ] All tests pass, ruff/mypy clean

---

## Phase 5: Event Delivery

**Goal**: get_events MCP tool for polling interface

### Tasks

#### P5.1: Create get_events MCP Tool
- **File**: `src/debate_hall_mcp/mcp/tools.py`
- **Tool**:
  ```python
  @tool
  def get_events(
      thread_id: str,
      after: str | None = None,
      limit: int = 50
  ) -> list[DebateEvent]
  ```
- **Integration**: Use event persistence layer from P1
- **Test**: Polling with cursor, pagination
- **TDD**: Write tests for event retrieval first

#### P5.2: Add Event Filtering
- **File**: `src/debate_hall_mcp/events.py`
- **Enhancement**: Filter by event_type
- **Test**: Filter specific event types
- **TDD**: Write tests for filtering first

### P5 Success Criteria
- [ ] get_events MCP tool registered
- [ ] Cursor-based pagination working
- [ ] Event type filtering
- [ ] All tests pass, ruff/mypy clean

---

## Phase 6: Integration

**Goal**: End-to-end testing, documentation, release prep

### Tasks

#### P6.1: End-to-End Integration Tests
- **File**: `tests/integration/test_auto_orchestration.py` (new)
- **Tests**:
  - Full debate with mocked CLI providers
  - Consensus approval path
  - Consensus rejection + refinement path
  - Error recovery with PAUSED + resume
  - Event polling during debate
- **TDD**: Integration test suite first

#### P6.2: Create Default Tier Configurations
- **File**: `src/debate_hall_mcp/data/default_tiers.yaml` (new)
- **Tiers**: standard (CLI), cheap (OpenRouter), mixed
- **Test**: Defaults load correctly
- **TDD**: N/A (data file)

#### P6.3: Update README with Auto-Orchestration
- **File**: `README.md`
- **Sections**:
  - Auto-orchestration overview
  - Tier configuration guide
  - Provider setup (CLI vs OpenRouter)
- **Test**: N/A (documentation)

#### P6.4: Version Bump and Changelog
- **Files**: `pyproject.toml`, `CHANGELOG.md`
- **Changelog**: Document all new features
- **Test**: N/A (metadata)

### P6 Success Criteria
- [ ] Integration tests pass
- [ ] Default tiers included
- [ ] README updated
- [ ] All quality gates pass

---

## Quality Gates

Each phase requires:

1. **IL Implementation** with TDD discipline
2. **CRS Review** (Gemini) - Code quality, architecture alignment
3. **CE Review** (Codex) - Production readiness, security

### Review Checklist

- [ ] All tests pass (`pytest`)
- [ ] Type checking clean (`mypy`)
- [ ] Linting clean (`ruff check`)
- [ ] Formatting clean (`black --check`)
- [ ] No security issues
- [ ] ADR-0002 compliance verified
- [ ] Backward compatibility maintained

---

## Execution Order

```
P1 (Foundation) → CRS → CE
       ↓
P2 (Providers) → CRS → CE
       ↓
P3 (Orchestrator) → CRS → CE
       ↓
P4 (Consensus) → CRS → CE
       ↓
P5 (Event Delivery) → CRS → CE
       ↓
P6 (Integration) → CRS → CE → Release
```

## Notes

- Settings UI deferred to separate issue (frontend component)
- Streaming (SSE/WebSocket) deferred to v0.3.0
- Each phase is independently mergeable
