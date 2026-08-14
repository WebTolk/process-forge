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

- task_id: `pre-release-remediation-implementation-20260730`
- run_id: `pre-release-remediation-20260730`
- assignment: `.pf/assignments/pre-release-remediation-implementation-20260730.yaml`
- capsule: `.pf/contexts/assignment-capsules/pre-release-remediation-implementation-20260730.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/pre-release-remediation-20260730/pre-release-remediation-implementation-20260730/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-process-forge-checksums.py`
- `tools/validate-public-cleanliness.py`
- `tools/smoke_*.py`
- `schemas/**`
- `processes/**`
- `templates/**`
- `seeds/**`
- `packs/**`
- `docs/**`
- `updates/**`
- `checksums/processforge.sha256`
- `dist/processforge.zip`
- `dist/processforge.manifest.json`
- `.processforge-releaseignore`
- `.pf/adr/pre-release-remediation-schema-authority-20260730.md`
- `.pf/artifacts/pre-release-remediation-*.md`
- `.pf/reviews/pre-release-remediation-*.md`
- `.pf/handoffs/pre-release-remediation-*.md`
- `.pf/logs/pre-release-remediation-20260730.md`
- `.pf/runs/pre-release-remediation-20260730/**`
- `.pf/assignments/pre-release-remediation-implementation-20260730.yaml`
- `.pf/assignments/remediation-*-20260730.yaml`
- `.pf/runtime/assignment-capsules/**`
- `.pf/runtime/current-session.json`

## allowed_read_files


## forbidden_files

- `.git/**`
- `.pf/contexts/**`
- `.pf/artifacts/pre-release-product-audit-20260730.md`
- `.pf/reviews/pre-release-product-audit-20260730-review.md`

## required_outputs

- `remediation-plan` -> `.pf/artifacts/pre-release-remediation-plan-20260730.md`
- `remediation-report` -> `.pf/artifacts/pre-release-remediation-report-20260730.md`
- `remediation-review` -> `.pf/reviews/pre-release-remediation-review-20260730.md`
- `release-handoff` -> `.pf/handoffs/pre-release-remediation-release-handoff-20260730.md`

## expected_report

- `.pf/artifacts/pre-release-remediation-report-20260730.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
