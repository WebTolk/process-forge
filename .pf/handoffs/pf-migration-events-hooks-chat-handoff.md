# Handoff: implementer -> next reviewer

Objective:
Complete the `.pf` migration and add process-owned events/hooks plus chat relay MVP.

Current status:
Ready for review. Core validators and smoke checks pass; context health is warn because optional capabilities are unresolved.

Input artifacts:
- `.pf/artifacts/pf-migration-events-hooks-chat-report.md`
- `.pf/reviews/pf-migration-events-hooks-chat-review.md`
- `schemas/event-envelope.schema.json`
- `schemas/hooks.schema.json`
- `schemas/chat-message.schema.json`
- `.pf/hooks.yaml`

Files changed:
- `.pf/**` flow migration and new flow outputs
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `tools/validate-process-forge-checksums.py`
- `schemas/**`
- `processes/**`
- `templates/**`
- `docs/**`
- `README.md`

Files not to touch:
- `задания/`
- `.pf/runtime/` except for local smoke or runtime verification

Known issues:
- Optional capability warnings remain in project context health.
- Network send and command hook execution are intentionally future-only.

Required checks:
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root . --check`
- `python tools\processforge.py events-validate --project-root .`
- `python tools\processforge.py doctor-context --project-root .`

Next recommended action:
Review the large `.pf` migration diff, then decide whether to commit this task together with the previous uncommitted layout/events task.
