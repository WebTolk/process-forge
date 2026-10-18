# Handoff: orchestrator -> integration/review

Objective:
Coordinate worker outputs for run `core-f09-f12-shell-20260910`.

Current status:
Initial worker assignments, capsules, and launch prompts were generated.

Input artifacts:
- .pf/runs/core-f09-f12-shell-20260910/orchestrator-plan.yaml
- .pf/runs/core-f09-f12-shell-20260910/orchestration-summary.md

Files changed:
- .pf/runs/core-f09-f12-shell-20260910/
- .pf/assignments/
- .pf/contexts/assignment-capsules/

Files not to touch:
- Files outside each worker `allowed_files`.

Known issues:
- Worker outputs are pending.

Required checks:
- `python .pf/runtime/bin/pf.py run-doctor --project-root . --run core-f09-f12-shell-20260910`
- `python .pf/runtime/bin/pf.py task-doctor --project-root . --task <task-id>`

Next recommended action:
Launch workers with the generated prompts, then integrate their required outputs.
