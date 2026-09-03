# CLI/MCP integration implementation report

## Delivered

- `project-init-status` is a read-only CLI command backed by the shared Core initialization status adapter.
- Core status now includes snapshot health, workplace, resource, MCP and repair-plan fields; initialize/repair share the explicit apply guard.
- `mcp-register` now defaults to a proposal unless `--apply` is explicit.
- Ledger-bound MCP has `pf.project_initialization.status`; `pf.search` remains local-snapshot-only.
- Runtime and authoring docs describe the two new read surfaces and explicit apply boundary.
- The FTS5 smoke bootstraps `src` itself, so it is executable directly from the checkout.

## Verification

- `py_compile` over changed CLI/Core/MCP/smoke modules: pass.
- `project-init-status --project-root . --json`: pass.
- `smoke_project_init_local_search_mcp.py`: pass.
- Static registration of `pf.search` and `pf.project_initialization.status`: pass.
- `git diff --check`: pass.

## Still required before final release acceptance

The deeper snapshot producer metadata and fully shared callback migration of the legacy writer/repair CLI remain a follow-up: the current `project-init-status` and explicit apply guard are integrated, while `init-project` continues to use its proven existing writer path. A Spark review is required next.
