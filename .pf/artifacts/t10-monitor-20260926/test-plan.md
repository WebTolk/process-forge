# T10 assurance plan and cases

Primary-agent review follows completed implementation; no subagents. Q01 truth/freshness/unknown/cache semantics and no-write canaries, Q02 malformed/oversize/future/PID/probe failure/owner race, Q03 existing lifecycle branch parity, Q04 numeric loopback and redirect/slow-trickle deadline, Q05 actual cell-state emulator for resize/shrink/erased tails and Unicode/control input, Q06 normal/exception cleanup and Windows console-mode restore, Q07 real CLI JSON/plain/non-TTY/offline/argument validation/diagnostic bypass. All are executed by smoke_runtime_monitor.py, not documentation-only cases.

Regression scope: singleton/orphan, status/version truth, scheduler isolation, domain-neutral helper rules, agent infrastructure policy and MCP/hook docs. Product checks: AST, doc links, public cleanliness, normalized checksum inventory; public-only fixture schema/checksum/new smoke; preservation of all baseline files outside nine allowed product files and own governance.

Actual Windows PTY transcript covers refresh, freshness changes, Q exit and restored alternate screen; additional Ctrl+C observation will use the same read-only command. No shared daemon lifecycle or config calls. Source viewer against installed state is not installed Core delivery proof. Read-only before/after owner identity is checked separately.

General checkout schema check currently fails at pre-T10 journal line 34212. Expected-failure evidence must retain the exact hash and line, and must not be presented as a green global schema run. Public-only fixture validates the changed product surface separately without editing historical event data. That fixture is not a release archive or installed candidate. Generic full release/install/browser checks are not_applicable for source viewer delivery; new smoke is registered in future release-test.

Automation: assurance.py persists each stdout/stderr/exit code and source hashes. Runtime fixture directories are isolated OS temp or declared durable .pf/tmp/t10-monitor-20260926. Never delete prior T06 evidence.
