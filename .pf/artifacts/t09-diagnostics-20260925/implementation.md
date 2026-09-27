# T09 implementation

Implemented stdlib-only src/processforge_core/diagnostics.py: eight levels/methods, profile/threshold/component/sink configuration and exact Work/session layers, downward storage limits/locks, expiry/detail sampling, sanitized bounded records, ContextVar correlation, JSONL interprocess lock/rotation/retention/quota, non-recursive failure health and exclusive read-only filtered bundle export.

Focused integrations: tools/processforge.py CLI options/status/export, common freshness wrapper and worker preparation; src/processforge_core/process_execution.py binds application-selected Work and emits metadata only after required journal succeeds; tools/pf_runtime/{mcp_server,host,codex_hooks}.py and tools/codex_exec_worker.py bind requests/ingress/attempts. Required process/session telemetry writers and raw ingress semantics retained. Hook failure stdout repaired after before proof; legacy debug output migrates to canonical sanitized stderr records, with bounded status/reason/event-count metadata.

Public developer regressions: tools/smoke_diagnostics.py and release-test registration; three existing hook stderr consumers updated to parse canonical records while retaining protocol/ingress assertions. Public schema and EN/RU diagnostics runbooks written under disjoint junior ownership, inspected by primary. Existing session telemetry/runtime docs link to new runbook in closeout integration.

Development verification: syntax check 7 Python files; MCP JSON-RPC and missing-session smokes PASS; Codex worker smoke PASS. New contract/privacy/failure/protocol/journal/concurrency/rotation/retention/export smoke PASS, including source CLI/MCP across all five profiles. Latest measured disabled 100000 calls median 0.116139s; enabled memory 10000 0.614143s; JSONL 10000 14.299841s. Full assurance and independent module review follow.

Implementation refinements within architecture: initial JSONL 10000 took 43.187783s, repeated stat calls replaced by one locked directory inventory; parallel-load retry was 20.901882s; isolated/repeated runs 12.208610s and 14.299841s meet fixed 20s budget. Invalid config fallback is off plus fixed non-sensitive stderr notice, rather than collecting normal errors under rejected locks. Earlier architecture's safe-fallback requirement is preserved; no limit was relaxed.

No installed update, service restart, snapshot refresh, registry changes or publication. Source delivery still requires formal assurance; source PASS does not qualify the installed MCP feature surface. All earlier approved evidence remains immutable.
