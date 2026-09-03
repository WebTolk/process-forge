# Current Work Selection Audit

Date: 2026-08-24
Status: ready_for_implementation

## Findings

- `governed_work_summary()` currently lists active runs but does not distinguish
  active substantive work, historical work, and bootstrap placeholders.
- The onboarding `first-assignment` can remain visible in instructions and must
  not be treated as the current substantive target after later governed runs
  exist.
- `pf.work.start` needs duplicate prevention by objective and active task/run
  state.

## Contract

- Active runs/tasks with statuses `open`, `in_progress`, `review`, or `blocked`
  are candidates.
- Completed/cancelled/failed runs and tasks are historical.
- `first-assignment` is a bootstrap placeholder and is excluded from current
  substantive work selection.
- Same active objective returns `continue_existing`.
- Same completed objective returns `operator_choice_required` rather than
  creating duplicate work.
