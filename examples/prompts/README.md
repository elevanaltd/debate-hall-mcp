# Example Custom Prompts

This directory contains example custom prompts for debate-hall-mcp.

## Usage

Copy the prompts you want to customize to `~/.debate-hall/prompts/`:

```bash
mkdir -p ~/.debate-hall/prompts
cp wind-security.oct.md ~/.debate-hall/prompts/
```

Then reference them in your tier configuration (`~/.debate-hall/tiers.yaml`):

```yaml
security-tier:
  wind:
    provider: cli
    cli: claude
    prompt_file: security  # Resolves to ~/.debate-hall/prompts/wind-security.oct.md
  wall:
    provider: cli
    cli: codex
    # No prompt_file = use embedded default
  door:
    provider: cli
    cli: gemini
  settings:
    consensus_required: true
    max_turns: 12
    max_refinement_loops: 3
```

## Naming Convention

Prompts follow the pattern: `{role}-{variant}.oct.md`

- `wind-security.oct.md` - Security-focused Wind prompt
- `wall-strict.oct.md` - Strict validation Wall prompt
- `door-technical.oct.md` - Technical architecture Door prompt

## Discovery

The App can discover available prompts using `list_available_prompts()`:

```python
from debate_hall_mcp.prompts.loader import list_available_prompts

prompts = list_available_prompts()
# Returns: {"wind": ["security"], "wall": [], "door": []}
```

## Creating Custom Prompts

Custom prompts should:

1. Use OCTAVE format (semantic markdown)
2. Include META section with VERSION and PURPOSE
3. Define COGNITION (PATHOS/ETHOS/LOGOS)
4. Specify ROLE (Wind/Wall/Door)
5. Include MUST_ALWAYS and MUST_NEVER behavioral mandates

See the embedded prompts in `src/debate_hall_mcp/prompts/__init__.py` for the full canonical format.
