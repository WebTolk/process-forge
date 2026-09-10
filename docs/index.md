# ProcessForge Documentation

![ProcessForge workplace layout](assets/processforge-architecture.svg)

Start from the top-level operating model: ProcessForge is installed once as a
tool, a workplace is the machine-level home for reusable resources, and each
repository keeps only a project-local `.pf/` layer.

The required initialization order is workplace first, workplace resources
second, and project onboarding third. Use guided workplace setup by default for
human-led machine setup. Use the fully automatic path only when the operator
provides explicit paths and choices.

## For Humans

- [Top-level README](../README.md)
- [Quickstart prompts](../QUICKSTART.md)
- [Installation](getting-started/installation.md)
- [Guided workplace setup](getting-started/guided-workplace-setup.md)
- [Initialization order](getting-started/initialization-order.md)
- [Workplace vs project](concepts/workplace-vs-project.md)
- [Resource authoring](getting-started/resource-authoring.md)
- [Project onboarding](getting-started/project-onboarding.md)
- [Built-in process stages](processes/built-in-processes.md)

## For AI Agents

- [Agent command runbook and prompts](getting-started/agent-prompts.md)
- [Guided workplace setup agent prompt](../prompts/guided-workplace-setup-agent.md)
- [Automatic workplace initialization agent prompt](../prompts/workplace-initialization-agent.md)
- [Project onboarding agent prompt](../prompts/project-onboarding-agent.md)
- [Release checklist](release-checklist.md)
- [Validation](validation/validation.md)

## Getting Started

- [First run](getting-started/first-run.md)
- [Installation](getting-started/installation.md)
- [Initialization order](getting-started/initialization-order.md)
- [Workplace initialization](getting-started/workplace-initialization.md)
- [Guided workplace setup](getting-started/guided-workplace-setup.md)
- [Project onboarding](getting-started/project-onboarding.md)
- [Agent command runbook and prompts](getting-started/agent-prompts.md)
- [Create your first process](getting-started/create-your-first-process.md)
- [Task batch workflow](getting-started/task-batch-workflow.md)
- [Built-in process stages](processes/built-in-processes.md)
- [Multi-agent orchestration](getting-started/multi-agent-orchestration.md)
- [Runtime driver and supervisor quickstart](getting-started/runtime-driver-supervisor.md)
- [Runtime autostart and Codex MCP startup](getting-started/runtime-autostart.md)
- [Quick getting started path](getting-started.md)
- [Russian documentation](ru/index.md)

## Authoring

- [Reusable templates](authoring/reusable-template-authoring.md)
- [Knowledge packages](authoring/knowledge-package-authoring.md)
- [Platform contracts](authoring/platform-contract-authoring.md)
- [Knowledge resource navigation](concepts/knowledge-resource-navigation.md)
- [Process authoring](authoring/process-authoring.md)
- [Authoring parity](authoring/authoring-parity.md)
- [Backfill existing processes](authoring/backfill-existing-processes.md)
- [Resource authoring](getting-started/resource-authoring.md)
- [Task batch execution](authoring/task-batch-execution.md)

## Concepts

- [Workplace vs project](concepts/workplace-vs-project.md)
- [Path constants](concepts/path-constants.md)
- [Context resolution](concepts/context-resolution.md)
- [Cascade merge](concepts/cascade-merge.md)
- [Package roots](concepts/workplace-resources.md)
- [Package roots overview](concepts/package-roots.md)
- [Project snapshot](concepts/project-context-snapshot.md)
- [Project snapshot overview](concepts/project-snapshot.md)
- [Hooks and events](concepts/processforge-events.md)
- [Hooks and events overview](concepts/hooks-events.md)
- [Runtime model](concepts/runtime-model.md)
- [Garage Core](concepts/garage-core.md)
- [Declarative process execution](concepts/declarative-process-execution.md)
- [PF Runtime MCP facade](concepts/runtime-mcp.md)
- [Agent session model](concepts/agent-session-model.md)
- [Project coordination modes](concepts/project-coordination-modes.md)
- [Runtime drivers](concepts/runtime-drivers.md)
- [Process supervisor](concepts/process-supervisor.md)
- [Director, ledger, inspector, and worker boundary](concepts/director-ledger-inspector-boundary.md)
- [Platform inheritance](concepts/platform-inheritance.md)
- [Process definition, run, task, iteration](concepts/process-definition-run-task-iteration.md)
- [Semantic parity](concepts/semantic-parity.md)
- [Runs, tasks, and iterations](concepts/runs-tasks-iterations.md)
- [Multi-agent orchestration](concepts/multi-agent-orchestration.md)
- [Known limitations](known-limitations.md)

## Layer Order

1. Workplace device: computer, laptop, server, or runner host.
2. ProcessForge tool root: CLI, schemas, processes, docs, templates, checks.
3. Global workplace resources: knowledge packages, reusable templates, tools,
   MCP providers, platform contracts, roots, registries, runtime data.
4. Project `.pf/` layer: selected resources, project context, assignments,
   runs, tasks, iterations, artifacts, reviews, handoffs, hooks.

Platform contracts are composition manifests. They can model a single platform
or a parent/child stack and connect the resources needed by a concrete project.
Process definitions remain platform-agnostic process mechanics.

## Release And Validation

- [Release checklist](release-checklist.md)
- [Release publishing](maintainers/release-publishing.md)
- [Initial release notes](releases/initial-release.md)
- [Validation](validation/validation.md)
