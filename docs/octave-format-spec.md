# OCTAVE Format Specification v1.0

**PURPOSE**: Canonical specification for Universal OCTAVE Storage format used by debate-hall-mcp.

**STATUS**: Phase 1 - Foundation & Specification

---

## 1. Overview

OCTAVE (Odyssean Context for Transmissible Agent-Verified Exchanges) is a human-readable format for storing structured debate transcripts with cryptographic integrity guarantees.

### Design Principles

1. **Human-Readable First**: OCTAVE files must be readable and editable by humans
2. **Cryptographic Integrity**: Hash chains prevent tampering (Immutable I4: Verifiable Event Ledger)
3. **Single Source of Truth**: OCTAVE format is the canonical representation
4. **Escaping via Standard Library**: Use `json.dumps()` for escaping - NO manual character processing

---

## 2. File Structure

An OCTAVE debate transcript consists of three sections:

```
META::
  field::value
  field::value

TURNS::[
  T0::Role[Cognition]#{content_hash}@{iso8601_timestamp}::"{escaped_content}"
  T1::Role[Cognition]#{content_hash}@{iso8601_timestamp}::"{escaped_content}"
  ...
]

SYNTHESIS::
  status::CLOSED_SYNTHESIS|CLOSED_EXHAUSTION|CLOSED_STALEMATE|CLOSED_FORCE
  content::"{escaped_synthesis_content}"
```

### 2.1 META Section

The META section contains debate metadata:

```
META::
  thread_id::"debate-unique-identifier"
  topic::"The debate topic or question"
  mode::fixed|mediated
  octave_mode::true|false
  strict_cognition::true|false
  max_turns::12
  max_rounds::4
  status::ACTIVE|CLOSED
  created_at::2026-01-08T10:30:00Z
  closed_at::2026-01-08T11:45:00Z
```

**Field Escaping**: All string values MUST be escaped using `json.dumps()`. This includes `thread_id`, `topic`, and `status`.

**Example with special characters**:
```
META::
  topic::"What if the topic contains \"quotes\" and\nnewlines?"
```

### 2.2 TURNS Section

The TURNS section contains the ordered list of debate turns with hash chain.

**Turn Format**:
```
T{index}::Role[Cognition]#{content_hash}@{timestamp}::"{escaped_content}"
```

**Components**:
- `T{index}`: Zero-based turn index (T0, T1, T2...)
- `Role`: Wind, Wall, or Door
- `Cognition`: PATHOS, ETHOS, or LOGOS
- `content_hash`: SHA-256 hash in hex format (64 characters)
- `timestamp`: ISO 8601 with timezone (e.g., `2026-01-08T10:30:00Z`)
- `escaped_content`: Content escaped via `json.dumps(content)[1:-1]` (strips outer quotes)

**Optional Metadata**:
Turns may include optional metadata in the header:
```
T0::Wind[PATHOS]#{hash}@{timestamp}[agent_role=implementation-lead,model=gpt-5]::"{content}"
```

**Example**:
```
TURNS::[
  T0::Wind[PATHOS]#abc123...def456@2026-01-08T10:30:00Z::"Should we prioritize speed or correctness?"
  T1::Wall[ETHOS]#def456...ghi789@2026-01-08T10:32:15Z::"Correctness is non-negotiable in production systems."
  T2::Door[LOGOS]#ghi789...jkl012@2026-01-08T10:35:42Z::"We can achieve both through TDD: tests define correctness, refactoring enables speed."
]
```

### 2.3 SYNTHESIS Section

The SYNTHESIS section contains the final resolution:

```
SYNTHESIS::
  status::CLOSED_SYNTHESIS
  content::"{escaped_synthesis_content}"
  closed_at::2026-01-08T11:45:00Z
```

**Status Values**:
- `CLOSED_SYNTHESIS`: Debate closed with Door's synthesis
- `CLOSED_EXHAUSTION`: Max turns/rounds reached
- `CLOSED_STALEMATE`: No progress detected
- `CLOSED_FORCE`: Force-closed by admin (I5: Safety Override)

