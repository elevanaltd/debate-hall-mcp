===DEBATE_HALL_PROJECT_IDEAS===

META:
  TYPE::IDEAS_DOCUMENT
  VERSION::1.0
  STATUS::DRAFT
  VISIBILITY::PROJECT_INTERNAL
  CONTEXT::"Transferred from HestAI-MCP context-steward-benefits"

## Overview
This document captures high-level ideas, potential features, and future directions for Debate Hall MCP, specifically regarding its integration into the broader HestAI "Integrity Engine" architecture.

## Product Vision: The Governance Communication Bus
Debate Hall evolves from a "Conflict Resolution Tool" into the central "Governance Communication Bus" for HestAI. It becomes the structural mechanism for high-gravity decisions and cross-role alignment.

## Potential Features

### 1. RACI Dialogue Mode (Recipe)
- **Concept**: A lightweight debate mode designed for rapid decision alignment, mapping Debate Hall roles to RACI roles.
- **Mapping**:
  - **Wind (Responsible)**: Proposes the action.
  - **Wall (Consulted)**: Validates constraints/risks (or yields).
  - **Door (Accountable)**: Ratifies the decision.
  - **Informed**: Receives the immutable transcript.
- **Mechanism**:
  - Single-Round / Speed Mode.
  - "Zero-Friction" option where Wall yields immediately if no objections.
- **Value**: Front-loaded alignment. Prevents "revert later" chaos by enforcing "check now" structure.

### 2. Decision Gravity Integration
- **Concept**: Debate Hall acts as the routing destination for High-Gravity decisions.
- **Trigger**: HestAI System Steward detects a "High Gravity" change (Score > 60).
- **Action**: Routes the agent to `debate-hall-mcp` to resolve the path.
- **Output**: The Debate ID becomes the "Decision Record" required to proceed.

### 3. Integrity Engine Support (Coherence Debates)
- **Concept**: Specialized recipes to resolve "Coherence vs. Velocity" conflicts (The Truth Paradox).
- **Scenario**: 3AM Hotfix vs. Strict Integrity.
- **Role**: Debate Hall orchestrates the "Break Glass" justification.
  - **Wind**: Argues for Velocity (Emergency).
  - **Wall**: Argues for Integrity (Broken Windows).
  - **Door**: Grants "Debt Lock" (Bypass + Blocking Debt).

### 4. "Context Compiler" Integration
- **Concept**: Debate Hall transcripts are not just logs; they are *compiled* into the project context.
- **Mechanism**:
  - `close_debate` output is structured OCTAVE.
  - This output is injected into `.hestai/context/decisions/` as a "Compiled Decision".
  - Future agents "read" this decision as part of their binding context.

## Future Roadmap
- **Decision API**: External tools post "Decision Requests" to Debate Hall.
- **Automated Facilitator**: An LLM-based facilitator that actively manages turn-taking and focus (beyond simple `pick_next_speaker`).

## Constraints and Considerations
- **Latency**: RACI mode must be fast (seconds, not minutes).
- **Fatigue**: Must avoid "Debate Fatigue". Low-gravity decisions should bypass this system.

## Validation Requirements
- Ensure new recipes align with Wind/Wall/Door cognitive architectures.
- Validate that "RACI Mode" produces auditable decision records.

## Change Log
- Document created: 2026-01-10 (Transferred from HestAI-MCP analysis)

===END===
