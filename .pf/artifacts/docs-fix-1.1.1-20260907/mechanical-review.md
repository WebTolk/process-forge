# Mechanical worker review and ownership handoff

2026-09-07, primary orchestrator. Both Spark attempts have durable exit_code 0; original report/runtime evidence is preserved in attempts/docs111-mechanical/1 and /2.

Attempt 2 resolves D01 semantic drift but is NOT accepted as-is. It regressed D05 from the correct list-of-records into an unsupported mapping keyed by id, despite the explicit brief, and added square-bracket synopsis flags to a runnable bash example for D08. Parser-only search checks did not catch these unrelated regressions. Worker report claims are therefore overridden by this review.

Worker has terminated. Ownership of its three product files transfers to the orchestrator for the following precise integration fixes: restore required_outputs list item with explicit id/path/type/required; make project-context-check example executable without synopsis brackets; clarify read-only inventory wording and Workplace-scoped maintenance wording. No other writer owns these files. Validate normalized output records and both doctor examples, then collect worker output as provenance, not as independent acceptance.
