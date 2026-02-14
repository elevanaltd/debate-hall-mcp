"""RACI Turn Manifest Compiler.

This module implements the Turn Manifest Compiler pattern for RACI governance mode.
RACI mode is a factory at debate_init that compiles a governance topology into an
immutable TurnManifest. The engine then executes the manifest as a simple
index-based sequence.

Sequence: R(proposal) -> C*(advice) -> R(rebuttal) -> A(verdict) -> I*(observation)
If no consulted agents: R(proposal) -> A(verdict) -> I*(observation)
If no informed agents: R(proposal) -> C*(advice) -> R(rebuttal) -> A(verdict)

Architecture Decision: The Turn Manifest Compiler emerged from two independent
Wind/Wall/Door debates (standard and premium tier both converged on this design).
The I-agent OBSERVATION turns were added via a premium-tier debate that converged
on transforming Informed agents from ceremonial metadata into active post-verdict
participants providing domain-specific impact analysis.
"""

from pydantic import BaseModel, Field, model_validator

from debate_hall_mcp.state import TurnManifest, TurnSpec, TurnType

# Maximum number of consulted agents (bounded governance)
MAX_CONSULTED = 5

# Maximum number of informed agents (prevents cost explosions from I-turn LLM calls)
MAX_INFORMED = 3


class RACIConfig(BaseModel):
    """Configuration for a RACI governance debate.

    Defines the four RACI roles:
    - Responsible (R): The agent who does the work / proposes the action
    - Accountable (A): The agent who makes the final GO/NO-GO decision
    - Consulted (C): Agents whose advice is sought before the decision
    - Informed (I): Agents who provide post-verdict impact analysis (OBSERVATION turns)

    Validation rules:
    - responsible and accountable must not be empty strings
    - consulted list max 5 entries (bounded governance)
    - informed list max 3 entries (prevents cost explosions)
    - responsible != accountable (separation of concerns, case-insensitive)
    - All role names must be non-empty strings

    Disjointness rules (all comparisons are case-insensitive):
    - No duplicate entries within informed list (V1)
    - No duplicate entries within consulted list (V2)
    - Informed must be disjoint from Responsible (V3)
    - Informed must be disjoint from Accountable (V4)
    - Informed must be disjoint from Consulted (V5)

    Each role must have exactly one RACI designation.
    """

    responsible: str = Field(..., description="Role name for Responsible agent")
    accountable: str = Field(..., description="Role name for Accountable agent")
    consulted: list[str] = Field(
        default_factory=list, description="Role names for Consulted agents"
    )
    informed: list[str] = Field(default_factory=list, description="Role names for Informed agents")

    @model_validator(mode="after")
    def validate_raci_config(self) -> "RACIConfig":
        """Validate RACI configuration constraints."""
        # Responsible must be non-empty
        if not self.responsible or not self.responsible.strip():
            raise ValueError("responsible must be a non-empty string")

        # Accountable must be non-empty
        if not self.accountable or not self.accountable.strip():
            raise ValueError("accountable must be a non-empty string")

        # Separation of concerns: R != A (case-insensitive)
        if self.responsible.lower().strip() == self.accountable.lower().strip():
            raise ValueError(
                f"responsible and accountable must differ (separation of concerns): "
                f"both are '{self.responsible}'"
            )

        # Consulted max 5 entries
        if len(self.consulted) > MAX_CONSULTED:
            raise ValueError(
                f"consulted list exceeds maximum of {MAX_CONSULTED} entries: "
                f"got {len(self.consulted)}"
            )

        # All consulted entries must be non-empty
        for i, c in enumerate(self.consulted):
            if not c or not c.strip():
                raise ValueError(
                    f"consulted entry at index {i} is empty: all role names must be non-empty"
                )

        # Informed max 3 entries (prevents cost explosions from I-turn LLM calls)
        if len(self.informed) > MAX_INFORMED:
            raise ValueError(
                f"informed list exceeds maximum of {MAX_INFORMED} entries: "
                f"got {len(self.informed)}"
            )

        # All informed entries must be non-empty
        for i, inf in enumerate(self.informed):
            if not inf or not inf.strip():
                raise ValueError(
                    f"informed entry at index {i} is empty: all role names must be non-empty"
                )

        # --- Disjointness validation (V1-V5) ---
        # Normalize role names for comparison (lowercase + strip)
        norm_r = self.responsible.lower().strip()
        norm_a = self.accountable.lower().strip()
        norm_consulted = [c.lower().strip() for c in self.consulted]
        norm_informed = [inf.lower().strip() for inf in self.informed]

        # V1: No duplicate informed entries
        seen_informed: set[str] = set()
        for idx, norm_inf in enumerate(norm_informed):
            if norm_inf in seen_informed:
                raise ValueError(
                    f"duplicate in informed list: role '{self.informed[idx]}' appears "
                    f"more than once — each role must have exactly one RACI designation"
                )
            seen_informed.add(norm_inf)

        # V2: No duplicate consulted entries
        seen_consulted: set[str] = set()
        for idx, norm_c in enumerate(norm_consulted):
            if norm_c in seen_consulted:
                raise ValueError(
                    f"duplicate in consulted list: role '{self.consulted[idx]}' appears "
                    f"more than once — each role must have exactly one RACI designation"
                )
            seen_consulted.add(norm_c)

        # V3: Informed must be disjoint from Responsible
        for idx, norm_inf in enumerate(norm_informed):
            if norm_inf == norm_r:
                raise ValueError(
                    f"role '{self.informed[idx]}' appears in both responsible and "
                    f"informed — each role must have exactly one RACI designation"
                )

        # V4: Informed must be disjoint from Accountable
        for idx, norm_inf in enumerate(norm_informed):
            if norm_inf == norm_a:
                raise ValueError(
                    f"role '{self.informed[idx]}' appears in both accountable and "
                    f"informed — each role must have exactly one RACI designation"
                )

        # V5: Informed must be disjoint from Consulted
        consulted_set = set(norm_consulted)
        for idx, norm_inf in enumerate(norm_informed):
            if norm_inf in consulted_set:
                raise ValueError(
                    f"role '{self.informed[idx]}' appears in both consulted and "
                    f"informed — each role must have exactly one RACI designation"
                )

        return self


