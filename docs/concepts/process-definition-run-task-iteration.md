# Process Definition, Run, Task, Iteration

Process definitions describe lifecycle mechanics, not platform-specific build
or delivery commands. For example, `software-feature-development` includes
conditional `release-delivery` and `evolve` stages, while a package/build/install
step belongs to an `execution_profile.delivery_profile` operation.

ProcessForge separates process design from execution records.

- A process definition in `processes/user/<id>.yaml` declares roles, stages,
  artifacts, gates, capabilities, and evolution policy.
- A run in `.pf/runs/<run-id>/run.yaml` records one scoped execution of a process for a cohesive result.
- A task in `.pf/assignments/<task-id>.yaml` records assignment-backed work
  inside a run.
- An iteration records a repeated `work`, `debug`, `fix`, `review`, `test`,
  `research`, `handoff`, or `note` attempt for a task.

## Choosing A Run Boundary

A Run should cover one cohesive result that can be reviewed and accepted against explicit criteria. File count, elapsed time, number of commits and worker responses do not define that boundary. Several related changes can belong to one result, while a small independent fix can be a complete result of its own.

Use tasks and iterations to organize work inside that boundary. Repeated domain/architecture reasoning, approved revisions, implementation and targeted checks need not create another Run. Final assurance assesses the accumulated candidate; release, publication and installation follow the agreed delivery requirement and project/operator policy. Reuse earlier evidence only while it remains applicable, rerunning checks invalidated by later changes.

A permitted stage contribution can use prepared input for the existing primary Assignment, with a writer handoff and primary review after collection. Changing the executor alone does not require another Task or Run.

A worker can own a substantial package with its own complete process. Its cycle is nested within the orchestrator's cycle: the primary integrates the result and evidence before parent acceptance. A child completion is not an automatic parent completion or publication. Batch related small tasks when that creates useful independent work; handle an isolated tiny edit in the primary when a separate worker lifecycle would add only coordination.

These boundaries do not change permissions. Use the current Work contract, declared outcomes, protected-artifact revision and governed handoff mechanisms; do not widen scope, invent a return transition or rebuild an immutable capsule.

Authoring produces the process definition and companion prompt/docs/examples.
Execution commands then use that process id:

```bash
python bin/pf.py run-create --project-root <project-root> --id <run-id> --title "<title>" --process <process-id> --apply
python bin/pf.py task-create --project-root <project-root> --run <run-id> --id task-001 --title "<task>" --process <process-id> --apply
python bin/pf.py iteration-add --project-root <project-root> --task task-001 --kind work --summary "..." --apply
```

The MVP is file-first. It records durable artifacts and events, but it does not
schedule work in the background or execute hooks as local commands.
