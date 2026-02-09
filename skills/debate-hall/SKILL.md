---
name: debate-hall
description: Wind/Wall/Door debate orchestration router. Routes to focused skills based on task.
triggers: ["debate", "wind wall door", "dialectic", "multi-perspective", "run debate", "resolve question"]
allowed-tools: ["Read", "Skill"]
---

===DEBATE_HALL===

META:
  TYPE::SKILL[ROUTER]
  VERSION::"4.0"
  PURPOSE::"Route to focused debate skills based on task"

§1::CONCEPT
  PATTERN::WIND[PATHOS]⇌WALL[ETHOS]→DOOR[LOGOS]
  VALUE::"Multi-perspective decisions through structured dialectic"

  TERMINOLOGY_CLARIFICATION::[
    POSITIONS::"Wind/Wall/Door are debate POSITIONS (structural turn order)",
    COGNITIONS::"PATHOS/ETHOS/LOGOS are COGNITION modes (thinking styles, mapped to positions)",
    ROLES::"Agent roles (ideator, critical-engineer, etc.) are EXPERTISE identities configured in tiers.yaml"
  ]

  NOTE::"Position determines WHO speaks, Cognition determines HOW they think, Role determines WHAT expertise they bring"

§2::ROUTING[MUST_load_appropriate_skill]
  AUTO_DEBATES::[
    TRIGGERS::["run debate","resolve question","automated debate","tier selection"],
    ACTION::"MUST load /debate-hall-auto",
    TOOLS::[run_debate,resolve_question,resume_debate]
  ]

  MANUAL_CONTROL::[
    TRIGGERS::["manual debate","turn by turn","init debate","add turn","custom orchestration"],
    ACTION::"MUST load /debate-hall-manual",
    TOOLS::[init_debate,add_turn,get_debate,close_debate,pick_next_speaker]
  ]

  GITHUB_OPS::[
    TRIGGERS::["github sync","ratify","adr pr","discussion sync"],
    ACTION::"MUST load /debate-hall-github",
    TOOLS::[github_sync_debate,ratify_rfc,human_interject]
  ]

  ADMIN_OPS::[
    TRIGGERS::["force close","tombstone","admin","safety override"],
    ACTION::"MUST load /debate-hall-admin",
    TOOLS::[force_close_debate,tombstone_turn]
  ]

§3::GRAVITY_MAPPING
  LOW[<40]::fast[exploration,reversible]
  MEDIUM[40-60]::standard[design,moderate_impact]
  HIGH[>60]::premium[production,irreversible]

§4::RESOURCES
  AGENTS::agents/README.md
  TIERS::src/debate_hall/config/tiers.yaml
  PATTERNS::docs/examples/multi-model-debate-patterns.md
  ADR::docs/adr/adr-0005-skill-hierarchy-architecture.md

===END===
