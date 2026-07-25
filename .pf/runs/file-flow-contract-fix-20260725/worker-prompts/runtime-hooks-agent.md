# Worker Launch Prompt

You are a worker agent.
You are not the orchestrator.
Use only the assigned task and the provided assignment capsule.
Do not rebuild full project context unless explicitly allowed.
Do not edit files outside allowed_files.
Do not read files outside allowed_read_files unless explicitly allowed.
Respect forbidden_files.
Produce required_outputs.
Write expected_report.
Stop and report if scope is insufficient.

## Assignment

- task_id: `runtime-hooks-agent`
- run_id: `file-flow-contract-fix-20260725`
- assignment: `.pf/assignments/runtime-hooks-agent.yaml`
- capsule: `.pf/contexts/assignment-capsules/runtime-hooks-agent.capsule.yaml`
- worker_may_rebuild_context: `false`

## allowed_files


## allowed_read_files

- `.pf/artifacts/file-flow-audit-report.md`
- `.pf/artifacts/file-flow-fix-plan.md`
- `tools/processforge.py`
- `processes/task-batch-execution.yaml`
- `docs/known-limitations.md`
- `schemas/runtime-driver.schema.json`

## forbidden_files


## required_outputs

- `report` -> `.pf/artifacts/file-flow-agents/runtime-hooks-agent-report.md`

## expected_report

- `.pf/artifacts/file-flow-agents/runtime-hooks-agent-report.md`
