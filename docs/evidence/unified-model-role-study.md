# M021: Unified Model-Role Optimization Study

**Research Question:** Which model performs best in each Wind/Wall/Door role when measured by both behavioral signatures AND task performance?

**Verdict:** Signatures describe HOW models work, not WHAT they excel at. M019's task performance findings validated with 100% assessor agreement.

---

## Executive Summary

M021 resolved a contradiction between two previous studies:
- **M019** (task performance) recommended: Claude→Wind, GPT→Wall, Gemini→Door
- **M020** (behavioral signatures) suggested different optimal assignments

**Key Discovery:** Behavioral signatures and task performance measure different things. A model's cognitive style (systematic, philosophical, etc.) doesn't predict which debate role it excels at.

**Validated Optimal Configuration:**
```
WIND/PATHOS:  Claude Opus 4.5    (systematic creativity)
WALL/ETHOS:   GPT-5.2 / Codex    (structured validation)
DOOR/LOGOS:   Gemini 3 Pro       (conceptual synthesis)
```

---

## Methodology

### Study Design

- **6 complete debates** across 3 architectural topics
- **Multiple configurations tested:**
  - Pure model debates (same model all roles)
  - M019 optimal (Claude-GPT-Gemini)
  - SKILL.md default (Gemini-Codex-Claude)

### Two-Dimensional Measurement

1. **Behavioral Signatures** (HOW models work):
   - Response structure, named concepts, meta-commentary
   - Cross-domain references, decision matrices

2. **Task Performance** (WHAT models excel at):
   - Wind/PATHOS rubric (50 points)
   - Wall/ETHOS rubric (60 points)
   - Door/LOGOS rubric (60 points)

### Blind Assessment

- Independent assessors (Gemini 3 Pro and Codex 5.2)
- Scored Door/LOGOS syntheses without knowing which model produced them
- **Inter-rater agreement: 100%** on ranking

---

## Results

### The Reconciliation: Signatures ≠ Role Fit

| Model | Behavioral Signature (HOW) | Best Role (WHAT) | Mechanism |
|-------|---------------------------|------------------|-----------|
| Claude | Systematic, exhaustive | Wind/PATHOS | Systematic EXPLORATION - methodically explores more options |
| GPT-5.2/Codex | Structured, evidence-based | Wall/ETHOS | Structured VALIDATION - clear evidence chains |
| Gemini | Philosophical, principle-finding | Door/LOGOS | Conceptual SYNTHESIS - reframes problems architecturally |

**Key Insight:** Claude is "systematically creative" - its systematic signature enables creative exploration. Gemini is "philosophically synthetic" - its philosophical signature drives conceptual reframing.

### Blind Assessment Scores (Door/LOGOS)

| Model as Door | Score | Quality |
|---------------|-------|---------|
| **Gemini** | 52.5/60 (87.5%) | Architecturally innovative |
| Claude | 45.5/60 (75.8%) | Pragmatic, actionable |

### Synthesis Quality Comparison

- **M019 Optimal**: Architecturally innovative syntheses ("Zero-Emit Typed JS", "Decoupled Gateway", "State-First Eventing")
- **Pure Claude**: Detailed week-by-week execution plans, less conceptually transformative
- Assessor feedback: Gemini "solved at the conceptual level"; Claude "solved at the execution level"

### Configuration Performance

| Configuration | Quality vs Default |
|--------------|-------------------|
| M019 Optimal (Claude-GPT-Gemini) | +29% |
| Pure Claude | Baseline |
| SKILL.md Default | Solid but less distinctive |

---

## Why M020's Signatures Didn't Predict Performance

M020 correctly identified behavioral signatures:
- Claude: Systematic enumeration, decision matrices
- Codex: Compact, metrics-focused
- Gemini: Metaphorical, principle-finding

But signatures describe cognitive STYLE, not output QUALITY for specific tasks:
- A systematic style can enable thorough exploration (good for Wind)
- A philosophical style can enable conceptual synthesis (good for Door)
- The signature predicts the MODE of work, not the FIT to role

---

## Implications

### For debate-hall-mcp Users

1. **Use M019 optimal for highest quality:**
   ```
   Wind: Claude (systematic exploration)
   Wall: GPT-5.2/Codex (structured validation)
   Door: Gemini (conceptual synthesis)
   ```

2. **Alternative for execution-focused synthesis:** Use Claude as Door if you need detailed implementation plans over architectural innovation

3. **Don't confuse signatures with fit:** A model's "style" doesn't determine its best role

### For Understanding Model Differences

- Models have consistent behavioral fingerprints (M020 validated)
- These fingerprints describe HOW models approach problems
- Role fit depends on WHAT the role requires, not the style of approach

---

## Reproducibility

### Original Study Location
```
/Volumes/HestAI-old/hestai-tests/methodology-research/M021-unified-model-role-optimization-study
```

### Key Files
- `README.md` - Study overview
- `TEST_PLAN.md` - Full methodology with rubrics
- `analysis/FINAL-RECOMMENDATIONS.md` - Actionable recommendations
- `analysis/blind-assessment-results.md` - Quantitative scores
- `analysis/logos-synthesis-rubric.md` - 60-point scoring framework

### Study Quality
- 6 complete debates executed
- 2 independent assessors
- 100% inter-rater agreement on rankings
- High confidence in findings

---

## Citation

```
HestAI Methodology Research. (2026). M021: Unified Model-Role
Optimization Study. Internal research report reconciling M019/M020
findings. Validates Claude→Wind, GPT→Wall, Gemini→Door with 100%
assessor agreement. Key insight: signatures ≠ role fit.
```
