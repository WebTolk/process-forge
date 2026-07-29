# Minimal Task Batch Run

This example creates one run with two assignment-backed tasks. Run it from any
directory by pointing the ProcessForge launcher at an already onboarded project.

```bash
python <processforge-root>/bin/pf.py run-create --project-root <project-root> --id minimal-run --title "Minimal run" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py task-create --project-root <project-root> --run minimal-run --id task-001-work --title "Do the work" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-work --kind work --summary "Implemented the first change." --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-work --kind debug --status passed --summary "Checked the first change." --apply
python <processforge-root>/bin/pf.py task-complete --project-root <project-root> --task task-001-work --summary "First task complete." --apply
python <processforge-root>/bin/pf.py task-create --project-root <project-root> --run minimal-run --id task-002-review --title "Review result" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-002-review --kind review --summary "Reviewed run output." --apply
python <processforge-root>/bin/pf.py task-complete --project-root <project-root> --task task-002-review --summary "Review complete." --apply
python <processforge-root>/bin/pf.py run-summary --project-root <project-root> --run minimal-run --apply
python <processforge-root>/bin/pf.py run-doctor --project-root <project-root> --run minimal-run
python <processforge-root>/bin/pf.py run-complete --project-root <project-root> --run minimal-run --apply
```
