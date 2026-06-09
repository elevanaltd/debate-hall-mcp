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

Debate Hall is configured **user-global**, so `run_debate` is available from
**any** project directory — you launch `claude` from whatever repo you want to
think about, **not** from `debate-hall-mcp`. Clone the repo, then run the
remaining commands from inside it:

```bash
git clone https://github.com/elevanaltd/debate-hall-mcp.git
cd debate-hall-mcp
pip install -e .                      # editable install from this clone
export OPENROUTER_API_KEY=sk-or-...   # get one at https://openrouter.ai
./setup-mcp.sh --claude-code          # run once
```

`setup-mcp.sh` registers the server in your user-global Claude Code config
(`~/.claude.json`) and installs a default tier config to
`~/.debate-hall/tiers.yaml`. That global tiers file is what makes debates work
from any directory. You can edit `~/.debate-hall/tiers.yaml` to add or tweak
tiers (e.g. `premium` / `ultra`).

**Keep the clone in place.** The user-global registration points at this clone's
`server.py`, so if you move or delete the directory, re-run
`./setup-mcp.sh --claude-code` from the new location.

After this, just `cd` into any repo, run `claude`, and ask it to run a debate.
The MCP server inherits `OPENROUTER_API_KEY` from the shell you launch `claude`
in — `setup-mcp.sh` never writes the key anywhere, so make sure it is exported
in that environment.
