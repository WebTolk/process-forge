# MCP And Search Live Acceptance Report

Date: 2026-08-23
Status: PASS with external live-host note

## Source-Level Acceptance

- `pf.session_context` readiness/search model: covered by MCP/session smokes.
- `pf.search`: covered by `smoke_project_init_local_search_mcp`.
- `pf.resolve`: covered by freshness/readiness and MCP local search flows.
- Fulltext/metadata/none policies: covered by
  `smoke_resource_indexing_policy_acceptance`.
- Stale/fresh invariant: covered by resource-indexing and freshness smokes.

## Installed RC MCP JSON-RPC Proof

Archive under test: `dist/processforge.zip` version `1.1.0`.

Setup:

- Extracted the archive into a temp installed core root.
- Initialized a temp workplace and project.
- Registered `docs.joomla` with resource `docs.joomla:joomla-docs`.
- Resource path used for the fixture: `D:\.agents\docs\joomla`.
- Refreshed project context and search index.
- Checked in session `joomla-session`.

Results:

- PASS: MCP `initialize` returned server version `1.1.0`.
- PASS: `pf.session_context` returned `context_freshness.status=fresh` and
  search status `fresh`.
- PASS: `pf.search` query `Joomla` returned `search_status=fresh`,
  `results=1`, first `resource_id=docs.joomla:joomla-docs`.
- PASS: `pf.resolve` for `docs.joomla:joomla-docs` returned
  `resource.status=available`.

## Live Codex Host

Direct stdio/runtime MCP proof passed against the installed RC. A real Codex
host trust/approval path was not exercised in this local release run; it remains
an external host-policy path, not a ProcessForge product failure in this
workspace.
