# Handoff: implementation -> review

Objective:
Introduce specializations as workplace/project resources and project overrides
as project-local resolved context inputs.

Current status:
Implementation, docs, schemas, templates, targeted smokes, public release-test,
release pack, and extracted archive test are complete.

Input artifacts:
- `.pf/artifacts/specialization-and-project-overrides-report.md`
- `задания/processforge_specialization_project_overrides_master_prompt.md`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `schemas/`
- `templates/`
- `docs/`
- `tools/smoke_specialization_*.py`
- `tools/smoke_project_overrides_*.py`
- `.pf/artifacts/`
- `.pf/reviews/`
- `.pf/logs/`

Files not to touch:
- `.pf/runtime/`
- unrelated existing assignments and historical artifacts

Known issues:
- Deep structured merge for `overlay`/`replace`/`fork` remains future work.
- No unresolved validation blocker remains for this slice.

Required checks:
- New specialization/project override smokes
- Schema validation
- Public cleanliness
- Checksum validation
- Public release-test
- Release pack and archive test
- `git diff --check`

Next recommended action:
Review the final diff, then commit/push if this slice is accepted.
