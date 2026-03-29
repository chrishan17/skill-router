## 1.0.2 - 2026-03-29

### Features
- Automatically set `disable-model-invocation: true` on sub-skills when grouped into a router, preventing direct invocation; restored on router deletion or skill removal
- Track which sub-skills had their flag set by the router in `_manifest.json` (`invocation_disabled_by_router`) to avoid clearing pre-existing flags

### Fixes
- Require `.openclaw` marker file for OpenClaw project detection (prevents false positives)

### Documentation
- Emphasise context window savings as a core value proposition on landing page and README
- Update context overhead numbers to reflect 100+ skill installations
- Highlight compounding context cost with each new skill install

### Tests
- Add full test suite for `disable-model-invocation` flag management (unit + integration)

## 1.0.1 - 2026-03-22

### Documentation
- Switch installation method to `npx skills install chrishan17/skill-router`
- Correct skill descriptions on landing page to reflect actual value proposition
- Audit and polish landing page — fonts, accessibility, transitions, design tokens, semantics

### Fixes
- Fix problem-item hover border clipped by adjacent elements

### CI
- Install pytest explicitly before running tests