---

## 3. Escaping Rules

### 3.1 The Golden Rule: Use json.dumps()

**MANDATORY**: All content escaping MUST use Python's `json.dumps()` function.

**Why**: `json.dumps()` correctly handles all special characters, escape sequences, and Unicode. Manual escaping is error-prone and creates security vulnerabilities.

**Implementation**:
```python
import json

def escape_content(content: str) -> str:
    """
    Escape content for OCTAVE format using json.dumps().

    Returns escaped string WITHOUT surrounding quotes
    (we add the quotes in the OCTAVE format itself).
    """
    # json.dumps() returns: '"escaped content"'
    # We strip the outer quotes: 'escaped content'
    return json.dumps(content)[1:-1]
```

**Example**:
```python
>>> content = 'Line 1\nLine 2 with "quotes"'
>>> escape_content(content)
'Line 1\\nLine 2 with \\"quotes\\"'
```

### 3.2 Special Characters Handled

`json.dumps()` automatically handles:

1. **Newlines**: `\n` → `\\n`
2. **Tabs**: `\t` → `\\t`
3. **Carriage returns**: `\r` → `\\r`
4. **Double quotes**: `"` → `\"`
5. **Backslashes**: `\` → `\\`
6. **Unicode**: Preserved as UTF-8

### 3.3 Escaping Order (Automatic)

**CRITICAL**: `json.dumps()` handles escape order correctly:

1. Backslashes escaped FIRST: `\` → `\\`
2. Then other special chars: `\n` → `\\n`

This prevents double-escaping bugs (e.g., `\n` → `\\n` → `\\\\n`).

### 3.4 Examples

**Input**: `"Hello\nWorld"`
**Escaped**: `\"Hello\\nWorld\"`
**In OCTAVE**: `T0::Wind[PATHOS]#...::\"Hello\\nWorld\"`

**Input**: `Line 1\nLine 2 with "quotes" and\ttabs`
**Escaped**: `Line 1\\nLine 2 with \\"quotes\\" and\\ttabs`

**Input**: `Path: C:\Users\file.txt`
**Escaped**: `Path: C:\\Users\\file.txt`

---

## 4. Hash Chain Computation

### 4.1 Hash Formula

Each turn's `content_hash` is computed as:

```
SHA256(role || content || timestamp || previous_hash)
```

Where `||` denotes concatenation.

### 4.2 Components

1. **role**: Lowercase string (`"wind"`, `"wall"`, `"door"`)
2. **content**: Original unescaped content string
3. **timestamp**: ISO 8601 string with timezone
4. **previous_hash**: Previous turn's `content_hash` (empty string for first turn)

### 4.3 Implementation

```python
import hashlib
from datetime import datetime, timezone

def calculate_turn_hash(
    role: str,
    content: str,
    timestamp: datetime,
    previous_hash: str = ""
) -> str:
    """
    Calculate SHA-256 hash for a debate turn.

    Args:
        role: Lowercase role name (wind, wall, door)
        content: Unescaped turn content
        timestamp: Timestamp with timezone
        previous_hash: Previous turn's hash (empty for first turn)

    Returns:
        64-character hex hash
    """
    # Convert timestamp to ISO 8601 with timezone
    timestamp_str = timestamp.isoformat()

    # Concatenate components
    hash_input = f"{role}{content}{timestamp_str}{previous_hash}"

    # Compute SHA-256
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
```

### 4.4 Hash Chain Properties

1. **First Turn**: `previous_hash` is empty string (`""`)
2. **Subsequent Turns**: `previous_hash` is the `content_hash` of prior turn
3. **Immutability**: Changing any turn breaks the chain (I4: Verifiable Event Ledger)
4. **Tombstones**: Tombstoned turns preserve their hash (content changed, hash NOT recomputed)

### 4.5 Verification

**On Load**: Verify hash chain links (NOT content hashes):
- Check `turn[i].previous_hash == turn[i-1].content_hash`
- Do NOT re-compute content hashes (would break tombstone compatibility)

