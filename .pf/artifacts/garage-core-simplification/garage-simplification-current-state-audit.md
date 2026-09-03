# Garage Simplification Current State Audit

Generated: 2026-08-24 14:45 +04
Run: `garage-core-simplification-20260824`
Assignment: `garage-core-simplification-audit-20260824`

## Summary

The current product still treats Agent Ledger session binding as a prerequisite
for the read-only MCP path that should be Garage-essential. This directly
contradicts the Garage Core Reset prompt.

The good news is that most lower-level functions already have enough project
root support to make the simplification feasible without rewriting Forge.

## Verified Current State

- `project-context-check --project-root .` reports:
  - snapshot `ctx-20260824-083958-50e142`;
  - status `fresh`;
  - resource readiness `fresh`;
  - execution readiness `ready`.
- The worktree is dirty from previous Garage stabilization work. This run must
  preserve those changes and build on them.
- Runtime status from the previous run was stopped; Garage must not depend on a
  long-lived daemon.

## Code Findings

### MCP Session Gate

`tools/pf_runtime/mcp_server.py` currently handles `pf.session_context`,
`pf.session_chat`, and `pf.session_activity` before the session gate, then
raises `missing_session` for every other tool when no session id is supplied.

Affected tools:

- `pf.project_state`;
- `pf.project_initialization.status`;
- `pf.project_initialization.initialize`;
- `pf.project_initialization.repair`;
- `pf.work_state`;
- `pf.resolve`;
- `pf.search`;
- `pf.workplace_state`.

The Garage prompt requires at least `pf.context`, `pf.project_state`,
`pf.search`, and `pf.resolve` to work without session.

### Host Project Resolution

`tools/pf_runtime/host.py` already has `project_for_session()` with this rule:
if `project_root` is provided, resolve the project from that path instead of
Ledger. This is the right seam for sessionless Garage reads.

### Search Index

`src/processforge_core/local_resource_search.py` already separates:

- `maintenance_tick()` for bounded refresh/rebuild;
- `search()` as a query operation that does not hide rebuild work.

However, request-local `path_ref` resolution is currently implemented inside
the MCP `pf.search` branch. CLI `search-index status` on the current project
shows a fresh index with `RESOURCES: 0` and `DOCUMENTS: 0`, while the snapshot
does contain `local_search_resources` with `path_ref`. This should move into a
Core service reusable by MCP and CLI/acceptance.

### Agent Instructions

`.pf/START_AGENT_HERE.md` still leads with reading snapshot files and running
`doctor-project`, and includes `hooks-dispatch` in useful commands. The new
prompt wants the ordinary agent path to start with `pf.context`, then
`pf.search`, then `pf.resolve`.

## Conclusion

The main implementation risk is not security; the snapshot authorization model
can remain intact. The risk is compatibility: session-scoped tools must stay
session-scoped, while read-only project context/search/resolve become
sessionless without leaking private chat, sessions, or unrelated project
resources.
