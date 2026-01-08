# Storage Strategy: Why JSON is Primary

## The Question
Why is JSON the primary storage format when OCTAVE is ~19% smaller?

## The Answer
**JSON preserves complete state, OCTAVE preserves only the debate dialectic.**

### What JSON Stores (Complete State)
- **Dialectic Content**: turns, synthesis, topic
- **Operational Metadata**:
  - `audit_log` - Administrative actions (force close, tombstone)
  - `github_binding` - GitHub sync state (PR/issue IDs, comment tracking)
  - `injected_context` - Human feedback from GitHub comments
  - `expected_next_role` - Mediated mode state
- **Configuration**: octave_mode, strict_cognition, octave_preamble

### What OCTAVE Stores (Dialectic Only)
- **Core Debate**: turns with content, role, cognition
- **Structure**: topic, mode, status, limits
- **Synthesis**: final outcome
- **Missing**: All operational metadata

### Size Comparison
- JSON: ~4,442 bytes (typical debate)
- OCTAVE: ~3,596 bytes (same debate)
- **OCTAVE is 19% smaller** but **loses critical operational data**

## Storage Strategy

### Dual-Format Approach
1. **JSON** (`.json`)
   - Primary storage
   - Complete state preservation
   - Single source of truth
   - Always written first

2. **OCTAVE** (`.oct.md`)
   - Supplementary format
   - Human-readable transcript
   - Optimized for dialectic content
   - Best-effort write (non-fatal on failure)

### Load Strategy
- **Always load from JSON** - preserves complete state
- OCTAVE files are write-only for human consumption
- No OCTAVE → JSON migration path (data loss would occur)

## Why This Makes Sense

### For System Operation
- GitHub sync needs `github_binding` metadata
- Audit trails require `audit_log` preservation
- Human feedback needs `injected_context` storage
- Mediated mode needs `expected_next_role` state

### For Human Consumption
- OCTAVE provides clean, readable transcripts
- Operational metadata is noise for human readers
- 19% smaller files for sharing/archiving debates

## Conclusion

JSON must be primary because:
1. **Complete state preservation** - No data loss
2. **System functionality** - GitHub sync, audit, feedback features need metadata
3. **Backward compatibility** - Existing JSON debates work unchanged

OCTAVE serves as:
1. **Human-readable export** - Clean transcripts without operational noise
2. **Archive format** - Smaller files for long-term storage
3. **Sharing format** - Easy to read and understand debate flow

The 19% size reduction is not worth losing operational metadata. The dual-format approach gives us the best of both worlds: complete state in JSON, readable transcripts in OCTAVE.
