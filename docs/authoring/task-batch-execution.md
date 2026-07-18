# Task Batch Execution Authoring

`task-batch-execution` is an execution process, not a process authoring wizard. It manages a concrete run that contains assignment-backed tasks and per-task iterations.

The process expects these stages:

- `run-intake`
- `task-planning`
- `task-execution-loop`
- `task-result-fixation`
- `run-review`
- `run-summary`

Blocking gates keep the file model coherent:

- a run must have tasks before completion;
- all blocking tasks must be `done`;
- completed tasks must have a result summary or result artifact;
- completed runs must have summary and handoff files;
- public run and task files must not contain private absolute paths.

The MVP intentionally does not include multi-agent claim or lease files, file locks, background watchers, a scheduler, a runner, WTAICC drivers, live hook interception, GUI, database, marketplace, or process authoring wizard.
