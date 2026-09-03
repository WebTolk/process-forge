# Garage Core Simplification Implementation Report

Date: 2026-08-24
Status: implemented, smoke-validated

## Scope Implemented

- Added `src/processforge_core/garage.py` with Garage services for
  `pf.context`, snapshot-authorized search, snapshot-authorized resolve, search
  readiness, path-ref resolution, and governed-work summary.
- Updated `tools/pf_runtime/mcp_server.py` so Level 1 Garage reads work from
  `project_root` before the Ledger session gate.
- Kept `pf.session_context`, `pf.session_chat`, and `pf.session_activity`
  session-scoped.
- Updated `tools/pf_runtime/host.py` resolve behavior to use the same
  snapshot-bound resource resolution service.
- Registered Garage acceptance smoke tests in `release-test`.
- Simplified `.pf/START_AGENT_HERE.md` around the intended path:
  `pf.context`, `pf.search`, `pf.resolve`, local work, then governed work.
- Updated `docs/concepts/runtime-mcp.md`,
  `docs/concepts/resource-search-index.md`, and added
  `docs/concepts/garage-core.md`.

## Contract Decisions

- `project_root` is the Garage read authority.
- A supplied `session_id` is optional for Garage reads and must match the
  resolved project when present.
- `pf.search` performs bounded technical maintenance for missing/stale indexes,
  then runs a pure query against the authorized local index.
- Search readiness is normalized to `ready`, `empty`, `stale`, or `blocked`.
- Unknown resource ids return `denied` rather than prompting global workplace
  search.
- Private `local_path` navigation is runtime-only and only attached after the
  result is within an authorized content root.

## Verification Already Run

```text
python -m py_compile src/processforge_core/garage.py tools/pf_runtime/mcp_server.py tools/pf_runtime/host.py tools/smoke_garage_no_hooks_sessionless.py tools/smoke_garage_session_enhanced.py tools/smoke_garage_cross_project_security.py tools/smoke_garage_real_joomla_search.py tools/processforge.py
python tools/smoke_garage_no_hooks_sessionless.py
python tools/smoke_garage_session_enhanced.py
python tools/smoke_garage_cross_project_security.py
python tools/smoke_garage_real_joomla_search.py
```

All four Garage smoke tests passed.

## Residual Risks

- The implementation validates the required MCP stdio path with local smoke
  tests, not through an externally hosted Codex MCP session.
- `ContextReconciliationService` records the intended safe-refresh boundary, but
  automatic semantic reconciliation remains outside this implementation slice.
