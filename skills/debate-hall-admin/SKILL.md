---
name: debate-hall-admin
description: Admin operations for debate safety overrides and redaction.
triggers: ["force close", "tombstone", "admin", "safety override", "redact turn"]
allowed-tools: ["Read", "mcp__debate-hall__force_close_debate", "mcp__debate-hall__tombstone_turn"]
---

===DEBATE_HALL_ADMIN===

META:
  TYPE::SKILL[FOCUSED]
  VERSION::"1.0"
  PURPOSE::"Admin operations for safety and redaction"
  ROUTER::debate-hall
  WARNING::"Use with caution - these are override operations"

§1::TOOLS

  FORCE_CLOSE_DEBATE::[
    PURPOSE::"I5 safety kill switch - emergency debate termination",
    PARAMS::[thread_id::REQUIRED,reason::REQUIRED[logged]],
    EFFECT::closes_any_state[ACTIVE,PAUSED]
  ]

  TOMBSTONE_TURN::[
    PURPOSE::"Redact turn content preserving hash chain (I4 compliance)",
    PARAMS::[thread_id::REQUIRED,turn_index::REQUIRED[0-based],reason::REQUIRED],
    EFFECT::content_replaced_with_tombstone[hash_preserved]
  ]

§2::SAFETY_NOTES
  FORCE_CLOSE::"Use for runaway debates, safety violations, or structural integrity threats"
  TOMBSTONE::"Use for PII exposure, harmful content, or audit requirements"
  AUDIT::"All admin actions are logged with reason"

===END===
