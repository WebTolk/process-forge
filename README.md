# ProcessForge

<div align="center">

**A platform-neutral, AI-provider-neutral framework for creating and running AI-assisted processes.**

[![Version](https://img.shields.io/badge/version-1.0.1-2F6FED?style=for-the-badge)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](requirements.txt)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=for-the-badge)](LICENSE)
[![File First](https://img.shields.io/badge/runtime-file--first-2E7D32?style=for-the-badge)](docs/concepts/runtime-model.md)
[![Platform Neutral](https://img.shields.io/badge/core-platform--neutral-6A1B9A?style=for-the-badge)](docs/concepts/domain-neutral-core.md)
[![Provider Neutral](https://img.shields.io/badge/AI-provider--neutral-455A64?style=for-the-badge)](docs/concepts/runtime-drivers.md)

**Russian documentation:** [README.ru.md](README.ru.md)

</div>

ProcessForge is a file-first framework for creating, versioning, and executing
AI-assisted processes. It is independent of concrete implementation platforms
and AI providers: domains, toolchains, knowledge packages, templates, runtime
drivers, and platform contracts are attached through versionable files instead
of being hardcoded into the core.

This README is written for people. AI agents should use the command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md),
which is limited to commands and mechanics implemented in the current codebase.

![ProcessForge workplace layout](docs/assets/processforge-architecture.svg)

## Why Use It

ProcessForge turns repeatable AI work into explicit process assets:

- formal process definitions with stages, roles, artifacts, gates,
  capabilities, tools, hooks, and handoff rules;
- project-local `.pf/` state for assignments, runs, tasks, iterations,
  artifacts, reviews, logs, handoffs, snapshots, and private runtime data;
- formalized knowledge through knowledge packages, resource indexes, source
  metadata, load policies, and update policies;
- reusable templates, tool registrations, MCP registrations, runtime drivers,
  and platform contracts that compose project context without core hardcode;
- **cascade-based context resolution from workplace and project resources into
  locked snapshots, assignment capsules, resolved rules, and parameters;**
- versioned files, checksums, release manifests, archive validation, and update
  checks from declared sources.

The result is a workflow system that a human can inspect in Git and an AI agent
can execute without relying on a hidden SaaS backend, one specific model, or one
specific product platform.

## Two Work Modes

### Garage Mode (1-1-1-1)

Use this for normal work: one human operator, one primary agent session, one
project, and one active process/run. The primary agent performs the work, runs
checks, writes artifacts, and finishes with a summary or handoff.

### Forge / Factory Mode

Use this when work must be split into independent branches. An orchestrator can
create bounded assignments and capsules, launch or coordinate worker sessions,
collect their outputs, and integrate the result through handoffs and reviews.

## Quick Start

### Place ProcessForge

Download the release archive, [dist/processforge.zip](dist/processforge.zip),
and unpack it into a stable folder that your AI agents can access, for example
a shared agent tools folder. Use that folder as `<processforge-root>` in the
prompts below.

If you work from a source checkout, use the repository root as
`<processforge-root>`.

### Start With An Agent Prompt

For guided setup, copy this into your AI agent:

```text
Initialize ProcessForge in step-by-step mode. It is located at
<processforge-root>.
```

For automatic setup, use this only when you already know the target paths and
want the agent to inspect existing instructions and resources first:

```text
Initialize ProcessForge in fully automatic mode. It is located at
<processforge-root>. First inspect the current AGENTS.md and setup skills.
```

After the workplace is ready, connect a project:

```text
Connect this project to my existing ProcessForge workplace.

Inspect the project first, choose a conservative project type, create the
project-local .pf layer, read .pf/START_AGENT_HERE.md, run doctor checks, and
summarize what ProcessForge now knows about the project.

Keep global resources in the workplace. Do not copy heavy documentation,
source mirrors, toolchains, or the ProcessForge repository into this project.
```

Inside an onboarded project, start each ProcessForge-backed session from
`.pf/START_AGENT_HERE.md`.

More starter prompts are in [QUICKSTART.md](QUICKSTART.md).

## Operating Model

### What ProcessForge Is

A workplace is a physical or virtual machine where humans and AI agents work:
a desktop, laptop, server, or runner host. ProcessForge is installed once as a
tool for that workplace.

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

### How The Layers Relate

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

### Initialization Order

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

## Work Modes In Detail

### Garage Mode (1-1-1-1)

The atomic execution unit is `1-1-1-1`: one human operator, one primary agent
session, one project, and one active process/run. In the default single-agent
flow the primary agent performs the work, runs CLI checks, writes artifacts,
and checks out; Worker and Inspector are phases/checks of the same session, not
separate participants. Agent Ledger is CLI/files, not a separate agent.

Basic prompt:

```text
Initialize this project with ProcessForge, connect the required tools and
knowledge, and use it for <what we are doing>. Fill all required artifacts.
```

Start a work session:

```text
Start a ProcessForge run for this work.

Read .pf/START_AGENT_HERE.md first. Create a run, split the work into explicit
tasks, record work/debug/fix/review iterations, keep artifacts and handoffs in
the project-local .pf folder, and finish with a run summary and doctor check.
```

### Forge / Factory Mode

A workplace can be Director-capable while individual projects remain simple.
Project coordination mode resolves as `simple`, `organized`, or `inherit` from
the workplace default. Use `organized` only for projects that should use the
workplace Director Office; simple projects keep the normal 1-1-1-1 flow.

Director and Supervisor/Execution Inspector are only needed for multi-agent,
process-transition, or external runtime-worker scenarios. See
[docs/concepts/agent-session-model.md](docs/concepts/agent-session-model.md).

For shell-agent plans, `orchestrator-shell-plan-apply --model <model>` passes
one selected model to every shell worker in the applied plan. Reasoning effort
is selected separately in the plan (`runtime.reasoning_effort` or worker
`reasoning_effort`) or on `worker-run prepare/start` with `--reasoning-effort`.

## Core Building Blocks

Process definitions describe process mechanics. They are configurable YAML
constructors with any number of stages, roles, artifacts, gates, capabilities,
allowed tools, and hooks. They do not need to name an implementation platform.

Platform contracts are composition entities for a concrete project context. A
platform may be single or composed as parent plus child. The contract connects
the required and recommended stack of knowledge packages, templates, tools, MCP
providers, capabilities, processes, coding standards, project type hints, and
policy data. ProcessForge core resolves these contracts from manifests; it does
not hardcode any real product, CMS, framework, marketplace, or business domain.

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
- Update tests are deterministic and use local-file fixtures; public
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

ProcessForge is licensed under the Apache License, Version 2.0. See
[LICENSE](LICENSE) and [NOTICE](NOTICE).
