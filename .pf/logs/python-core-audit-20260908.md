# Python core audit log

## 2026-09-08 12:00 +04:00 — primary auditor

Task: establish governed analysis-only Python core audit.
Files analyzed: .pf/AGENTS.md, manifests, snapshot, current audit assignment/capsule, latest docs-fix handoff; src/processforge_core/process_execution.py and local_resource_search.py excerpts; tools/processforge.py AST.
Files changed: own audit plan and log; context refresh and work-start generated PF state.
Artifacts changed: .pf/artifacts/python-core-audit-20260908/plan.md.
Templates used: PF logging/handoff conventions; pinned task-batch-execution.
Tools used: PF MCP, Serena, IDE MCP, local CLI, Python AST, PowerShell.
Decisions: preserve existing dirty changes; audit sequentially; local CLI fallback because installed MCP still rejects refreshed context.
Risks: semantic tooling unavailable; no findings confirmed yet; prior release suite stopped at sessionless search.
Next steps: record baseline, transition to execution, reproduce candidate defects in isolated fixtures.
Handoff: primary auditor retains sole write ownership of audit files.

## 2026-09-08 12:04 +04:00 — primary auditor

Task: static audit and isolated reproduction of high-risk core behavior.
Files analyzed: tools/processforge.py; src/processforge_core/{garage,process_execution,local_resource_search,core_update,project_initialization}.py; process_catalog; tools/pf_runtime/{mcp_server,host,raw_ingress_kernel}.py; relevant smoke fixtures.
Files changed: own reproduction/check runners and JSON/text evidence under .pf/artifacts/python-core-audit-20260908; Pyflakes vendor under own .pf/tmp directory.
Artifacts changed: baseline.json, pyflakes.txt, fast-results.json, integration-results.json, ingress-scan-results.json, checks/results.json and check outputs, source-preservation.json, source-context-check.json, report.md.
Templates used: audit plan and PF log format.
Tools used: Python AST, Pyflakes 3.4.0 (263 files), temporary PF/Workplace fixtures, stdio MCP, controlled OSError injection, sys.settrace, Git blame, 12 existing validators/smokes.
Decisions: confirm 12 defects (5 P1, 7 P2); separate stale test fixture and environment limitations; no product repairs within analysis-only scope.
Validation: 11 existing checks PASS; sessionless/no-hooks search smoke FAIL with empty_corpus; integration reproduction finishes successfully and proves forbidden resource returned despite resolve denial; all 26 inventoried core/runtime SHA-256 unchanged.
Risks: symlink probe unavailable due WinError 1314; full source/archive/extracted release qualification not performed. Early search-fixture attempts were rejected by snapshot freshness or lacked selected resources; only the final unmodified generated snapshot with a real Workplace index is accepted as F01 evidence.
Next steps: review finding priorities and evidence, validate audit task/run, publish local handoff, complete this audit's governed stages.
Handoff: primary auditor retains report review and closeout responsibility; pinned process forbids subagents.
