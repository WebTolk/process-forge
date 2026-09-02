# Release Blocker: Run Artifact Consistency

Status: `remediated_pending_release_requalification`

Recorded at: `2026-08-31T11:55:00Z`

## Summary

The final 1.1.0 release must be reopened before being treated as ready for public rollout. Dogfooding found a confirmed ProcessForge integrity defect: concurrent mutating commands against the same run can leave `run.yaml`, `summary.md`, `task-index.md`, and the run handoff with conflicting statuses, while `run-doctor` still reports PASS.

This is not a packaging/provenance failure in the already published ZIP. It is a release-blocking product defect in PF run artifact consistency and diagnostics.

## Evidence

External dogfooding project:

- project: `D:\Dev\wt-image-resize-and-convert-joomla-plugin`
- run: `run-image-media-api-plugin-20260831`
- observed command pair: `run-summary --apply` and `run-complete --apply`
- both commands were launched in parallel against the same run at approximately `2026-08-31T06:48:40Z`
- event order included `run.completed` followed by two `run.summary.created` events in the same second

Observed stale derived state after manual partial recovery:

- `run.yaml`: `status: completed`
- `summary.md`: still reported `status: in_progress`
- `task-index.md`: still reported `Run status: in_progress`
- `.pf/handoffs/runs/run-image-media-api-plugin-20260831-handoff.md`: still reported `Status: in_progress`
- `run-doctor`: PASS despite the status drift above

## Root Cause

`run-summary --apply` loads the run, writes summary/handoff artifacts, and saves the run. `run-complete --apply` sets the run to `completed`, saves it, emits `run.completed`, then invokes summary generation.

When both commands run concurrently, the standalone `run-summary` can hold a stale `in_progress` copy and save it after `run-complete` has already saved `completed`. There is no per-run writer lock or optimistic concurrency check protecting this read-modify-write sequence.

`run-doctor` validates that the run status value is legal and that blocking tasks are done, but it does not verify parity between `run.yaml` and derived artifacts (`summary.md`, `task-index.md`, handoff).

## Release Impact

Impact: `release_blocker`

Reason:

- PF can publish contradictory lifecycle artifacts for a completed run.
- The recommended recovery path is not reliably detected by built-in diagnostics.
- Dogfooding agents may manually edit only `run.yaml`, leaving stale downstream artifacts and a false sense of consistency.

The already published v1.1.0 GitHub Release and ZIP remain provenance-valid, but the 1.1.0 release should not be considered final until this product defect is fixed, tested, and a replacement final artifact/tag/release decision is made.

## Required Remediation

- Add per-run mutation serialization or optimistic concurrency around run read-modify-write paths, especially `run-summary --apply`, `run-complete --apply`, task status updates, and other commands that save the same run artifact family.
- Ensure `run-complete --apply` renders summary/handoff/task-index from the same completed run state, without allowing a stale writer to revert derived artifacts.
- Extend `run-doctor` to validate status parity across `run.yaml`, `summary.md`, `task-index.md`, and run handoff.
- Add a deterministic regression test that runs concurrent `run-summary --apply` and `run-complete --apply` against the same run and asserts all derived artifacts remain `completed`.
- Add or extend a focused smoke so a manually edited `run.yaml` with stale summary/handoff/task-index fails doctor.

## Pause Handoff

No product code was changed in this pause. The next session should start from this artifact, implement the remediation, run focused tests first, then rerun release/archive/update gates before deciding whether to replace the current v1.1.0 GitHub Release assets.

## Remediation Completed

Recorded at: `2026-09-02T10:47:33Z`

Implemented in `tools/processforge.py`:

- All writers of an existing Run now use the per-run registry lock. This covers
  `run-summary`, `run-complete`, `task-create`, `task-start`, and task status
  updates.
- Run YAML and the task index are individually published with same-directory
  atomic replacement. `run-complete` renders the summary, handoff, task index,
  and `run.yaml` from one completed Run document while holding the lock.
- `run-doctor` holds the same lock while reading and verifies the declared
  status in `summary.md`, `task-index.md`, and the Run handoff. A completed Run
  must also have all three artifacts.

Regression evidence:

- `python tools/smoke_process_run_task_batch.py`: PASS.
- `python tools/processforge.py release-test --root . --no-clean --only
  smoke_process_run_task_batch --trace-smokes`: PASS in 69.24 seconds.
- The focused smoke launches `run-summary --apply` and `run-complete --apply`
  concurrently, verifies all four Run artifacts are `completed`, manually
  changes the summary to `in_progress`, requires `run-doctor` to fail, then
  restores it through `run-summary` and requires doctor to pass.

## Remaining Release Decision

The product defect is remediated, but the public 1.1.0 release remains
blocked for a clean-source requalification, checksum inventory refresh, fresh
archive/install/update verification, and an explicit decision about the
already published assets. The current working tree is intentionally dirty, so
these release-delivery gates were not represented as passed.
