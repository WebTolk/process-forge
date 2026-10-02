# evolve-20261002-02 Intake And Scope

Timestamp: 2026-10-02T12:58:10Z

Brief:
- Implement typed `scope_intent` support for MCP `pf.work.start`.
- Keep scope intent bounded to the existing creation-time assignment contract.
- Preserve current CLI `--scope-file` behavior and existing immutable capsules.

Accepted scope:
- Product change target: `tools/pf_runtime/mcp_server.py`.
- Supporting checks may update:
  - `tools/smoke_garage_work_start_sessionless.py`
  - `tools/smoke_mcp_codex_contract.py`
  - `tools/smoke_work_start_scope.py`
- Documentation may update:
  - `docs/concepts/work-context.md`
  - `docs/ru/concepts/work-context.md`
- `tools/processforge.py` is intentionally out of write scope because active
  Work `agent-entry-e01-e02-scoped` owns it.

Task record:
- Backlog task: `.pf/artifacts/evolve/tasks-20261002/evolve-20261002-02.md`.
- Dependency on `evolve-20261002-01` is satisfied by predecessor Work
  `garage-implement-evolve-20261002-01-preflight-execution-mode-and-effecti`.
- This task does not include install, Runtime restart, host reconnect, or
  release publication.

Acceptance interpretation:
- MCP `pf.work.start` accepts a typed JSON object, not a path, named
  `scope_intent`.
- The MCP argument schema rejects arbitrary assignment fields by keeping
  `additionalProperties: false`.
- The server validates `scope_intent` with the same `creation_scope_intent`
  function used by CLI `--scope-file`.
- Positive and negative smokes cover MCP schema, valid scope creation,
  invalid scope rejection, and legacy objective-only start.
