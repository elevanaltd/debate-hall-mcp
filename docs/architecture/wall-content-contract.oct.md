===WALL_CONTENT_CONTRACT===

META:
  TYPE::"CONTENT_CONTRACT"
  VERSION::"1.0"
  PURPOSE::"Define semantic structure for Wall agent blocking turns"
  STATUS::ACTIVE

§1::CONTEXT

ORIGIN::[
  DEBATE::blocks-as-opportunities-2025-12-25,
  INSIGHT::"Non-existence is not a constraint - it is an opportunity",
  PROBLEM::"Wall agents block on missing artifacts without distinguishing constraint from construction opportunity",
  SOLUTION::"Content contract defines semantic structure; protocol remains pure"
]

PRINCIPLE::[
  "The debate-hall-mcp protocol is a conduit, not a judge",
  "Semantic distinctions belong in content, where agents express nuance",
  "Protocol ensures integrity and ordering; callers interpret meaning",
  "Blocking semantics guide response via readable content, not hidden metadata"
]

§2::BLOCK_NATURE_DISTINCTION

CONSTRAINT_BLOCK::[
  DEFINITION::"Immutable reality that cannot be changed by construction",
  EXAMPLES::[
    "Security policy violation",
    "Type system incompatibility",
    "Physical law constraint",
    "Resource exhaustion",
    "Permission denial"
  ],
  RESPONSE::"Redirect or abandon path"
]

OPPORTUNITY_BLOCK::[
  DEFINITION::"Void that invites construction - absence is precondition for creation",
  EXAMPLES::[
    "File does not exist",
    "Function not implemented",
    "Test not written",
    "Documentation missing",
    "Configuration absent"
  ],
  RESPONSE::"Specify what to build"
]

§3::REQUIRED_STRUCTURE

WALL_BLOCK_TURN_FORMAT::
```octave
===WALL_BLOCK===

VERDICT::BLOCKED|APPROVED|CONDITIONAL

IF_VERDICT==BLOCKED::[
  BLOCK_NATURE::CONSTRAINT|OPPORTUNITY,

  IF_CONSTRAINT::[
    IMMUTABLE_REALITY::"Description of constraint that cannot be changed",
    VIOLATION::"What specifically violates this constraint",
    REDIRECT::"Alternative path if one exists"
  ],

  IF_OPPORTUNITY::[
    VOID_IDENTIFIED::"What does not exist but could",
    CONSTRUCTION_SPEC::"What exactly needs to be built",
    ACCEPTANCE_CRITERIA::"How to know construction succeeded"
  ],

  REMEDIATION_REQUEST::"Specific action to transform block into path"
]

===END_WALL_BLOCK===
```

§4::ENFORCEMENT

VALIDATION_APPROACH::[
  LOCATION::"Orchestrator/caller responsibility, not protocol",
  METHOD::"Parse OCTAVE content keys before accepting Wall turn",
  FAILURE::"Reject turn if BLOCKED verdict lacks required structure"
]

BACKWARD_COMPATIBILITY::[
  EXISTING_DEBATES::"Remain valid - no migration required",
  NEW_DEBATES::"Orchestrators MAY enforce this contract",
  ADOPTION::"Progressive - agents adopt as they are updated"
]

§5::EXAMPLES

EXAMPLE_CONSTRAINT_BLOCK::
```octave
===WALL_BLOCK===

VERDICT::BLOCKED

BLOCK_NATURE::CONSTRAINT

IMMUTABLE_REALITY::"RLS policy requires authenticated user context"
VIOLATION::"Proposed query executes without auth token validation"
REDIRECT::"Wrap query in authenticated session context"

REMEDIATION_REQUEST::"Add auth middleware before database access layer"

===END_WALL_BLOCK===
```

EXAMPLE_OPPORTUNITY_BLOCK::
```octave
===WALL_BLOCK===

VERDICT::BLOCKED

BLOCK_NATURE::OPPORTUNITY

VOID_IDENTIFIED::"tests/unit/test_auth_flow.py does not exist"
CONSTRUCTION_SPEC::"Unit tests covering login, logout, token refresh flows"
ACCEPTANCE_CRITERIA::"pytest passes with >80% coverage on auth module"

REMEDIATION_REQUEST::"Create test file with RED tests for auth flows before implementation"

===END_WALL_BLOCK===
```

§6::PHILOSOPHICAL_FOUNDATION

THE_VOID_CANVAS::[
  "Every OPPORTUNITY block is a canvas, not a wall",
  "The absence of something is the precondition for its creation",
  "Wall agents become architects of empty space, not gatekeepers",
  "Blocking transforms from stop sign to construction specification"
]

EMERGENCE::[
  "This contract emerged from Wind/Wall/Door debate",
  "Wind proposed semantic distinction at protocol level",
  "Wall challenged with ledger integrity constraints",
  "Door synthesized: content contract preserves both"
]

===END_WALL_CONTENT_CONTRACT===
