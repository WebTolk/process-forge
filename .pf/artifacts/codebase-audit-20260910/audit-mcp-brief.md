# MCP routing and worker collection

Audit tools/pf_runtime/mcp_server.py, session_read.py, garage.py, tools/codex_exec_worker.py and worker collection in tools/processforge.py. Focus authorization/session binding, protocol error handling, lost reports, retry/idempotence. Follow up prior context-collection reports but independently reproduce correct execution path: prior report-capture probe stopped at untrusted_conversation_provenance, NOT unsafe_automatic_content. Do not repeat unproven interpretation. Aim for 2-4 concrete defects.

Baseline HEAD 901d0551773fe7a5b382b89ebe95b212b0747e83. Audit-only assignment: do not modify product code or other assignments. Write only your report, probes and evidence under .pf/artifacts/codebase-audit-20260910/audit-mcp/ and .pf/tmp/audit-mcp/. Reports in Russian preferred.

Use local docs first. Serena symbols unavailable (active languages empty); bounded rg/AST/shell fallback is allowed. Do not run PF work-start/transition or rebuild context: primary owns governance. No subagents, no infrastructure repair. No git operations modifying state. Existing dirty PF work belongs to others.

For each finding include severity, exact current file and line, violated documented or executable contract, real trigger, expected vs actual, runnable Python reproducer, captured output, impact, minimal proposed fix, isolated remediation task with allowed files, acceptance checks and S/M/L complexity plus recommended junior model. Distinguish confirmed reproduction from hypothesis. Do not claim mocked paths establish an actual user entry point without tracing reachability. If sandbox denies Python/process/file operations, save a self-contained reproducer for primary execution and label it unverified. Write report even if no confirmed defects.

Use temporary isolated fixtures only. Avoid external network/docs; no external facts are needed. Keep raw stdout/stderr as files if needed. Finish the bounded audit after a useful pass; do not attempt exhaustive whole-product verification. Keep final response concise and avoid copying full report into worker final output.
