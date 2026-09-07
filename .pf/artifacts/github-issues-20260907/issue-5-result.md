# GitHub Issue #5 — Workplace Local Resource Index

Status: ready_for_review

Problem: although the SQLite database path was already Workplace-wide, the CLI
and automatic maintenance derived its scope from each project snapshot. That
made a single physical index appear project-scoped and required a project
context for maintenance.

Resolution:

- `search-index status`, `refresh`, `rebuild`, `doctor`, and `tick` now take
  only `--workplace` and enumerate registered Workplace packages and templates.
- The global catalogue respects `indexing.mode` and reconciles removed resources.
- Garage maintenance and `pf.session_context` observe the global index; neither
  asks Runtime, Ledger, or sessions to enumerate projects.
- `pf.search` retains the requesting project's snapshot as an authorization
  filter over the shared database; it does not build a project copy.
- Documentation now describes the command boundary and one-index model.

Validation:

- `python tools/smoke_workplace_search_index.py` — PASS: two project filters,
  one physical package record, `fulltext`/`metadata`/`none`, and `pf.resolve`.
- `python tools/smoke_search_update_operational_hardening.py` — PASS.
- `python -m py_compile ...` and `git diff --check` — PASS.

Residual:

- The long stdio MCP regression was updated to the new CLI contract. Its test
  runner exceeded the interactive command-output window after the final
  assertion path, so its completion signal must be re-run in normal release QA.
