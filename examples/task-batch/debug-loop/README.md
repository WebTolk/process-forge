# Debug Loop Run

This example shows repeated work/debug/fix iterations before task completion.
Run it from any directory by pointing the ProcessForge launcher at an already
onboarded project.

```bash
python <processforge-root>/bin/pf.py run-create --project-root <project-root> --id debug-loop --title "Debug loop" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py task-create --project-root <project-root> --run debug-loop --id task-001-fix-regression --title "Resolve failed check" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-fix-regression --kind work --summary "Implemented initial fix." --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-fix-regression --kind debug --status failed --summary "Regression still fails." --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-fix-regression --kind fix --summary "Adjusted edge case handling." --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-fix-regression --kind debug --status passed --summary "Regression passes." --apply
python <processforge-root>/bin/pf.py task-complete --project-root <project-root> --task task-001-fix-regression --summary "Regression fixed and checked." --apply
python <processforge-root>/bin/pf.py run-summary --project-root <project-root> --run debug-loop --apply
python <processforge-root>/bin/pf.py run-doctor --project-root <project-root> --run debug-loop
python <processforge-root>/bin/pf.py run-complete --project-root <project-root> --run debug-loop --apply
```
