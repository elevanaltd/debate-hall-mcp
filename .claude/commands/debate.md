---
description: Run a full Wind/Wall/Door multi-model debate on a topic
argument-hint: <the question or topic to debate>
---

Use the `run_debate` MCP tool to run a complete automated Wind/Wall/Door debate
on the topic below, then present the result to me:

1. Lead with the **synthesis** (the Door's final resolution) in plain language.
2. Then give a short bullet summary of the strongest **Wind** ideas and the
   key **Wall** objections that shaped it.

Topic: $ARGUMENTS

Call `run_debate` with `tier="standard"` by default. Use `tier="fast"` only if
I said I want something quick or cheap. Do not use `init_debate`, `add_turn`,
`resolve_question`, or any other debate tool — `run_debate` only.
