## 2026-09-07 12:15 - primary-agent

Task: Analyse and resolve GitHub issues #5 and #4 sequentially.
Files changed: none.
Artifacts changed: `.pf/artifacts/github-issues-20260907-run-record.md`.
Templates used: none.
Tools used: GitHub CLI; ProcessForge work-start/work-state; source inspection.
Decisions: Start with #5. The physical DB is already workplace-owned, but the indexed scope and maintenance path are still derived from a project snapshot.
Risks: Indexing must enumerate only registered Workplace resources and must preserve project authorization during search.
Next steps: Add a workplace resource snapshot and migrate CLI/automatic maintenance to it; validate package de-duplication and cross-project filtering.
Handoff: none.

## 2026-09-07 13:40 - primary-agent

Task: Complete the long stdio MCP regression for GitHub issue #5.
Files changed: no product behaviour changes; temporary diagnostic instrumentation was removed.
Artifacts changed: `.pf/artifacts/github-issues-20260907/issue-5-final-validation.md`.
Templates used: none.
Tools used: isolated background test process with captured output.
Decisions: Treat the first silent interactive return as an output-capture limit, then wait for the actual process result.
Risks: none remaining for the previously conditional MCP check.
Next steps: continue the separately created issue #4 run in a fresh session.
Handoff: issue #5 is fully validated.

## 2026-09-07 13:30 - primary-agent

Task: Resolve GitHub issue #5, shared Workplace local-resource index.
Files changed: `src/processforge_core/local_resource_search.py`, `src/processforge_core/garage.py`, `tools/processforge.py`, `tools/pf_runtime/session_read.py`, `tools/smoke_workplace_search_index.py`, `tools/smoke_project_init_local_search_mcp.py`, `docs/concepts/resource-search-index.md`.
Artifacts changed: `.pf/artifacts/github-issues-20260907/issue-5-result.md`.
Templates used: none.
Tools used: GitHub CLI, ProcessForge work state, Python smoke tests, compiler.
Decisions: Registered Workplace packages/templates are the maintenance source; project snapshots remain query authorization only. The retained `search_index_maintenance_for_known_projects` name is a compatibility shim and now ignores project roots.
Risks: The legacy stdio MCP smoke was updated but its final completion output exceeded the interactive command window; re-run it in release QA.
Next steps: Analyse and implement issue #4 only after this isolated #5 result is retained.
Handoff: none.
