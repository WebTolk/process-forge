# Handoff: implementation -> release validation

Objective:
Enforce specialization as a resource profile boundary and validate capability
resolution against process-owned requirements.

Current status:
Implementation, schemas, templates, docs, targeted smokes, public release-test,
release pack, and extracted archive test are complete.

Input artifacts:
- `.pf/artifacts/specialization-resource-profile-boundary-report.md`
- `задания/processforge_specialization_resource_profile_boundary_master_prompt.md`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/specialization_smoke_helpers.py`
- `tools/smoke_specialization_*.py`
- `tools/smoke_process_*specialization*.py`
- `schemas/`
- `templates/specialization.yaml`
- `docs/`
- `.pf/artifacts/`
- `.pf/reviews/`
- `.pf/logs/`

Files not to touch:
- `.pf/runtime/`
- unrelated historical assignments and artifacts

Known issues:
- No unresolved validation blocker remains for this slice.
- Deep merge for project override modes beyond MVP remains future work.

Required checks:
- New boundary smokes
- Full specialization/project override smoke set
- Schema validation
- Public cleanliness
- Checksum validation
- Public release-test
- Release pack and archive test
- `git diff --check`

Next recommended action:
Review the final diff, then commit/push if this slice is accepted.
