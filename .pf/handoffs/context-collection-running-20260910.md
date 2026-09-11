# Active shell diagnostics
User requested launching PF shell workers. Both started on 2026-09-10 using codex-exec, gpt-5.6-luna/medium.
Carrier: garage-orchestrate-bounded-pf-shell-diagnosis-of-mcp-versus-source-conte (task-execution-loop).
Shell run: context-collection-shell-20260910.
Tasks: context-origin (PID 13420) diagnoses source/installed/MCP classification freshness; report-capture (PID 15708) diagnoses expected report -> raw ingress -> transcript cardinality.
Boundaries: public sources read-only for both; private reproducer/report/proposed-diff ownership disjoint under .pf/artifacts/context-collection-20260910/<task> and .pf/tmp/<task>. Primary integrates public code sequentially after diagnosis. No infrastructure changes assigned.
Evidence: .pf/artifacts/context-collection-20260910/launch-status.json, plan/briefs, baseline snapshot and installed-context-baseline.txt; .pf/runtime/agent-runs/context-collection-shell-20260910/<task>/status.json, heartbeat.json, stderr.log, exit.json when finished.
Next: inspect worker status and expected report.md files; accept only actual results. Preserve previous audit and F09-F12 evidence. If collect hits known transcript cardinality issue, record it; do not edit transcripts or assume worker exit0 means collection success. Run remains in progress; this is launch handoff, not completion.
