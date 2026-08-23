## 2026-08-23 13:28 - codex-main

Task:
Freshness vs execution readiness release blocker from `задания/process-forge-freshness-execution-readiness-release-blocker-master-prompt.md`.
Files changed:
`.pf/runs/freshness-execution-readiness-20260823/run.yaml`, `.pf/assignments/freshness-execution-readiness-main.yaml`, `.pf/contexts/assignment-capsules/freshness-execution-readiness-main.capsule.yaml`, `.pf/logs/freshness-execution-readiness-20260823.md`.
Artifacts changed:
Run, task, capsule, log initialized.
Templates used:
ProcessForge assignment/capsule flow.
Tools used:
`project-context-check`, `run-create`, `task-create`, `assignment-capsule`, `rg`.
Decisions:
The release blocker is in `project_context_check_result()`: missing required capabilities are currently appended to `broken_refs`, which makes read-only MCP/search treat otherwise valid resources as `snapshot_not_fresh`.
Risks:
Need preserve fail-closed behavior for missing/corrupt snapshots and stale resource fingerprints.
Next steps:
Implement readiness split, add regression smoke, run Joomla acceptance.
Handoff:
None.

## 2026-08-23 17:44 - codex-main

Task:
Final validation preparation and ProcessForge closure for freshness/readiness release blocker.
Files changed:
`.pf/artifacts/freshness-execution-readiness/release-blocker-validation.md`, `.pf/assignments/freshness-execution-readiness-main.yaml`, `.pf/runs/freshness-execution-readiness-20260823/run.yaml`, `.pf/runs/freshness-execution-readiness-20260823/summary.md`, `.pf/handoffs/runs/freshness-execution-readiness-20260823-handoff.md`.
Artifacts changed:
Validation report updated; assignment and run marked completed.
Templates used:
ProcessForge task/run completion commands.
Tools used:
`task-complete`, `run-complete`, `release-test --public`.
Decisions:
Named release ZIP/manifest artifacts under `dist/` are stale public artifacts by local release policy and were removed, leaving only `processforge.zip` and `processforge.manifest.json`.
Risks:
Final provenance smoke requires a committed clean Git tree; unrelated pre-existing projection/report dirt will be kept outside the release-source validation.
Next steps:
Commit the slice, temporarily clear unrelated dirty files from the worktree, rerun public release validation, push.
Handoff:
`.pf/handoffs/runs/freshness-execution-readiness-20260823-handoff.md`.

## 2026-08-23 17:14 - codex-main

Task:
Implementation, acceptance and review remediation for freshness/readiness release blocker.
Files changed:
`tools/processforge.py`, `tools/pf_runtime/mcp_server.py`, `tools/pf_runtime/session_read.py`, `tools/smoke_context_freshness_vs_execution_readiness.py`, docs, `.pf/artifacts/freshness-execution-readiness/**`, `.pf/reviews/freshness-execution-readiness/**`.
Artifacts changed:
Audit, model, capability-provider audit, implementation report, Joomla acceptance report, reviews and validation report.
Templates used:
None.
Tools used:
`py_compile`, focused smokes, stdio MCP, `project-context-check`, `search-index refresh`, delegated architecture/code review.
Decisions:
Missing execution capabilities are reported under `execution_readiness`; missing required resources/platform resolution remain context/resource failures and block search/indexing. `pf.resolve` now gates concrete resource resolution on fresh/fresh_with_updates context.
Risks:
Broad release/archive validation still pending; checksum inventory needs refresh after public file changes.
Next steps:
Run schema/public/checksum/release-adjacent validation, update assignment status, inspect final diff.
Handoff:
None.
