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

- task_id: `central-ingress-idempotency-contract-20260814`
- run_id: `central-agent-event-ingress-20260814`
- assignment: `.pf/assignments/central-ingress-idempotency-contract-20260814.yaml`
- capsule: `.pf/contexts/assignment-capsules/central-ingress-idempotency-contract-20260814.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/central-agent-event-ingress-20260814/central-ingress-idempotency-contract-20260814/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/central-agent-event-ingress-20260814/idempotency-and-replay-contract.md`

## allowed_read_files

- `задания/process-forge-central-agent-event-ingress-master-prompt.md`
- `.pf/artifacts/central-agent-event-ingress-20260814/central-event-ingress-design-v2.md`
- `.pf/artifacts/central-agent-event-ingress-20260814/event-storage-layout-v2.md`
- `.pf/artifacts/central-agent-event-ingress-20260814/event-routing-policy-v2.md`
- `.pf/artifacts/central-agent-event-ingress-20260814/central-event-ingress-design-review.md`
- `.pf/artifacts/central-agent-event-ingress-20260814/current-event-test-inventory-review.md`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/codex_hooks.py`
- `tools/processforge.py`

## forbidden_files


## required_outputs

- `idempotency-and-replay-contract` -> `.pf/artifacts/central-agent-event-ingress-20260814/idempotency-and-replay-contract.md`

## expected_report

- `.pf/artifacts/central-agent-event-ingress-20260814/idempotency-and-replay-contract.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
