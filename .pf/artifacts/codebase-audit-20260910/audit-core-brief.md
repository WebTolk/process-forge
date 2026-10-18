# Python core and execution contracts

Audit src/processforge_core, tools/processforge.py core CLI dispatch and contracts. Focus on NEW reproducible bugs in validation, atomicity, process transitions, malformed input, updater and resource search. Prior F01-F12 were repaired at current HEAD; read prior repair summaries before treating any as still open. Do not spend the whole audit retesting prior bugs. Aim for 2-4 concrete high-value defects, not style.

Baseline HEAD 901d0551773fe7a5b382b89ebe95b212b0747e83. Audit-only assignment: do not modify product code or other assignments. Write only your report, probes and evidence under .pf/artifacts/codebase-audit-20260910/audit-core/ and .pf/tmp/audit-core/. Reports in Russian preferred.

Use local docs first. Serena symbols unavailable (active languages empty); bounded rg/AST/shell fallback is allowed. Do not run PF work-start/transition or rebuild context: primary owns governance. No subagents, no infrastructure repair. No git operations modifying state. Existing dirty PF work belongs to others.

For each finding include severity, exact current file and line, violated documented or executable contract, real trigger, expected vs actual, runnable Python reproducer, captured output, impact, minimal proposed fix, isolated remediation task with allowed files, acceptance checks and S/M/L complexity plus recommended junior model. Distinguish confirmed reproduction from hypothesis. Do not claim mocked paths establish an actual user entry point without tracing reachability. If sandbox denies Python/process/file operations, save a self-contained reproducer for primary execution and label it unverified. Write report even if no confirmed defects.

Use temporary isolated fixtures only. Avoid external network/docs; no external facts are needed. Keep raw stdout/stderr as files if needed. Finish the bounded audit after a useful pass; do not attempt exhaustive whole-product verification. Keep final response concise and avoid copying full report into worker final output.
