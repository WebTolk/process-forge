# Worker Launch Prompt

You are a worker agent.
You are not the orchestrator.
Use only the assigned task and the provided assignment capsule.
Do not rebuild full project context unless explicitly allowed.
Do not edit files outside allowed_files.
Do not read files outside allowed_read_files unless explicitly allowed.
Use workspace_access_file for explicitly granted workplace resources.
Do not copy private paths from workspace_access_file into public project artifacts, assignments, capsules, or reports.
Respect forbidden_files.
Produce required_outputs.
Write expected_report.
Stop and report if scope is insufficient.
Invoke subagents only when subagent_policy.allow is true.
When subagent reports are required, write them only under subagent_policy.reports_dir.

## Assignment

- task_id: `runtime-workplace-state-differential`
- run_id: `runtime-lifecycle-clean-repro-20260814`
- assignment: `.pf/assignments/runtime-workplace-state-differential.yaml`
- capsule: `.pf/contexts/assignment-capsules/runtime-workplace-state-differential.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/runtime-lifecycle-clean-repro-20260814/runtime-workplace-state-differential/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/runtime-lifecycle-clean-repro-20260814/runtime-workplace-state-differential-worker.md`

## allowed_read_files

- `.pf/artifacts/runtime-lifecycle-clean-repro-20260814/runtime-lifecycle-clean-repro.md`
- `.pf/runtime/pf-runtime/service.json`
- `.pf/runtime/pf-runtime/runtime.lock`
- `.pf/runtime/pf-runtime/logs/runtime.stdout.log`
- `.pf/runtime/pf-runtime/logs/runtime.stderr.log`
- `tools/pf_runtime/service.py`
- `задания/process-forge-runtime-lifecycle-clean-repro-master-prompt.md`

## forbidden_files


## required_outputs

- `runtime-workplace-state-differential-worker` -> `.pf/artifacts/runtime-lifecycle-clean-repro-20260814/runtime-workplace-state-differential-worker.md`

## expected_report

- `.pf/artifacts/runtime-lifecycle-clean-repro-20260814/runtime-workplace-state-differential-worker.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
