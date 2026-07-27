# ProcessForge Documentation

![ProcessForge workplace layout](assets/processforge-architecture.svg)

Start from the top-level operating model: a workplace is the machine where
humans and AI agents run work, ProcessForge is installed once as a tool, global
resources live in the workplace, and each repository keeps a project-local
`.pf/` layer.

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
- [Multi-agent orchestration](getting-started/multi-agent-orchestration.md)
- [Runtime driver and supervisor quickstart](getting-started/runtime-driver-supervisor.md)
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
- [Package roots](concepts/workplace-resources.md)
- [Package roots overview](concepts/package-roots.md)
- [Project snapshot](concepts/project-context-snapshot.md)
- [Project snapshot overview](concepts/project-snapshot.md)
- [Hooks and events](concepts/processforge-events.md)
- [Hooks and events overview](concepts/hooks-events.md)
- [Runtime model](concepts/runtime-model.md)
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
- [Initial release notes](releases/initial-release.md)
- [Validation](validation/validation.md)
