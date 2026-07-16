# ProcessForge Quickstart

Canonical runtime is Python:

- root launcher: `python bin/pf.py`
- optional short command: `pf`

## Step 1. Initialize Workplace

```bash
python bin/pf.py workplace-init --workplace ./pf-workplace --apply
python bin/pf.py doctor-workplace --root ./pf-workplace
```

## Step 2. Onboard Project

```bash
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python bin/pf.py doctor-project --project-root ./my-project
```

## Step 3. Give This Prompt To Your AI Agent

```bash
python bin/pf.py agent-start-prompt --project-root ./my-project
```

## Step 4. Start First Assignment

Open `.pf/assignments/first-assignment.yaml` in the onboarded project and follow `.pf/START_AGENT_HERE.md`.

Inside a normal linked project, do not run `python tools/processforge.py` from the project root. The project does not contain ProcessForge core. Use:

```bash
pf doctor-project --project-root .
```

Fallback:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```
