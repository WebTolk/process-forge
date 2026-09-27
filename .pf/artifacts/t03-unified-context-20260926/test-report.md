# T03 test report

Verdict: source acceptance PASS. The actual connected MCP governs this task using its existing T08 legacy capsule; this is distinct from testing the new source feature and is not installed-feature acceptance.

- Developer probe: actual governed and CLI builders produce exactly equal execution_contract values in isolated equivalent project roots. Immutable source and semantic intent changes are rejected; lifecycle/preferences are stable; force refuses overwrite.
- Registered smoke_work_capsule_contract_parity: 17 named checks PASS. It covers empty permissions/resources, analysis write denial, missing capabilities/sources, missing/nonmember runs, obligations, conflicting source checksums, portable paths and source budgets, semantic mutations, malformed policy, legacy/unknown versions, outer byte anchor, pinned process/stage parameters, and real transition immutability. See worker-regression.md for exact harness history and separate source fixes.
- Eleven compatibility checks PASS: project overrides, assignment parameters, snapshot pinning, specializations, workspace access, pinned process transition, stage transition, multi-process Work, Codex worker governance, shell worker, and T02 resource binding. Exact outputs/timing are retained in assurance-results.json, finished 2026-09-26T03:40:18Z.
- Final schema, public cleanliness, checksum inventory, Python parsing, EN/RU links and positive/negative contract schema checks are recorded in final-checks.json and delivery-verification.json. The embedded schema equals the standalone definition; all 18 required-field negative cases reject.

Earlier shell cleanup failure was diagnosed as a fixture leaving a ready attempt. Fixture stop records and a CRC-verified archive are in shell-cleanup.json and shell-fixture-cleanup-failure.zip; cleanup now checks its resolved target containment. An initial AST check failed on an existing BOM and was corrected to utf-8-sig. A broken RU relative link was repaired. These failures are not hidden in the final verdict.

Limit: this Windows account cannot create test symlinks; that branch is unavailable, not PASS. Traversal and absolute-path negatives pass. No full release/package/installed-host verdict is inferred from these focused checks. Original main capsule checksum remains 8ee0d2ac810317140423b23529603a42183f2c6be3649e8c94ee33544fdcea9a.
