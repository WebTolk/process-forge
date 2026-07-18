# Minimal Task Batch Run

This example creates one run with two assignment-backed tasks.

```bash
python bin/pf.py run-create --project-root . --id minimal-run --title "Minimal run" --process task-batch-execution --apply
python bin/pf.py task-create --project-root . --run minimal-run --id task-001-work --title "Do the work" --process software-feature-development --apply
python bin/pf.py iteration-add --project-root . --task task-001-work --kind work --summary "Implemented the first change." --apply
python bin/pf.py iteration-add --project-root . --task task-001-work --kind debug --status passed --summary "Checked the first change." --apply
python bin/pf.py task-complete --project-root . --task task-001-work --summary "First task complete." --apply
python bin/pf.py task-create --project-root . --run minimal-run --id task-002-review --title "Review result" --process testing --apply
python bin/pf.py iteration-add --project-root . --task task-002-review --kind review --summary "Reviewed run output." --apply
python bin/pf.py task-complete --project-root . --task task-002-review --summary "Review complete." --apply
python bin/pf.py run-summary --project-root . --run minimal-run --apply
python bin/pf.py run-doctor --project-root . --run minimal-run
python bin/pf.py run-complete --project-root . --run minimal-run --apply
```
