# Architecture Decision: Custom Parser vs octave-mcp

## Critical Discovery
**Our format is NOT compatible with octave-mcp!** We use an "OCTAVE-like" format that differs significantly from the official OCTAVE v3 specification.

### Format Comparison
```
OUR FORMAT:                    OCTAVE-MCP FORMAT:
META::                         ===INFERRED===
  THREAD_ID::"test"           META:
  TOPIC::"Test"                 THREAD_ID::test
                                TOPIC::Test
TURNS::[...]                  ===END===
```

## Current State
We have **custom parser/serializer** modules that produce an OCTAVE-inspired format, but NOT actual OCTAVE.

## The Problem
Our implementation bypasses octave-mcp's official parser/emitter, potentially:
- Missing consistency guarantees
- Deviating from OCTAVE specification
- Duplicating effort
- Missing future octave-mcp improvements

## Analysis

### What octave-mcp Provides
```python
# Full AST-based parsing
doc = octave_mcp.parse(content)  # Returns Document AST
output = octave_mcp.emit(doc)    # Emits from AST

# Features we're NOT using:
- AST manipulation
- Schema validation
- Seal/verification
- Operator support (::, →, ⊕, etc.)
- Proper OCTAVE grammar
```

### What We Built Instead
```python
# Regex-based parsing
data = parse_octave(content)  # Returns dict
output = serialize_octave(data)  # Serializes dict

# Our approach:
- Simple regex patterns
- Direct dict manipulation
- JSON escaping
- No AST overhead
```

## Why This Happened

1. **Impedance Mismatch**:
   - octave-mcp works with AST nodes (Document, Section, Assignment)
   - debate-hall needs simple dicts (meta, turns, synthesis)
   - Converting AST ↔ dict adds complexity

2. **Limited Subset**:
   - We only use 3 sections (META, TURNS, SYNTHESIS)
   - No operators, no complex grammar
   - Just key-value pairs and lists

3. **Escape Handling**:
   - We need JSON-compatible escaping for turn content
   - octave-mcp uses different escaping rules
   - json.dumps/loads gives us exactly what we need

## The Trade-off

### Using octave-mcp (Proper Way)
```python
def save_with_octave_mcp(room: DebateRoom):
    doc = octave_mcp.Document()

    # Build AST
    meta_section = octave_mcp.Section("META")
    meta_section.add_assignment("THREAD_ID", room.thread_id)
    # ... many more assignments

    turns_section = octave_mcp.Section("TURNS")
    for turn in room.turns:
        # Complex turn formatting
        turn_str = format_turn(turn)
        turns_section.add_value(turn_str)

    doc.add_section(meta_section)
    doc.add_section(turns_section)

    return octave_mcp.emit(doc)
```

**Pros**:
- ✅ Guaranteed OCTAVE compliance
- ✅ Future compatibility
- ✅ Validation built-in

**Cons**:
- ❌ Complex AST building
- ❌ More code (AST ↔ domain model)
- ❌ Performance overhead
- ❌ Escaping mismatches

### Our Current Approach (Pragmatic)
```python
def save_with_custom(room: DebateRoom):
    return serialize_octave({
        "meta": {
            "THREAD_ID": room.thread_id,
            # ... simple dict
        },
        "turns": [
            # Simple list of dicts
        ]
    })
```

**Pros**:
- ✅ Simple and direct
- ✅ Fast (no AST overhead)
- ✅ JSON-compatible escaping
- ✅ Easier to test

**Cons**:
- ❌ Not using official parser
- ❌ Could drift from spec
- ❌ Missing validation

## Recommendation

**KEEP the custom implementation for now**, but:

1. **Add octave-mcp validation**:
```python
def validate_our_output(content: str):
    try:
        octave_mcp.parse(content)  # Validate syntax
        return True
    except Exception:
        return False
```

2. **Consider migration if**:
   - We need more OCTAVE features (operators, schemas)
   - octave-mcp adds direct dict support
   - Performance isn't critical

3. **Document the subset**:
   - We use "OCTAVE-lite" (just sections, no operators)
   - Our format is OCTAVE-compatible but simplified

## The Real Issue

The mismatch isn't our fault - it's architectural:
- **octave-mcp** is built for complex documents with operators, schemas, seals
- **debate-hall** needs simple structured data (like JSON with comments)
- Using full OCTAVE AST for simple data is over-engineering

## Conclusion - UPDATED

Our implementation produces an **OCTAVE-inspired format** that is NOT actual OCTAVE v3. This is a more significant deviation than originally understood.

### The Truth
1. We're using a **simplified syntax** that looks like OCTAVE but isn't
2. The format is **incompatible** with octave-mcp parser
3. We cannot validate with octave-mcp (format mismatch)
4. The `.oct.md` extension is misleading

### Options Going Forward

#### Option 1: Fix to Real OCTAVE (Recommended if standardization matters)
- Rewrite serializer to produce `===INFERRED===` wrapper format
- Use proper OCTAVE v3 syntax
- Validate with octave-mcp
- Benefit: True standard compliance

#### Option 2: Rename Our Format (Recommended if simplicity matters)
- Call it `.debate.md` or similar
- Document it as "debate transcript format"
- Stop claiming OCTAVE compatibility
- Benefit: Honest about what we're doing

#### Option 3: Keep As-Is with Documentation
- Document that it's "OCTAVE-inspired" not actual OCTAVE
- Explain the differences clearly
- Accept the incompatibility
- Benefit: No code changes needed

### The Real Issue Remains
The mismatch exists because:
- **octave-mcp** is for complex structured documents with schemas
- **debate-hall** needs simple human-readable transcripts
- We borrowed OCTAVE's aesthetic but not its complexity

### Final Recommendation
**Option 3** - Keep the current implementation but be honest about it. Our format works well for our needs, even if it's not "real" OCTAVE. The important thing is that it's consistent, readable, and serves our purpose.
