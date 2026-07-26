# Multi-Agent Orchestration

Multi-agent orchestration is the out-of-box ProcessForge process for splitting a run into bounded worker assignments.

It composes multiple Primary Agent Sessions. Each worker is not a sub-persona
inside the orchestrator; it is its own `1-1-1-1` session with a `session_id`,
assignment, capsule, scope, and output contract. Agent Director/Orchestrator
coordinates those sessions. The default single-agent flow does not require this
process.

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

- Public config fields are behavioral. If a field is accepted in schemas, templates, docs, or examples, it must affect behavior, be documented as metadata-only, or fail validation when unsupported.
- Unsupported public fields fail validation unless they are placed in the explicit `metadata` or `x_` extension namespace.
- Parallel workers must not have overlapping write scopes unless the plan explicitly sets `allow_write_scope_overlap: true`.
- When `allow_write_scope_overlap: true` is resolved, generated assignments and capsules record an allow policy, and the supervisor does not block workers solely because their write scopes overlap inside that plan.
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
- `config-resolution-report.yaml` with the config values that were applied to assignments, capsules, supervisor scheduling, and output collection
