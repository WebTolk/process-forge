# evolve-20261002-02 Investigation

Timestamp: 2026-10-02T13:05:20Z

Investigation report:
- Current MCP `pf.work.start` accepted only `session_id`, `project_root`,
  `objective`, and `process_id`.
- CLI already validates file-provided scope through
  `processforge_core.process_execution.creation_scope_intent`.
- `tools/pf_runtime/mcp_server.py` already imports `ProcessExecutionService`,
  so MCP can pass typed scope intent without editing `tools/processforge.py`.
- `tools/processforge.py` remains excluded because it is owned by active Work
  `agent-entry-e01-e02-scoped`.
- Python knowledge route checked through Work resource `docs.python:root`;
  it is available as metadata-only material at `D:\.agents\docs\python`.

Impact analysis:
- Public MCP tool schema changes for `pf.work.start` by adding one bounded
  optional object field: `scope_intent`.
- Existing objective-only MCP start remains valid.
- Arbitrary top-level arguments remain rejected by `additionalProperties: false`.
- Arbitrary assignment fields are rejected by the nested `scope_intent`
  schema and by `creation_scope_intent`.
- Runtime behavior uses the same immutable capsule creation path as CLI.

Evidence:
- `python -X utf8 -m py_compile tools/pf_runtime/mcp_server.py tools/smoke_garage_work_start_sessionless.py tools/smoke_mcp_codex_contract.py src/processforge_core/process_execution.py` passed.
- `python -X utf8 -B tools/smoke_mcp_codex_contract.py` passed.
- `python -X utf8 -B tools/smoke_garage_work_start_sessionless.py` passed.
