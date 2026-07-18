# ProcessForge

**Russian documentation:** [README.ru.md](README.ru.md)

ProcessForge is a file-first process framework for AI-assisted project work.
It keeps process definitions, runs, tasks, iterations, artifacts, reviews,
handoffs, knowledge packages, templates, and platform contracts in versionable
files.

This README is written for people. It intentionally gives you copy-paste prompts
instead of command lists. Give a prompt to your AI agent and let the agent use
the full command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md).

![ProcessForge architecture](docs/assets/processforge-architecture.svg)

## What To Ask The Agent

### Set up ProcessForge

```text
Set up ProcessForge for my local projects.

Use ProcessForge as a file-first workflow tool. Read the repository
documentation first, then use the agent command runbook in
docs/getting-started/agent-prompts.md.

Create or verify a workplace, run the relevant doctor checks, and report:
- where the workplace is;
- whether it is ready;
- what project onboarding prompt I should use next.

Do not copy the whole ProcessForge repository into .codex, .claude, .agents, or
other agent configuration folders.
```

### Connect A Project

```text
Connect this project to my existing ProcessForge workplace.

Read the project structure before changing files. Use the ProcessForge agent
command runbook, create the project-local .pf layer, read .pf/START_AGENT_HERE.md,
run doctor checks, and summarize the first useful run/task plan.

Keep ProcessForge installed as a tool. Do not copy the full ProcessForge
repository into this project or into agent configuration folders.
```

### Start A Work Session

```text
Start a ProcessForge run for this work.

Read .pf/START_AGENT_HERE.md first. Create a run, split the work into explicit
tasks, record work/debug/fix/review iterations, keep artifacts and handoffs in
the project-local .pf folder, and finish with a run summary and doctor check.
```

### Create A Process

```text
Create a new ProcessForge process for this project.

Use the process authoring workflow. Ask me for missing decisions, keep the
authoring answers and draft process current, review semantic parity, apply the
process only after review, and prove that the process can be used for a run.
```

### Create Shared Resources

```text
Create the shared ProcessForge resources needed for this project.

Ask whether I need a reusable template, a knowledge package, a platform contract,
or all of them. Keep machine-level resources in the workplace, reference them by
stable ids, avoid private absolute paths in public files, and run the matching
doctor checks.
```

### Validate A Release

```text
Validate the ProcessForge repository for release.

Use the repository's agent command runbook and release checklist. Run the public
cleanliness, checksum, release-test, release-pack, release-archive-test, and
whitespace checks. Use a neutral archive name in documentation and reports so
the docs do not embed a release number.
```

## Documentation Map

- [Quickstart prompts](QUICKSTART.md)
- [Documentation index](docs/index.md)
- [Agent command runbook](docs/getting-started/agent-prompts.md)
- [Workplace vs project](docs/concepts/workplace-vs-project.md)
- [Runtime model](docs/concepts/runtime-model.md)
- [Runs, tasks, and iterations](docs/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/authoring/authoring-parity.md)
- [Known limitations](docs/known-limitations.md)

## License

See [LICENSE](LICENSE).
