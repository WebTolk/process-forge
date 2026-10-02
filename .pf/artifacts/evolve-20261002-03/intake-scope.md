# evolve-20261002-03 Intake And Scope

Timestamp: 2026-10-02T14:16:00Z

Brief:
- Normalize resource indexing policy so project search, context snapshot, Work
  bindings and prepared resources agree about full-text availability.
- Explicit metadata/none policies must remain metadata-only.
- The current Work reproduces the reported mismatch: `pf.work.resolve` for
  `docs.python:root` returns `material_kind=metadata`,
  `navigation=metadata_only` and an empty manifest.

Accepted scope:
- `src/processforge_core/work_resource_material.py`
- `src/processforge_core/work_resources.py`
- `tools/smoke_resource_indexing_policy_acceptance.py`
- `tools/smoke_work_resource_binding.py`
- `docs/concepts/work-resources.md`
- `docs/ru/concepts/work-resources.md`
- `.pf/artifacts/evolve-20261002-03/**`
- `.pf/logs/evolve-20261002-03.md`
- `.pf/reviews/evolve-20261002-03.md`
- `.pf/handoffs/evolve-20261002-03.md`

Out of scope:
- `tools/processforge.py`, because active Work `agent-entry-e01-e02-scoped`
  owns that file.
- Commit, push, installation and Runtime restart.
- Changes to old capsules/processes/accepted artifacts.

Task record:
- Source: `.pf/artifacts/evolve/tasks-20261002/evolve-20261002-03.md`
- Type: defect.
- Priority: P1.

Risk:
- If the project snapshot path requires a product change in `tools/processforge.py`,
  this task must stop with a blocker instead of broadening scope.
