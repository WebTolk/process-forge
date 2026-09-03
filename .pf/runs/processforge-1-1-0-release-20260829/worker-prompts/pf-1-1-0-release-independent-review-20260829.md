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

- task_id: `pf-1-1-0-release-independent-review-20260829`
- run_id: `processforge-1-1-0-release-20260829`
- assignment: `.pf/assignments/pf-1-1-0-release-independent-review-20260829.yaml`
- capsule: `.pf/contexts/assignment-capsules/pf-1-1-0-release-independent-review-20260829.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/processforge-1-1-0-release-20260829/pf-1-1-0-release-independent-review-20260829/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/reviews/processforge-1.1.0-release-20260829.md`

## allowed_read_files

- `dist/processforge-1.1.0.zip`
- `dist/processforge-1.1.0.manifest.json`
- `.pf/artifacts/processforge-1-1-0-release-20260829/release-build-report.md`
- `.pf/artifacts/processforge-1-1-0-release-20260829/release-surface-audit.md`
- `.pf/artifacts/processforge-1-1-0-release-20260829/checksum-provenance-report.md`
- `VERSION`
- `README.md`
- `README.ru.md`
- `CHANGELOG.md`
- `updates/processforge-update-index.yaml`
- `docs/getting-started/update-system.md`
- `docs/ru/getting-started/update-system.md`

## forbidden_files


## required_outputs

- `independent_release_review` -> `.pf/reviews/processforge-1.1.0-release-20260829.md`

## expected_report

- `.pf/reviews/processforge-1.1.0-release-20260829.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
