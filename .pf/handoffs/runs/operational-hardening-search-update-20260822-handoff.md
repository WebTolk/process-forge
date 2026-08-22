# Handoff: primary-agent -> release-validation

Objective:
Operational hardening for search index maintenance and core updater recovery.

Current status:
Implementation and first smokes are in progress.

Input artifacts:
- `.pf/artifacts/operational-hardening-search-update-20260822/`
- `задания/process-forge-operational-hardening-search-update-master-prompt.md`

Files changed:
- Search index core
- Core updater core
- CLI resource event dirty marking
- Smoke tests
- Docs/artifacts

Files not to touch:
- Runtime daemon ownership model unless separately scoped.

Known issues:
- Live Codex proof not executable from repository-only context.
- Real Windows locked-handle smoke remains pending.

Required checks:
- Python compile
- Search operational smoke
- MCP local search smoke
- Core updater smoke
- Checksum validation
- `git diff --check`

Next recommended action:
Complete validation, refresh checksum inventory, commit, and push.
