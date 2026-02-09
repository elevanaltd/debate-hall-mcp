---
name: debate-hall-github
description: GitHub integration for debate synchronization and ADR ratification.
triggers: ["github sync", "ratify rfc", "adr pr", "discussion sync", "human interject"]
allowed-tools: ["Read", "mcp__debate-hall__github_sync_debate", "mcp__debate-hall__ratify_rfc", "mcp__debate-hall__human_interject"]
---

===DEBATE_HALL_GITHUB===

META:
  TYPE::SKILL[FOCUSED]
  VERSION::"1.0"
  PURPOSE::"GitHub integration for debate sync and ADR ratification"
  ROUTER::debate-hall

§1::TOOLS

  GITHUB_SYNC_DEBATE::[
    PURPOSE::"Post debate turns to GitHub Discussion/Issue",
    PARAMS::[
      thread_id::REQUIRED,
      repo::REQUIRED["owner/repo"],
      target_id::REQUIRED[node_ID_or_issue_number],
      target_type::"discussion"|"issue"[default:discussion]
    ],
    BEHAVIOR::idempotent[tracks_synced_turns]
  ]

  RATIFY_RFC::[
    PURPOSE::"Generate ADR from Door synthesis and create PR",
    REQUIRES::debate_must_be_closed,
    PARAMS::[
      thread_id::REQUIRED,
      repo::REQUIRED["owner/repo"],
      adr_number::REQUIRED[explicit_to_prevent_collisions],
      adr_path::OPTIONAL["docs/adr/"]
    ],
    RETURNS::pr_url+pr_number+adr_path+branch_name
  ]

  HUMAN_INTERJECT::[
    PURPOSE::"Inject human GitHub comment into active debate",
    PARAMS::[
      thread_id::REQUIRED,
      repo::REQUIRED,
      target_id::REQUIRED,
      comment_id::REQUIRED[DC_xxx_or_numeric]
    ]
  ]

§2::WORKFLOW
  SYNC_FIRST::github_sync_debate→posts_turns_as_comments
  PREREQUISITE::debate_must_be_closed[use_/debate-hall-manual_or_/debate-hall-auto_to_close]
  RATIFY::ratify_rfc→creates_ADR_PR_from_synthesis

===END===
