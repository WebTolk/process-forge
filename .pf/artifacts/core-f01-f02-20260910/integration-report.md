# F01/F02 remediation integration — accepted with full-suite boundary

Primary orchestrator, 2026-09-10. Scope: Python audit F01 project search authorization and F02 unowned Core update path collisions. User explicitly requested junior PF shell workers. No version change, commit, push, publication or installed Core update.

Baseline: dev, 1aecc18b6824204ca45ab30241b92d26e6d583a5, with existing uncommitted docs and required-output fixes. baseline.json and baseline.diff capture starting public state. Previous approved audit evidence remains untouched.

## Final implementation

- Garage query now uses project root and resolved project snapshot; maintenance/readiness continue on the shared Workplace snapshot/index. SQL counts, pagination and results are authorized before presentation; resolve behavior stays unchanged.
- Core update planning reports unowned_path_collision for an existing newly-owned target or unsafe ancestor. Apply rebuilds the plan and rejects this blocker even with force_local_modifications, before creating update/backup state. Identical bytes do not silently establish ownership.
- A removed owned regular file may become a directory for newly added child files; symlink ancestors remain blocked. Existing local-modification confirmation and backup-byte preservation are retained.
- Public tests register real Workplace packages/resources and select them through normal project refresh. Cross-project checks include a genuinely indexed positive control, own/forbidden queries, authorized totals/pages, empty selection, resolve denial, session/project mismatch and shared-index preservation. Sessionless smoke retains no-hooks/no-daemon behavior.

## Delegation and adjudication

Luna/high: f01-search and f02-update implementation; Luna/medium: f02-owned-ancestor correction and report-only f0102-assurance; Luna/high: f0102-review. All launched via PF worker-run/codex-exec, never independent desktop tasks. Non-overlapping implementation scopes, no writers during final assurance.

Primary rejected first public-test workarounds involving Git HEAD and fixed private scratch paths. Worker sandbox TemporaryDirectory WinError 5 was handled as an environment limitation; genuine unchanged test runs were executed by primary. Primary also reproduced and corrected owned-ancestor compatibility regression and renamed fixture packages to satisfy public-cleanliness policy. Rejected attempts and corrections are retained in separate evidence directories/amendment.

## Verification established

- Genuine targeted updater, cross-project security, sessionless, and project-resource-narrowing checks PASS. Updated owned-ancestor updater regression PASS with actual backup-byte assertions.
- Final isolated public copy without .git/.pf: updated updater/security smokes PASS. Replacing only corresponding product modules with pinned baseline makes both new regressions FAIL at expected assertions.
- Source-preservation check PASS: prior tracked public dirty files unchanged outside declared scope plus public checksum inventory.
- Symlink and dangling-symlink runtime cases explicitly SKIP WinError 1314; no privileged runtime coverage claimed.
- Independent assurance: PASS with recorded environment/coverage limits. Independent final review: PASS, no actionable findings in bounded final diff. All five shell assignments exited 0 and were collected DONE; scoped shell run-doctor PASS.
- Final checksum verification and git diff --check PASS. Initial full-source attempt failed public-cleanliness fixture ids; corrected and preserved as historical failure.
- Final full-source attempt: **45 PASS / 1 FAIL**, 781.40 seconds in release runner, terminal RESULT FAIL. Failure is smoke_long_lived_runtime.py:179/130/33, test Runtime exits during startup with code 1. Fail-fast stopped remaining checks. Command: python -u bin/pf.py release-test --no-clean --trace-smokes --fail-fast. Raw stdout, JSON and trace preserved under full-source-2*.
- Exact clean baseline public HEAD 1aecc18b reproduced the SAME runtime startup failure: exit 1, 24.594 seconds, 946 tracked public files from git archive without .pf/.git. See baseline-runtime.json and baseline-runtime.stderr.txt. This is an independently reproduced existing blocker, not a reason to weaken the test or change installed infrastructure in this batch.

## Remaining boundaries

F01/F02 accepted for this bounded remediation; F03-F12 remain open in the original Python-core audit. Source release readiness is NOT confirmed because of the separately reproduced Runtime startup blocker; later checks in the suite remain unexecuted. No archive/extracted-distribution or public-release qualification. Existing dist archives preserved. Next: separately diagnose the temporary Runtime startup failure and remediate F03-F05 evidence/terminal transaction consistency, then remaining findings and full source qualification.
