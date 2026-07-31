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

## What ProcessForge Is

A workplace is a physical or virtual machine where humans and AI agents work:
a desktop, laptop, server, or runner host. ProcessForge is installed once as a
tool for that workplace.

## Core Entities

The workplace stores global machine-level resources: process definitions,
knowledge packages, reusable templates, tool registrations, MCP registrations,
platform contracts, roots, registries, cache, runtime events, and logs.

Each project keeps its own `.pf/` layer. The project layer stores project
context, selected global resources, assignments, runs, tasks, iterations,
artifacts, reviews, handoffs, hooks, and private runtime files.

Project context has a lock-file model. `.pf/process-forge.yaml` declares
`context_requirements`; `project-context-refresh` resolves them into
`.pf/contexts/project-context.snapshot.yaml` plus immutable generations under
`.pf/contexts/project-context.snapshots/`. `project-context-check` reports
`fresh`, `fresh_with_updates`, `stale`, or `broken`; assignment capsules pin a
snapshot id/checksum and are not rewritten by later refreshes.

## Work Modes

### Garage Mode (1-1-1-1)

The atomic execution unit is `1-1-1-1`: one human operator, one primary agent
session, one project, and one active process/run. In the default single-agent
flow the primary agent performs the work, runs CLI checks, writes artifacts,
and checks out; Worker and Inspector are phases/checks of the same session, not
separate participants. Agent Ledger is CLI/files, not a separate agent. Director
and Supervisor/Execution Inspector are only needed for multi-agent,
process-transition, or external runtime-worker scenarios. See
[docs/concepts/agent-session-model.md](docs/concepts/agent-session-model.md).

### Forge / Factory Mode

A workplace can be Director-capable while individual projects remain simple.
Project coordination mode resolves as `simple`, `organized`, or `inherit` from
the workplace default. Use `organized` only for projects that should use the
workplace Director Office; simple projects keep the normal 1-1-1-1 flow.

Process definitions describe process mechanics. They are configurable YAML
constructors with any number of stages, roles, artifacts, gates, capabilities,
allowed tools, and hooks. They do not need to name an implementation platform.

Platform contracts are composition entities for a concrete project context. A
platform may be single or composed as parent plus child. The contract connects
the required and recommended stack of knowledge packages, templates, tools, MCP
providers, capabilities, processes, coding standards, project type hints, and
policy data. ProcessForge core resolves these contracts from manifests; it does
not hardcode any real product, CMS, framework, marketplace, or business domain.

## How The Layers Relate

Use ProcessForge from the outside in:

1. ProcessForge tool root: the installed CLI, built-in processes, schemas,
   checks, docs, and prompt templates.
2. Workplace: machine-level state and reusable resources shared by projects.
3. Workplace resources: knowledge roots/packages, reusable templates, tools,
   MCP providers, package roots, process definitions, and platform contracts.
4. Project `.pf/`: project context, selected resources, assignments, runs,
   tasks, iterations, artifacts, reviews, handoffs, and hooks.

The project layer depends on the workplace layer. It should not contain copied
ProcessForge source code, heavy documentation mirrors, shared toolchains, or
global resource payloads.

## Initialization Order

Use this order for a new workplace:

1. Install the ProcessForge distribution.
2. Verify the ProcessForge distribution.
3. Run guided workplace setup by default for a human-led first setup.
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

Use `workplace-setup` as the default setup path when an AI agent configures a
new machine for a human. The agent should ask questions in blocks, write
`answers.yaml`, produce `proposal.md`, ask for approval, apply the workplace,
run `doctor-workplace`, and only then move to resource authoring or project
onboarding.

The launch directory is not a ProcessForge role. During machine setup the agent
must use explicit paths for the installed ProcessForge distribution, the
workplace root, optional global agent/instruction roots, and real project roots.
Folders named `.codex`, `.claude`, `.agents`, or any custom agent root can be
knowledge or instruction sources; they do not become projects unless the
operator explicitly targets them with `project-onboard`.

Use `first-run`, `workplace-init`, and direct create/register commands as the
fully automatic path only when the operator explicitly requests automation and
provides the required paths and answers.

## Quick Start

1. Read this README to understand the model and boundaries.
2. Open [Quickstart prompts](QUICKSTART.md) and copy the setup prompt into your
   AI agent.
3. Let the agent run guided workplace setup.
4. Create or register workplace resources: knowledge, templates, tools, MCP
   providers, package roots, and platform contracts.
5. Onboard the first project only after the workplace and its shared resources
   are ready.
6. Inside the project, start every ProcessForge-backed session from
   `.pf/START_AGENT_HERE.md`.

## Supported Wizards And Creation Commands

ProcessForge currently supports file-first creation flows for:

