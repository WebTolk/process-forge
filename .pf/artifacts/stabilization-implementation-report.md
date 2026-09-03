# Garage/Forge Stabilization Implementation Report

Date: 2026-08-24
Run: `stabilization-garage-forge-20260824`
Task: `stabilization-implementation-20260824`

## Implemented

- Added `codex_integration` to `project-init-status`.
  It reports project-local `.codex/hooks.json` state, managed event coverage, missing events, global hook-file presence, and restart requirement without exposing local absolute paths.

- Added deterministic Codex hook installation to `project-onboard`.
  New PF projects now receive project-local Codex observation hooks through the existing safe merge/backup installer.

- Added `project-init-repair --repair-action install_codex_hooks --apply`.
  Missing, stale, or invalid managed hook state is now repairable through the normal initialization repair path.

- Added `.codex/hooks.json` to private `.gitignore` policy.
  The file contains a local adapter command path and must not be a public project artifact.

- Changed `doctor-project` `.gitignore` checks to use effective Git protection.
  A broad rule such as `.pf/` now passes protection for `.pf/process-forge.local.yaml`, `.pf/runtime/`, and `.pf/cache/`; missing exact policy lines are downgraded to WARN.

- Registered focused release-test checks:
  `smoke_project_init_codex_integration` and `smoke_doctor_gitignore_effective_protection`.

## Validation

- `python -m py_compile tools/processforge.py src/processforge_core/project_initialization.py tools/smoke_project_init_codex_integration.py tools/smoke_doctor_gitignore_effective_protection.py`
- `python tools/smoke_codex_integration.py`
- `python tools/smoke_project_init_codex_integration.py`
- `python tools/smoke_doctor_gitignore_effective_protection.py`
- `python tools/smoke_project_init_acceptance.py`
- `python tools/processforge.py release-test --root . --only smoke_project_init_codex_integration --only smoke_doctor_gitignore_effective_protection --no-clean --trace-smokes`
- `python tools/processforge.py doctor-project --project-root .`
- `python tools/processforge.py events-validate --project-root .`
- `git diff --check`

All listed checks passed. `git diff --check` emitted only CRLF normalization warnings for existing Windows working-copy files.

## Residual Gaps

- MCP `pf.project_initialization.repair` schema still does not advertise `install_codex_hooks` in this slice because `tools/pf_runtime/mcp_server.py` was outside the task write scope.
- MCP stdio startup still does not run bounded Garage bootstrap maintenance before serving tools.
- `search_readiness` is still represented through existing `project-context-check`, `session_context.search`, and `pf.search` index status rather than a dedicated first-class MCP object.
- Full clean new-project real Codex SessionStart acceptance requires starting a fresh Codex session after hooks are installed; this cannot be proven inside the current already-running session.
