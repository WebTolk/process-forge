# Handoff: snapshot-events -> next maintainer

Objective:
Continue ProcessForge stabilization after `.pf` layout, snapshot, telemetry,
events, hooks, and outbox support.

Current status:
Core commands now emit private events, session telemetry is still written, hooks
support dry-run/outbox behavior, and legacy context commands are deprecated.

Input artifacts:
- `artifacts/pf-layout-snapshot-events-report.md`
- `reviews/pf-layout-snapshot-events-review.md`
- `artifacts/pf-layout-migration-proposal.md`
- `contexts/project-context.snapshot.yaml`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `README.md`
- `docs/getting-started.md`
- `docs/concepts/*`
- `schemas/*`
- `templates/*`
- `.gitignore`
- `.processforge-releaseignore`

Files not to touch:
- Do not move legacy root flow directories into `.pf/` without a reviewed
  migration inventory.
- Do not include `задания/` in product commits.
- Do not restore or remove the pre-existing deleted master prompt files without
  explicit direction.

Known issues:
- Optional capability providers are unresolved, so snapshot health is `warn`.
- Hooks do not execute local commands or send network requests in the MVP.

Required checks:
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root .`
- `python tools\processforge.py doctor-context --project-root .`

Next recommended action:
Review whether dogfooding migration should start, then decide which root flow
artifacts are active evidence and which can move into `.pf/`.
