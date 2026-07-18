# Debug Loop Run

This example shows repeated work/debug/fix iterations before task completion.

```bash
python bin/pf.py run-create --project-root . --id debug-loop --title "Debug loop" --process task-batch-execution --apply
python bin/pf.py task-create --project-root . --run debug-loop --id task-001-fix-regression --title "Fix regression" --process bug-fix --apply
python bin/pf.py iteration-add --project-root . --task task-001-fix-regression --kind work --summary "Implemented initial fix." --apply
python bin/pf.py iteration-add --project-root . --task task-001-fix-regression --kind debug --status failed --summary "Regression still fails." --apply
python bin/pf.py iteration-add --project-root . --task task-001-fix-regression --kind fix --summary "Adjusted edge case handling." --apply
python bin/pf.py iteration-add --project-root . --task task-001-fix-regression --kind debug --status passed --summary "Regression passes." --apply
python bin/pf.py task-complete --project-root . --task task-001-fix-regression --summary "Regression fixed and checked." --apply
python bin/pf.py run-summary --project-root . --run debug-loop --apply
python bin/pf.py run-doctor --project-root . --run debug-loop
python bin/pf.py run-complete --project-root . --run debug-loop --apply
```
