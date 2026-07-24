# Handoff: orchestrator -> integration/review

Objective:
Coordinate worker outputs for run `post-runtime-supervisor-audit`.

Current status:
Initial worker assignments, capsules, and launch prompts were generated.

Input artifacts:
- .pf/runs/post-runtime-supervisor-audit/orchestrator-plan.yaml
- .pf/runs/post-runtime-supervisor-audit/orchestration-summary.md

Files changed:
- .pf/runs/post-runtime-supervisor-audit/
- .pf/assignments/
- .pf/contexts/assignment-capsules/

Files not to touch:
- Files outside each worker `allowed_files`.

Known issues:
- Worker outputs are pending.

Required checks:
- `python .pf/runtime/bin/pf.py run-doctor --project-root . --run post-runtime-supervisor-audit`
- `python .pf/runtime/bin/pf.py task-doctor --project-root . --task <task-id>`

Next recommended action:
Launch workers with the generated prompts, then integrate their required outputs.
