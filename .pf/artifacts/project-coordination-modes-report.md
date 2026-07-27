# Project Coordination Modes Report

Timestamp: 2026-07-27T10:06:00+04:00
Agent/role: main implementation agent
Task: `задания/processforge_project_level_coordination_modes_master_prompt.md`
Status: delivered and validated

## Scope

Implemented project-level coordination modes for ProcessForge so one workplace can provide Director capability while each project resolves its own effective coordination mode.

## Workplace vs Project Hierarchy

- Workplace owns shared capability: Agent Ledger, registries, runtime drivers, Director Office capability, Director mailbox capability, default project mode, and error workflow support.
- Workplace config now carries `coordination.director_enabled`, `coordination.director_office_enabled`, `coordination.default_project_mode`, and Director Office paths.
- Project config now carries `coordination.mode` with `inherit`, `simple`, or `organized`.
- `inherit` resolves through the workplace `default_project_mode`; explicit `simple` and `organized` remain project-local choices.

## Mode Resolution

Resolution is centralized in the project coordination helpers used by:

- `project-mode status`
- `project-mode set`
- `project-mode doctor`
- `doctor-project`
- `project-context-refresh`
- `assignment-capsule`
- `process-doctor`
- `director-inbox-submit`
- `director-case-refresh`
- `error-route`

Expected behavior:

- `project.coordination.mode=simple` makes the project simple even when workplace Director is enabled.
- `project.coordination.mode=organized` requires workplace Director capability and Director Office availability.
- `project.coordination.mode=inherit` follows `workplace.coordination.default_project_mode`.

## Simple and Organized Coexistence

The smoke suite proves that a single workplace can host:

- project A in effective `organized` mode;
- project B in effective `simple` mode;
- project B switched to `organized` and back to `simple` without disabling workplace Director capability.

Simple project mode remains usable for single-agent 1-1-1-1 workflows while the same workplace has an active Director Office for organized projects.

## Director Office Behavior

Director Office remains workplace-level:

- `.pf/director`
- `.pf/director/inbox`
- `.pf/director/outbox`
- `.pf/director/cases`
- `.pf/director/history`
- `.pf/director/runtime`

No per-project Director Office is created by default. Director cases are keyed under the workplace office by project id and are only refreshed for organized projects unless simple inclusion is explicitly requested.

## Director Inbox Behavior

`director-inbox-submit` now respects effective project mode:

- organized project worker reports are accepted;
- simple project worker reports fail with a clear message and do not write Director inbox messages by default;
- workspace-level/operator-note submission remains available when appropriate.

The failure path points to `project-mode set --mode organized` instead of implying workplace-level Director enablement is enough.

## Snapshot and Capsule Differences

Project snapshots now include `workplace_coordination`.

For effective `simple` projects:

- `effective_mode: simple`
- `director_required: false`
- Director may be available at workplace level without becoming a project obligation.

For effective `organized` projects:

- `effective_mode: organized`
- `director_required: true`
- Director process and inbox submit metadata are included.

Assignment capsules use the same resolver. Simple capsules omit Director inbox obligations, while organized capsules include Director inbox metadata when the process requires or supports it.

## Process Authoring Changes

Process authoring answers, templates, docs, prompts, and generated process output now capture:

- `coordination_requirements.mode`: `simple_allowed`, `organized_required`, or `organized_optional`;
- Director inbox required/optional behavior;
- `error_handling.mode`: `none`, `director_inbox`, `route_to_process`, or `needs_operator`;
- `fallback_if_no_director`: `needs_operator` or `fail_validation`.

Validation rejects processes that require Director inbox while claiming `simple_allowed`, and `process-doctor` blocks `organized_required` processes in effective simple projects unless `--force` is used.

## Error Workflow Behavior

`error-route` now respects effective project mode:

- organized projects with `mode=director_inbox` write `error_report` messages to Director inbox;
- simple projects with Director inbox mode and fallback `needs_operator` record an operator-needed outcome instead of writing to Director;
- simple projects with `route_to_process` can route errors through process routes without requiring Director.

## Public Boundary

Public release includes schemas, templates, docs, prompts, process definitions, CLI code, and deterministic smokes.

Generated state remains outside the archive:

- `.pf/runtime`
- `.pf/artifacts`
- `.pf/handoffs`
- `.pf/contexts`
- `.pf/runs`
- `.pf/assignments`
- `.pf/dogfooding`
- workplace Director generated inbox, history, runtime, and case data

No `.ps1` files were added. No real external agent ecosystem built-ins were added.

## Tests Run

Targeted:

- `python tools/smoke_project_coordination_modes.py`
- `python tools/smoke_mixed_workplace_projects.py`
- `python tools/smoke_worker_awareness_of_director.py`
- `python tools/smoke_error_workflow.py`
- `python tools/smoke_agent_ledger.py`
- `python tools/smoke_agent_director_tick.py`
- `python tools/smoke_process_transition_handoff.py`
- `python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`

Existing public:

- `python tools/smoke_first_run.py`
- `python tools/smoke_process_run_task_batch.py`
- `python tools/smoke_runtime_driver_registry.py`
- `python tools/smoke_worker_run_shell.py`
- `python tools/smoke_process_supervisor_tick.py`
- `python tools/smoke_config_behavior_contracts.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`

Release:

- `python bin/pf.py release-test --root . --only smoke_project_coordination_modes --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --only smoke_mixed_workplace_projects --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --only smoke_worker_awareness_of_director --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --only smoke_error_workflow --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --public --timeout-scale 1`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`
- clean extracted archive targeted smokes
- clean extracted archive `python bin/pf.py release-test --root <extract> --public --fail-fast --timeout-scale 1`
- `git diff --check`

## Result

All acceptance criteria are covered by implementation and validation. The clean extracted archive public gate returned `PASS with warnings` only because the extracted temporary directory is not a git repository, so `git diff --check` is skipped there.
