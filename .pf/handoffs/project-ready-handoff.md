# Handoff: project-onboarding -> first-assignment

Objective:
Connect `process-forge` to ProcessForge and prepare the first assignment.

Current status:
Project onboarding files were generated.

Input artifacts:
- .pf/process-forge.yaml
- .pf/process-forge.local.yaml
- .pf/contexts/project-context.snapshot.yaml
- .pf/START_AGENT_HERE.md
- .pf/assignments/first-assignment.yaml

Files changed:
- .pf/
- .gitignore

Files not to touch:
- Workplace registry files unless the user explicitly requests workplace changes.
- Global packages unless a separate workplace process approves it.

Known issues:
- Detection is observed, not domain-approved.

Required checks:
- `python .pf/runtime/bin/pf.py doctor-project --project-root .`
- `python .pf/runtime/bin/pf.py project-context-check --project-root .`

Next recommended action:
Start `.pf/assignments/first-assignment.yaml`.
