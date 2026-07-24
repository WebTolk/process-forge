# Project Onboarding

Project onboarding is run once per project after a workplace exists.

It creates the project-local `.pf/` flow root:

- `.pf/AGENTS.md`
- `.pf/START_AGENT_HERE.md`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml`
- `.pf/hooks.yaml`
- `.pf/assignments/first-assignment.yaml`
- `.pf/runtime/bin/pf.py`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/project-onboarding-report.md`
- `.pf/reviews/project-onboarding-review.md`
- `.pf/handoffs/project-ready-handoff.md`

Command:

For dry-run, create or select `./my-project` first. Apply mode can create a
missing greenfield project root.

```bash
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python bin/pf.py doctor-project --project-root ./my-project
```

This process does not recreate the workplace and does not copy global packages into the project.

The project-local launcher reads private `.pf/process-forge.local.yaml` or `PROCESSFORGE_HOME` to find the ProcessForge distribution. Public files such as `.pf/START_AGENT_HERE.md` do not reveal the resolved distribution path.

Inside the linked project:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```
