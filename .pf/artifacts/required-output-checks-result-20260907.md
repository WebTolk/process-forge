# Required output checks: result and validation

Status: fix verified; full-suite attempt stopped on an independently confirmed baseline defect
Source baseline: dev, 1aecc18b6824204ca45ab30241b92d26e6d583a5.

## Cause and fix

Git blame attributes the erroneous nine-line branch to 07b1fb68011f5928be824f0c7343322992cf809a (2026-08-31, release: finalize ProcessForge 1.1.0 source). Git show confirms that this commit inserted the branch into required_output_checks while separately extending doctor-project's gitignore loop. There was no removal of this warning from doctor-project in that diff. The misplaced branch reads entry, which exists in the doctor loop but is undefined in output validation. Its intended placement is inferred from its content; history proves the insertion and surrounding doctor changes, not the editing action that caused it.

Removed only that branch. Missing path without waiver now reaches the existing FAIL; a waiver still returns WARN. The completion command checks failures before changing assignment/run state. Existing file, missing file, optional output, expected_report and waiver parsing contracts remain unchanged.

## Reproduction

Before modifying production code, `python tools/smoke_process_run_task_batch.py` failed in the new direct matrix:

```text
tools/processforge.py:12476 in required_output_checks
elif entry == ".codex/hooks.json" and not (project_root / entry).exists():
NameError: name 'entry' is not defined
```

## Verified coverage

- 13 required-output cases: absent/blank/null path, dictionary/bare-id/CLI-string forms, strict and pending modes, missing-path waiver, existing file, absent file, absent-file waiver and optional outputs.
- 5 expected_report cases: existing/missing/pending and both waiver aliases.
- Real task-complete CLI: exact controlled failure message, exit 1, no traceback, unchanged assignment and run bytes and no process events on rejection; waiver leads to done in both assignment and run, with persisted reason.
- task-doctor: missing-path FAIL and persisted-waiver WARN. run-doctor retains structural consistency behavior. Existing successful artifact/report completion and final run completion pass.
- doctor-project hooks protection: existing smoke now explicitly asserts PASS for .codex/hooks.json. Optional-hooks documentation test also passes.

## Commands and results

- Focused invocation of `required_output_check_matrix` and `required_output_workflow` from tools/smoke_process_run_task_batch.py in TemporaryDirectory: PASS.
- `python tools/smoke_process_run_task_batch.py`: PASS, including positive, negative, required-output and concurrent-artifact workflows.
- `python tools/smoke_doctor_gitignore_effective_protection.py`: PASS.
- `python tools/smoke_docs_codex_hooks_optional.py`: PASS.
- `python tools/validate-process-forge-checksums.py --write` then `--check`: PASS; only three changed public-file hashes.
- `git diff --check`: PASS.
- Current governed assignment task-doctor and run-doctor: PASS.
- `python -u tools/processforge.py release-test --no-clean --trace-smokes --fail-fast`: 86 PASS, 1 FAIL; RESULT: FAIL after 816.381 seconds, at smoke_context_freshness_vs_execution_readiness. All earlier checks passed, including the expanded task batch smoke (64.09 seconds). Checks after this failure were not run; the terminal suite report is preserved in required-output-checks-release-test-20260907.json and .md. No release packaging/publication or installed Core update is implied.

## Full-suite baseline failure

The unchanged smoke_context_freshness_vs_execution_readiness.py:160 calls `search-index refresh --project-root <project> --workplace <workplace>`. The CLI refresh parser accepts --workplace but no --project-root. The subprocess exits 2 with `error: unrecognized arguments: --project-root ...`; the smoke raises AssertionError and exits 1. This failure happens before required_output_checks or task-complete can execute.

Baseline verification loaded the exact `HEAD:tools/processforge.py` using `git show`, compiled it with the canonical source __file__, and invoked its parser with `search-index refresh --project-root baseline-probe --workplace baseline-workplace-probe`. It produced the same unsupported --project-root error and exit 2. Only argument parsing was exercised; nonexistent probe paths were never opened or modified. The failed smoke has no diff from HEAD, and this patch changes no parser definitions. The baseline issue is outside this fix and remains unchanged.

## Boundaries and observations

task-create already rejects newly declared required outputs without path; the regression therefore prepares a valid temporary task and removes its path to model existing file-first assignment state. This is fixture setup only. Initial test authoring assumptions about task-create and run-doctor were corrected against observed/source contracts.

doctor-project currently requires .codex/hooks.json ignore protection even when hooks are absent. The misplaced optional warning suggests a separate policy discrepancy. No doctor behavior change is included here.

Production files: tools/processforge.py, tools/smoke_process_run_task_batch.py, tools/smoke_doctor_gitignore_effective_protection.py, checksums/processforge.sha256. Version, release notes, ingress locks, installed distribution and user projects are untouched. PF projections already had changes before work began; preserve their history and the new run evidence.