**Example Verification**:
```python
def verify_hash_chain(turns: list[Turn]) -> None:
    """Verify hash chain links (not content hashes)."""
    for i, turn in enumerate(turns):
        if i == 0:
            # First turn must have empty/null previous_hash
            if turn.previous_hash not in ("", None):
                raise ValueError(f"First turn has non-empty previous_hash")
        else:
            # Check link to previous turn
            expected = turns[i-1].content_hash
            if turn.previous_hash != expected:
                raise ValueError(
                    f"Hash chain break at turn {i}: "
                    f"expected {expected}, got {turn.previous_hash}"
                )
```

---

## 5. Timestamp Format

### 5.1 ISO 8601 with Timezone

**Format**: `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`

**Python**:
```python
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc)
iso_string = timestamp.isoformat()  # "2026-01-08T10:30:00+00:00"
```

### 5.2 Timezone Requirement

**MANDATORY**: All timestamps MUST include timezone information.

**Recommended**: Use UTC for consistency.

---

## 6. Optional Metadata

Turns may include optional metadata in the header:

```
T0::Role[Cognition]#{hash}@{timestamp}[agent_role=value,model=value]::"{content}"
```

**Fields**:
- `agent_role`: Agent's role identifier (e.g., `implementation-lead`)
- `model`: Model used (e.g., `gpt-5`, `claude-sonnet-4`)

**Parsing**: Metadata is key=value pairs in square brackets, comma-separated.

**Example**:
```
T2::Door[LOGOS]#abc...def@2026-01-08T10:35:00Z[agent_role=door-agent,model=gemini-3-pro]::"Synthesis content"
```

---

## 7. Migration Strategy

### 7.1 Read Preference

When loading debate state:

1. **Try .oct.md first**: `{thread_id}.oct.md`
2. **Fall back to .json**: `{thread_id}.json`
3. **Error if neither exists**

### 7.2 Write Strategy (Phase 1)

During initial implementation:

1. **Primary**: Write `.oct.md` file
2. **Backup**: Also write `.json` file (for safety)

### 7.3 Write Strategy (Phase 2+)

After OCTAVE format is proven stable:

1. **Only**: Write `.oct.md` file
2. **Deprecate**: Stop writing `.json` files

### 7.4 Backward Compatibility

**JSON Format Preservation**: Existing `.json` files continue to load correctly throughout all phases.

---

## 8. Complete Example

### 8.1 Example OCTAVE File

```
META::
  thread_id::"debate-001-tdd-vs-speed"
  topic::"Should we prioritize test-driven development or delivery speed?"
  mode::fixed
  octave_mode::true
  strict_cognition::true
  max_turns::12
  max_rounds::4
  status::CLOSED
  created_at::2026-01-08T10:30:00Z
  closed_at::2026-01-08T11:45:00Z

TURNS::[
  T0::Wind[PATHOS]#7f3a89b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0@2026-01-08T10:30:00Z::"We need to deliver features faster! Can we skip writing tests for now and add them later?"
  T1::Wall[ETHOS]#8e4b90c3d2e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1@2026-01-08T10:32:15Z::"Skipping tests creates technical debt that slows future development. We've seen this pattern fail before."
  T2::Door[LOGOS]#9f5c01d4e3f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2@2026-01-08T10:35:42Z::"TDD enables both speed AND quality: tests define correctness upfront, preventing debugging cycles that consume more time than writing tests. The 'later' for adding tests never comes."
]

SYNTHESIS::
  status::CLOSED_SYNTHESIS
  content::"Adopt TDD as standard practice. The time investment in test-first development pays dividends through reduced debugging, confident refactoring, and sustainable velocity. Speed without correctness is an illusion."
  closed_at::2026-01-08T11:45:00Z
```

### 8.2 Example with Special Characters

