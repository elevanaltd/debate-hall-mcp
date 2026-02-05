# ADR-0003: Stratified Feature Flag Architecture

**Status**: Proposed
**Date**: 2026-02-04
**Decision Makers**: Wind/Wall/Door Debate (Cross-Tier Synthesis)
**Context**: Feature flag architecture for multi-tenant SaaS applications

## Context

A Wind/Wall/Door debate was conducted across three tiers (fast, standard, premium) to determine the optimal feature flag architecture for a multi-tenant SaaS application with requirements for:
- Per-tenant feature rollouts
- A/B testing capabilities
- Sales-driven premium feature toggles
- Low latency evaluation
- Blast radius containment
- Auditability

Each tier produced a distinct synthesis:
- **Fast tier** ($0.016): "Kinetic Routing" - unified SDK routing to Static/Kinetic/Volatile backends
- **Standard tier** ($0.30): "JIT Configuration Compiler" - policy compilation into signed artifacts
- **Premium tier** ($0.63): "Stratified Flag Resolution" - layers matched to flag "physics"

## Decision

Implement a **hybrid architecture** that synthesizes insights from all three tiers:

### Core Architecture: Stratified Layers (Premium)

Three layers stratified by flag "physics" (read/write patterns, consistency requirements):

| Layer | Flag Type | Mechanism | Latency |
|-------|-----------|-----------|---------|
| **1. Entitlements** | Sales/Plan toggles | Inject into Auth Context (JWT/session) | 0ms |
| **2. Operational** | Kill switches, maintenance | Push to local cache via pub/sub | <1ms |
| **3. Experimentation** | A/B tests, canaries | Real-time vendor SDK (LaunchDarkly/Unleash) | 10-50ms |

### Control Plane: JIT Compiler (Standard)

Policy Engine that:
1. Evaluates complex rules (tier + usage + time)
2. Validates configuration changes before deployment
3. Signs artifacts for integrity verification
4. Pushes compiled state to appropriate layer

### Developer Interface: Unified SDK (Fast)

Single interface that abstracts layer complexity:
```python
# Developer sees simple API
if feature.is_enabled("premium_dashboard", user_context):
    show_premium_dashboard()

# SDK internally routes to correct layer based on flag metadata
```

### Lifecycle Management: Auto-Decommissioning (Fast)

Telemetry-driven flag lifecycle:
1. Track flag evaluation frequency and last-change timestamp
2. Identify stale flags (no changes in 30+ days)
3. Auto-suggest tier migrations (Experimentation → Operational → Entitlement)
4. Flag candidates for code removal (Feature Flag Debt elimination)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      CONTROL PLANE                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Policy Engine (OPA)                     │   │
│  │  - Evaluates: Tier + Usage + Time + Health rules        │   │
│  │  - Validates: Schema + Constraints + Impact simulation  │   │
│  │  - Signs: Cryptographic artifact signing                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│           ┌────────────────┼────────────────┐                  │
│           ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ Auth System │  │ Cache Layer │  │ Vendor SDK          │    │
│  │ (Layer 1)   │  │ (Layer 2)   │  │ (Layer 3)           │    │
│  │             │  │             │  │                     │    │
│  │ Entitlement │  │ Operational │  │ Experimentation     │    │
│  │ flags in    │  │ flags via   │  │ flags via           │    │
│  │ JWT/session │  │ Redis/pub   │  │ LaunchDarkly API    │    │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘    │
│         │                │                     │               │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          └────────────────┼─────────────────────┘
                           ▼
              ┌─────────────────────────┐
              │      Unified SDK        │
              │  feature.is_enabled()   │
              │                         │
              │  Routes internally to   │
              │  correct layer based    │
              │  on flag metadata       │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Lifecycle Manager     │
              │                         │
              │  - Staleness tracking   │
              │  - Tier migration hints │
              │  - Debt elimination     │
              └─────────────────────────┘
```

## Consequences

### Positive

1. **80% of checks at 0ms latency**: Entitlements (most common) are in auth context
2. **Blast radius containment**: Each layer isolated; Layer 3 failures don't affect Layer 1
3. **Sales agility preserved**: Entitlements update on next auth refresh (seconds)
4. **A/B testing capabilities**: Full vendor SDK for complex targeting
5. **Auditability**: Single control plane with signed artifacts
6. **Tech debt prevention**: Auto-decommissioning eliminates flag sprawl
7. **Developer simplicity**: Single SDK interface hides complexity

### Negative

1. **Initial complexity**: Three layers + control plane vs single solution
2. **Flag classification required**: Each flag needs `lifecycle_policy` metadata
3. **Vendor dependency**: Layer 3 still requires external service
4. **Migration effort**: Existing flags need classification and routing

### Neutral

1. **Cost**: Vendor SDK costs reduced ~80% (only Layer 3 uses it)
2. **Team skills**: Requires understanding of event-driven architecture

## Implementation Path

### Phase 1: Foundation (Week 1-2)
1. Define flag schema with mandatory `lifecycle_policy` field
2. Implement Unified SDK wrapper with layer routing
3. Set up Layer 2 cache infrastructure (Redis pub/sub)

### Phase 2: Control Plane (Week 3-4)
1. Build Policy Engine with validation rules
2. Implement artifact signing and verification
3. Create admin UI for flag management

### Phase 3: Lifecycle Management (Week 5-6)
1. Instrument flag evaluation telemetry
2. Build staleness detection and alerts
3. Implement tier migration suggestions

### Phase 4: Migration (Week 7-8)
1. Classify existing flags
2. Migrate to appropriate layers
3. Deprecate legacy flag system

## Validation

This architecture was validated through cross-tier debate:
- **Architectural convergence**: All three tiers independently arrived at stratified/tiered approach
- **Consensus**: Premium tier achieved true consensus with critical-engineer validation
- **Cost modeling**: Premium tier provided 80% cost reduction simulation
- **Risk assessment**: Wall agents across tiers identified and mitigated risks

## References

- `docs/test-reports/2026-02-04-feature-flags-cross-tier-comparison.md`
- `docs/test-reports/2026-02-04-feature-flags-fast-decision-record.oct.md`
- `docs/test-reports/2026-02-04-feature-flags-standard-decision-record.oct.md`
- `docs/test-reports/2026-02-04-test3b-premium-decision-record.oct.md`

## Decision Provenance

| Tier | Thread ID | Decision Hash |
|------|-----------|---------------|
| Fast | `2026-02-04-feature-flags-fast-tier-comparison` | `bccc7649...` |
| Standard | `2026-02-04-feature-flags-standard-tier-comparison` | `a1eb2b4c...` |
| Premium | `2026-02-04-should-we-implement-feature-fl-01kgm5kp` | (original test 3b) |
