# Clean Install Acceptance Report

Date: 2026-08-23
Status: pending final RC archive

## Planned Checks

- `bin/pf.py --help`
- `workplace-init`
- `doctor-workplace`
- `project-init`
- `project-context-refresh`
- `search-index tick`
- Runtime start/status/doctor
- MCP initialize/tools-list
- `pf.session_context`
- `pf.search`
- `pf.resolve`

## Current Evidence

Source-level project initialization, MCP/local search, and Runtime smokes passed
before final archive packaging:

- `smoke_project_init_local_search_mcp`: PASS.
- `smoke_project_init_acceptance`: PASS.
- `smoke_long_lived_runtime`: PASS.

Full clean-install acceptance must be rerun against the final committed 1.1.0
archive.
