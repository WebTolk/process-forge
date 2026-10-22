# Remediation of independent review findings

2026-10-22, primary integrator. First independent native review returned FAIL for
two reproduced P2 issues. Both are corrected within the existing final Work.

R1: timestamp accepts an external object, checks str explicitly and raises a
controlled ValueError. Collector commits the valid prefix, returns malformed_receipt
and resumes after the unaccepted tail is repaired. CLI retains JSON/error code 2.
Four invalid types (null/integer/list/object) are covered at collector and CLI.

R2: start_execution pairs UTC and monotonic observations with no file I/O between
them. Only in-memory final timing is updated at that point. The earlier persisted
open capture revision remains unknown-duration if abruptly interrupted; finish
persists actual execution endpoints in revision 2. A delayed metadata write cannot
inflate occupied time. Deterministic regression: two-second writes, ten-second
execution => elapsed=occupied=10, aligned clocks, six-second clipped execution=6.

Changed product files: binding.py, codex_exec_worker.py and the collector/CLI test
modules. All other candidate hashes remain unchanged. Registered Ruff lint/format
and 11-file scoped mypy pass again; joint suite and driver smoke results are in
the accompanying remediation QA report. First review's frozen reports/manifests
are retained unchanged. A separate independent re-review must accept these fixes;
primary does not self-approve. No unrelated implementation is included.
