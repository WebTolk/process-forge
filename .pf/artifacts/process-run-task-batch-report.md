# Process Run / Task Batch MVP Report

## Scope

Implemented the file-only Process Run / Task Batch MVP from `задания/processforge_process_run_task_batch_mvp_master_prompt.md`.

## Added Entities

- Run/work session: `.pf/runs/<run-id>/run.yaml`.
- Task: user-facing alias for the existing assignment entity.
- Iteration: repeated work/debug/fix/review/test/research/handoff/note attempt inside a task assignment YAML.

## Storage Model

Runs are stored under `.pf/runs/<run-id>/`. The run owns `run.yaml`, `plan.md`, `task-index.md`, `summary.md`, per-run artifact/review directories, and final handoff references.

Tasks remain canonical assignments in `.pf/assignments/<task-id>.yaml`. Each task includes `run_id`, and the run groups tasks through `tasks[]` records with assignment path, order, status, and blocking flag.

Task artifacts are grouped under `.pf/artifacts/runs/<run-id>/<task-id>/`.

## CLI Commands

Added:

- `run-create`
- `run-list`
- `run-status`
- `run-doctor`
- `run-summary`
- `run-complete`
- `task-create`
- `task-list`
- `task-start`
- `task-complete`
- `task-doctor`
- `iteration-add`
- `iteration-complete`

## Doctors

`run-doctor` checks run file presence, required run keys, status validity, process availability, task id uniqueness, assignment existence, task run linkage, task statuses, completed-run final artifacts, public-safe paths, and event presence.

`task-doctor` checks assignment presence, required task keys, status validity, run linkage, process availability, iteration id uniqueness, iteration kinds/statuses, public-safe paths, and completed-task result summary or artifact.

## Schemas And Templates

Added `schemas/run.schema.json`, `schemas/iteration.schema.json`, `templates/run.yaml`, `templates/assignment-task.yaml`, and `templates/iteration.yaml`. Updated `schemas/assignment.schema.json` for task/run/iteration fields and `schemas/process-event.schema.json` for run/task/iteration event names.

## Process And Prompt

Added `processes/task-batch-execution.yaml` and `prompts/task-batch-execution-agent.md`.

## START_AGENT_HERE

`agent-start-prompt` now refreshes the run block. With an active run, it shows `run-status` and the task iteration loop. Without a run, it shows `run-create`.

## Tests

Passed:

- `python -m py_compile tools\processforge.py tools\smoke_process_run_task_batch.py`
- `python tools\smoke_process_run_task_batch.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\processforge.py release-test --root .`
- `python tools\processforge.py release-pack --root . --output dist\processforge-v0.1.0.zip`
- `python tools\processforge.py release-archive-test --archive dist\processforge-v0.1.0.zip`
- `python tools\processforge.py project-context-refresh --project-root .`

## Remaining Limits

No multi-agent claim/lease, file locks, scheduler, daemon, watcher, runner, WTAICC driver, live hook interception, GUI, database, marketplace, or process authoring wizard were added. Hooks remain observational/outbox-only.

## Process Authoring MVP Readiness

The future Process Authoring MVP can now target a deeper model: process definitions can define default stages and gates, while concrete runs execute multiple assignment-backed tasks and record repeated task iterations.
