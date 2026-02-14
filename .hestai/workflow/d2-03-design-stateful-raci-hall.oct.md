===D2_03_DESIGN===

META:
  TYPE::DESIGN_SPEC
  VERSION::"1.0"
  STATUS::APPROVED
  PARENT::"issue-163-stateful-raci-hall"
  AUTHOR::"Synthesizer (LOGOS)"
  DATE::"2026-02-14"

## APPROACH: The Hall as Workflow Container (Separated Model)

**Unified Concept:**
We adopt the **Separated Hall Model (Path 1)** as the structural foundation to satisfy Validator constraint S1/Verdict. However, we infuse it with the **TurnManifest Compiler (Path 2)** logic to drive dynamic workflows, and utilize **Hash-Chained Events (Path 3)** for immutable history tracking.

The `Hall` is not a `DebateRoom`. It is a higher-order **Workflow Container** that orchestrates a `RaciMatrix`. It maintains state (The "Hall") and spawns ephemeral `DebateRooms` or `SpeedConsultations` as child processes to resolve specific steps in the RACI flow. The `DebateOrchestrator` is refactored to be a generic "Turn Processor" that can handle either a fixed debate loop or a dynamic RACI manifest.

This approach resolves the tension between "Reuse Code" (Ideator) and "Don't Overload" (Validator) by reusing the *logic* (Orchestrator/Engine) but separating the *state* (Hall vs Room).

## DATA_MODEL

### HallState (New)
Managed by a new `HallManager`. Persisted separately from DebateRooms.
```python
class HallState(BaseModel):
    id: str = Field(default_factory=generate_id) # "hall-YYYY-MM-DD-topic"
    topic: str
    raci_matrix: RaciMatrix
    status: HallStatus = HallStatus.ACTIVE
    history: List[HallEvent] = [] # Linear timeline of decisions/actions
    context_files: List[str] = [] # Shared context for all child debates
    
    # Validation: Enforce S2 (Lock Discipline)
    # Child debates reference this ID but cannot modify this object directly.
```

### RaciMatrix (New)
Defines the dynamic participant structure.
```python
class RaciMatrix(BaseModel):
    responsible: str # The Proposer (e.g., "implementation-lead")
    accountable: str # The Decision Maker (e.g., "tech-lead")
    consulted: List[str] = [] # Advisors (e.g., ["security", "legal"])
    informed: List[str] = [] # Observers (e.g., ["product-owner"])
```

### DebateRoom (Extension)
Extended to support hierarchy without coupling.
```python
class DebateRoom(BaseModel):
    # ... existing fields ...
    parent_hall_id: Optional[str] = None # Soft Constraint S1
```

## MCP_TOOLS

1.  **`hall_open(topic: str, raci_config: Dict[str, Any]) -> str`**
    *   Initializes `HallState`.
    *   Compiles `RaciMatrix` -> `TurnManifest` (initial plan).
    *   Returns `hall_id`.

2.  **`hall_consult(hall_id: str, role: str, question: str) -> str`**
    *   **Mode:** Speed (2-turn).
    *   **Action:** Spawns a temporary `DebateOrchestrator` in `speed` mode.
    *   **Context:** Injects `HallState.history` (read-only).
    *   **Output:** Appends `ConsultationEvent` to `HallState.history`.

3.  **`hall_debate(hall_id: str, topic: str, tier: str = "standard") -> str`**
    *   **Mode:** Standard (Wind/Wall/Door).
    *   **Action:** Spawns a full `DebateOrchestrator`.
    *   **Context:** Injects `HallState.history` (read-only).
    *   **Output:** Returns `thread_id`. (Completion requires `hall_decide`).

4.  **`hall_decide(hall_id: str, decision: DecisionRecord) -> str`**
    *   **Action:** The Accountable role ratifies a decision.
    *   **Output:** Appends `DecisionEvent` to `HallState.history`.
    *   **Effect:** May trigger `hall_close` if objectives met.

5.  **`hall_close(hall_id: str) -> str`**
    *   **Action:** Finalizes the Hall. Generates summary.
    *   **Status:** `ACTIVE` -> `CLOSED`.

## ORCHESTRATOR_REFACTOR (Solving H1)

