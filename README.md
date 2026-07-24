# ProcessForge

**Russian documentation:** [README.ru.md](README.ru.md)

ProcessForge is a file-first process framework for AI-assisted project work.
It keeps process definitions, runs, tasks, iterations, artifacts, reviews,
handoffs, knowledge packages, templates, tools, MCP registrations, and platform
contracts in versionable files.

This README is written for people. It starts from the workplace model and gives
copy-paste prompts for an operator. AI agents should use the command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md),
which is limited to commands and mechanics implemented in the current codebase.

![ProcessForge workplace layout](docs/assets/processforge-architecture.svg)

## Mental Model

A workplace is a physical or virtual machine where humans and AI agents work:
a desktop, laptop, server, or runner host. ProcessForge is installed once as a
tool for that workplace.

The workplace stores global machine-level resources: process definitions,
knowledge packages, reusable templates, tool registrations, MCP registrations,
platform contracts, roots, registries, cache, runtime events, and logs.

Each project keeps its own `.pf/` layer. The project layer stores project
context, selected global resources, assignments, runs, tasks, iterations,
artifacts, reviews, handoffs, hooks, and private runtime files.

Process definitions describe process mechanics. They are configurable YAML
constructors with any number of stages, roles, artifacts, gates, capabilities,
allowed tools, and hooks. They do not need to name an implementation platform.

Platform contracts are composition entities for a concrete project context. A
platform may be single or composed as parent plus child. The contract connects
the required and recommended stack of knowledge packages, templates, tools, MCP
providers, capabilities, processes, coding standards, project type hints, and
policy data. ProcessForge core resolves these contracts from manifests; it does
not hardcode any real product, CMS, framework, marketplace, or business domain.

## Initialization Order

Use this order for a new workplace:

1. Install the ProcessForge distribution.
2. Verify the ProcessForge distribution.
3. Initialize the workplace.
4. Configure path constants and roots.
5. Configure knowledge roots, especially local documentation roots.
6. Register tools and MCP servers.
7. Create or import knowledge packages.
8. Create reusable templates.
9. Create platform contracts from the resources above.
10. Onboard projects into the workplace.
11. Create run/task workflows for real work.
12. Create custom processes when the built-in mechanics are not enough.

Do not start with a platform contract if its required packages, templates,
tools, MCP servers, processes, coding standards, or capabilities do not exist
yet. Create or register the dependencies first, then compose the platform.

## Supported Wizards And Creation Commands

ProcessForge currently supports file-first creation flows for:

- workplace initialization: `workplace-init` / `init-workplace`
- guided workplace setup: `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply`, and `workplace-setup status`
- project onboarding: `project-onboard` / `init-project`
- first run bootstrap: `first-run`
- process authoring: `process-authoring-start`, `process-authoring-review`,
  `process-authoring-apply`, and one-command `process-create`
- knowledge packages: `knowledge-package-create`, `knowledge-add-url`,
  `knowledge-add-resource`, `knowledge-index-refresh`, `knowledge-package-doctor`
- reusable templates: `template-create`, `template-add`, `template-doctor`
- platform contracts: `platform-create`, `platform-contract-install`,
  `platform-contract-doctor`
- tools and MCP providers: `tool-register`, `mcp-register`
- runs, tasks, and iterations: `run-create`, `task-create`, `iteration-add`,
  completion, summary, and doctor commands
- multi-agent orchestration: `orchestrator-plan create`,
  `orchestrator-plan validate`, `orchestrator-plan apply`,
  `orchestrator-plan status`, and `worker-launch-prompt create`

The `--interactive` flag is accepted by first-run initialization commands for
UX compatibility, but the current implementation is file-first and does not
require terminal prompting.

## Operator Prompts

### Prepare A Workplace

```text
Prepare ProcessForge on this machine.

Find the installed ProcessForge tool root or unpacked distribution, read the
human README, then use docs/getting-started/agent-prompts.md for exact
commands.

Create or verify a workplace, run the relevant doctor checks, and report:
- ProcessForge tool root;
- workplace path;
- whether the workplace is ready;
- which project onboarding prompt I should use next.

Keep ProcessForge as an installed tool. Do not copy the full repository into
agent configuration folders or into project repositories.
```

### Connect A Project

```text
Connect this project to my existing ProcessForge workplace.

Inspect the project first, choose a conservative project type, create the
project-local .pf layer, read .pf/START_AGENT_HERE.md, run doctor checks, and
summarize what ProcessForge now knows about the project.

Keep global resources in the workplace. Do not copy heavy documentation,
source mirrors, toolchains, or the ProcessForge repository into this project.
```

### Compose A Platform Stack

```text
Create the ProcessForge resources needed for this project platform.

Work dependency-first: register tools and MCP servers, create or import
knowledge packages, create reusable templates, then create a platform contract
that composes those resources. If the platform has a parent and child, model
that inheritance in the platform manifests and prove it with the platform
doctor and project snapshot.
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
process only after review, and prove that the process can be listed, described,
and used for a run.
```

## Documentation Map

- [Quickstart prompts](QUICKSTART.md)
- [Documentation index](docs/index.md)
- [Installation and requirements](docs/getting-started/installation.md)
- [Initialization order](docs/getting-started/initialization-order.md)
- [Agent command runbook](docs/getting-started/agent-prompts.md)
- [Workplace vs project](docs/concepts/workplace-vs-project.md)
- [Runtime model](docs/concepts/runtime-model.md)
- [Platform contracts](docs/concepts/platform-contracts.md)
- [Platform inheritance](docs/concepts/platform-inheritance.md)
- [Knowledge resource navigation](docs/concepts/knowledge-resource-navigation.md)
- [Runs, tasks, and iterations](docs/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/authoring/authoring-parity.md)
- [Known limitations](docs/known-limitations.md)

## Requirements

Runtime requirements:

- Python 3.11+ is recommended.
- Python 3.10+ is allowed only when the current test suite confirms compatibility.
- Python package dependencies from `requirements.txt`, currently `PyYAML`.
- Use a UTF-8 capable filesystem.
- The user or agent needs read/write access to the ProcessForge distribution,
  workplace, and project folders.
- Runtime usage does not require PowerShell.
- ProcessForge does not require a daemon or background process in file-only mode.

Development and release-check requirements:

- Python 3.11+.
- Python package dependencies from `requirements.txt`.
- Git for source installation and release checks such as `git diff --check`.
- Ability to run subprocesses and create temporary directories.
- ZIP support from the Python standard library.

Optional integrations include MCP servers, external tools, browser checks, and
version-control workflows. Runtime usage from a release archive does not require
Git unless the user wants version-control integration.

## Using ProcessForge With Agent Environments

Do not copy the whole ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders.

Install ProcessForge once as a tool, initialize a workplace, and add a short
instruction to the agent configuration telling it where ProcessForge is
installed and that project-specific instructions live in `.pf/START_AGENT_HERE.md`.

## License

See [LICENSE](LICENSE).
