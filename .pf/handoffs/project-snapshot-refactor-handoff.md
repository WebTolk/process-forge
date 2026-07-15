# Handoff: snapshot-refactor -> next maintainer

Objective:
Review and, if approved, plan the repository migration from legacy root layout
to `.pf/`.

Current status:
Stage 1 support is implemented. New projects use `.pf/`; this repository still
uses legacy root layout with compatibility support.

Input artifacts:
- `artifacts/project-snapshot-refactor-report.md`
- `artifacts/pf-layout-migration-proposal.md`
- `reviews/project-snapshot-refactor-review.md`
- `contexts/project-context.snapshot.yaml`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `docs/concepts/*`
- `schemas/*`
- `templates/*`
- `.gitignore`
- `.processforge-releaseignore`

Files not to touch:
- Do not move legacy root flow directories into `.pf/` without explicit review.
- Do not restore or remove pre-existing deleted master prompt files without user
  direction.

Known issues:
- Current snapshot health is `warn` because optional providers are unresolved.
- The current master prompt assignment has no YAML front matter.

Required checks:
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\processforge.py doctor-context --project-root .`

Next recommended action:
Review the migration proposal and decide whether Stage 2 inventory should begin.
