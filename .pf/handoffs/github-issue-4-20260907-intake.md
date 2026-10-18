# Handoff: run-coordinator -> task-worker

Objective:

Implement GitHub Issue #4: a safe, plan-first migration of existing
ProcessForge Workplaces for the 1.0.2 to 1.1.0 transition.

Current status:

The Issue #4 run passed intake. The current project snapshot is fresh. The
current Core updater owns only Core archive replacement; Workplace defaults are
currently materialized by `workplace-init`, which must not be used as the
update mechanism.

Input artifacts:

- `.pf/artifacts/github-issue-4-20260907/run-record.md`
- GitHub Issue #4
- `docs/getting-started/update-system.md`
- `src/processforge_core/core_update.py`

Files changed:

- None in product code at intake.

Files not to touch:

- Uncommitted changes belonging to the existing Search Index / Issue #5
  workstream, unless a conflict is first identified and resolved explicitly.

Known issues:

- Serena has no available language server for this repository, so analysis must
  use targeted text inspection and recorded smoke tests.

Required checks:

- plan, confirmed apply, preservation of custom Workplace values, rollback or
  recoverable failure information, and post-update Workplace checks in an
  isolated fixture.

Next recommended action:

Design the narrow migration manifest and transaction boundary before changing
the Core updater.
