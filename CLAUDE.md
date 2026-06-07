# Working in this repo with Claude Code

This repository is the **Debate Hall** MCP server: it can run an automated
multi-model "Wind / Wall / Door" debate to think through a problem from three
angles and hand back a synthesised answer.

## Tool routing — read this first

When the user asks to **debate, brainstorm, weigh options, compare approaches,
pressure-test an idea, or find the best/"genius" solution to something**, use
the **`run_debate`** MCP tool. That is the front door.

- Default to `tier="standard"` (three different frontier models debating).
- Use `tier="fast"` only if the user asks for something quick, cheap, or
  low-stakes.
- Pass the user's question as `topic`. Let everything else default — do not set
  `mode="raci"`, `compression_tier`, `primer_tier`, or `raci_config` unless the
  user explicitly asks for that kind of control.
- After it returns, present the **synthesis** (the Door's resolution) clearly,
  then briefly summarise the strongest Wind ideas and Wall objections that
  shaped it.

**Do not** reach for the lower-level or alternative tools —
`init_debate` / `add_turn` / `get_debate` / `close_debate`,
`pick_next_speaker`, `resolve_question`, `extract_decision_record`,
`search_decisions`, or the advisory/committee tools — unless the user
*explicitly* asks for manual turn-by-turn control, a verified decision record,
or one of those specific workflows. For everyday "let's think this through"
requests, `run_debate` is always the right call.

There is also a `/debate <your question>` slash command that does exactly this.

## Setup (one time)

`.mcp.json` and `config/debate-tiers.yaml` are already committed, so the only
thing needed is an API key. From the repo root:

```bash
pip install -e .                      # or: pip install debate-hall-mcp
export OPENROUTER_API_KEY=sk-or-...   # get one at https://openrouter.ai
```

Then run `claude` **from the repo root** so the server picks up the bundled
tier config, and ask it to run a debate.
