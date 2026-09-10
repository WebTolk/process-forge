# Task Batch Workflow

Use task batch execution when one work session contains multiple related tasks
and each task may need several work/debug/fix iterations. For the ordinary
governed work loop, prefer [Garage Core](../concepts/garage-core.md) and
[Declarative process execution](../concepts/declarative-process-execution.md);
the CLI sequence below is a compatibility-oriented batch example.

Prerequisite: the operator has already activated the official
`processforge.official.software-development` and `processforge.official.verification`
packs in the Workplace. This example uses their `software-feature-development`
and `testing` processes, respectively. Confirm they
are available with `process-list`; if not, request operator setup before using
this example. Ordinary project work must not activate packs as an implicit
repair step.

Create a run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id release-prep --title "Release preparation" --process task-batch-execution --apply
```

Create tasks:

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run release-prep --id task-001-docs --title "Update docs" --process software-feature-development --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run release-prep --id task-002-tests --title "Run tests" --process testing --apply
```

Record iterations:

```bash
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-docs --kind work --summary "Updated run docs." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-docs --kind debug --status passed --summary "Docs links checked." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-002-tests --kind work --summary "Ran the test batch." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-002-tests --kind debug --status passed --summary "Tests and logs reviewed." --apply
```

Complete tasks and the run:

```bash
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-docs --summary "Docs updated and checked." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-002-tests --summary "Tests completed and reviewed." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run release-prep --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run release-prep
python .pf/runtime/bin/pf.py run-complete --project-root . --run release-prep --apply
```

`run-complete` fails while any blocking task remains open, so every blocking
task must be finished before the run closes.

Inside an onboarded project, prefer the linked runtime launcher:

```bash
python .pf/runtime/bin/pf.py run-status --project-root . --run release-prep
```
