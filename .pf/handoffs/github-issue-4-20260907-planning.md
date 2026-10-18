# Handoff: run-coordinator -> task-worker

Objective:

Execute the single assignment in the Issue #4 run: add a compatible
1.0.2-to-1.1.0 Workplace migration to the updater.

Current status:

The run has one blocking, assignment-backed task. Its planning boundary is the
existing Core updater and Workplace templates; the expected output is a narrow
migration transaction plus isolated acceptance evidence.

Input artifacts:

- `.pf/artifacts/github-issue-4-20260907/run-record.md`
- `.pf/runs/garage-resolve-github-issue-4-add-compatible-workplace-migration-to-the/task-index.md`

Files changed:

- No product code during planning.

Files not to touch:

- Pre-existing dirty files from the Search Index / Issue #5 workstream.

Known issues:

- The core updater has no Workplace-aware manifest or rollback action yet.

Required checks:

- New missing PF-owned default is installed and registered.
- Existing custom Workplace values survive plan and apply.
- Apply is explicit, plan is read-only, and failed migration has recoverable
  state or a rollback path.
- Post-update validation runs in the fixture.

Next recommended action:

Add the migration design and its fixture smoke, then implement the minimal
transaction in the Core updater.
