# Implementation Report: Garage Stabilization After New Project Test

Generated: 2026-08-24 13:55 +04
Run: `garage-stabilization-after-new-project-20260824`
Assignment: `garage-after-new-project-implementation-20260824`

## Changes

### MCP Diagnostics

Updated `tools/pf_runtime/mcp_server.py`:

- `safe_tool_error()` now returns actionable remediation metadata for
  `missing_session`, `unknown_session`, `session_not_routed`, and
  `session_project_mismatch`;
- `pf.project_initialization.repair` schema now exposes the existing
  `install_codex_hooks` repair action.

This keeps MCP fail-closed while making the Garage failure actionable.

### Session Projection Consistency

Updated `tools/processforge.py`:

- `update_stale_agent_presence()` now rewrites project/workplace
  current-session projections when an online presence expires and is marked
  `stale`.

This closes the observed gap where Ledger presence could expire while
`.pf/runtime/current-session.json` still looked online.

### Fulltext Acceptance Fixture

Added `tools/smoke_fulltext_article_indexing.py`:

- creates a temporary project article;
- proves query-before-maintenance returns `missing`;
- runs bounded maintenance;
- proves a unique article term is found through SQLite FTS with the expected
  `resource_id` and `canonical_path`.

### Regression Smokes

Added:

- `tools/smoke_mcp_missing_session_diagnostics.py`;
- `tools/smoke_session_projection_expiry.py`;
- `tools/smoke_fulltext_article_indexing.py`.

Registered all three in `release-test`.

### Documentation

Updated:

- `docs/concepts/runtime-mcp.md` with the richer missing-session remediation
  contract;
- `docs/concepts/resource-search-index.md` with the distinction between index
  freshness and semantic corpus readiness.

## Validation

Passed:

```text
python -m py_compile tools/processforge.py tools/pf_runtime/mcp_server.py tools/smoke_mcp_missing_session_diagnostics.py tools/smoke_session_projection_expiry.py tools/smoke_fulltext_article_indexing.py
python tools/smoke_mcp_missing_session_diagnostics.py
python tools/smoke_fulltext_article_indexing.py
python tools/smoke_session_projection_expiry.py
python tools/processforge.py release-test --root . --only smoke_mcp_missing_session_diagnostics --only smoke_session_projection_expiry --only smoke_fulltext_article_indexing --no-clean
```

## Residual Gaps

Not completed in this implementation slice:

- real new Codex SessionStart proof after opening a fresh Codex session;
- real Codex MCP registration/tool visibility proof;
- full Runtime version-product renaming beyond current truth reporting;
- derived-report lifecycle implementation beyond audit classification;
- a complete high-level governed-work bootstrap API.

Status: `pass_with_conditions`.
