# Changelog

All notable changes to debate-hall-mcp are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-01-05

### Added
- WebSearch tool for ideator and synthesizer agents
- OCTAVE MCP package integration for OCTAVE formatting
- Comprehensive investigation of MCP tools functionality

### Changed
- Updated base agents (Wind/Wall/Door) to v3.0
- Updated specialist agents (Ideator, Validator, Synthesizer) to v4.0
- Refined model assignments based on M019 and M021 studies
- Streamlined documentation structure
- Updated thread_id validation format

### Fixed
- Resolve module import configuration issues
- Correct mypy errors
- Strengthen pre-commit hooks
- Add complete escape sequences for OCTAVE format
- Correct tool names in agent YAML frontmatter

### Refactored
- Removed backward compatibility debt from OCTAVE formatter
- Removed model recommendation from ideator agent

### Documentation
- Reorganized and deduplicated documentation
- Added controlled comparison and research studies
- Moved usage patterns to docs/guides/
- Created CONTRIBUTING.md

## [0.2.0] - 2026-01-03

### Added
- Platform-agnostic debate-hall skill (`skills/debate-hall/SKILL.md`)
- CHANGELOG.md for release history
- Advanced patterns in skill: Flash Debate, Socratic Pattern, Multi-Model Specialist
- "When to Use Debate-Hall" trigger conditions (from ho-orchestrate integration)
- README sections: "For AI Agents" (prominent callout) and "What is OCTAVE?"
- Skills README with installation instructions for Claude Code, Codex, Gemini
- Prominent AI agent skill callout at top of README

### Changed
- I2 (OCTAVE Binding) now marked COMPLETE - all acceptance criteria met
- PROJECT-CONTEXT updated with accurate issue status

### Verified
- All 20 closed issues validated with implementation evidence
- 262 tests passing, 91.44% coverage maintained

## [0.1.1] - 2025-01-01

### Fixed
- Cross-platform file locking using `filelock` library (Issue #48)
- Cross-platform atomic file operations using `os.replace` (PR #51)
- `.env` path calculation for repo root discovery (PR #71)

### Changed
- Updated pytest markers configuration for HestAI alignment (PR #72)

## [0.1.0] - 2025-12-31

### Added

#### Core Features
- `init_debate` - Create debate rooms with configurable limits
- `add_turn` - Record Wind/Wall/Door turns with cognition validation
- `get_debate` - View state, transcript, and next speaker
- `close_debate` - Finalize with synthesis (JSON or OCTAVE format)
- `pick_next_speaker` - Mediated mode speaker selection
- `force_close_debate` - I5 safety kill switch
- `tombstone_turn` - I4-compliant turn redaction

#### GitHub Integration
- `github_sync_debate` - Sync debate turns to GitHub Discussions/Issues
- `ratify_rfc` - Generate ADR from synthesis and create PR
- `human_interject` - Inject human GitHub comments into debate

#### Architecture Immutables
- I1: Cognitive State Isolation - Server-side state management
- I3: Finite Dialectic Closure - Hard turn/round limits
- I4: Verifiable Event Ledger - SHA-256 hash chain
- I5: Sovereign Safety Override - Admin kill switch

#### Enforcement Hardening (PRs #42-#46)
- Role-cognition mapping (Wind/PATHOS, Wall/ETHOS, Door/LOGOS)
- Mediated mode expected speaker persistence
- Synthesis validation (LOGOS rules on close)
- Atomic file writes (tempfile + rename + fsync)
- Audit trail with tombstone context preservation

### Quality
- 262 tests (257 unit + 5 e2e)
- 91.44% test coverage
- mypy strict mode (0 errors)
- ruff + black (0 violations)

### Documentation
- Comprehensive README with tool reference
- Agent definitions (Wind, Wall, Door)
- Specialist agents (Ideator, Validator, Synthesizer)
- Wall Content Contract (OCTAVE semantic structure)
- Multi-model debate patterns guide

## Known Limitations

### Issue #73: Phase 2 GitHub Automation (Investigation)
Automated debate triggering via GitHub webhooks/actions is not yet implemented. The three core GitHub tools (`github_sync_debate`, `ratify_rfc`, `human_interject`) are fully functional for manual orchestration. See Issue #73 for investigation status.

---

[Unreleased]: https://github.com/elevanaltd/debate-hall-mcp/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/elevanaltd/debate-hall-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/elevanaltd/debate-hall-mcp/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/elevanaltd/debate-hall-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/elevanaltd/debate-hall-mcp/releases/tag/v0.1.0
