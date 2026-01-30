# Debate Hall Prompts

This directory contains project-local prompt variants for debate-hall-mcp.

## Layered Discovery

When you reference a named variant (e.g., `prompt_file: "security"`), the loader searches in order:

1. **Project-local**: `./prompts/{role}-{name}.oct.md`
2. **User-global**: `~/.debate-hall/prompts/{role}-{name}.oct.md`
3. **Embedded default**: Ship ZERO fallback

This means prompts in this directory are automatically available to anyone using this repo.

## Shipped Variants

| File | Role | Use Case |
|------|------|----------|
| `wind-security.oct.md` | Wind | Security-focused threat exploration |

## Usage

Reference variants in your tier configuration (`~/.debate-hall/tiers.yaml` or project-local):

```yaml
security-tier:
  wind:
    provider: cli
    cli: claude
    prompt_file: security  # Finds ./prompts/wind-security.oct.md
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

## Adding Your Own

Create prompts following the naming convention: `{role}-{variant}.oct.md`

- `wind-creative.oct.md` - Creative exploration variant
- `wall-strict.oct.md` - Extra strict validation
- `door-technical.oct.md` - Technical architecture focus

## User Customization

Users can override project-local prompts by creating the same file in `~/.debate-hall/prompts/`.
User-global prompts take precedence in resolution order.

## Discovery API

The App can discover all available prompts:

```python
from debate_hall_mcp.prompts.loader import list_available_prompts

prompts = list_available_prompts()
# Returns: {"wind": ["security"], "wall": [], "door": []}
```

## Prompt Format

Prompts should use OCTAVE format. See `wind-security.oct.md` for an example, or the embedded prompts in `src/debate_hall_mcp/prompts/__init__.py` for the full canonical format.
