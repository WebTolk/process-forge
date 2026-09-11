# Handoff: orchestrator -> integration/review

Objective:
Coordinate worker outputs for run `docs-fix-1-1-1-shell-20260907`.

Current status:
Initial worker assignments, capsules, and launch prompts were generated.

Input artifacts:
- .pf/runs/docs-fix-1-1-1-shell-20260907/orchestrator-plan.yaml
- .pf/runs/docs-fix-1-1-1-shell-20260907/orchestration-summary.md

Files changed:
- .pf/runs/docs-fix-1-1-1-shell-20260907/
- .pf/assignments/
- .pf/contexts/assignment-capsules/

Files not to touch:
- Files outside each worker `allowed_files`.

Known issues:
- Worker outputs are pending.

Required checks:
- `python .pf/runtime/bin/pf.py run-doctor --project-root . --run docs-fix-1-1-1-shell-20260907`
- `python .pf/runtime/bin/pf.py task-doctor --project-root . --task <task-id>`

Next recommended action:
Launch workers with the generated prompts, then integrate their required outputs.
