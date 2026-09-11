# Required output checks: task plan

Status: ready
Run: garage-fix-required-output-checks-nameerror-per-process-forge-fix-requir
Assignment: fix-required-output-checks-nameerror-per-process-forge-fix-required-outp

One assignment covers the bounded core fix. Owner: primary agent. Process: task-batch-execution, single_agent.

1. Reproduce NameError before editing production code using a regression in the existing task batch smoke.
2. Domain contract: optional output PASS; missing path FAIL or WARN with waiver; existing file PASS; missing file FAIL in strict mode or WARN pending; expected_report and saved waiver behavior remain unchanged.
3. Implementation decision: delete the nine unrelated Codex gitignore lines from required_output_checks. Keep canonical doctor-project loop intact. No new abstraction, format or CLI change.
4. Add direct matrix coverage and real CLI checks for validation messages, absence of traceback, unchanged assignment/run state on failure, and persisted waiver on success. Retain successful artifact/report completion coverage. Run existing hooks/gitignore tests.
5. Run focused smoke, task/run suite and repository release-test with no destructive cleanup; refresh checksum inventory for changed public files. Record exact failures if full coverage exposes unrelated defects.
6. Review and record result, run/task doctors, final handoff and terminal PF transition.

Allowed files: tools/processforge.py; tools/smoke_process_run_task_batch.py; tools/smoke_doctor_gitignore_effective_protection.py (assert the existing hooks protection result); checksums/processforge.sha256 if needed for validation; this run's PF evidence. Other project and installed distribution files are outside scope.

The canonical run task-index is .pf/runs/garage-fix-required-output-checks-nameerror-per-process-forge-fix-requir/task-index.md. Current result: pending implementation and validation.
