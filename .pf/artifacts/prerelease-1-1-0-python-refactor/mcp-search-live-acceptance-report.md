# MCP And Search Live Acceptance Report

Date: 2026-08-23
Status: partial

## Source-Level Acceptance

- `pf.session_context` readiness/search model: covered by MCP/session smokes.
- `pf.search`: covered by `smoke_project_init_local_search_mcp`.
- `pf.resolve`: covered by freshness/readiness and MCP local search flows.
- Fulltext/metadata/none policies: covered by
  `smoke_resource_indexing_policy_acceptance`.
- Stale/fresh invariant: covered by resource-indexing and freshness smokes.

## Live Codex Host

Direct stdio/runtime proof is in scope. A real Codex-host MCP trust/approval
path may remain host-policy dependent. If unavailable, it will be reported as an
external host blocker rather than a ProcessForge product failure.
