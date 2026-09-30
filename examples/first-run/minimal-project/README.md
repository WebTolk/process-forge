# Minimal Project Onboarding Example

Create a workplace and onboard a generic project:

```bash
python bin/pf.py workplace-init --workplace ./pf-workplace --apply
mkdir my-project
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ./my-project
python bin/pf.py doctor-project --project-root ./my-project
```

`agent-start-prompt` is a no-write preview. Ordinary work starts from root
`AGENTS.md`, verifies `pf.context`, and uses `pf.work.start`, `pf.work.state`
and `pf.work.transition` with returned identities until `run_completed`.
Legacy projects without root entry explicitly read `.pf/AGENTS.md`.

START is no longer needed: new projects do not generate it, and existing files
remain untouched. Status, doctor and deterministic repair do not require it.

Expected project result:

- root `AGENTS.md`, hidden `.pf/AGENTS.md`, and `.pf/agent-entry.json`
- `.pf/assignments/first-assignment.yaml` (compatibility placeholder, not required Work)
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/project-onboarding-report.md`
- `.pf/handoffs/project-ready-handoff.md`
