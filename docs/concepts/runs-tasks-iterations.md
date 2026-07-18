# Runs, Tasks, And Iterations

ProcessForge separates a reusable process definition from a concrete work session.

```text
Process Definition = template
Run = concrete work session, batch, or release cycle
Task = assignment inside a run
Iteration = repeated work/debug/fix/review attempt inside a task
```

## Process Definition

A process definition lives in `processes/<process-id>.yaml`. It describes how a class of work should be governed: stages, roles, artifacts, gates, events, and evolution policy.

## Run

A run lives in `.pf/runs/<run-id>/run.yaml`. It groups several assignment-backed tasks and records the final run artifacts:

```text
.pf/runs/<run-id>/summary.md
.pf/handoffs/runs/<run-id>-handoff.md
```

Run files are public ProcessForge project files. They must not contain local absolute paths or secrets.

## Task

Task is the user-facing alias for the existing assignment entity. The canonical task record is still:

```text
.pf/assignments/<task-id>.yaml
```

Every task inside a run includes:

```yaml
run_id: <run-id>
```

The run stores task references in `tasks`, including task id, assignment path, status, order, and blocking flag.

## Iteration

Iterations live inside the task assignment YAML. Supported kinds are `work`, `debug`, `fix`, `review`, `test`, `research`, `handoff`, and `note`.

Supported iteration statuses are `planned`, `in_progress`, `completed`, `passed`, `failed`, and `cancelled`.

## Events And Hooks

Run, task, and iteration commands emit events to `.pf/runtime/events/events.ndjson`. Existing hook dispatch remains observational and writes outbox payloads when hooks match the event type. There is no daemon, scheduler, watcher, lease, or live interception in this MVP.
