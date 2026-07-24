# Multi-Agent Orchestration

Multi-agent orchestration is the out-of-box ProcessForge process for splitting a run into bounded worker assignments.

The orchestrator creates an `orchestrator-task-plan.yaml`, validates scope rules, applies the plan, and receives worker outputs for integration.

Workers receive only:

- their assignment file
- their assignment capsule
- allowed read and write scopes
- forbidden files
- required outputs
- expected report path

Workers do not receive full project context by default. Assignment capsules set `worker_may_rebuild_context: false`.

## Scope Rules

- Parallel workers must not have overlapping write scopes unless the plan explicitly allows overlap.
- `forbidden_files` override `allowed_files`.
- Required outputs must be inside the worker allowed files or under the project artifact area.
- Core files are writable only when explicitly allowed.
- A worker stops and reports when the provided scope is insufficient.

## Apply Output

`orchestrator-plan apply --apply` creates:

- a run
- worker task assignments
- assignment capsules
- worker launch prompts
- task index
- orchestration summary
- initial orchestrator handoff
