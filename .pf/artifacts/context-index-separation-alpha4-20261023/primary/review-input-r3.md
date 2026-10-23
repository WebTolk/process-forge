# Final independent native review: alpha4 with selected batch indexing

Review only source-candidate-r13.json's frozen candidate-batch tree, all 41 files;
verify their SHA256 before/after. Main delta is main-owned-r3.diff. The original
r4 and corrected r10 trees remain immutable at their original paths. Read the r1
NO-GO report/probes and verify its four fixes through actual application routes.

Read current architecture-r2, storage-decision-r3, trigger-policy-r4,
review-fixes-plan-r2, idle-invalidation-decision-r4, query-busy-decision-r5,
batch-design-r7, batch-metadata-decision-r8, batch-acceptance-corrections-r9 and
selected-invalidation-decision-r10. r10 explicitly supersedes only the blanket
no-selective-ack rule: unknown/unselected/failed/raced global work still cannot
be acknowledged. Only known changes completely covered by successful selection
may resume known search coverage without full source-body verification.

Check the new batch CLI/Core/parser, native per-item latest-manifest transaction
and audit semantics, dry-run, preflight/duplicate/refusal, partial/committed-audit
failure, successful qualified ID order, exactly one final callback, no selection
widening or URL download, separate index failure, and actual Main wiring.

Probe independent notification publication/retirement, failure and crash windows,
whole-read checkpoints, global/project distinction, unknown/mixed/new notifications,
prior failures, selected disabled resources and unresolved roots. Check catalogue
metadata projection cannot hide unselected metadata/coverage changes, alter the
full-reconciliation timestamp or expose private stored hashes. No unselected source
body may be opened. Query authorization/counts/errors/pagination remain preserved.

Validate the exact bundled schema ref and nested root; arbitrary external refs
remain refused. The affected MCP readiness smoke retains every existing assertion
and now explicitly indexes its own fixture workplace. Check all tests/docs and
test-report-r3, quality/coverage/receipts and actual batch CLI acceptance. Full r12
pytest/15 native checks are bound to r13 by exact production bytes/Python AST
parity; the two import whitespace edits do not invent a new full test run.

SQLite FTS5 remains the real store; backend replacement is a narrow tested seam.
The same service serves explicit CLI and a cold job for the future PF scheduler.
No actual timer/Runtime registration, MySQL/vector/RAG implementation or broad
DAL is authorized. Required context/current project/Work access remain enforced.

Read actual pinned Python excerpts/provenance and OOP guidance. Emit READ_ACK.
Use stdlib fixture probes only in your own scratch; no product edits, Git, PF
lifecycle, external QA installation, infrastructure, live workplace/indexing or
subagents. Primary owns registered QA and delivery. Report concrete severity,
path/line, trigger/impact and correction for each finding, then CODE GO or NO-GO
and a real final RESULT. Do not treat pending full source/archive release gates
as completed or confuse stdio fixtures with actual installed/host acceptance.
