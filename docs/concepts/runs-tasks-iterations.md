# Runs, Tasks, And Iterations

![Run lifecycle](../assets/processforge-run-lifecycle.svg)

ProcessForge separates a reusable process definition from a concrete work session.

```text
Process Definition = template
Run = one scoped execution for a cohesive result
Task = assignment inside a run
Iteration = repeated work/debug/fix/review attempt inside a task
```

## Ordinary governed Work

For a new objective, use `pf.context -> pf.work.start -> pf.work.state -> work
and evidence -> pf.work.transition`, then follow the returned state until
`action: run_completed`. Keep the exact returned Run/Assignment/context
selectors, check permissions and use [continuation](work-continuation.md) to
resume existing work. The final transition writes the summary and handoff;
it does not close the host session. See [Garage Core](garage-core.md) and
[evidence examples](declarative-process-execution.md).

The manual `run-create`, `task-create`, `iteration-add`, `task-complete`,
`run-summary`, `run-doctor` and `run-complete` commands belong to the
[advanced task-batch workflow](../getting-started/task-batch-workflow.md).
They maintain explicit batch records; they are not extra completion steps for
the governed Work cycle above. An iteration record alone does not advance a stage.

## Process Definition

A process definition lives in `processes/user/<process-id>.yaml`. It describes how a class of work should be governed: stages, roles, artifacts, gates, events, and evolution policy.

## Run

A run lives in `.pf/runs/<run-id>/run.yaml`. It groups assignment-backed tasks and records the final run artifacts:

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

Run, task, and iteration commands emit events to `.pf/runtime/events/events.sqlite3`. Existing hook dispatch remains observational and writes outbox payloads when hooks match the event type. This file-first flow does not require a daemon, scheduler, watcher, lease, or live interception. The optional workplace PF Runtime service is a separate lifecycle host and does not turn these commands into background-scheduled work.
