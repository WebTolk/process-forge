# Process Definition, Run, Task, Iteration

Process definitions describe lifecycle mechanics, not platform-specific build
or delivery commands. For example, `software-feature-development` includes
conditional `release-delivery` and `evolve` stages, while a package/build/install
step belongs to an `execution_profile.delivery_profile` operation.

ProcessForge separates process design from execution records.

- A process definition in `processes/<id>.yaml` declares roles, stages,
  artifacts, gates, capabilities, and evolution policy.
- A run in `.pf/runs/<run-id>/run.yaml` records one work session using a process.
- A task in `.pf/assignments/<task-id>.yaml` records assignment-backed work
  inside a run.
- An iteration records a repeated `work`, `debug`, `fix`, `review`, `test`,
  `research`, `handoff`, or `note` attempt for a task.

Authoring produces the process definition and companion prompt/docs/examples.
Execution commands then use that process id:

```bash
python bin/pf.py run-create --project-root <project-root> --id <run-id> --title "<title>" --process <process-id> --apply
python bin/pf.py task-create --project-root <project-root> --run <run-id> --id task-001 --title "<task>" --process <process-id> --apply
python bin/pf.py iteration-add --project-root <project-root> --task task-001 --kind work --summary "..." --apply
```

The MVP is file-first. It records durable artifacts and events, but it does not
schedule work in the background or execute hooks as local commands.
