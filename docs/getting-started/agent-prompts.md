# Agent Prompts

ProcessForge ships two copy-paste prompts for first-run work:

- `prompts/workplace-initialization-agent.md`
- `prompts/project-onboarding-agent.md`

After onboarding a project, generate the project-specific start prompt:

```bash
python bin/pf.py agent-start-prompt --project-root ./my-project
```

The command prints `.pf/START_AGENT_HERE.md` and creates it if it is missing.

The generated prompt uses:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

It must not assume that distribution-internal scripts exist in a normal linked project.

## Using ProcessForge With Agent Environments

Do not copy the whole ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders.

Install ProcessForge once as a tool, initialize a workplace, and add a short
instruction to your agent configuration telling it where ProcessForge is
installed and that project-specific instructions live in
`.pf/START_AGENT_HERE.md`.

## Prompt: Initialize Workplace

```text
You are setting up ProcessForge on this machine.

Use ProcessForge as a file-first workflow tool.
Initialize a new workplace, run doctor-workplace, and create a short setup report.

Use:

python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply

Do not modify any project yet.
Do not create .pf inside a project.
After setup, show me the workplace path, doctor result, and next command for project onboarding.
```

## Prompt: Onboard Project

```text
You are onboarding this project into ProcessForge.

First read the project structure. Then connect it to the existing ProcessForge workplace.

Use:

python <processforge-root>/bin/pf.py project-onboard --project-root . --workplace <workplace-path> --type <project-type> --apply

After onboarding:
1. Read .pf/START_AGENT_HERE.md.
2. Run doctor-project.
3. Summarize the project snapshot.
4. Suggest the first run/task plan.
```

## Prompt: Create Reusable Template

```text
Create a new reusable ProcessForge template.

Use the template authoring flow. Propose a template id, title, kind, inputs, outputs and example files. Then create the template and run template-doctor.

Use:

python <processforge-root>/bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>

Show the created files and explain how the template can be used in a project.
```

## Prompt: Create Knowledge Package

```text
Create a new ProcessForge knowledge package.

Ask me what knowledge source I want to add: URL, local folder, markdown files, notes or documentation mirror plan.
Create the package in the selected package root, add an initial resource index, and run knowledge-package-doctor.

Use:

python <processforge-root>/bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python <processforge-root>/bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>

Do not put private absolute paths into public files. Use path_ref or private resource registry when needed.
```

## Prompt: Create Platform Contract

```text
Create a new ProcessForge platform contract.

Ask me about project type hints, required capabilities, recommended knowledge packages, templates, tools, MCP servers and default processes.
Create the platform contract and run platform-contract-doctor.

Use:

python <processforge-root>/bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>

Do not copy packages or templates into the platform contract. Reference them by ids.
```

## Prompt: Create Custom Process

```text
Create a new ProcessForge process using the process authoring workflow.

Do not write YAML manually first. Start an authoring session, propose defaults, ask me about stages, roles, artifacts, gates, required knowledge, tools and task/iteration loop. Keep answers.yaml and draft.process.yaml updated.

Use:

python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>

Check that the new process can be used with run-create.
```

## Prompt: Create Task Batch Run

```text
Create a ProcessForge run for this work session.

Use the task-batch workflow. Create a run, split the work into tasks, and for each task record work/debug/fix/review iterations. At the end, create a run summary and handoff.

Use:

python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```
