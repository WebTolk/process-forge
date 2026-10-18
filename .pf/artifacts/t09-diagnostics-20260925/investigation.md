# T09 investigation and impact

Source baseline a180ad624442d4fbe8ac1710073ef7d4c44babc4; no product code changed before investigation. Current installed MCP remains T08-qualified; this Work changes source only until integrated delivery.

Confirmed defect: reproduce-hook-stdout.py captures malformed JSON and injected Stop dispatch OSError. Both return exit 0, diagnostic JSON on stdout, empty stderr; Stop neutral response absent. hook-stdout-before.json is the durable before proof. codex_hooks.main except branch is the responsible layer; do not change transport/freshness policy to repair it.

Existing optional telemetry helper in tools/processforge.py:11038-11055 performs recursive value-pattern redaction and unbounded NDJSON appends. emit_process_event and ProcessExecutionService._emit are required process facts, not an optional logger; keep their write/error semantics unchanged. Do not apply diagnostic truncation to required evidence.

MCP respond/respond_valid centralize JSON-RPC validation and tool failure encoding; tool_result authorizes current session/project. Its facade must preserve error contents, notification silence and stdio wire. Garage ProjectContextService.check and ResourceSearchService.search obtain concrete freshness results; that shared boundary can emit reason/snapshot metadata without dumping documents. CLI final main dispatch can bind one invocation logger. Runtime ingest_event resolves project, persists raw receipt first then derives effects: diagnostics must not replace or reorder raw receipt. Worker preparation in the CLI is an existing common boundary; actual provider runner is tools/codex_exec_worker.py, not tools/pf_runtime/codex_exec_worker.py. Scope path corrected here; worker prompt redesign stays T05.

Existing docs distinguish private session telemetry/process facts/chat. New optional diagnostic directory and separate config can avoid changing snapshot/profile/freshness or old schemas. New core module is picked up by source distribution inclusion; source smoke should be registered in release commands. Checksum/public-surface validators will verify exact registries after edits.

Source/tooling evidence: scoped source inspection and worker-source-map.md (advisory descriptive map). Serena/IDE unavailable. Python standard library only; local PSR LoggerInterface and official Python logging/PSR-3 consulted during T01 provide the interface/mapping reference. No PHP dependency needed.

Impact/risk: synchronous diagnostic IO must be bounded and best effort; cross-process writes need a bounded lock. Filtering/off must not suppress original exception or journal. Arbitrary context serialization, secrets embedded in strings, export paths, config override locks and long-lived detail expiry require regression tests. Existing hook/provider/session authorization tests must still pass.
