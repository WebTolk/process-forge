# Built-In Process Stages

ProcessForge ships with built-in core processes under `processes/core/`. These
processes are file-first workflows: the YAML process definition is the
authoritative contract, and this page is a human-readable stage guide.

Use this page to choose a process before starting a run. Use
`python bin/pf.py process-describe --project-root . --process <process-id>` when
you need the exact current YAML details.

## Development Process

For normal product or code work, use `task-batch-execution` first. It is the
default development process for the Garage Mode `1-1-1-1` flow: one operator,
one primary agent session, one project, and one active run.

Stages:

1. `run-intake`: create the run or inspect the active run.
2. `task-planning`: create assignment-backed tasks and attach them to the run.
3. `task-execution-loop`: do the work in recorded iterations: analysis,
   implementation, debugging, testing, review, research, handoff, or notes.
4. `task-result-fixation`: complete each task with a result summary or result
   artifact.
5. `run-review`: run `run-doctor` and `task-doctor` checks before completion.
6. `run-summary`: aggregate task results into the final summary and handoff.

This process is intentionally practical. It does not require Director Office,
leases, external workers, or a background daemon. Use it for ordinary
development requests, release preparation, documentation updates, bug fixes,
and feature work that one primary agent can coordinate safely.

Use `multi-agent-task-orchestration` when independent workstreams need separate
agent sessions. Use `orchestrator-shell-agents-supervision` when those workers
are launched as shell-agent processes through runtime drivers.

## Process Selection

| Need | Start With |
|---|---|
| Work on a project, feature, bug, release, or docs task | `task-batch-execution` |
| Connect an existing repository to ProcessForge | `project-onboarding` |
| Initialize a new project flow and inspect project specifics | `project-initialization` |
| Prepare a machine-level workplace | `guided-workplace-setup` or `workplace-initialization` |
| Split work across independent agents | `multi-agent-task-orchestration` |
| Launch shell workers from an orchestrator plan | `orchestrator-shell-agents-supervision` |
| Create a new process definition | `process-authoring` |
| Update a process version | `process-version-upgrade` |
| Create knowledge, templates, tools, MCP, or platform resources | the corresponding authoring/register process |

## Stage Reference

| Process | Purpose | Stages |
|---|---|---|
| `agent-director-supervision` | Coordinate organized projects through pending handoffs, availability, leases, target runs, and continuation capsules. | `inspect` -> `assign` -> `wait-or-return` |
| `authoring-parity-audit` | Audit existing processes and resources against authoring workflows. | `intake` -> `discover-existing-processes` -> `import-authoring-answers` -> `generate-candidates` -> `semantic-compare` -> `doctor-candidates` -> `resource-parity-checks` -> `report-findings` -> `handoff` |
| `context-resolution` | Resolve sources into context index, rules, conflict report, and assignment context packages. | `source-discovery` -> `rule-classification` -> `cascade-merge` -> `conflict-detection` -> `context-index-generation` -> `resolved-rules-generation` -> `fingerprint-recording` -> `ecp-capsule-generation` |
| `guided-workplace-setup` | Guide a human-led workplace setup from answers to proposal and apply. | `intake` -> `dialogue` -> `review` -> `apply` |
| `knowledge-package-authoring` | Create a workplace knowledge package through authoritative package roots. | `intake` -> `select-package-root` -> `create-package-structure` -> `write-package-manifest` -> `create-resource-index` -> `add-initial-resources` -> `run-package-doctor` -> `handoff` |
| `knowledge-package-improvement` | Propose, review, and integrate reusable process knowledge. | `propose` -> `assess` -> `integrate` |
| `knowledge-package-update` | Update a knowledge package through inspection, proposal, update, and compatibility checks. | `current-package-inspection` -> `change-proposal` -> `resource-update` |
| `knowledge-resource-add` | Add a knowledge resource through proposal, classification, index refresh, validation, and review. | `intake` -> `target-resolution` -> `package-index-update` -> `validation` |
| `mcp-register` | Register an MCP capability provider without storing secrets. | `intake` -> `registry-update` |
| `multi-agent-task-orchestration` | Compose bounded worker assignments for multiple agent sessions. | `plan` -> `assign` -> `worker-execution` -> `integration-review` |
| `orchestrator-shell-agents-supervision` | Launch and supervise shell-agent worker sessions through runtime drivers. | `plan` -> `launch` -> `collect` |
| `platform-contract-authoring` | Create a platform contract linking project type hints to resources and processes. | `intake` -> `select-platform-root` -> `create-platform-structure` -> `write-platform-contract` -> `link-capabilities` -> `link-knowledge-packages` -> `link-templates` -> `link-tools-mcp` -> `run-platform-doctor` -> `handoff` |
| `platform-contract-install` | Create or update a platform contract mapping capabilities and resources. | `platform-definition` -> `contract-creation` |
| `process-authoring` | Create, review, apply, and validate a new ProcessForge process definition. | `intake` -> `draft-process` -> `logic-review` -> `apply-process` -> `process-doctor` -> `handoff` |
| `process-supervisor` | Prepare, start, observe, verify, and collect external runtime worker state. | `prepare` -> `start` -> `collect` |
| `process-version-upgrade` | Assess and perform safe upgrades between process versions. | `compare` -> `decide` |
| `processforge-update-check` | Check a linked ProcessForge distribution update index and record project impact. | `discover` -> `assess` |
| `project-initialization` | Connect a project to ProcessForge and a configured workplace layer. | `intake` -> `workplace-resolution` -> `repository-scan` -> `project-classification` -> `global-resource-matching` -> `project-specificity-extraction` -> `proposal` -> `review` -> `apply` -> `doctor` |
| `project-onboarding` | Attach a project to an existing ProcessForge workplace without recreating the workplace. | `intake` -> `create-project-flow` -> `detect-project` -> `snapshot` -> `first-assignment` -> `validate` -> `handoff` |
| `reusable-template-authoring` | Create, register, validate, and hand off a reusable workplace template. | `intake` -> `select-template-root` -> `create-template-structure` -> `write-manifest` -> `write-example-files` -> `register-template` -> `run-template-doctor` -> `handoff` |
| `runtime-driver-registry` | Govern neutral runtime driver manifests and registry entries. | `inventory` -> `validate` |
| `session-bootstrap` | Start or inspect a primary agent session and resolve current project state. | `intake` -> `mode-detection` -> `flow-location` -> `workplace-resolution` -> `context-freshness-check` -> `status-scan` -> `session-report` |
| `task-batch-execution` | Execute project work sequentially inside one primary agent run. | `run-intake` -> `task-planning` -> `task-execution-loop` -> `task-result-fixation` -> `run-review` -> `run-summary` |
| `template-add` | Add a simple reusable template folder and optional registry entry. | `intake` -> `template-folder-creation` |
| `tool-register` | Register a workplace tool capability provider. | `intake` -> `registry-update` |
| `workplace-initialization` | Initialize or update the machine-local workplace layer. | `intake` -> `device-discovery` -> `terms-setup` -> `registry-setup` -> `tool-discovery` -> `mcp-discovery` -> `proposal` -> `review` -> `apply` -> `doctor` |

## Validation

Before changing a built-in process, run:

```bash
python bin/pf.py process-doctor --project-root . --process <process-id> --contract-only
python bin/pf.py builtin-process-catalog-doctor --root . --public
```

Before publishing a release that changes processes or this documentation, run
the normal release gates from the release checklist.
