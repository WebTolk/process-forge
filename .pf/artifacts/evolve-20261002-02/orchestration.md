# evolve-20261002-02 Orchestration

Timestamp: 2026-10-02T12:55:43Z

Task record:
- Backlog item: `.pf/artifacts/evolve/tasks-20261002/evolve-20261002-02.md`.
- Objective: pass a bounded typed scope intent through MCP `pf.work.start`.
- Predecessor: completed `evolve-20261002-01` Work
  `garage-implement-evolve-20261002-01-preflight-execution-mode-and-effecti` /
  `implement-evolve-20261002-01-preflight-execution-mode-and-effective-perm`.

Execution context summary:
- New governed Work: `garage-implement-evolve-20261002-02-pass-typed-scope-intent-through-mcp`.
- Assignment: `implement-evolve-20261002-02-pass-typed-scope-intent-through-mcp-work-st`.
- Capsule: `implement-evolve-20261002-02-pass-typed-scope-intent-through-mcp-work-st-capsule`.
- Capsule checksum: `sha256:76fe6a2d0d05b224cef58cfb2cfadc28158f5e312291d333655dd8e12b5bd84e`.
- Scope file: `.pf/tmp/evolve-20261002-02-scope.json`.
- Writer scope excludes `tools/processforge.py` because active Work
  `agent-entry-e01-e02-scoped` owns that file. The MCP change will use the
  already imported `ProcessExecutionService` path in `tools/pf_runtime/mcp_server.py`.

Lifecycle mode decision:
- Use `software-feature-development`.
- Keep work in the primary agent; no subagents.
- Run the full stage chain through PF transitions.
- No infrastructure restart, install, or rollout is in scope for this task.

Planned checks:
- `python -X utf8 -m py_compile tools/pf_runtime/mcp_server.py src/processforge_core/process_execution.py tools/smoke_work_start_scope.py tools/smoke_garage_work_start_sessionless.py tools/smoke_mcp_codex_contract.py`
- Focused MCP/Work smokes after implementation.
- `git diff --check` on touched files and artifacts.
