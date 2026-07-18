# ProcessForge Quickstart

Canonical runtime is Python:

- root launcher: `python bin/pf.py`
- optional short command: `pf`

```bash
git clone <repo>
cd process-forge
python bin/pf.py version
```

## Step 1. Initialize Workplace

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

## Step 2. Onboard Project

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py doctor-project --project-root ../my-project
```

## Step 3. Give This Prompt To Your AI Agent

```bash
python bin/pf.py agent-start-prompt --project-root ../my-project
```

## Step 4. Start First Assignment

Open `.pf/assignments/first-assignment.yaml` in the onboarded project and follow `.pf/START_AGENT_HERE.md`.

## Step 5. Run A Task Batch

```bash
python bin/pf.py run-create --project-root ../my-project --id example-run --title "Example run" --process task-batch-execution --apply
python bin/pf.py task-create --project-root ../my-project --run example-run --id task-001-example --title "Example task" --process software-feature-development --apply
python bin/pf.py iteration-add --project-root ../my-project --task task-001-example --kind work --summary "Initial work done." --apply
python bin/pf.py task-complete --project-root ../my-project --task task-001-example --summary "Task completed." --apply
python bin/pf.py run-summary --project-root ../my-project --run example-run --apply
python bin/pf.py run-doctor --project-root ../my-project --run example-run
```

Inside a normal linked project, do not run `python tools/processforge.py` from the project root. The project does not contain ProcessForge core. Use:

```bash
pf doctor-project --project-root .
```

Fallback:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

## Release Validation

From the ProcessForge distribution root:

```bash
python bin/pf.py release-test --root .
```
