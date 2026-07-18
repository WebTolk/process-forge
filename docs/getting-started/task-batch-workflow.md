# Task Batch Workflow

Use task batch execution when one work session contains multiple related tasks and each task may need several work/debug/fix iterations.

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
```

Complete tasks and the run:

```bash
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-docs --summary "Docs updated and checked." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run release-prep --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run release-prep
python .pf/runtime/bin/pf.py run-complete --project-root . --run release-prep --apply
```

Inside an onboarded project, prefer the linked runtime launcher:

```bash
python .pf/runtime/bin/pf.py run-status --project-root . --run release-prep
```