**Problem:** `DebateOrchestrator.run_turn` hardcodes `[Wind, Wall, Door]`.
**Solution:** `Dynamic Participant Injection`.

1.  **Abstract `Participant`:**
    Create a `Participant` class wrapping `role`, `prompt_path`, and `capabilities`.
    
2.  **Refactor `DebateOrchestrator`:**
    ```python
    class DebateOrchestrator:
        def __init__(self, ..., participants: List[Participant] = None):
            if not participants:
                self.participants = self._load_standard_tier() # Default Wind/Wall/Door
            else:
                self.participants = participants
    ```

3.  **Manifest-Driven Execution:**
    For RACI mode, the `DebateOrchestrator` doesn't loop fixed roles. It executes the next step in the `TurnManifest`.
    *   *Refinement:* The `HallManager` acts as the "Meta-Orchestrator", stepping through the RACI manifest and calling `DebateOrchestrator` (configured with specific participants) for each step.

## COMPRESSION_STRATEGY (Solving H3)

**Strategy:** Decision Record Stacking & Token Budgeting.

1.  **Stacking:** Only the `DecisionRecord` (summary + synthesis) of past child-debates is kept in the `HallState.history` context.
    *   *Math:* ~80 tokens/decision.
    *   *Budget:* 4096 tokens (Standard) / 80 = ~50 active decisions in context. Ample for most workflows.

2.  **Pre-flight Checks (H3):**
    Before `hall_consult` or `hall_debate`:
    ```python
    current_tokens = count_tokens(HallState.history)
    if current_tokens > MAX_CONTEXT_WINDOW - RESERVED_BUFFER:
        raise ContextLimitExceeded("Hall history full. Please summarize or archive.")
    ```

## LOCK_DISCIPLINE (Solving S2)

**Rule:** `Parent (Hall) -> Child (Room) -> Parent (Hall)`

1.  **Read:** Child receives `HallState` as *Read-Only Context* (injected into System Prompt).
2.  **Write:** Child writes *only* to its own `transcript` and `DecisionRecord`.
3.  **Commit:** Upon child completion, `HallManager` reads the Child's `DecisionRecord` and appends it to `HallState.history` as an immutable event.
    *   *Constraint:* Child NEVER calls `hall_update` directly.

## PARTICIPANT_TO_ROLE_MAPPING (Solving F1)

**Registry Bridge:**
We need a mapping from abstract RACI roles (e.g., "Security") to concrete System Prompts.

1.  **Configuration:** `config.py` adds `AGENT_REGISTRY`.
    ```python
    AGENT_REGISTRY = {
        "security": "agents/security-specialist.oct.md",
        "legal": "agents/policy-compliance.oct.md",
        "product": "agents/product-owner.oct.md",
        # ... standard roles ...
    }
    ```
2.  **Dynamic Loading:**
    When `hall_open` receives `raci_config={"consulted": ["security"]}`, it looks up "security" in `AGENT_REGISTRY`.
    *   *Fallback:* If not found, use a generic "Consultant" prompt with the role name injected as a variable.

## IMPLEMENTATION_SEQUENCE

1.  **Phase 1: Core Models & Registry (H2, F1)**
    *   Define `HallState`, `RaciMatrix`, `HallEvent`.
    *   Implement `AgentRegistry` and `Participant` abstraction.
    *   Add `hall_*` event types to `EventType` enum.

2.  **Phase 2: Orchestrator Refactor (H1)**
    *   Refactor `DebateOrchestrator` to accept dynamic `participants`.
    *   Ensure backward compatibility with standard Wind/Wall/Door debates.

3.  **Phase 3: Hall Manager & Tools (S1, S2)**
    *   Implement `HallManager` (CRUD for HallState).
    *   Implement `hall_open`, `hall_close`.
    *   Implement `hall_consult` (Speed mode integration).

4.  **Phase 4: Debate Integration & Compression (H3)**
    *   Implement `hall_debate` (Standard mode integration).
    *   Add token counting and pre-flight checks.
    *   Implement parent-context injection.

5.  **Phase 5: E2E Verification**
    *   Test full RACI flow: Open -> Consult -> Debate -> Decide -> Close.
