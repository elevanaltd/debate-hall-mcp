"""RACI Turn Manifest Compiler.

This module implements the Turn Manifest Compiler pattern for RACI governance mode.
RACI mode is a factory at debate_init that compiles a governance topology into an
immutable TurnManifest. The engine then executes the manifest as a simple
index-based sequence.

Sequence: R(proposal) -> C1(advice) -> C2(advice) -> ... -> R(rebuttal) -> A(verdict)
If no consulted agents: R(proposal) -> A(verdict)

Architecture Decision: The Turn Manifest Compiler emerged from two independent
Wind/Wall/Door debates (standard and premium tier both converged on this design).
"""

from pydantic import BaseModel, Field, model_validator

from debate_hall_mcp.state import TurnManifest, TurnSpec, TurnType

# Maximum number of consulted agents (bounded governance)
MAX_CONSULTED = 5


class RACIConfig(BaseModel):
    """Configuration for a RACI governance debate.

    Defines the four RACI roles:
    - Responsible (R): The agent who does the work / proposes the action
    - Accountable (A): The agent who makes the final GO/NO-GO decision
    - Consulted (C): Agents whose advice is sought before the decision
    - Informed (I): Agents who are notified of the outcome (no turns)

    Validation rules:
    - responsible and accountable must not be empty strings
    - consulted list max 5 entries (bounded governance)
    - responsible != accountable (separation of concerns)
    - All role names must be non-empty strings
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

        # Separation of concerns: R != A
        if self.responsible == self.accountable:
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

        # All informed entries must be non-empty
        for i, inf in enumerate(self.informed):
            if not inf or not inf.strip():
                raise ValueError(
                    f"informed entry at index {i} is empty: all role names must be non-empty"
                )

        return self


def compile_raci_manifest(config: RACIConfig) -> TurnManifest:
    """Compile RACI config into a deterministic turn manifest.

    Produces an immutable execution plan that the orchestrator follows as a
    simple index-based sequence.

    Sequence with consulted agents:
        R(proposal) -> C1(advice) -> C2(advice) -> ... -> R(rebuttal) -> A(verdict)

    Sequence without consulted agents:
        R(proposal) -> A(verdict)

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

    return TurnManifest(
        specs=specs,
        responsible=config.responsible,
        accountable=config.accountable,
        consulted=list(config.consulted),
        informed=list(config.informed),
    )
