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

- task_id: `r02-release-command-review`
- run_id: `r02-release-command-review-20260911`
- assignment: `.pf/assignments/r02-release-command-review.yaml`
- capsule: `.pf/contexts/assignment-capsules/r02-release-command-review.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/r02-release-command-review-20260911/r02-release-command-review/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/r02-release-candidate-20260911/r02-release-command-review/**`
- `.pf/tmp/r02-release-command-review/**`

## allowed_read_files

- `.pf/AGENTS.md`
- `.pf/artifacts/r02-release-candidate-20260911/**`
- `tools/processforge.py`
- `tools/release_test.py`
- `VERSION`
- `checksums/**`
- `docs/**`

## forbidden_files

- `src/**`
- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `.pf/process-forge.yaml`

## required_outputs

- `r02-release-command-review-report` -> `.pf/artifacts/r02-release-candidate-20260911/r02-release-command-review/report.md`

## expected_report

- `.pf/artifacts/r02-release-candidate-20260911/r02-release-command-review/report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