```
META::
  thread_id::"debate-002-escaping"
  topic::"How do we handle \"quotes\" and\nnewlines?"
  mode::fixed
  octave_mode::true
  strict_cognition::false
  max_turns::6
  max_rounds::2
  status::CLOSED
  created_at::2026-01-08T14:00:00Z
  closed_at::2026-01-08T14:15:00Z

TURNS::[
  T0::Wind[PATHOS]#a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2@2026-01-08T14:00:00Z::"Content with special chars:\n- Newline\n- \"Double quotes\"\n- Tab:\there\n- Backslash: C:\\path\\file.txt"
  T1::Wall[ETHOS]#b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3@2026-01-08T14:05:00Z::"All special characters must be properly escaped using json.dumps() to prevent parse errors."
  T2::Door[LOGOS]#c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4@2026-01-08T14:10:00Z::"Using standard library escaping ensures correctness and prevents security vulnerabilities."
]

SYNTHESIS::
  status::CLOSED_SYNTHESIS
  content::"Standard library escaping (json.dumps) is mandatory. Manual character processing is prohibited."
  closed_at::2026-01-08T14:15:00Z
```

---

## 9. Security Considerations

### 9.1 Path Traversal Prevention

**Thread IDs** must be validated before file operations:

```python
def validate_thread_id(thread_id: str) -> None:
    """Validate thread_id contains no path traversal characters."""
    if any(char in thread_id for char in ['/', '\\', '..']):
        raise ValueError(f"Invalid thread_id: {thread_id}")
```

### 9.2 Injection Prevention

**Content Escaping** via `json.dumps()` prevents injection attacks:
- SQL injection: N/A (no SQL)
- Command injection: N/A (content is data, not executed)
- OCTAVE structure injection: Prevented by escaping

### 9.3 Hash Chain Integrity

**Verification on Load**: Detect tampering by verifying hash chain links.

---

## 10. Parser Implementation Notes

### 10.1 Parsing Strategy

1. **Parse META section**: Extract key-value pairs
2. **Parse TURNS section**: Extract turn list with regex
3. **Parse SYNTHESIS section**: Extract status and content
4. **Unescape content**: Use `json.loads(f'"{escaped}"')` to unescape

### 10.2 Unescaping

**Reverse of Escaping**:
```python
import json

def unescape_content(escaped: str) -> str:
    """
    Unescape OCTAVE content using json.loads().

    Args:
        escaped: Escaped content WITHOUT surrounding quotes

    Returns:
        Original unescaped content
    """
    # Wrap in quotes for json.loads()
    return json.loads(f'"{escaped}"')
```

**Example**:
```python
>>> escaped = 'Line 1\\nLine 2 with \\"quotes\\"'
>>> unescape_content(escaped)
'Line 1\nLine 2 with "quotes"'
```

### 10.3 Error Handling

**Parse Errors**: Clear error messages indicating:
- Which section failed (META, TURNS, SYNTHESIS)
- Which line number
- What was expected vs. found

---

## 11. Implementation Checklist

### Phase 1: Foundation & Specification
- [x] Complete format specification document
- [ ] Test skeleton for parser
- [ ] Test skeleton for serializer

### Phase 2: Parser Implementation
- [ ] Parse META section
- [ ] Parse TURNS section
- [ ] Parse SYNTHESIS section
- [ ] Unescape content using json.loads()
- [ ] Verify hash chain links on load

### Phase 3: Serializer Implementation
- [ ] Serialize META section
- [ ] Serialize TURNS section
- [ ] Serialize SYNTHESIS section
- [ ] Escape content using json.dumps()

### Phase 4: Integration
- [ ] Update save_debate_state() to write .oct.md
- [ ] Update load_debate_state() to read .oct.md first
- [ ] Maintain .json backup writes (Phase 1 safety)
- [ ] Integration tests for full round-trip

---

## 12. References

- **octave-mcp**: External OCTAVE validation package
- **I4 Immutable**: Verifiable Event Ledger (hash chain)
- **I5 Immutable**: Sovereign Safety Override (force close)
- **TDD Discipline**: Test-first implementation required

---

**VERSION**: 1.0
**LAST UPDATED**: 2026-01-08
**STATUS**: Complete - Ready for Phase 1 test structure