def compile_raci_manifest(config: RACIConfig) -> TurnManifest:
    """Compile RACI config into a deterministic turn manifest.

    Produces an immutable execution plan that the orchestrator follows as a
    simple index-based sequence.

    Sequence with consulted and informed agents:
        R(proposal) -> C*(advice) -> R(rebuttal) -> A(verdict) -> I*(observation)

    Sequence without consulted agents:
        R(proposal) -> A(verdict) -> I*(observation)

    Sequence without informed agents:
        R(proposal) -> C*(advice) -> R(rebuttal) -> A(verdict)

    Args:
        config: Validated RACIConfig with R, A, C, I assignments

    Returns:
        TurnManifest with ordered turn specifications
    """
    specs: list[TurnSpec] = []

    # 1. R: Responsible presents proposal
    specs.append(
        TurnSpec(
            role=config.responsible,
            turn_type=TurnType.PROPOSAL,
            raci_designation="R",
        )
    )

    # 2. C*: Each Consulted agent provides advice
    for consulted_agent in config.consulted:
        specs.append(
            TurnSpec(
                role=consulted_agent,
                turn_type=TurnType.ADVICE,
                raci_designation="C",
            )
        )

    # 3. R: Responsible synthesizes feedback (only if there are consulted agents)
    if config.consulted:
        specs.append(
            TurnSpec(
                role=config.responsible,
                turn_type=TurnType.REBUTTAL,
                raci_designation="R",
            )
        )

    # 4. A: Accountable renders GO/NO-GO verdict
    specs.append(
        TurnSpec(
            role=config.accountable,
            turn_type=TurnType.VERDICT,
            raci_designation="A",
        )
    )

    # 5. I*: Each Informed agent provides post-verdict observation
    for informed_agent in config.informed:
        specs.append(
            TurnSpec(
                role=informed_agent,
                turn_type=TurnType.OBSERVATION,
                raci_designation="I",
            )
        )

    return TurnManifest(
        specs=specs,
        responsible=config.responsible,
        accountable=config.accountable,
        consulted=list(config.consulted),
        informed=list(config.informed),
    )
