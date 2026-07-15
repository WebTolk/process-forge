# Handoff: codex -> maintainer

Objective:
Implement ProcessForge path constants and path aliases from `processforge_path_constants_assignment.md`.

Current status:
Implemented locally on top of the existing uncommitted Resource Management MVP changes.

Input artifacts:
- `задания/processforge_path_constants_assignment.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/processforge.py`
- `tools/smoke_resource_management.py`
- `schemas/path-constants.schema.json`
- `schemas/path-ref.schema.json`
- `schemas/workplace.schema.json`
- `templates/workplace.yaml`
- `templates/workplace-init.answers.yaml`
- `templates/registries/*.yaml`
- `docs/concepts/path-constants.md`
- `docs/concepts/path-resolution.md`
- related resource privacy/workplace authoring docs

Files not to touch:
- `.pf/runtime/` remains private runtime state.
- Do not revert Resource Management MVP changes that were already present before this task.

Known issues:
- No VFS was added.
- Healthcheck commands are not executed.
- Optional external roots may warn when missing but do not block doctor-workplace.

Required checks:
- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py doctor-project --project-root .`
- `python tools/smoke_resource_management.py`
- `git diff --check`

Next recommended action:
Run one real workplace registration flow with an existing local knowledge root and review the generated `path_ref` before committing.