- workplace initialization: `workplace-init` / `init-workplace`
- guided workplace setup: `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply`, and `workplace-setup status`
- project onboarding: `project-onboard` / `init-project`
- coordination modes: `workplace-mode status`, `workplace-mode set`,
  `project-mode status`, `project-mode set`, `director-inbox-submit`,
  `director-case-refresh`, and `error-route`
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
- agent ledger and handoffs: `agent-register`, `agent-checkin`,
  `agent-availability`, `agent-lease-grant`, `process-route-list`,
  `handoff-create`, `handoff-status`, and `agent-director-tick`
- primary agent sessions: `session-start`, `session-heartbeat`,
  `session-status`, and `session-end`
- orchestrator shell agents: `orchestrator-shell-plan-create`,
  `orchestrator-shell-plan-validate`, and `orchestrator-shell-plan-apply`
  with optional `--model <model>` to pass one selected model to every shell
  worker in the applied plan
- runtime drivers and worker execution: `runtime-driver list`,
  `runtime-driver validate`, `worker-run prepare`, `worker-run start`,
  `worker-run status`, `worker-run collect`, `supervisor tick`,
  `supervisor run`, and the semantic aliases `execution-inspector-tick` and
  `execution-inspector-run`

`supervisor` is the historical technical command name for the Process
Execution Inspector. It checks assigned worker runtime state; it is not the
Agent Director. The responsibility boundary is documented in
[docs/concepts/director-ledger-inspector-boundary.md](docs/concepts/director-ledger-inspector-boundary.md).

The `--interactive` flag is accepted by first-run initialization commands for
UX compatibility, but the current implementation is file-first and does not
require terminal prompting.

## Operator Prompts

### Prepare A Workplace By Guided Setup

```text
Initialize ProcessForge in step-by-step mode. It is located at
<processforge-root>.
```

### Fully Automatic Setup

```text
Initialize ProcessForge in fully automatic mode. It is located at
<processforge-root>. First inspect the current AGENTS.md and setup skills.
```

In automatic mode, the agent first reports what it found on the device, maps
existing instructions, skills, docs, tools, platforms, and project roots to
ProcessForge entities, asks for approval of the setup scenario, and only then
applies changes.

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

For humans:

- [Quickstart prompts](QUICKSTART.md)
- [Installation and requirements](docs/getting-started/installation.md)
- [Guided workplace setup](docs/getting-started/guided-workplace-setup.md)
- [Initialization order](docs/getting-started/initialization-order.md)
- [Workplace vs project](docs/concepts/workplace-vs-project.md)
- [Resource authoring](docs/getting-started/resource-authoring.md)
- [Project onboarding](docs/getting-started/project-onboarding.md)
- [Built-in process stages](docs/processes/built-in-processes.md)

For AI agents:

- [Agent command runbook](docs/getting-started/agent-prompts.md)
- [Workplace initialization agent prompt](prompts/workplace-initialization-agent.md)
- [Guided workplace setup agent prompt](prompts/guided-workplace-setup-agent.md)
- [Project onboarding agent prompt](prompts/project-onboarding-agent.md)
- [Release checklist](docs/release-checklist.md)

Detailed index:

- [Documentation index](docs/index.md)
- [Installation and requirements](docs/getting-started/installation.md)
- [Initialization order](docs/getting-started/initialization-order.md)
- [Agent command runbook](docs/getting-started/agent-prompts.md)
- [Built-in process stages](docs/processes/built-in-processes.md)
- [Context resolution](docs/concepts/context-resolution.md)
- [Cascade merge](docs/concepts/cascade-merge.md)
- [Workplace vs project](docs/concepts/workplace-vs-project.md)
- [Runtime model](docs/concepts/runtime-model.md)
- [Runtime drivers](docs/concepts/runtime-drivers.md)
- [Agent session model](docs/concepts/agent-session-model.md)
- [Project coordination modes](docs/concepts/project-coordination-modes.md)
- [Process supervisor](docs/concepts/process-supervisor.md)
- [Agent ledger](docs/concepts/agent-ledger.md)
- [Process transitions](docs/concepts/process-transitions.md)
- [Handoff contracts](docs/concepts/handoff-contracts.md)
- [Agent Director](docs/concepts/agent-director.md)
- [Shell agent subagent policy](docs/concepts/shell-agent-subagent-policy.md)
- [Platform contracts](docs/concepts/platform-contracts.md)
- [Platform inheritance](docs/concepts/platform-inheritance.md)
- [Knowledge resource navigation](docs/concepts/knowledge-resource-navigation.md)
- [Update sites](docs/concepts/update-sites.md)
- [Update lifecycle](docs/concepts/update-lifecycle.md)
- [Update system quick start](docs/getting-started/update-system.md)
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
- Runtime drivers are opt-in. The default `manual` driver writes launch state
  and does not start a process.

Development and release-check requirements:

- Python 3.11+.
- Python package dependencies from `requirements.txt`.
- Git for source installation and release checks such as `git diff --check`.
- Ability to run subprocesses and create temporary directories.
- ZIP support from the Python standard library.
- Update tests are deterministic and use local file-provider fixtures; public
  release checks do not require real network access.

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
