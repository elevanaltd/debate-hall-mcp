# ADR-0001: Skills-Based OCTAVE Compression Architecture

## Status

**ACCEPTED** (2026-01-02)

## Context

Issue #26 identified a fundamental architectural question: How should debate-hall-mcp implement OCTAVE format support for debate transcripts?

Three approaches were considered:

| Option | Description | Risk |
|--------|-------------|------|
| **A: Validation Only** | Validate turn content as OCTAVE on input | Blocks non-OCTAVE agents |
| **B: Export Capability** | Convert JSON transcript to OCTAVE on export | Tool duplication with octave-mcp |
| **C: Full Integration** | Require octave-mcp as dependency | Tight coupling, complexity |

The original `octave_formatter.py` truncated turn content to 80 characters, destroying the semantic compression that agents produce.

## Decision

We adopt a **Skills-Based Compression Architecture** where:

1. **Skills are the OCTAVE source of truth** - Agents load OCTAVE skills (`octave-literacy`, `octave-mastery`, `octave-mythology`) that enable them to produce semantically-compressed OCTAVE natively during debates.

2. **debate-hall-mcp is an envelope wrapper** - The formatter creates the `===DEBATE_TRANSCRIPT===` envelope and preserves agent-produced content verbatim with security sanitization.

3. **octave-mcp handles general OCTAVE operations** - Validation, schema enforcement, and general transformations. Debate-specific conversion should NOT live in octave-mcp.

4. **`octave_mode` flag controls behavior** - Optional flag on `init_debate` enables OCTAVE-mode debates where output defaults to OCTAVE format.

## Architecture

```
+---------------------------------------------------------------+
|                    SKILLS (Source of Truth)                    |
|  ~/.claude/skills/octave-*                                     |
|  When OCTAVE updates -> update skills -> all agents benefit    |
+---------------------------------------------------------------+
                              |
            Agents load skills, KNOW OCTAVE syntax
                              |
                              v
+---------------------------+     +-----------------------------+
|    debate-hall-mcp        |     |        octave-mcp           |
|                           |     |                             |
|  DOMAIN: Debate           |     |  DOMAIN: OCTAVE Format      |
|  - Orchestration          |     |  - octave_validate          |
|  - Hash chain             |     |  - octave_write             |
|  - Turn management        |     |  - octave_eject             |
|  - Persistence (JSON)     |     |  - Schema enforcement       |
|                           |     |                             |
|  OUTPUT: JSON primary     |     |  NOT debate-specific        |
|  OCTAVE: Envelope only    |     |  General OCTAVE operations  |
+---------------------------+     +-----------------------------+
```

## Implementation

### Changes Made

1. **`octave_formatter.py`**:
   - Added `OutputMode` enum (FULL/SUMMARY)
   - Added `_sanitize_value()` for security (prevents `===FAKE===` injection)
   - FULL mode preserves complete content (new default)
   - SUMMARY mode truncates to 80 chars (backward compatibility)

2. **`init_debate`**:
   - Added `octave_mode: bool = False` parameter
   - Stored in `DebateRoom` model

3. **`close_debate`**:
   - When `octave_mode=True` and no explicit `output_format`, defaults to OCTAVE
   - Explicit `output_format` always overrides

4. **`get_debate`**:
   - Returns `octave_mode` in response

### Usage

```python
# Standard debate (JSON output)
init_debate(thread_id="...", topic="...", mode="fixed")
close_debate(thread_id="...", synthesis="...")  # -> JSON

# OCTAVE-mode debate
init_debate(thread_id="...", topic="...", mode="fixed", octave_mode=True)
close_debate(thread_id="...", synthesis="...")  # -> OCTAVE

# Override default
init_debate(thread_id="...", topic="...", octave_mode=True)
close_debate(thread_id="...", synthesis="...", output_format="json")  # -> JSON
```

## Consequences

### Positive

- **Separation of Concerns**: debate-hall-mcp owns debates, octave-mcp owns format validation
- **Skill-Driven Evolution**: OCTAVE spec changes propagate via skill updates, not code changes
- **No Content Loss**: Agent-produced OCTAVE preserved verbatim
- **Security**: Envelope marker injection prevented
- **Backward Compatible**: Existing debates unaffected (default JSON output)

### Negative

- **Skill Dependency**: Quality of OCTAVE output depends on agents having skills loaded
- **No Input Validation**: Turns are not validated as OCTAVE on input (by design)

### Neutral

- `octave_debate_to_octave` in octave-mcp should be deprecated (separate issue)

## References

- [Issue #26](https://github.com/elevanaltd/debate-hall-mcp/issues/26) - OCTAVE format support
- [octave-mcp debate_convert.py](https://github.com/elevanaltd/octave-mcp/blob/main/src/octave_mcp/mcp/debate_convert.py) - Reference implementation (to be deprecated)
- OCTAVE Skills: `octave-literacy`, `octave-mastery`, `octave-mythology`, `octave-compression`
