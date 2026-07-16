# Minimal Project Onboarding Example

Create a workplace and onboard a generic project:

```bash
python tools/processforge.py workplace-init --workplace ./pf-workplace --apply
mkdir my-project
python tools/processforge.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python tools/processforge.py agent-start-prompt --project-root ./my-project
python tools/processforge.py doctor-project --project-root ./my-project
```

Expected project result:

- `.pf/START_AGENT_HERE.md`
- `.pf/assignments/first-assignment.yaml`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/project-onboarding-report.md`
- `.pf/handoffs/project-ready-handoff.md`
